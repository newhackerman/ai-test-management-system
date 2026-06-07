"""
配置权限管理服务
"""
import json
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..models.config import (
    ConfigPermission, SystemConfig, ConfigGroup, Environment, 
    PermissionType, PermissionAction
)
from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import Permission, RolePermission
from ..utils.config_cache import config_cache_service
import logging

logger = logging.getLogger(__name__)


class ConfigPermissionService:
    """配置权限管理服务"""
    
    def __init__(self):
        self.cache_service = config_cache_service
    
    # === 权限检查 ===
    
    async def check_config_permission(self, user_id: int, config_key: str, 
                                    environment: Environment, action: PermissionAction) -> bool:
        """
        检查用户对配置的权限
        
        Args:
            user_id: 用户ID
            config_key: 配置键
            environment: 环境
            action: 操作类型
            
        Returns:
            是否有权限
        """
        try:
            # 先从缓存获取
            cache_key = f"config_permission:{user_id}:{config_key}:{environment.value}:{action.value}"
            cached_result = self.cache_service.redis.get(cache_key)
            
            if cached_result is not None:
                return bool(cached_result)
            
            db = next(get_db())
            try:
                # 检查是否是超级管理员
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                # 超级管理员有所有权限
                if user.is_superuser:
                    self.cache_service.redis.set(cache_key, True, expire=300)
                    return True
                
                # 检查用户是否被禁用
                if not user.is_active:
                    self.cache_service.redis.set(cache_key, False, expire=300)
                    return False
                
                # 获取配置信息
                config = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.config_key == config_key,
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).first()
                
                if not config:
                    return False
                
                # 检查具体的配置权限
                has_permission = await self._check_user_config_access(
                    user_id, config, action, db
                )
                
                # 缓存结果
                self.cache_service.redis.set(cache_key, has_permission, expire=300)
                
                return has_permission
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"检查配置权限失败: {e}")
            return False
    
    async def _check_user_config_access(self, user_id: int, config: SystemConfig,
                                      action: PermissionAction, db: Session) -> bool:
        """检查用户对特定配置的访问权限"""
        try:
            # 1. 检查直接的配置权限
            direct_permission = db.query(ConfigPermission).filter(
                and_(
                    ConfigPermission.user_id == user_id,
                    ConfigPermission.config_id == config.id,
                    ConfigPermission.permission_type == PermissionType.CONFIG,
                    ConfigPermission.actions.contains([action.value]),
                    ConfigPermission.deleted_at.is_(None)
                )
            ).first()
            
            if direct_permission:
                return True
            
            # 2. 检查分组权限
            if config.group_id:
                group_permission = db.query(ConfigPermission).filter(
                    and_(
                        ConfigPermission.user_id == user_id,
                        ConfigPermission.group_id == config.group_id,
                        ConfigPermission.permission_type == PermissionType.GROUP,
                        ConfigPermission.actions.contains([action.value]),
                        ConfigPermission.deleted_at.is_(None)
                    )
                ).first()
                
                if group_permission:
                    return True
            
            # 3. 检查环境权限
            env_permission = db.query(ConfigPermission).filter(
                and_(
                    ConfigPermission.user_id == user_id,
                    ConfigPermission.environment == config.environment,
                    ConfigPermission.permission_type == PermissionType.ENVIRONMENT,
                    ConfigPermission.actions.contains([action.value]),
                    ConfigPermission.deleted_at.is_(None)
                )
            ).first()
            
            if env_permission:
                return True
            
            # 4. 检查角色权限
            user_roles = db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.deleted_at.is_(None)
                )
            ).all()
            
            for user_role in user_roles:
                # 检查角色是否有配置管理权限
                role_permissions = db.query(RolePermission).join(Permission).filter(
                    and_(
                        RolePermission.role_id == user_role.role_id,
                        Permission.code.in_([
                            f'config:{action.value}',
                            f'config:{config.environment.value}:{action.value}',
                            'config:manage:all'
                        ]),
                        RolePermission.deleted_at.is_(None),
                        Permission.deleted_at.is_(None)
                    )
                ).first()
                
                if role_permissions:
                    return True
            
            # 5. 检查全局权限（仅限读取）
            if action == PermissionAction.READ:
                global_permission = db.query(ConfigPermission).filter(
                    and_(
                        ConfigPermission.user_id == user_id,
                        ConfigPermission.permission_type == PermissionType.GLOBAL,
                        ConfigPermission.actions.contains([action.value]),
                        ConfigPermission.deleted_at.is_(None)
                    )
                ).first()
                
                if global_permission:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查用户配置访问权限失败: {e}")
            return False
    
    async def check_batch_config_permission(self, user_id: int, config_keys: List[str],
                                          environment: Environment, 
                                          action: PermissionAction) -> Dict[str, bool]:
        """
        批量检查配置权限
        
        Args:
            user_id: 用户ID
            config_keys: 配置键列表
            environment: 环境
            action: 操作类型
            
        Returns:
            配置键与权限的映射
        """
        results = {}
        
        for config_key in config_keys:
            try:
                has_permission = await self.check_config_permission(
                    user_id, config_key, environment, action
                )
                results[config_key] = has_permission
            except Exception as e:
                logger.error(f"检查配置权限失败: {config_key}, 错误: {e}")
                results[config_key] = False
        
        return results
    
    # === 权限管理 ===
    
    async def grant_config_permission(self, user_id: int, target_user_id: int,
                                    permission_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        授予配置权限
        
        Args:
            user_id: 操作用户ID
            target_user_id: 目标用户ID
            permission_data: 权限数据
            
        Returns:
            (是否成功, 错误信息, 权限数据)
        """
        try:
            # 检查操作权限
            has_permission = await self.check_permission_management_access(user_id)
            if not has_permission:
                return False, "无权限进行权限管理", None
            
            db = next(get_db())
            try:
                # 验证目标用户存在
                target_user = db.query(User).filter(User.id == target_user_id).first()
                if not target_user:
                    return False, "目标用户不存在", None
                
                # 创建权限记录
                permission = ConfigPermission(
                    user_id=target_user_id,
                    permission_type=PermissionType(permission_data["permission_type"]),
                    config_id=permission_data.get("config_id"),
                    group_id=permission_data.get("group_id"),
                    environment=Environment(permission_data["environment"]) if permission_data.get("environment") else None,
                    actions=permission_data["actions"],
                    granted_by=user_id,
                    expires_at=permission_data.get("expires_at"),
                    created_by=user_id,
                    updated_by=user_id
                )
                
                db.add(permission)
                db.commit()
                db.refresh(permission)
                
                # 清理相关缓存
                self._clear_user_permission_cache(target_user_id)
                
                permission_dict = self._permission_to_dict(permission)
                logger.info(f"授予配置权限成功: 用户{target_user_id}")
                
                return True, None, permission_dict
                
            except IntegrityError as e:
                db.rollback()
                return False, "权限已存在", None
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"授予配置权限失败: {e}")
            return False, f"授予权限失败: {str(e)}", None
    
    async def revoke_config_permission(self, user_id: int, permission_id: int) -> Tuple[bool, Optional[str]]:
        """
        撤销配置权限
        
        Args:
            user_id: 操作用户ID
            permission_id: 权限ID
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 检查操作权限
            has_permission = await self.check_permission_management_access(user_id)
            if not has_permission:
                return False, "无权限进行权限管理"
            
            db = next(get_db())
            try:
                permission = db.query(ConfigPermission).filter(
                    and_(
                        ConfigPermission.id == permission_id,
                        ConfigPermission.deleted_at.is_(None)
                    )
                ).first()
                
                if not permission:
                    return False, "权限不存在"
                
                # 软删除
                permission.soft_delete()
                permission.updated_by = user_id
                
                db.commit()
                
                # 清理相关缓存
                self._clear_user_permission_cache(permission.user_id)
                
                logger.info(f"撤销配置权限成功: 权限{permission_id}")
                return True, None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"撤销配置权限失败: {e}")
            return False, f"撤销权限失败: {str(e)}"
    
    async def get_user_config_permissions(self, user_id: int, target_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取用户的配置权限列表
        
        Args:
            user_id: 操作用户ID
            target_user_id: 目标用户ID，None表示查询自己的权限
            
        Returns:
            权限列表
        """
        try:
            query_user_id = target_user_id if target_user_id else user_id
            
            # 如果查询其他用户的权限，需要检查权限
            if target_user_id and target_user_id != user_id:
                has_permission = await self.check_permission_management_access(user_id)
                if not has_permission:
                    return []
            
            db = next(get_db())
            try:
                permissions = db.query(ConfigPermission).filter(
                    and_(
                        ConfigPermission.user_id == query_user_id,
                        ConfigPermission.deleted_at.is_(None)
                    )
                ).order_by(ConfigPermission.created_at.desc()).all()
                
                return [self._permission_to_dict(perm) for perm in permissions]
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取用户配置权限失败: {e}")
            return []
    
    async def check_permission_management_access(self, user_id: int) -> bool:
        """检查用户是否有权限管理权限"""
        try:
            db = next(get_db())
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                # 超级管理员有所有权限
                if user.is_superuser:
                    return True
                
                # 检查是否有权限管理角色
                user_roles = db.query(UserRole).join(Role).filter(
                    and_(
                        UserRole.user_id == user_id,
                        Role.code.in_(['admin', 'permission_manager']),
                        UserRole.deleted_at.is_(None),
                        Role.deleted_at.is_(None)
                    )
                ).first()
                
                return user_roles is not None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"检查权限管理权限失败: {e}")
            return False
    
    # === 权限查询和统计 ===
    
    async def get_config_access_users(self, config_key: str, environment: Environment) -> List[Dict[str, Any]]:
        """
        获取有权限访问指定配置的用户列表
        
        Args:
            config_key: 配置键
            environment: 环境
            
        Returns:
            用户列表
        """
        try:
            db = next(get_db())
            try:
                # 获取配置信息
                config = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.config_key == config_key,
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).first()
                
                if not config:
                    return []
                
                users = []
                
                # 1. 直接的配置权限
                direct_users = db.query(User).join(ConfigPermission).filter(
                    and_(
                        ConfigPermission.config_id == config.id,
                        ConfigPermission.permission_type == PermissionType.CONFIG,
                        ConfigPermission.deleted_at.is_(None),
                        User.deleted_at.is_(None),
                        User.is_active == True
                    )
                ).all()
                
                users.extend([{
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "permission_source": "直接权限"
                } for user in direct_users])
                
                # 2. 分组权限
                if config.group_id:
                    group_users = db.query(User).join(ConfigPermission).filter(
                        and_(
                            ConfigPermission.group_id == config.group_id,
                            ConfigPermission.permission_type == PermissionType.GROUP,
                            ConfigPermission.deleted_at.is_(None),
                            User.deleted_at.is_(None),
                            User.is_active == True
                        )
                    ).all()
                    
                    users.extend([{
                        "user_id": user.id,
                        "username": user.username,
                        "full_name": user.full_name,
                        "permission_source": "分组权限"
                    } for user in group_users])
                
                # 3. 环境权限
                env_users = db.query(User).join(ConfigPermission).filter(
                    and_(
                        ConfigPermission.environment == environment,
                        ConfigPermission.permission_type == PermissionType.ENVIRONMENT,
                        ConfigPermission.deleted_at.is_(None),
                        User.deleted_at.is_(None),
                        User.is_active == True
                    )
                ).all()
                
                users.extend([{
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "permission_source": "环境权限"
                } for user in env_users])
                
                # 4. 超级管理员
                superusers = db.query(User).filter(
                    and_(
                        User.is_superuser == True,
                        User.is_active == True,
                        User.deleted_at.is_(None)
                    )
                ).all()
                
                users.extend([{
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "permission_source": "超级管理员"
                } for user in superusers])
                
                # 去重
                seen = set()
                unique_users = []
                for user in users:
                    if user['user_id'] not in seen:
                        seen.add(user['user_id'])
                        unique_users.append(user)
                
                return unique_users
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取配置访问用户失败: {e}")
            return []
    
    async def get_permission_statistics(self, environment: Optional[Environment] = None) -> Dict[str, Any]:
        """
        获取权限统计信息
        
        Args:
            environment: 环境过滤
            
        Returns:
            统计信息
        """
        try:
            db = next(get_db())
            try:
                stats = {}
                
                # 总权限数
                query = db.query(ConfigPermission).filter(
                    ConfigPermission.deleted_at.is_(None)
                )
                
                if environment:
                    query = query.filter(ConfigPermission.environment == environment)
                
                total_permissions = query.count()
                stats['total_permissions'] = total_permissions
                
                # 按类型统计
                type_stats = {}
                for perm_type in PermissionType:
                    count = query.filter(
                        ConfigPermission.permission_type == perm_type
                    ).count()
                    type_stats[perm_type.value] = count
                
                stats['permission_by_type'] = type_stats
                
                # 按操作统计
                action_stats = {}
                for action in PermissionAction:
                    count = query.filter(
                        ConfigPermission.actions.contains([action.value])
                    ).count()
                    action_stats[action.value] = count
                
                stats['permission_by_action'] = action_stats
                
                # 有权限的用户数
                unique_users = query.distinct(ConfigPermission.user_id).count()
                stats['users_with_permissions'] = unique_users
                
                # 即将过期的权限数
                from datetime import datetime, timedelta
                expiring_soon = query.filter(
                    and_(
                        ConfigPermission.expires_at.is_not(None),
                        ConfigPermission.expires_at <= datetime.utcnow() + timedelta(days=7)
                    )
                ).count()
                stats['expiring_permissions'] = expiring_soon
                
                return stats
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取权限统计失败: {e}")
            return {}
    
    # === 辅助方法 ===
    
    def _permission_to_dict(self, permission: ConfigPermission) -> Dict[str, Any]:
        """将权限模型转换为字典"""
        return {
            "id": permission.id,
            "user_id": permission.user_id,
            "permission_type": permission.permission_type.value,
            "config_id": permission.config_id,
            "group_id": permission.group_id,
            "environment": permission.environment.value if permission.environment else None,
            "actions": permission.actions,
            "granted_by": permission.granted_by,
            "expires_at": permission.expires_at.isoformat() if permission.expires_at else None,
            "created_at": permission.created_at.isoformat() if permission.created_at else None,
            "updated_at": permission.updated_at.isoformat() if permission.updated_at else None
        }
    
    def _clear_user_permission_cache(self, user_id: int):
        """清理用户权限缓存"""
        try:
            # 清理权限缓存
            self.cache_service.delete_user_permissions(user_id)
            
            # 清理配置权限缓存
            pattern = f"config_permission:{user_id}:*"
            keys = self.cache_service.redis.keys(pattern)
            for key in keys:
                self.cache_service.redis.delete(key)
                
        except Exception as e:
            logger.error(f"清理用户权限缓存失败: {e}")
    
    # === 权限审核 ===
    
    async def submit_permission_request(self, user_id: int, request_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        提交权限申请
        
        Args:
            user_id: 申请用户ID
            request_data: 申请数据
            
        Returns:
            (是否成功, 错误信息, 申请数据)
        """
        try:
            import time
            db = next(get_db())
            try:
                # 这里可以创建权限申请记录
                # 实际实现中可能需要单独的权限申请表
                
                logger.info(f"用户{user_id}提交权限申请")
                
                # 发送通知给管理员
                # 这里可以集成消息通知服务
                
                return True, None, {"request_id": f"req_{user_id}_{int(time.time())}"}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"提交权限申请失败: {e}")
            return False, f"提交申请失败: {str(e)}", None

# 全局配置权限服务实例
config_permission_service = ConfigPermissionService()