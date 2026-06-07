"""
组件定义数据模型

实现WidgetDefinition SQLAlchemy模型，支持组件类型管理和权限控制
"""

from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON, Integer, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum as PyEnum
from typing import Dict, List, Any, Optional
from .dashboard_config import RoleType

Base = declarative_base()

class WidgetCategory(PyEnum):
    """组件分类枚举"""
    STATISTICS = "STATISTICS"  # 统计类组件
    CHARTS = "CHARTS"  # 图表类组件
    PROGRESS = "PROGRESS"  # 进度类组件
    STATUS = "STATUS"  # 状态类组件
    RANKING = "RANKING"  # 排行类组件
    CALENDAR = "CALENDAR"  # 日历类组件
    MAP = "MAP"  # 地图类组件
    TABLE = "TABLE"  # 表格类组件
    CUSTOM = "CUSTOM"  # 自定义组件

class DataSourceType(PyEnum):
    """数据源类型枚举"""
    API = "API"  # REST API
    DATABASE = "DATABASE"  # 数据库查询
    WEBSOCKET = "WEBSOCKET"  # WebSocket实时数据
    CACHE = "CACHE"  # 缓存数据
    STATIC = "STATIC"  # 静态数据

class WidgetDefinition(Base):
    """
    组件定义表
    
    定义仪表板中可用的组件类型、配置和权限
    """
    __tablename__ = 'widget_definitions'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='组件定义ID')
    widget_type = Column(String(50), unique=True, nullable=False, comment='组件类型标识')
    widget_name = Column(String(100), nullable=False, comment='组件显示名称')
    description = Column(Text, comment='组件描述')
    category = Column(Enum(WidgetCategory), nullable=False, comment='组件分类')
    
    # 配置信息
    default_config = Column(JSON, comment='默认配置JSON')
    data_source_config = Column(JSON, comment='数据源配置JSON')
    supported_roles = Column(JSON, comment='支持的角色列表JSON')
    
    # 尺寸限制
    min_width = Column(Integer, default=2, comment='最小宽度(网格单位)')
    min_height = Column(Integer, default=2, comment='最小高度(网格单位)')
    max_width = Column(Integer, default=12, comment='最大宽度(网格单位)')
    max_height = Column(Integer, default=12, comment='最大高度(网格单位)')
    
    # 组件属性
    is_resizable = Column(Boolean, default=True, comment='是否可调整大小')
    is_movable = Column(Boolean, default=True, comment='是否可移动')
    requires_data = Column(Boolean, default=True, comment='是否需要数据源')
    refresh_interval = Column(Integer, default=30, comment='默认刷新间隔(秒)')
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment='是否激活')
    version = Column(String(20), default='1.0.0', comment='组件版本')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_widget_type', 'widget_type'),
        Index('idx_category', 'category'),
        Index('idx_is_active', 'is_active'),
        Index('idx_category_active', 'category', 'is_active'),
        {'comment': '组件定义表'}
    )
    
    def __repr__(self):
        return f"<WidgetDefinition(id={self.id}, type='{self.widget_type}', name='{self.widget_name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'widget_type': self.widget_type,
            'widget_name': self.widget_name,
            'description': self.description,
            'category': self.category.value if self.category else None,
            'default_config': self.default_config,
            'data_source_config': self.data_source_config,
            'supported_roles': self.supported_roles,
            'min_width': self.min_width,
            'min_height': self.min_height,
            'max_width': self.max_width,
            'max_height': self.max_height,
            'is_resizable': self.is_resizable,
            'is_movable': self.is_movable,
            'requires_data': self.requires_data,
            'refresh_interval': self.refresh_interval,
            'is_active': self.is_active,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_supported_by_role(self, role_type: RoleType) -> bool:
        """检查角色是否支持此组件"""
        if not self.supported_roles:
            return True  # 如果没有限制，则所有角色都支持
        
        if isinstance(self.supported_roles, list):
            return role_type.value in self.supported_roles
        
        return False
    
    def validate_size(self, width: int, height: int) -> bool:
        """验证组件尺寸是否合法"""
        return (self.min_width <= width <= self.max_width and 
                self.min_height <= height <= self.max_height)
    
    def get_default_size(self) -> Dict[str, int]:
        """获取默认尺寸"""
        return {
            'width': max(self.min_width, min(4, self.max_width)),
            'height': max(self.min_height, min(3, self.max_height))
        }
    
    @classmethod
    def create_builtin_widgets(cls) -> List['WidgetDefinition']:
        """创建内置组件定义"""
        builtin_widgets = [
            # 统计类组件
            cls(
                widget_type='project_overview',
                widget_name='项目概览',
                description='显示项目总体状态和关键指标',
                category=WidgetCategory.STATISTICS,
                default_config={
                    'show_total_count': True,
                    'show_status_distribution': True,
                    'show_health_score': True,
                    'color_scheme': 'default'
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/project-overview',
                    'method': 'GET',
                    'cache_ttl': 300
                },
                supported_roles=['ADMIN', 'PROJECT_MANAGER'],
                min_width=4, min_height=3, max_width=8, max_height=6,
                refresh_interval=60
            ),
            
            cls(
                widget_type='system_status',
                widget_name='系统状态',
                description='显示系统运行状态和性能指标',
                category=WidgetCategory.STATUS,
                default_config={
                    'show_cpu_usage': True,
                    'show_memory_usage': True,
                    'show_disk_usage': True,
                    'show_network_status': True,
                    'alert_threshold': 80
                },
                data_source_config={
                    'type': DataSourceType.WEBSOCKET.value,
                    'endpoint': '/ws/system-metrics',
                    'real_time': True
                },
                supported_roles=['ADMIN', 'DEVOPS'],
                min_width=3, min_height=2, max_width=6, max_height=4,
                refresh_interval=10
            ),
            
            # 图表类组件
            cls(
                widget_type='requirement_trend',
                widget_name='需求趋势图',
                description='显示需求完成情况的时间趋势',
                category=WidgetCategory.CHARTS,
                default_config={
                    'chart_type': 'line',
                    'time_range': '30d',
                    'show_prediction': True,
                    'color_scheme': 'blue'
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/requirement-trend',
                    'method': 'GET',
                    'params': {'range': '30d'}
                },
                supported_roles=['REQUIREMENT_MANAGER', 'PROJECT_MANAGER'],
                min_width=4, min_height=3, max_width=12, max_height=6,
                refresh_interval=300
            ),
            
            cls(
                widget_type='test_execution_chart',
                widget_name='测试执行图表',
                description='显示测试用例执行统计和通过率',
                category=WidgetCategory.CHARTS,
                default_config={
                    'chart_type': 'bar',
                    'show_pass_rate': True,
                    'show_execution_trend': True,
                    'group_by': 'date'
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/test-execution',
                    'method': 'GET'
                },
                supported_roles=['TESTER', 'PROJECT_MANAGER'],
                min_width=4, min_height=3, max_width=8, max_height=5,
                refresh_interval=120
            ),
            
            # 进度类组件
            cls(
                widget_type='milestone_progress',
                widget_name='里程碑进度',
                description='显示项目里程碑完成进度',
                category=WidgetCategory.PROGRESS,
                default_config={
                    'show_percentage': True,
                    'show_timeline': True,
                    'highlight_overdue': True,
                    'progress_style': 'bar'
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/milestone-progress',
                    'method': 'GET'
                },
                supported_roles=['PROJECT_MANAGER', 'ADMIN'],
                min_width=3, min_height=2, max_width=6, max_height=4,
                refresh_interval=180
            ),
            
            # 表格类组件
            cls(
                widget_type='my_tasks',
                widget_name='我的任务',
                description='显示当前用户的任务列表',
                category=WidgetCategory.TABLE,
                default_config={
                    'show_priority': True,
                    'show_due_date': True,
                    'show_status': True,
                    'max_rows': 10,
                    'sort_by': 'priority'
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/my-tasks',
                    'method': 'GET',
                    'user_specific': True
                },
                supported_roles=['DEVELOPER', 'TESTER', 'DESIGNER', 'ARCHITECT'],
                min_width=4, min_height=3, max_width=8, max_height=6,
                refresh_interval=60
            ),
            
            # 排行类组件
            cls(
                widget_type='team_performance',
                widget_name='团队绩效排行',
                description='显示团队成员绩效排行榜',
                category=WidgetCategory.RANKING,
                default_config={
                    'metric_type': 'productivity',
                    'time_range': '7d',
                    'show_avatar': True,
                    'max_items': 10
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/team-performance',
                    'method': 'GET'
                },
                supported_roles=['PROJECT_MANAGER', 'ADMIN'],
                min_width=3, min_height=4, max_width=6, max_height=8,
                refresh_interval=300
            ),
            
            # 日历类组件
            cls(
                widget_type='project_calendar',
                widget_name='项目日历',
                description='显示项目重要事件和里程碑日历',
                category=WidgetCategory.CALENDAR,
                default_config={
                    'view_type': 'month',
                    'show_milestones': True,
                    'show_meetings': True,
                    'show_deadlines': True
                },
                data_source_config={
                    'type': DataSourceType.API.value,
                    'endpoint': '/api/v1/dashboards/data/project-calendar',
                    'method': 'GET'
                },
                supported_roles=['PROJECT_MANAGER', 'ADMIN', 'REQUIREMENT_MANAGER'],
                min_width=4, min_height=4, max_width=8, max_height=6,
                refresh_interval=600
            )
        ]
        
        return builtin_widgets
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证组件配置是否有效"""
        if not config:
            return True  # 空配置是有效的
        
        # 验证尺寸配置
        if 'width' in config and 'height' in config:
            if not self.validate_size(config['width'], config['height']):
                return False
        
        # 验证数据源配置
        if self.requires_data and 'data_source' in config:
            data_source = config['data_source']
            if not isinstance(data_source, dict):
                return False
            
            # 检查必需的数据源字段
            if 'type' not in data_source:
                return False
        
        return True
    
    def merge_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并用户配置和默认配置"""
        merged_config = self.default_config.copy() if self.default_config else {}
        
        if user_config:
            merged_config.update(user_config)
        
        return merged_config