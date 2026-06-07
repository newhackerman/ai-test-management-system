"""
仪表板管理数据模型
"""
from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON, Integer, Boolean, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum as PyEnum

from ..core.database import Base

class RoleType(PyEnum):
    """角色类型枚举"""
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    REQUIREMENT_MANAGER = "REQUIREMENT_MANAGER"
    DESIGNER = "DESIGNER"
    ARCHITECT = "ARCHITECT"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    DEVOPS = "DEVOPS"
    THIRD_PARTY = "THIRD_PARTY"

class WidgetCategory(PyEnum):
    """组件分类枚举"""
    STATISTICS = "STATISTICS"  # 统计类
    CHARTS = "CHARTS"  # 图表类
    PROGRESS = "PROGRESS"  # 进度类
    STATUS = "STATUS"  # 状态类
    RANKING = "RANKING"  # 排行类
    CALENDAR = "CALENDAR"  # 日历类
    MAP = "MAP"  # 地图类
    TABLE = "TABLE"  # 表格类

class SchemeType(PyEnum):
    """配色方案类型枚举"""
    SYSTEM = "SYSTEM"  # 系统预设
    ENTERPRISE = "ENTERPRISE"  # 企业定制
    USER_CUSTOM = "USER_CUSTOM"  # 用户自定义

class DashboardConfig(Base):
    """仪表板配置模型"""
    __tablename__ = 'dashboard_configs'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='配置ID')
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    role_type = Column(Enum(RoleType), nullable=False, comment='角色类型')
    dashboard_name = Column(String(100), nullable=False, comment='仪表板名称')
    is_default = Column(Boolean, default=False, comment='是否默认配置')
    
    # 配置信息
    layout_config = Column(JSON, comment='布局配置')
    widget_configs = Column(JSON, comment='组件配置列表')
    theme_config = Column(JSON, comment='主题配置')
    refresh_interval = Column(Integer, default=30, comment='刷新间隔(秒)')
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<DashboardConfig(id={self.id}, user_id={self.user_id}, role='{self.role_type}')>"

class WidgetDefinition(Base):
    """组件定义模型"""
    __tablename__ = 'widget_definitions'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='组件定义ID')
    widget_type = Column(String(50), unique=True, nullable=False, comment='组件类型')
    widget_name = Column(String(100), nullable=False, comment='组件名称')
    description = Column(Text, comment='组件描述')
    category = Column(Enum(WidgetCategory), nullable=False, comment='组件分类')
    
    # 配置信息
    default_config = Column(JSON, comment='默认配置')
    data_source_config = Column(JSON, comment='数据源配置')
    supported_roles = Column(JSON, comment='支持的角色列表')
    
    # 尺寸限制
    min_width = Column(Integer, default=2, comment='最小宽度')
    min_height = Column(Integer, default=2, comment='最小高度')
    max_width = Column(Integer, default=12, comment='最大宽度')
    max_height = Column(Integer, default=12, comment='最大高度')
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<WidgetDefinition(id={self.id}, type='{self.widget_type}', name='{self.widget_name}')>"

class ColorScheme(Base):
    """配色方案模型"""
    __tablename__ = 'color_schemes'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='配色方案ID')
    scheme_name = Column(String(100), nullable=False, comment='方案名称')
    scheme_type = Column(Enum(SchemeType), nullable=False, comment='方案类型')
    scheme_category = Column(String(50), comment='方案分类（商务、科技、清新等）')
    
    # 配色信息
    color_palette = Column(JSON, nullable=False, comment='颜色数组')
    description = Column(Text, comment='方案描述')
    preview_image = Column(String(500), comment='预览图片路径')
    
    # 方案属性
    is_default = Column(Boolean, default=False, comment='是否默认方案')
    is_public = Column(Boolean, default=False, comment='是否公开方案')
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 创建者信息
    created_by = Column(BigInteger, comment='创建者ID')
    organization_id = Column(BigInteger, comment='组织ID（企业方案）')
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment='使用次数')
    rating = Column(DECIMAL(3, 2), default=0.00, comment='用户评分')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<ColorScheme(id={self.id}, name='{self.scheme_name}', type='{self.scheme_type}')>"

class UserColorPreferences(Base):
    """用户配色偏好模型"""
    __tablename__ = 'user_color_preferences'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='偏好ID')
    user_id = Column(BigInteger, nullable=False, unique=True, comment='用户ID')
    color_scheme_id = Column(BigInteger, comment='选择的配色方案ID')
    custom_colors = Column(JSON, comment='用户自定义颜色')
    
    # 偏好设置
    auto_switch_dark_mode = Column(Boolean, default=False, comment='是否自动切换暗色模式')
    accessibility_mode = Column(Boolean, default=False, comment='是否启用无障碍模式')
    high_contrast = Column(Boolean, default=False, comment='是否启用高对比度')
    
    # 应用范围
    apply_to_charts = Column(Boolean, default=True, comment='是否应用到图表')
    apply_to_widgets = Column(Boolean, default=True, comment='是否应用到组件')
    apply_to_theme = Column(Boolean, default=False, comment='是否应用到整体主题')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<UserColorPreferences(id={self.id}, user_id={self.user_id})>"

class DashboardDataCache(Base):
    """仪表板数据缓存模型"""
    __tablename__ = 'dashboard_data_cache'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='缓存ID')
    cache_key = Column(String(255), nullable=False, unique=True, comment='缓存键')
    data_type = Column(String(50), nullable=False, comment='数据类型')
    data_content = Column(JSON, nullable=False, comment='数据内容')
    
    # 关联信息
    project_id = Column(BigInteger, comment='关联项目ID')
    user_id = Column(BigInteger, comment='关联用户ID')
    
    # 缓存管理
    expires_at = Column(DateTime, nullable=False, comment='过期时间')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<DashboardDataCache(id={self.id}, key='{self.cache_key}', type='{self.data_type}')>"

class WebSocketConnection(Base):
    """WebSocket连接管理模型"""
    __tablename__ = 'websocket_connections'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='连接ID')
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    connection_id = Column(String(255), nullable=False, unique=True, comment='连接标识')
    role_type = Column(Enum(RoleType), nullable=False, comment='角色类型')
    
    # 连接信息
    project_ids = Column(JSON, comment='订阅的项目ID列表')
    subscribed_events = Column(JSON, comment='订阅的事件类型')
    client_info = Column(JSON, comment='客户端信息')
    
    # 连接状态
    is_active = Column(Boolean, default=True, comment='是否活跃')
    last_heartbeat = Column(DateTime, default=datetime.utcnow, comment='最后心跳时间')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<WebSocketConnection(id={self.id}, user_id={self.user_id}, connection_id='{self.connection_id}')>"