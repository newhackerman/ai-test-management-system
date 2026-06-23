"""
配置管理核心服务
"""
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, cast, String
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..models.config import (
    SystemConfig, ConfigGroup, ConfigHistory, ConfigAudit, 
    SystemEnvironment, ConfigPermission, ConfigType, Environment
)
from ..utils.encryption import get_encryption_service
from ..utils.config_validator import ConfigValidator, validate_config, convert_config_value
from ..utils.advanced_validator import AdvancedConfigValidator
from ..utils.config_cache import config_cache_service, NotificationType
from ..schemas.config import (
    ConfigCreateRequest, ConfigUpdateRequest, ConfigResponse,
    ConfigListResponse, ConfigSearchRequest
)
import logging

logger = logging.getLogger(__name__)

CONFIG_TYPE_SEARCH_ALIASES = {
    "字符串": ConfigType.STRING,
    "文本": ConfigType.TEXT,
    "长文本": ConfigType.TEXT,
    "整数": ConfigType.INTEGER,
    "数字": ConfigType.INTEGER,
    "浮点": ConfigType.FLOAT,
    "浮点数": ConfigType.FLOAT,
    "布尔": ConfigType.BOOLEAN,
    "布尔值": ConfigType.BOOLEAN,
    "开关": ConfigType.BOOLEAN,
    "数组": ConfigType.ARRAY,
    "邮箱": ConfigType.EMAIL,
    "邮件": ConfigType.EMAIL,
    "链接": ConfigType.URL,
    "地址": ConfigType.URL,
    "枚举": ConfigType.ENUM,
    "密码": ConfigType.PASSWORD,
    "文件": ConfigType.FILE,
    "颜色": ConfigType.COLOR,
    "日期": ConfigType.DATE,
    "时间": ConfigType.TIME,
}

ENVIRONMENT_SEARCH_ALIASES = {
    "开发": Environment.DEV,
    "开发环境": Environment.DEV,
    "测试": Environment.TEST,
    "测试环境": Environment.TEST,
    "预发": Environment.STAGING,
    "预发环境": Environment.STAGING,
    "生产": Environment.PROD,
    "生产环境": Environment.PROD,
    "演示": Environment.DEMO,
    "演示环境": Environment.DEMO,
    "性能": Environment.PERF,
    "性能环境": Environment.PERF,
    "性能测试": Environment.PERF,
    "性能测试环境": Environment.PERF,
}


