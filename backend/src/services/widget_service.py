"""
组件管理服务

实现组件定义管理、注册、配置和权限验证功能
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
import json
import logging
from fastapi import Depends

from ..models.widget_definition import WidgetDefinition, WidgetCategory, DataSourceType
from ..models.dashboard_config import RoleType
from ..models.user import User
from ..core.database import get_db
from ..services.permission import PermissionService
from ..utils.redis_client import RedisCache

logger = logging.getLogger(__name__)

class WidgetService:
    """组件管理服务"""
    
    def __init__(self, db: Session, cache_manager: RedisCache = None, permission_service: PermissionService = None):
        self.db = db
        self.cache_manager = cache_manager or RedisCache("widget")
        self.permission_service = permission_service or PermissionService(db)
    
    async def get_available_widgets(self, user_id: int, role_type: str, category: Optional[str] = None) -> List[WidgetDefinition]:
        """
        获取用户可用的组件列表
        
        Args:
            user_id: 用户ID
            role_type: 角色类型
            category: 可选，按分类过滤组件
            
        Returns:
            List[WidgetDefinition]: 可用组件列表
        """
        try:
            # 验证角色类型
            if not self._validate_role_type(role_type):
                raise ValueError(f"Invalid role type: {role_type}")
            
            role_enum = RoleType(role_type)
            
            # 尝试从缓存获取
            cache_key = f"available_widgets:{role_type}"
            cached_widgets = await self.cache_manager.get(cache_key)
            if cached_widgets:
                logger.info(f"Retrieved available widgets from cache for role {role_type}")
                widgets = [self._deserialize_widget(widget_data) for widget_data in cached_widgets]
                if category:
                    widgets = [w for w in widgets if (w.category or '') == category]
                return widgets
            
            # 获取所有激活的组件
            all_widgets = self.db.query(WidgetDefinition).filter(
                WidgetDefinition.is_active == True
            )
            if category:
                all_widgets = all_widgets.filter(WidgetDefinition.category == category)
            all_widgets = all_widgets.all()
            
            # 过滤支持该角色的组件
            available_widgets = []
            for widget in all_widgets:
                if widget.is_supported_by_role(role_enum):
                    # 检查用户是否有使用该组件的权限
                    if await self._check_widget_permission(user_id, widget.widget_type):
                        available_widgets.append(widget)
            
            # 缓存结果
            serialized_widgets = [self._serialize_widget(widget) for widget in available_widgets]
            await self.cache_manager.set(cache_key, serialized_widgets, ttl=1800)  # 30分钟缓存
            
            logger.info(f"Retrieved {len(available_widgets)} available widgets for role {role_type}")
            return available_widgets
            
        except Exception as e:
            logger.error(f"Error getting available widgets for role {role_type}: {str(e)}")
            raise
    
    async def get_widget_by_type(self, widget_type: str) -> Optional[WidgetDefinition]:
        """
        根据类型获取组件定义
        
        Args:
            widget_type: 组件类型
            
        Returns:
            WidgetDefinition: 组件定义对象
        """
        try:
            # 尝试从缓存获取
            cache_key = f"widget_definition:{widget_type}"
            cached_widget = await self.cache_manager.get(cache_key)
            if cached_widget:
                logger.info(f"Retrieved widget definition from cache for type {widget_type}")
                return self._deserialize_widget(cached_widget)
            
            # 从数据库获取
            widget = self.db.query(WidgetDefinition).filter(
                and_(
                    WidgetDefinition.widget_type == widget_type,
                    WidgetDefinition.is_active == True
                )
            ).first()
            
            if widget:
                # 缓存结果
                await self.cache_manager.set(cache_key, self._serialize_widget(widget), ttl=3600)
                logger.info(f"Retrieved widget definition for type {widget_type}")
            
            return widget
            
        except Exception as e:
            logger.error(f"Error getting widget definition for type {widget_type}: {str(e)}")
            raise
    
    async def register_widget(self, widget_data: Dict[str, Any]) -> WidgetDefinition:
        """
        注册新的组件定义
        
        Args:
            widget_data: 组件定义数据
            
        Returns:
            WidgetDefinition: 注册后的组件定义对象
        """
        try:
            # 验证组件数据
            if not self._validate_widget_data(widget_data):
                raise ValueError("Invalid widget data")
            
            # 检查组件类型是否已存在
            existing_widget = self.db.query(WidgetDefinition).filter(
                WidgetDefinition.widget_type == widget_data['widget_type']
            ).first()
            
            if existing_widget:
                raise ValueError(f"Widget type '{widget_data['widget_type']}' already exists")
            
            # 创建组件定义
            widget = WidgetDefinition(
                widget_type=widget_data['widget_type'],
                widget_name=widget_data['widget_name'],
                description=widget_data.get('description'),
                category=WidgetCategory(widget_data['category']),
                default_config=widget_data.get('default_config', {}),
                data_source_config=widget_data.get('data_source_config', {}),
                supported_roles=widget_data.get('supported_roles', []),
                min_width=widget_data.get('min_width', 2),
                min_height=widget_data.get('min_height', 2),
                max_width=widget_data.get('max_width', 12),
                max_height=widget_data.get('max_height', 12),
                is_resizable=widget_data.get('is_resizable', True),
                is_movable=widget_data.get('is_movable', True),
                requires_data=widget_data.get('requires_data', True),
                refresh_interval=widget_data.get('refresh_interval', 30),
                version=widget_data.get('version', '1.0.0')
            )
            
            self.db.add(widget)
            self.db.commit()
            self.db.refresh(widget)
            
            # 清除相关缓存
            await self._clear_widget_caches()
            
            logger.info(f"Registered new widget: {widget.widget_type}")
            return widget
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registering widget: {str(e)}")
            raise
    
    async def update_widget_config(self, widget_type: str, config_updates: Dict[str, Any]) -> WidgetDefinition:
        """
        更新组件配置
        
        Args:
            widget_type: 组件类型
            config_updates: 配置更新数据
            
        Returns:
            WidgetDefinition: 更新后的组件定义对象
        """
        try:
            # 获取组件定义
            widget = self.db.query(WidgetDefinition).filter(
                WidgetDefinition.widget_type == widget_type
            ).first()
            
            if not widget:
                raise ValueError(f"Widget type '{widget_type}' not found")
            
            # 更新配置
            if 'default_config' in config_updates:
                widget.default_config = config_updates['default_config']
            
            if 'data_source_config' in config_updates:
                widget.data_source_config = config_updates['data_source_config']
            
            if 'supported_roles' in config_updates:
                widget.supported_roles = config_updates['supported_roles']
            
            if 'refresh_interval' in config_updates:
                widget.refresh_interval = config_updates['refresh_interval']
            
            # 更新其他属性
            updatable_fields = [
                'widget_name', 'description', 'min_width', 'min_height',
                'max_width', 'max_height', 'is_resizable', 'is_movable',
                'requires_data', 'is_active', 'version'
            ]
            
            for field in updatable_fields:
                if field in config_updates:
                    setattr(widget, field, config_updates[field])
            
            widget.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(widget)
            
            # 清除相关缓存
            await self._clear_widget_caches()
            cache_key = f"widget_definition:{widget_type}"
            await self.cache_manager.delete(cache_key)
            
            logger.info(f"Updated widget config: {widget_type}")
            return widget
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating widget config for {widget_type}: {str(e)}")
            raise
    
    async def get_widgets_by_category(self, category: str, role_type: str = None) -> List[WidgetDefinition]:
        """
        根据分类获取组件列表
        
        Args:
            category: 组件分类
            role_type: 角色类型（可选）
            
        Returns:
            List[WidgetDefinition]: 组件列表
        """
        try:
            # 验证分类
            if not self._validate_category(category):
                raise ValueError(f"Invalid category: {category}")
            
            category_enum = WidgetCategory(category)
            
            # 构建缓存键
            cache_key = f"widgets_by_category:{category}"
            if role_type:
                cache_key += f":{role_type}"
            
            # 尝试从缓存获取
            cached_widgets = await self.cache_manager.get(cache_key)
            if cached_widgets:
                logger.info(f"Retrieved widgets from cache for category {category}")
                return [self._deserialize_widget(widget_data) for widget_data in cached_widgets]
            
            # 从数据库获取
            query = self.db.query(WidgetDefinition).filter(
                and_(
                    WidgetDefinition.category == category_enum,
                    WidgetDefinition.is_active == True
                )
            )
            
            widgets = query.all()
            
            # 如果指定了角色，进行过滤
            if role_type:
                role_enum = RoleType(role_type)
                widgets = [widget for widget in widgets if widget.is_supported_by_role(role_enum)]
            
            # 缓存结果
            serialized_widgets = [self._serialize_widget(widget) for widget in widgets]
            await self.cache_manager.set(cache_key, serialized_widgets, ttl=1800)
            
            logger.info(f"Retrieved {len(widgets)} widgets for category {category}")
            return widgets
            
        except Exception as e:
            logger.error(f"Error getting widgets by category {category}: {str(e)}")
            raise
    
    async def validate_widget_instance_config(
        self, 
        widget_type: str, 
        instance_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证组件实例配置
        
        Args:
            widget_type: 组件类型
            instance_config: 实例配置
            
        Returns:
            Dict[str, Any]: 验证结果和合并后的配置
        """
        try:
            # 获取组件定义
            widget_def = await self.get_widget_by_type(widget_type)
            if not widget_def:
                return {
                    'valid': False,
                    'errors': [f"Widget type '{widget_type}' not found"],
                    'config': None
                }
            
            errors = []
            
            # 验证尺寸
            if 'width' in instance_config and 'height' in instance_config:
                if not widget_def.validate_size(instance_config['width'], instance_config['height']):
                    errors.append(f"Invalid size: {instance_config['width']}x{instance_config['height']}")
            
            # 验证配置格式
            if not widget_def.validate_config(instance_config):
                errors.append("Invalid configuration format")
            
            # 合并默认配置和实例配置
            merged_config = widget_def.merge_config(instance_config)
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'config': merged_config
            }
            
        except Exception as e:
            logger.error(f"Error validating widget instance config for {widget_type}: {str(e)}")
            return {
                'valid': False,
                'errors': [str(e)],
                'config': None
            }
    
    async def get_widget_data_source_info(self, widget_type: str) -> Optional[Dict[str, Any]]:
        """
        获取组件数据源信息
        
        Args:
            widget_type: 组件类型
            
        Returns:
            Dict[str, Any]: 数据源信息
        """
        try:
            widget_def = await self.get_widget_by_type(widget_type)
            if not widget_def or not widget_def.data_source_config:
                return None
            
            data_source_info = widget_def.data_source_config.copy()
            
            # 添加组件基本信息
            data_source_info.update({
                'widget_type': widget_def.widget_type,
                'requires_data': widget_def.requires_data,
                'refresh_interval': widget_def.refresh_interval
            })
            
            return data_source_info
            
        except Exception as e:
            logger.error(f"Error getting data source info for {widget_type}: {str(e)}")
            return None
    
    async def initialize_builtin_widgets(self) -> List[WidgetDefinition]:
        """
        初始化内置组件定义
        
        Returns:
            List[WidgetDefinition]: 初始化的组件列表
        """
        try:
            # 获取内置组件定义
            builtin_widgets = WidgetDefinition.create_builtin_widgets()
            
            created_widgets = []
            for widget_data in builtin_widgets:
                # 检查是否已存在
                existing = self.db.query(WidgetDefinition).filter(
                    WidgetDefinition.widget_type == widget_data.widget_type
                ).first()
                
                if not existing:
                    self.db.add(widget_data)
                    created_widgets.append(widget_data)
                    logger.info(f"Created builtin widget: {widget_data.widget_type}")
            
            if created_widgets:
                self.db.commit()
                
                # 刷新对象
                for widget in created_widgets:
                    self.db.refresh(widget)
                
                # 清除缓存
                await self._clear_widget_caches()
            
            logger.info(f"Initialized {len(created_widgets)} builtin widgets")
            return created_widgets
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initializing builtin widgets: {str(e)}")
            raise
    
    def _validate_role_type(self, role_type: str) -> bool:
        """验证角色类型是否有效"""
        try:
            RoleType(role_type)
            return True
        except ValueError:
            return False
    
    def _validate_category(self, category: str) -> bool:
        """验证组件分类是否有效"""
        try:
            WidgetCategory(category)
            return True
        except ValueError:
            return False

    async def get_widget_categories(self) -> List[str]:
        """获取所有组件分类列表（返回枚举值字符串）。"""
        try:
            return [c.value for c in WidgetCategory]
        except Exception as e:
            logger.error(f"Error getting widget categories: {str(e)}")
            return []
    
    def _validate_widget_data(self, widget_data: Dict[str, Any]) -> bool:
        """验证组件数据是否有效"""
        required_fields = ['widget_type', 'widget_name', 'category']
        
        for field in required_fields:
            if field not in widget_data:
                return False
        
        # 验证分类
        if not self._validate_category(widget_data['category']):
            return False
        
        # 验证尺寸
        if 'min_width' in widget_data and 'max_width' in widget_data:
            if widget_data['min_width'] > widget_data['max_width']:
                return False
        
        if 'min_height' in widget_data and 'max_height' in widget_data:
            if widget_data['min_height'] > widget_data['max_height']:
                return False
        
        return True
    
    async def _check_widget_permission(self, user_id: int, widget_type: str) -> bool:
        """检查用户是否有使用指定组件的权限"""
        try:
            # 检查是否有通用组件使用权限
            has_general_permission = await self.permission_service.check_permission(
                user_id, 'widget:use'
            )
            
            if has_general_permission:
                return True
            
            # 检查是否有特定组件权限
            specific_permission = f"widget:use:{widget_type}"
            has_specific_permission = await self.permission_service.check_permission(
                user_id, specific_permission
            )
            
            return has_specific_permission
            
        except Exception as e:
            logger.error(f"Error checking widget permission for user {user_id}, widget {widget_type}: {str(e)}")
            return False
    
    async def _clear_widget_caches(self):
        """清除组件相关的缓存"""
        try:
            # 清除所有角色的可用组件缓存
            for role in RoleType:
                cache_key = f"available_widgets:{role.value}"
                await self.cache_manager.delete(cache_key)
            
            # 清除分类缓存
            for category in WidgetCategory:
                cache_key = f"widgets_by_category:{category.value}"
                await self.cache_manager.delete(cache_key)
                
                # 清除带角色的分类缓存
                for role in RoleType:
                    cache_key = f"widgets_by_category:{category.value}:{role.value}"
                    await self.cache_manager.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error clearing widget caches: {str(e)}")
    
    def _serialize_widget(self, widget: WidgetDefinition) -> Dict[str, Any]:
        """序列化组件对象用于缓存"""
        return widget.to_dict()
    
    def _deserialize_widget(self, data: Dict[str, Any]) -> WidgetDefinition:
        """从缓存数据反序列化组件对象"""
        widget = WidgetDefinition()
        for key, value in data.items():
            if hasattr(widget, key):
                if key in ['created_at', 'updated_at'] and isinstance(value, str):
                    setattr(widget, key, datetime.fromisoformat(value))
                elif key == 'category' and isinstance(value, str):
                    setattr(widget, key, WidgetCategory(value))
                else:
                    setattr(widget, key, value)
        return widget


def get_widget_service(db: Session = Depends(get_db)) -> WidgetService:
    """
    获取组件服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        WidgetService: 组件服务实例
    """
    return WidgetService(db)

