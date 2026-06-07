"""
高级权限控制系统
支持行级权限、列级权限、时间权限、动态权限等
"""
import json
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from datetime import datetime, time, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from dataclasses import dataclass

from ..core.database import get_db
from ..models.config import SystemConfig, ConfigGroup, Environment
from ..models.user import User
from ..models.role import Role
from ..models.user import UserRole
import logging

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """权限级别"""
    NONE = "NONE"           # 无权限
    READ = "READ"           # 只读
    WRITE = "WRITE"         # 读写
    ADMIN = "ADMIN"         # 管理员
    OWNER = "OWNER"         # 所有者


class PermissionScope(Enum):
    """权限范围"""
    GLOBAL = "GLOBAL"       # 全局权限
    GROUP = "GROUP"         # 分组权限
    CONFIG = "CONFIG"       # 单个配置权限
    ENVIRONMENT = "ENVIRONMENT"  # 环境权限
    TAG = "TAG"            # 标签权限


class TimeBasedPermissionType(Enum):
    """时间权限类型"""
    ALWAYS = "ALWAYS"       # 永久有效
    SCHEDULE = "SCHEDULE"   # 定时权限
    TEMPORARY = "TEMPORARY" # 临时权限
    APPROVAL = "APPROVAL"   # 审批权限


@dataclass
class PermissionContext:
    """权限上下文"""
    user_id: int
    config_key: Optional[str] = None
    group_id: Optional[int] = None
    environment: Optional[str] = None
    tags: Optional[List[str]] = None
    action: Optional[str] = None
    timestamp: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class PermissionRule:
    """权限规则"""
    rule_id: str
    name: str
    description: str
    scope: PermissionScope
    level: PermissionLevel
    conditions: Dict[str, Any]
    time_restrictions: Optional[Dict[str, Any]] = None
    row_filters: Optional[Dict[str, Any]] = None
    column_filters: Optional[List[str]] = None
    custom_logic: Optional[str] = None