class ConfigService:
    """配置管理核心服务"""
    
    def __init__(self):
        self.encryption_service = get_encryption_service()
        self.validator = ConfigValidator()
        self.advanced_validator = AdvancedConfigValidator(self)
        self.cache_service = config_cache_service
    
    # === 基础CRUD操作 ===
    
    async def get_config(self, config_key: str, environment: Environment = Environment.PROD,
                        decrypt: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取单个配置
        
        Args:
            config_key: 配置键
            environment: 环境
            decrypt: 是否解密敏感配置
            
        Returns:
            配置数据
        """
        try:
            # 先从缓存获取
            cached_config = self.cache_service.get_config(config_key, environment)
            if cached_config:
                logger.debug(f"从缓存获取配置: {config_key}")
                return cached_config
            
            # 从数据库查询
            db = next(get_db())
            try:
                config = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.config_key == config_key,
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None),
                        SystemConfig.is_enabled == True
                    )
                ).first()
                
                if not config:
                    return None
                
                # 转换为字典
                config_data = self._config_to_dict(config, decrypt)
                
                # 缓存结果
                self.cache_service.set_config(config_key, config_data, environment)
                
                return config_data
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取配置失败: {config_key}, 错误: {e}")
            return None
    
    async def get_configs(self, environment: Environment = Environment.PROD,
                         group_id: Optional[int] = None, 
                         page: int = 1, size: int = 20,
                         search: Optional[str] = None,
                         config_type: Optional[ConfigType] = None,
                         is_core: Optional[bool] = None) -> ConfigListResponse:
        """
        获取配置列表
        
        Args:
            environment: 环境
            group_id: 分组ID
            page: 页码
            size: 页大小
            search: 搜索关键词
            config_type: 配置类型
            is_core: 是否核心配置
            
        Returns:
            配置列表响应
        """
        try:
            db = next(get_db())
            try:
                # 构建查询
                query = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                )
                
                # 分组过滤
                if group_id:
                    query = query.filter(SystemConfig.group_id == group_id)
                
                # 搜索过滤：按用户在页面能看到或自然会输入的内容做宽匹配。
                search_terms = [term.strip() for term in (search or "").split() if term.strip()]
                if search_terms:
                    query = query.outerjoin(ConfigGroup, SystemConfig.group_id == ConfigGroup.id)
                    for term in search_terms:
                        like_term = f"%{term}%"
                        term_filters = [
                            SystemConfig.config_key.ilike(like_term),
                            SystemConfig.config_value.ilike(like_term),
                            SystemConfig.description.ilike(like_term),
                            SystemConfig.default_value.ilike(like_term),
                            SystemConfig.example_value.ilike(like_term),
                            cast(SystemConfig.validation_rule, String).ilike(like_term),
                            cast(SystemConfig.tags, String).ilike(like_term),
                            cast(SystemConfig.config_type, String).ilike(like_term),
                            cast(SystemConfig.environment, String).ilike(like_term),
                            ConfigGroup.group_name.ilike(like_term),
                            ConfigGroup.group_code.ilike(like_term),
                            ConfigGroup.description.ilike(like_term),
                        ]
                        normalized_term = term.strip().lower()
                        type_alias = CONFIG_TYPE_SEARCH_ALIASES.get(term.strip())
                        environment_alias = ENVIRONMENT_SEARCH_ALIASES.get(term.strip())

                        if type_alias:
                            term_filters.append(SystemConfig.config_type == type_alias)
                        if environment_alias:
                            term_filters.append(SystemConfig.environment == environment_alias)
                        if normalized_term in {"启用", "已启用", "enable", "enabled", "true"}:
                            term_filters.append(SystemConfig.is_enabled == True)
                        if normalized_term in {"禁用", "已禁用", "disable", "disabled", "false"}:
                            term_filters.append(SystemConfig.is_enabled == False)
                        if normalized_term in {"核心", "核心配置", "core"}:
                            term_filters.append(SystemConfig.is_core == True)
                        if normalized_term in {"加密", "已加密", "encrypted"}:
                            term_filters.append(SystemConfig.is_encrypted == True)
                        if normalized_term in {"必填", "必填项", "required"}:
                            term_filters.append(SystemConfig.is_required == True)

                        query = query.filter(or_(*term_filters))
                
                # 类型过滤
                if config_type:
                    query = query.filter(SystemConfig.config_type == config_type)
                
                # 核心配置过滤
                if is_core is not None:
                    query = query.filter(SystemConfig.is_core == is_core)
                
                # 总数
                total = query.count()
                
                # 分页
                offset = (page - 1) * size
                configs = query.order_by(
                    SystemConfig.sort_order.asc(),
                    SystemConfig.created_at.desc()
                ).offset(offset).limit(size).all()
                
                # 转换为字典列表
                items = [self._config_to_dict(config, decrypt=False) for config in configs]
                
                result = ConfigListResponse(
                    items=items,
                    total=total,
                    page=page,
                    size=size,
                    pages=(total + size - 1) // size
                )
                
                # 只缓存无搜索/筛选的普通列表，避免筛选结果污染相同分页的列表缓存。
                if not search_terms and not config_type and is_core is None:
                    self.cache_service.set_config_list(result.dict(), environment, group_id, page, size)
                
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取配置列表失败: {e}")
            return ConfigListResponse(items=[], total=0, page=page, size=size, pages=0)
    
    async def create_config(self, config_data: ConfigCreateRequest, 
                           operator_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        创建配置
        
        Args:
            config_data: 配置创建请求
            operator_id: 操作人ID
            
        Returns:
            (是否成功, 错误信息, 配置数据)
        """
        try:
            # 基础验证配置值
            is_valid, error_msg = validate_config(
                config_data.config_value,
                config_data.config_type.value,
                config_data.validation_rule
            )
            
            if not is_valid:
                return False, f"配置值验证失败: {error_msg}", None
            
            # 高级验证（如果有高级验证规则）
            if hasattr(config_data, 'advanced_validation_rules') and config_data.advanced_validation_rules:
                is_valid, error_msg = await self.advanced_validator.validate_with_dependencies(
                    config_data.config_key,
                    config_data.config_value,
                    config_data.config_type.value,
                    config_data.environment.value,
                    config_data.advanced_validation_rules
                )
                
                if not is_valid:
                    return False, f"高级验证失败: {error_msg}", None
            
            # 类型转换
            converted_value = convert_config_value(config_data.config_value, config_data.config_type.value)
            
            # 处理加密
            final_value = config_data.config_value
            if config_data.is_encrypted:
                final_value = self.encryption_service.encrypt(config_data.config_value)
            
            db = next(get_db())
            try:
                # 检查键名是否已存在
                existing = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.config_key == config_data.config_key,
                        SystemConfig.environment == config_data.environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).first()
                
                if existing:
                    return False, "配置键已存在", None
                
                # 创建配置
                config = SystemConfig(
                    config_key=config_data.config_key,
                    config_value=final_value,
                    config_type=config_data.config_type,
                    group_id=config_data.group_id,
                    environment=config_data.environment,
                    description=config_data.description,
                    default_value=config_data.default_value,
                    example_value=config_data.example_value,
                    validation_rule=config_data.validation_rule,
                    is_core=config_data.is_core,
                    is_enabled=config_data.is_enabled,
                    is_encrypted=config_data.is_encrypted,
                    is_required=config_data.is_required,
                    tags=config_data.tags,
                    sort_order=config_data.sort_order or 0,
                    created_by=operator_id,
                    updated_by=operator_id
                )
                
                db.add(config)
                db.commit()
                db.refresh(config)
                
                # 记录历史
                await self._record_history(
                    config.id, config.config_key, config.environment,
                    None, config_data.config_value, "CREATE",
                    "创建配置", operator_id, db
                )
                
                # 清理相关缓存
                self.cache_service.clear_config_cache(config_data.environment)
                
                # 发布变更事件
                self.cache_service.publish_config_change(
                    config.config_key, config.environment,
                    NotificationType.CONFIG_CREATED,
                    {"operator_id": operator_id}
                )
                
                # 发布WebSocket事件
                try:
                    from ..api.websocket import publish_config_change
                    await publish_config_change(
                        config_key=config.config_key,
                        environment=config.environment.value,
                        change_type='CREATE',
                        user_id=operator_id
                    )
                except Exception as e:
                    logger.warning(f"发布WebSocket事件失败: {e}")
                
                config_dict = self._config_to_dict(config)
                logger.info(f"创建配置成功: {config.config_key}")
                
                return True, None, config_dict
                
            except IntegrityError as e:
                db.rollback()
                return False, "数据库约束错误", None
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"创建配置失败: {e}")
            return False, f"创建配置失败: {str(e)}", None
    
    async def update_config(self, config_key: str, config_data: ConfigUpdateRequest,
                           operator_id: int, environment: Environment = Environment.PROD) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        更新配置
        
        Args:
            config_key: 配置键
            config_data: 配置更新请求
            operator_id: 操作人ID
            environment: 环境
            
        Returns:
            (是否成功, 错误信息, 配置数据)
        """
        try:
            db = next(get_db())
            try:
                # 查询现有配置
                config = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.config_key == config_key,
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).first()
                
                if not config:
                    return False, "配置不存在", None
                
                # 记录原始值
                old_value = config.config_value
                if config.is_encrypted:
                    old_value = self.encryption_service.decrypt(old_value)
                
                # 验证新值
                new_value = config_data.config_value if config_data.config_value is not None else old_value
                config_type = config_data.config_type or config.config_type
                
                is_valid, error_msg = validate_config(
                    new_value,
                    config_type.value,
                    config_data.validation_rule
                )
                
                if not is_valid:
                    return False, f"配置值验证失败: {error_msg}", None
                
                # 处理加密
                final_value = new_value
                is_encrypted = config_data.is_encrypted if config_data.is_encrypted is not None else config.is_encrypted
                
                if is_encrypted:
                    final_value = self.encryption_service.encrypt(new_value)
                
                # 更新配置
                if config_data.config_value is not None:
                    config.config_value = final_value
                if config_data.config_type is not None:
                    config.config_type = config_data.config_type
                if config_data.description is not None:
                    config.description = config_data.description
                if config_data.default_value is not None:
                    config.default_value = config_data.default_value
                if config_data.example_value is not None:
                    config.example_value = config_data.example_value
                if config_data.validation_rule is not None:
                    config.validation_rule = config_data.validation_rule
                if config_data.is_core is not None:
                    config.is_core = config_data.is_core
                if config_data.is_enabled is not None:
                    config.is_enabled = config_data.is_enabled
                if config_data.is_encrypted is not None:
                    config.is_encrypted = config_data.is_encrypted
                if config_data.is_required is not None:
                    config.is_required = config_data.is_required
                if config_data.tags is not None:
                    config.tags = config_data.tags
                if config_data.sort_order is not None:
                    config.sort_order = config_data.sort_order
                
                config.updated_by = operator_id
                config.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(config)
                
                # 记录历史
                await self._record_history(
                    config.id, config.config_key, config.environment,
                    old_value, new_value, "UPDATE",
                    config_data.change_reason or "更新配置", operator_id, db
                )
                
                # 清理缓存
                self.cache_service.delete_config(config_key, environment)
                self.cache_service.clear_config_cache(environment)
                
                # 发布变更事件
                self.cache_service.publish_config_change(
                    config.config_key, config.environment,
                    NotificationType.CONFIG_UPDATED,
                    {
                        "operator_id": operator_id,
                        "old_value": old_value,
                        "new_value": new_value
                    }
                )
                
                # 发布WebSocket事件
                try:
                    from ..api.websocket import publish_config_change
                    await publish_config_change(
                        config_key=config.config_key,
                        environment=config.environment.value,
                        change_type='UPDATE',
                        user_id=operator_id
                    )
                except Exception as e:
                    logger.warning(f"发布WebSocket事件失败: {e}")
                
                config_dict = self._config_to_dict(config)
                logger.info(f"更新配置成功: {config.config_key}")
                
                return True, None, config_dict
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False, f"更新配置失败: {str(e)}", None
    
    async def delete_config(self, config_key: str, operator_id: int,
                           environment: Environment = Environment.PROD,
                           hard_delete: bool = False) -> Tuple[bool, Optional[str]]:
        """
        删除配置
        
        Args:
            config_key: 配置键
            operator_id: 操作人ID
            environment: 环境
            hard_delete: 是否硬删除
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            db = next(get_db())
            try:
                config = db.query(SystemConfig).filter(
                    and_(
                        SystemConfig.config_key == config_key,
                        SystemConfig.environment == environment,
                        SystemConfig.deleted_at.is_(None)
                    )
                ).first()
                
                if not config:
                    return False, "配置不存在"
                
                # 记录原始值（用于历史记录）
                old_value = config.config_value
                if config.is_encrypted:
                    old_value = self.encryption_service.decrypt(old_value)
                
                if hard_delete:
                    # 硬删除
                    db.delete(config)
                else:
                    # 软删除
                    config.soft_delete()
                    config.updated_by = operator_id
                
                db.commit()
                
                # 记录历史
                await self._record_history(
                    config.id, config.config_key, config.environment,
                    old_value, None, "DELETE",
                    "删除配置", operator_id, db
                )
                
                # 清理缓存
                self.cache_service.delete_config(config_key, environment)
                self.cache_service.clear_config_cache(environment)
                
                # 发布变更事件
                self.cache_service.publish_config_change(
                    config.config_key, config.environment,
                    NotificationType.CONFIG_DELETED,
                    {"operator_id": operator_id}
                )
                
                # 发布WebSocket事件
                try:
                    from ..api.websocket import publish_config_change
                    await publish_config_change(
                        config_key=config.config_key,
                        environment=config.environment.value,
                        change_type='DELETE',
                        user_id=operator_id
                    )
                except Exception as e:
                    logger.warning(f"发布WebSocket事件失败: {e}")
                
                logger.info(f"删除配置成功: {config.config_key}")
                return True, None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False, f"删除配置失败: {str(e)}"
    
    # === 辅助方法 ===
    
    def _config_to_dict(self, config: SystemConfig, decrypt: bool = True) -> Dict[str, Any]:
        """将配置模型转换为字典"""
        value = config.config_value
        
        # 解密处理
        if decrypt and config.is_encrypted and value:
            try:
                value = self.encryption_service.decrypt(value)
            except Exception as e:
                logger.warning(f"解密配置失败: {config.config_key}, 错误: {e}")
        
        return {
            "id": config.id,
            "config_key": config.config_key,
            "config_value": value,
            "config_type": config.config_type.value,
            "group_id": config.group_id,
            "environment": config.environment.value,
            "description": config.description,
            "default_value": config.default_value,
            "example_value": config.example_value,
            "validation_rule": config.validation_rule,
            "is_core": config.is_core,
            "is_enabled": config.is_enabled,
            "is_encrypted": config.is_encrypted,
            "is_required": config.is_required,
            "tags": config.tags,
            "sort_order": config.sort_order,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "created_by": config.created_by,
            "updated_by": config.updated_by
        }
    
    async def _record_history(self, config_id: int, config_key: str, environment: Environment,
                             old_value: Optional[str], new_value: Optional[str], 
                             change_type: str, change_reason: str, operator_id: int, db: Session):
        """记录配置变更历史"""
        try:
            history = ConfigHistory(
                config_id=config_id,
                config_key=config_key,
                environment=environment,
                old_value=old_value,
                new_value=new_value,
                change_type=change_type,
                change_reason=change_reason,
                operator_id=operator_id,
                created_by=operator_id
            )
            
            db.add(history)
            db.commit()
            
        except Exception as e:
            logger.error(f"记录配置历史失败: {e}")
    
    # === 批量操作 ===
    
    async def batch_update_configs(self, updates: List[Dict], operator_id: int) -> Tuple[bool, str, Dict]:
        """批量更新配置"""
        try:
            db = next(get_db())
            success_count = 0
            failed_count = 0
            errors = []
            
            try:
                for update_data in updates:
                    config_key = update_data.get("config_key")
                    environment = Environment(update_data.get("environment", "PROD"))
                    
                    try:
                        # 构建更新请求
                        update_request = ConfigUpdateRequest(**{
                            k: v for k, v in update_data.items() 
                            if k not in ["config_key", "environment"]
                        })
                        
                        success, error, _ = await self.update_config(
                            config_key, update_request, operator_id, environment
                        )
                        
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"{config_key}: {error}")
                            
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"{config_key}: {str(e)}")
                
                result = {
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "errors": errors
                }
                
                return True, f"批量更新完成: 成功{success_count}个, 失败{failed_count}个", result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"批量更新配置失败: {e}")
            return False, f"批量更新失败: {str(e)}", {}


# 全局配置服务实例
config_service = ConfigService()
