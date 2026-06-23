"""
环境管理服务
"""
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..models.config import (
    SystemEnvironment, SystemConfig, ConfigGroup, Environment, ConfigType
)
from ..utils.config_cache import config_cache_service, NotificationType
from ..schemas.config import ConfigResponse
import logging

logger = logging.getLogger(__name__)


class EnvironmentService:
    """环境管理服务"""
    
    def __init__(self):
        self.cache_service = config_cache_service
    
    # === 环境管理 ===
    
    async def get_environments(self) -> List[Dict[str, Any]]:
        """
        获取所有环境信息
        
        Returns:
            环境列表
        """
        try:
            db = next(get_db())
            try:
                environments = db.query(SystemEnvironment).filter(
                    SystemEnvironment.deleted_at.is_(None)
                ).order_by(SystemEnvironment.sort_order.asc()).all()
                
                return [self._environment_to_dict(env) for env in environments]
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取环境列表失败: {e}")
            return []
    
    async def get_environment(self, env_code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个环境信息
        
        Args:
            env_code: 环境代码
            
        Returns:
            环境信息
        """
        try:
            db = next(get_db())
            try:
                environment = db.query(SystemEnvironment).filter(
                    and_(
                        SystemEnvironment.env_code == env_code,
                        SystemEnvironment.deleted_at.is_(None)
                    )
                ).first()
                
                if not environment:
                    return None
                
                return self._environment_to_dict(environment)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取环境信息失败: {env_code}, 错误: {e}")
            return None
    
    async def create_environment(self, env_data: Dict[str, Any], operator_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        创建环境
        
        Args:
            env_data: 环境数据
            operator_id: 操作人ID
            
        Returns:
            (是否成功, 错误信息, 环境数据)
        """
        try:
            db = next(get_db())
            try:
                # 检查环境代码是否已存在
                existing = db.query(SystemEnvironment).filter(
                    and_(
                        SystemEnvironment.env_code == env_data["env_code"],
                        SystemEnvironment.deleted_at.is_(None)
                    )
                ).first()
                
                if existing:
                    return False, "环境代码已存在", None
                
                # 创建环境
                environment = SystemEnvironment(
                    env_code=env_data["env_code"],
                    env_name=env_data["env_name"],
                    description=env_data.get("description"),
                    is_active=env_data.get("is_active", True),
                    sort_order=env_data.get("sort_order", 0),
                    config_data=env_data.get("config_data", {}),
                    created_by=operator_id,
                    updated_by=operator_id
                )
                
                db.add(environment)
                db.commit()
                db.refresh(environment)
                
                # 清理缓存
                self.cache_service.clear_environment_cache()
                
                env_dict = self._environment_to_dict(environment)
                logger.info(f"创建环境成功: {environment.env_code}")
                
                return True, None, env_dict
                
            except IntegrityError as e:
                db.rollback()
                return False, "数据库约束错误", None
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"创建环境失败: {e}")
            return False, f"创建环境失败: {str(e)}", None
    
    async def update_environment(self, env_code: str, env_data: Dict[str, Any], 
                               operator_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        更新环境
        
        Args:
            env_code: 环境代码
            env_data: 环境数据
            operator_id: 操作人ID
            
        Returns:
            (是否成功, 错误信息, 环境数据)
        """
        try:
            db = next(get_db())
            try:
                environment = db.query(SystemEnvironment).filter(
                    and_(
                        SystemEnvironment.env_code == env_code,
                        SystemEnvironment.deleted_at.is_(None)
                    )
                ).first()
                
                if not environment:
                    return False, "环境不存在", None
                
                # 更新字段
                if "env_name" in env_data:
                    environment.env_name = env_data["env_name"]
                if "description" in env_data:
                    environment.description = env_data["description"]
                if "is_active" in env_data:
                    environment.is_active = env_data["is_active"]
                if "sort_order" in env_data:
                    environment.sort_order = env_data["sort_order"]
                if "config_data" in env_data:
                    environment.config_data = env_data["config_data"]
                
                environment.updated_by = operator_id
                environment.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(environment)
                
                # 清理缓存
                self.cache_service.clear_environment_cache()
                
                env_dict = self._environment_to_dict(environment)
                logger.info(f"更新环境成功: {environment.env_code}")
                
                return True, None, env_dict
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"更新环境失败: {e}")
            return False, f"更新环境失败: {str(e)}", None
    
    async def delete_environment(self, env_code: str, operator_id: int, 
                               hard_delete: bool = False) -> Tuple[bool, Optional[str]]:
        """
        删除环境
        
        Args:
            env_code: 环境代码
            operator_id: 操作人ID
            hard_delete: 是否硬删除
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            db = next(get_db())
            try:
                environment = db.query(SystemEnvironment).filter(
                    and_(
                        SystemEnvironment.env_code == env_code,
                        SystemEnvironment.deleted_at.is_(None)
                    )
                ).first()
                
                if not environment:
                    return False, "环境不存在"
                
                # 检查是否有配置使用此环境
                env_enum = Environment(env_code)
                config_count = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == env_enum,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).count()
                
                if config_count > 0:
                    return False, f"该环境下还有{config_count}个配置，无法删除"
                
                if hard_delete:
                    # 硬删除
                    db.delete(environment)
                else:
                    # 软删除
                    environment.soft_delete()
                    environment.updated_by = operator_id
                
                db.commit()
                
                # 清理缓存
                self.cache_service.clear_environment_cache()
                
                logger.info(f"删除环境成功: {environment.env_code}")
                return True, None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"删除环境失败: {e}")
            return False, f"删除环境失败: {str(e)}"
    
    # === 环境配置同步 ===
    
    async def sync_configs_between_environments(self, source_env: Environment, 
                                              target_env: Environment,
                                              config_keys: Optional[List[str]] = None,
                                              operator_id: int = None) -> Tuple[bool, str, Dict]:
        """
        在不同环境间同步配置
        
        Args:
            source_env: 源环境
            target_env: 目标环境
            config_keys: 要同步的配置键列表，为空时同步所有
            operator_id: 操作人ID
            
        Returns:
            (是否成功, 消息, 同步结果)
        """
        try:
            db = next(get_db())
            try:
                # 构建查询条件
                query = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == source_env,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.is_enabled == True
                    )
                )
                
                if config_keys:
                    query = query.filter(SystemConfig.config_key.in_(config_keys))
                
                source_configs = query.all()
                
                if not source_configs:
                    return False, "源环境中没有找到匹配的配置", {}
                
                success_count = 0
                failed_count = 0
                updated_count = 0
                created_count = 0
                errors = []
                
                for source_config in source_configs:
                    try:
                        # 查找目标环境中的配置
                        target_config = db.query(SystemConfig).filter(
                            and_(
                                SystemConfig.config_key == source_config.config_key,
                                SystemConfig.environment == target_env,
                                SystemConfig.deleted_at.is_(None)
                            )
                        ).first()
                        
                        if target_config:
                            # 更新现有配置
                            target_config.config_value = source_config.config_value
                            target_config.config_type = source_config.config_type
                            target_config.description = source_config.description
                            target_config.default_value = source_config.default_value
                            target_config.example_value = source_config.example_value
                            target_config.validation_rule = source_config.validation_rule
                            target_config.is_core = source_config.is_core
                            target_config.is_encrypted = source_config.is_encrypted
                            target_config.is_required = source_config.is_required
                            target_config.tags = source_config.tags
                            target_config.updated_by = operator_id
                            target_config.updated_at = datetime.utcnow()
                            updated_count += 1
                        else:
                            # 创建新配置
                            new_config = SystemConfig(
                                config_key=source_config.config_key,
                                config_value=source_config.config_value,
                                config_type=source_config.config_type,
                                group_id=source_config.group_id,
                                environment=target_env,
                                description=source_config.description,
                                default_value=source_config.default_value,
                                example_value=source_config.example_value,
                                validation_rule=source_config.validation_rule,
                                is_core=source_config.is_core,
                                is_enabled=source_config.is_enabled,
                                is_encrypted=source_config.is_encrypted,
                                is_required=source_config.is_required,
                                tags=source_config.tags,
                                sort_order=source_config.sort_order,
                                created_by=operator_id,
                                updated_by=operator_id
                            )
                            db.add(new_config)
                            created_count += 1
                        
                        success_count += 1
                        
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"{source_config.config_key}: {str(e)}")
                
                db.commit()
                
                # 清理目标环境的缓存
                self.cache_service.clear_config_cache(target_env)
                
                # 发布同步完成事件
                self.cache_service.publish_environment_sync(
                    source_env, target_env, 
                    {"success_count": success_count, "failed_count": failed_count}
                )
                
                result = {
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "errors": errors
                }
                
                message = f"同步完成: 成功{success_count}个, 失败{failed_count}个, 新建{created_count}个, 更新{updated_count}个"
                logger.info(f"环境配置同步: {source_env.value} -> {target_env.value}, {message}")
                
                return True, message, result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"环境配置同步失败: {e}")
            return False, f"同步失败: {str(e)}", {}
    
    async def compare_environments(self, env1: Environment, env2: Environment) -> Dict[str, Any]:
        """
        比较两个环境的配置差异
        
        Args:
            env1: 环境1
            env2: 环境2
            
        Returns:
            比较结果
        """
        try:
            db = next(get_db())
            try:
                # 获取两个环境的配置
                configs1 = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == env1,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).all()
                
                configs2 = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == env2,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).all()
                
                # 构建配置字典
                config_dict1 = {c.config_key: c for c in configs1}
                config_dict2 = {c.config_key: c for c in configs2}
                
                # 分析差异
                only_in_env1 = []  # 只在环境1中存在
                only_in_env2 = []  # 只在环境2中存在
                different_values = []  # 值不同的配置
                same_configs = []  # 相同的配置
                
                all_keys = set(config_dict1.keys()) | set(config_dict2.keys())
                
                for key in all_keys:
                    if key in config_dict1 and key not in config_dict2:
                        only_in_env1.append(self._config_to_dict(config_dict1[key]))
                    elif key not in config_dict1 and key in config_dict2:
                        only_in_env2.append(self._config_to_dict(config_dict2[key]))
                    else:
                        config1 = config_dict1[key]
                        config2 = config_dict2[key]
                        
                        if config1.config_value != config2.config_value:
                            different_values.append({
                                "config_key": key,
                                "env1_value": config1.config_value,
                                "env2_value": config2.config_value,
                                "env1_type": config1.config_type.value,
                                "env2_type": config2.config_type.value
                            })
                        else:
                            same_configs.append(key)
                
                return {
                    "env1": env1.value,
                    "env2": env2.value,
                    "only_in_env1": only_in_env1,
                    "only_in_env2": only_in_env2,
                    "different_values": different_values,
                    "same_configs": same_configs,
                    "summary": {
                        "total_env1": len(config_dict1),
                        "total_env2": len(config_dict2),
                        "only_in_env1_count": len(only_in_env1),
                        "only_in_env2_count": len(only_in_env2),
                        "different_count": len(different_values),
                        "same_count": len(same_configs)
                    }
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"环境比较失败: {e}")
            return {}
    
    # === 辅助方法 ===
    
    def _environment_to_dict(self, environment: SystemEnvironment) -> Dict[str, Any]:
        """将环境模型转换为字典"""
        return {
            "id": environment.id,
            "env_code": environment.env_code,
            "env_name": environment.env_name,
            "description": environment.description,
            "is_active": environment.is_active,
            "sort_order": environment.sort_order,
            "config_data": environment.config_data,
            "created_at": environment.created_at.isoformat() if environment.created_at else None,
            "updated_at": environment.updated_at.isoformat() if environment.updated_at else None,
            "created_by": environment.created_by,
            "updated_by": environment.updated_by
        }
    
    def _config_to_dict(self, config: SystemConfig) -> Dict[str, Any]:
        """将配置模型转换为字典（简化版）"""
        return {
            "id": config.id,
            "config_key": config.config_key,
            "config_value": config.config_value,
            "config_type": config.config_type.value,
            "environment": config.environment.value,
            "description": config.description,
            "is_core": config.is_core,
            "is_enabled": config.is_enabled,
            "is_encrypted": config.is_encrypted
        }
    
    # === 环境配置统计 ===
    
    async def get_environment_statistics(self, environment: Environment) -> Dict[str, Any]:
        """
        获取环境配置统计信息
        
        Args:
            environment: 环境
            
        Returns:
            统计信息
        """
        try:
            db = next(get_db())
            try:
                # 总配置数
                total_configs = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).count()
                
                # 启用的配置数
                enabled_configs = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.is_enabled == True
                    )
                ).count()
                
                # 核心配置数
                core_configs = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.is_core == True
                    )
                ).count()
                
                # 加密配置数
                encrypted_configs = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.is_encrypted == True
                    )
                ).count()

                # 必填配置数
                required_configs = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.is_required == True
                    )
                ).count()

                # 最近 7 天变更数与最后更新时间
                recent_threshold = datetime.utcnow() - timedelta(days=7)
                recently_updated_configs = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.updated_at >= recent_threshold
                    )
                ).count()
                latest_config = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).order_by(desc(SystemConfig.updated_at)).first()
                
                # 按类型统计
                type_stats = {}
                for config_type in ConfigType:
                    count = db.query(SystemConfig).filter(
                        and_(
                            SystemConfig.environment == environment,
                            SystemConfig.config_type == config_type,
                            SystemConfig.deleted_at.is_(None)
                        )
                    ).count()
                    type_stats[config_type.value] = count
                
                # 按分组统计
                group_stats = []
                group_query = db.query(ConfigGroup)
                if hasattr(ConfigGroup, "deleted_at"):
                    group_query = group_query.filter(ConfigGroup.deleted_at.is_(None))
                if hasattr(ConfigGroup, "is_enabled"):
                    group_query = group_query.filter(ConfigGroup.is_enabled == True)
                groups = group_query.all()
                
                for group in groups:
                    count = db.query(SystemConfig).filter(
                        and_(
                            SystemConfig.environment == environment,
                            SystemConfig.group_id == group.id,
                            SystemConfig.deleted_at.is_(None)
                        )
                    ).count()
                    
                    group_stats.append({
                        "group_id": group.id,
                        "group_name": group.group_name,
                        "config_count": count
                    })

                ungrouped_count = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.group_id.is_(None),
                        SystemConfig.deleted_at.is_(None)
                    )
                ).count()
                if ungrouped_count:
                    group_stats.insert(0, {
                        "group_id": None,
                        "group_name": "\u672a\u5206\u7ec4",
                        "config_count": ungrouped_count
                    })
                
                return {
                    "environment": environment.value,
                    "total_configs": total_configs,
                    "enabled_configs": enabled_configs,
                    "disabled_configs": total_configs - enabled_configs,
                    "core_configs": core_configs,
                    "encrypted_configs": encrypted_configs,
                    "required_configs": required_configs,
                    "recently_updated_configs": recently_updated_configs,
                    "last_updated_at": latest_config.updated_at.isoformat() if latest_config and latest_config.updated_at else None,
                    "type_statistics": type_stats,
                    "group_statistics": group_stats
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取环境统计失败: {e}")
            return {}


# 全局环境服务实例
environment_service = EnvironmentService()