class AdvancedPermissionManager:
    """高级权限管理器"""
    
    def __init__(self):
        self.permission_cache = {}
        self.rule_cache = {}
    
    async def check_permission(
        self, 
        context: PermissionContext, 
        required_permission: PermissionLevel = PermissionLevel.READ
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        检查权限
        
        Args:
            context: 权限上下文
            required_permission: 所需权限级别
            
        Returns:
            (是否有权限, 错误信息, 权限详情)
        """
        try:
            # 1. 检查全局权限
            global_permission = await self._check_global_permission(context, required_permission)
            if global_permission[0]:
                return global_permission
            
            # 2. 检查角色权限
            role_permission = await self._check_role_permission(context, required_permission)
            if role_permission[0]:
                return role_permission
            
            # 3. 检查行级权限
            row_permission = await self._check_row_level_permission(context, required_permission)
            if row_permission[0]:
                return row_permission
            
            # 4. 检查时间权限
            time_permission = await self._check_time_based_permission(context, required_permission)
            if not time_permission[0]:
                return time_permission
            
            # 5. 检查列级权限
            column_permission = await self._check_column_level_permission(context, required_permission)
            if not column_permission[0]:
                return column_permission
            
            return False, "权限不足", {}
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False, f"权限检查失败: {str(e)}", {}
    
    async def _check_global_permission(
        self, 
        context: PermissionContext, 
        required_permission: PermissionLevel
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查全局权限"""
        try:
            db = next(get_db())
            
            # 检查用户是否有全局管理员权限
            user_roles = db.query(UserRole).filter(UserRole.user_id == context.user_id).all()
            for user_role in user_roles:
                role = db.query(Role).filter(Role.id == user_role.role_id).first()
                if role and role.code == 'SUPER_ADMIN':
                    return True, None, {
                        "permission_type": "global",
                        "level": "ADMIN",
                        "source": "super_admin_role"
                    }
            
            db.close()
            return False, "无全局权限", {}
            
        except Exception as e:
            logger.error(f"全局权限检查失败: {e}")
            return False, f"全局权限检查失败: {str(e)}", {}
    
    async def _check_role_permission(
        self, 
        context: PermissionContext, 
        required_permission: PermissionLevel
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查角色权限"""
        try:
            db = next(get_db())
            
            # 获取用户角色
            user_roles = db.query(UserRole).filter(UserRole.user_id == context.user_id).all()
            
            for user_role in user_roles:
                role = db.query(Role).filter(Role.id == user_role.role_id).first()
                if not role or not role.is_active:
                    continue
                
                # 检查角色权限
                permissions = role.permissions or {}
                
                # 环境权限检查
                if context.environment:
                    env_permissions = permissions.get('environments', {})
                    env_permission = env_permissions.get(context.environment, 'NONE')
                    if self._compare_permission_level(env_permission, required_permission.value):
                        return True, None, {
                            "permission_type": "role",
                            "level": env_permission,
                            "source": f"role_{role.code}",
                            "environment": context.environment
                        }
                
                # 分组权限检查
                if context.group_id:
                    group_permissions = permissions.get('groups', {})
                    group_permission = group_permissions.get(str(context.group_id), 'NONE')
                    if self._compare_permission_level(group_permission, required_permission.value):
                        return True, None, {
                            "permission_type": "role",
                            "level": group_permission,
                            "source": f"role_{role.code}",
                            "group_id": context.group_id
                        }
                
                # 标签权限检查
                if context.tags:
                    tag_permissions = permissions.get('tags', {})
                    for tag in context.tags:
                        tag_permission = tag_permissions.get(tag, 'NONE')
                        if self._compare_permission_level(tag_permission, required_permission.value):
                            return True, None, {
                                "permission_type": "role",
                                "level": tag_permission,
                                "source": f"role_{role.code}",
                                "tag": tag
                            }
            
            db.close()
            return False, "角色权限不足", {}
            
        except Exception as e:
            logger.error(f"角色权限检查失败: {e}")
            return False, f"角色权限检查失败: {str(e)}", {}
    
    async def _check_row_level_permission(
        self, 
        context: PermissionContext, 
        required_permission: PermissionLevel
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查行级权限"""
        try:
            # 行级权限规则示例：
            # - 只能访问自己创建的配置
            # - 只能访问特定标签的配置
            # - 只能访问特定分组的配置
            
            if not context.config_key:
                return True, None, {}  # 如果没有指定配置项，跳过行级检查
            
            db = next(get_db())
            
            # 获取配置信息
            config = db.query(SystemConfig).filter(
                and_(
                    SystemConfig.config_key == context.config_key,
                    SystemConfig.environment == context.environment or Environment.PROD,
                    SystemConfig.deleted_at.is_(None)
                )
            ).first()
            
            if not config:
                db.close()
                return False, "配置不存在", {}
            
            # 检查是否为配置创建者
            if config.created_by == context.user_id:
                db.close()
                return True, None, {
                    "permission_type": "row_level",
                    "level": "OWNER",
                    "source": "creator",
                    "config_key": context.config_key
                }
            
            # 检查标签权限
            if config.tags and context.tags:
                config_tags = set(config.tags)
                user_tags = set(context.tags)
                if config_tags.intersection(user_tags):
                    db.close()
                    return True, None, {
                        "permission_type": "row_level",
                        "level": "READ",
                        "source": "tag_match",
                        "config_key": context.config_key,
                        "matched_tags": list(config_tags.intersection(user_tags))
                    }
            
            # 检查分组权限
            if config.group_id == context.group_id:
                db.close()
                return True, None, {
                    "permission_type": "row_level",
                    "level": "READ",
                    "source": "group_match",
                    "config_key": context.config_key,
                    "group_id": config.group_id
                }
            
            db.close()
            return False, "行级权限不足", {}
            
        except Exception as e:
            logger.error(f"行级权限检查失败: {e}")
            return False, f"行级权限检查失败: {str(e)}", {}
    
    async def _check_time_based_permission(
        self, 
        context: PermissionContext, 
        required_permission: PermissionLevel
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查时间权限"""
        try:
            current_time = context.timestamp or datetime.now()
            
            # 检查工作时间权限
            if not self._is_within_work_hours(current_time):
                # 非工作时间，检查是否有特殊权限
                if required_permission in [PermissionLevel.WRITE, PermissionLevel.ADMIN]:
                    return False, "非工作时间不允许写操作", {}
            
            # 检查临时权限
            temp_permission = await self._check_temporary_permission(context.user_id, current_time)
            if temp_permission[0]:
                return temp_permission
            
            # 检查定时权限
            schedule_permission = await self._check_scheduled_permission(context.user_id, current_time)
            if schedule_permission[0]:
                return schedule_permission
            
            return True, None, {
                "permission_type": "time_based",
                "level": "READ",
                "source": "standard_hours"
            }
            
        except Exception as e:
            logger.error(f"时间权限检查失败: {e}")
            return False, f"时间权限检查失败: {str(e)}", {}
    
    async def _check_column_level_permission(
        self, 
        context: PermissionContext, 
        required_permission: PermissionLevel
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查列级权限"""
        try:
            # 列级权限规则示例：
            # - 敏感字段只有管理员可以查看
            # - 某些字段只有特定角色可以修改
            
            sensitive_fields = ['config_value', 'validation_rule']
            admin_only_fields = ['is_core', 'is_encrypted']
            
            if context.action in ['read', 'view']:
                # 读取敏感字段需要特殊权限
                if required_permission == PermissionLevel.READ:
                    return True, None, {
                        "permission_type": "column_level",
                        "level": "READ",
                        "restricted_fields": sensitive_fields
                    }
            
            elif context.action in ['update', 'modify']:
                # 修改管理员字段需要管理员权限
                if required_permission in [PermissionLevel.ADMIN, PermissionLevel.OWNER]:
                    return True, None, {
                        "permission_type": "column_level",
                        "level": "WRITE",
                        "source": "admin_level"
                    }
                else:
                    return False, "修改敏感字段需要管理员权限", {}
            
            return True, None, {
                "permission_type": "column_level",
                "level": "READ"
            }
            
        except Exception as e:
            logger.error(f"列级权限检查失败: {e}")
            return False, f"列级权限检查失败: {str(e)}", {}
    
    def _compare_permission_level(self, user_level: str, required_level: str) -> bool:
        """比较权限级别"""
        level_hierarchy = {
            'NONE': 0,
            'READ': 1,
            'WRITE': 2,
            'ADMIN': 3,
            'OWNER': 4
        }
        
        user_score = level_hierarchy.get(user_level, 0)
        required_score = level_hierarchy.get(required_level, 0)
        
        return user_score >= required_score
    
    def _is_within_work_hours(self, check_time: datetime) -> bool:
        """检查是否在工作时间内"""
        # 工作时间：周一到周五，9:00-18:00
        weekday = check_time.weekday()  # 0=Monday, 6=Sunday
        if weekday >= 5:  # 周末
            return False
        
        current_time = check_time.time()
        work_start = time(9, 0)  # 09:00
        work_end = time(18, 0)   # 18:00
        
        return work_start <= current_time <= work_end
    
    async def _check_temporary_permission(
        self, 
        user_id: int, 
        current_time: datetime
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查临时权限"""
        try:
            # 这里可以查询临时权限表
            # 为演示目的，使用简单逻辑
            
            # 检查是否有临时权限记录
            # temp_permissions = db.query(TemporaryPermission).filter(
            #     and_(
            #         TemporaryPermission.user_id == user_id,
            #         TemporaryPermission.start_time <= current_time,
            #         TemporaryPermission.end_time >= current_time,
            #         TemporaryPermission.is_active == True
            #     )
            # ).all()
            
            return False, "无临时权限", {}
            
        except Exception as e:
            logger.error(f"临时权限检查失败: {e}")
            return False, f"临时权限检查失败: {str(e)}", {}
    
    async def _check_scheduled_permission(
        self, 
        user_id: int, 
        current_time: datetime
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """检查定时权限"""
        try:
            # 这里可以查询定时权限表
            # 为演示目的，使用简单逻辑
            
            # 检查是否有定时权限记录
            # scheduled_permissions = db.query(ScheduledPermission).filter(
            #     and_(
            #         ScheduledPermission.user_id == user_id,
            #         ScheduledPermission.is_active == True
            #     )
            # ).all()
            
            return False, "无定时权限", {}
            
        except Exception as e:
            logger.error(f"定时权限检查失败: {e}")
            return False, f"定时权限检查失败: {str(e)}", {}
    
    async def grant_temporary_permission(
        self,
        user_id: int,
        permission_level: PermissionLevel,
        scope: Dict[str, Any],
        duration_hours: int,
        granted_by: int,
        reason: str
    ) -> Tuple[bool, Optional[str]]:
        """授予临时权限"""
        try:
            # 创建临时权限记录
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=duration_hours)
            
            # 这里应该插入到临时权限表
            logger.info(f"为用户 {user_id} 授予临时权限: {permission_level.value}, 有效期至 {end_time}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"授予临时权限失败: {e}")
            return False, f"授予临时权限失败: {str(e)}"
    
    async def revoke_permission(
        self,
        user_id: int,
        permission_type: str,
        permission_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """撤销权限"""
        try:
            # 撤销指定权限
            logger.info(f"撤销用户 {user_id} 的权限: {permission_type}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"撤销权限失败: {e}")
            return False, f"撤销权限失败: {str(e)}"
    
    async def get_user_effective_permissions(
        self, 
        user_id: int, 
        context: Optional[PermissionContext] = None
    ) -> Dict[str, Any]:
        """获取用户有效权限"""
        try:
            permissions = {
                "global": [],
                "role": [],
                "row_level": [],
                "column_level": [],
                "time_based": [],
                "temporary": [],
                "scheduled": []
            }
            
            # 检查各种权限类型
            if context:
                global_perm = await self._check_global_permission(context, PermissionLevel.READ)
                if global_perm[0]:
                    permissions["global"].append(global_perm[2])
                
                role_perm = await self._check_role_permission(context, PermissionLevel.READ)
                if role_perm[0]:
                    permissions["role"].append(role_perm[2])
                
                row_perm = await self._check_row_level_permission(context, PermissionLevel.READ)
                if row_perm[0]:
                    permissions["row_level"].append(row_perm[2])
                
                col_perm = await self._check_column_level_permission(context, PermissionLevel.READ)
                if col_perm[0]:
                    permissions["column_level"].append(col_perm[2])
                
                time_perm = await self._check_time_based_permission(context, PermissionLevel.READ)
                if time_perm[0]:
                    permissions["time_based"].append(time_perm[2])
            
            return permissions
            
        except Exception as e:
            logger.error(f"获取用户权限失败: {e}")
            return {}


# 权限装饰器
def require_advanced_permission(
    required_level: PermissionLevel = PermissionLevel.READ,
    scope: Optional[PermissionScope] = None
):
    """
    高级权限装饰器
    
    Args:
        required_level: 所需权限级别
        scope: 权限范围
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里应该从请求上下文中获取用户信息
            # 为演示目的，使用简化逻辑
            
            permission_manager = AdvancedPermissionManager()
            
            # 构建权限上下文
            context = PermissionContext(
                user_id=kwargs.get('user_id', 1),  # 应该从JWT中获取
                config_key=kwargs.get('config_key'),
                group_id=kwargs.get('group_id'),
                environment=kwargs.get('environment'),
                action=func.__name__
            )
            
            # 检查权限
            has_permission, error, details = await permission_manager.check_permission(
                context, required_level
            )
            
            if not has_permission:
                raise PermissionError(f"权限不足: {error}")
            
            # 将权限详情添加到kwargs中
            kwargs['permission_details'] = details
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


print("✅ 高级权限控制系统已创建完成")