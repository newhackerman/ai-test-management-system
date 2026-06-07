"""
仪表板配置数据模型

实现DashboardConfig SQLAlchemy模型，支持角色化配置和用户个性化定制
"""

from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON, Integer, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, List, Any

Base = declarative_base()

class RoleType(PyEnum):
    """用户角色类型枚举"""
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    REQUIREMENT_MANAGER = "REQUIREMENT_MANAGER"
    DESIGNER = "DESIGNER"
    ARCHITECT = "ARCHITECT"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    DEVOPS = "DEVOPS"
    THIRD_PARTY = "THIRD_PARTY"

class DashboardConfig(Base):
    """
    仪表板配置表
    
    支持角色化仪表板配置和用户个性化定制
    """
    __tablename__ = 'dashboard_configs'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='配置ID')
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    role_type = Column(Enum(RoleType), nullable=False, comment='角色类型')
    dashboard_name = Column(String(100), nullable=False, comment='仪表板名称')
    is_default = Column(Boolean, default=False, comment='是否默认配置')
    
    # 配置信息
    layout_config = Column(JSON, comment='布局配置JSON')
    widget_configs = Column(JSON, comment='组件配置列表JSON')
    theme_config = Column(JSON, comment='主题配置JSON')
    refresh_interval = Column(Integer, default=30, comment='刷新间隔(秒)')
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_user_role', 'user_id', 'role_type'),
        Index('idx_role_type', 'role_type'),
        Index('idx_is_default', 'is_default'),
        Index('idx_is_active', 'is_active'),
        {'comment': '仪表板配置表'}
    )
    
    def __repr__(self):
        return f"<DashboardConfig(id={self.id}, user_id={self.user_id}, role='{self.role_type.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role_type': self.role_type.value if self.role_type else None,
            'dashboard_name': self.dashboard_name,
            'is_default': self.is_default,
            'layout_config': self.layout_config,
            'widget_configs': self.widget_configs,
            'theme_config': self.theme_config,
            'refresh_interval': self.refresh_interval,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_default_config(cls, user_id: int, role_type: RoleType) -> 'DashboardConfig':
        """创建默认配置"""
        default_layouts = {
            RoleType.ADMIN: {
                'grid_cols': 12,
                'grid_rows': 8,
                'widgets': [
                    {'type': 'system_overview', 'x': 0, 'y': 0, 'w': 6, 'h': 3},
                    {'type': 'user_statistics', 'x': 6, 'y': 0, 'w': 6, 'h': 3},
                    {'type': 'project_summary', 'x': 0, 'y': 3, 'w': 12, 'h': 5}
                ]
            },
            RoleType.PROJECT_MANAGER: {
                'grid_cols': 12,
                'grid_rows': 8,
                'widgets': [
                    {'type': 'project_overview', 'x': 0, 'y': 0, 'w': 8, 'h': 4},
                    {'type': 'team_status', 'x': 8, 'y': 0, 'w': 4, 'h': 4},
                    {'type': 'milestone_progress', 'x': 0, 'y': 4, 'w': 6, 'h': 4},
                    {'type': 'risk_monitor', 'x': 6, 'y': 4, 'w': 6, 'h': 4}
                ]
            },
            RoleType.DEVELOPER: {
                'grid_cols': 12,
                'grid_rows': 6,
                'widgets': [
                    {'type': 'my_tasks', 'x': 0, 'y': 0, 'w': 6, 'h': 3},
                    {'type': 'code_quality', 'x': 6, 'y': 0, 'w': 6, 'h': 3},
                    {'type': 'team_activity', 'x': 0, 'y': 3, 'w': 12, 'h': 3}
                ]
            },
            RoleType.TESTER: {
                'grid_cols': 12,
                'grid_rows': 6,
                'widgets': [
                    {'type': 'test_execution', 'x': 0, 'y': 0, 'w': 6, 'h': 3},
                    {'type': 'defect_summary', 'x': 6, 'y': 0, 'w': 6, 'h': 3},
                    {'type': 'quality_metrics', 'x': 0, 'y': 3, 'w': 12, 'h': 3}
                ]
            }
        }
        
        # 获取角色默认布局，如果没有则使用通用布局
        layout = default_layouts.get(role_type, default_layouts[RoleType.DEVELOPER])
        
        return cls(
            user_id=user_id,
            role_type=role_type,
            dashboard_name=f"{role_type.value}_dashboard",
            is_default=True,
            layout_config=layout,
            widget_configs=[],
            theme_config={
                'color_scheme': 'default',
                'dark_mode': False,
                'compact_mode': False
            },
            refresh_interval=30,
            is_active=True
        )
    
    def validate_layout_config(self) -> bool:
        """验证布局配置的有效性"""
        if not self.layout_config:
            return False
        
        required_fields = ['grid_cols', 'grid_rows', 'widgets']
        for field in required_fields:
            if field not in self.layout_config:
                return False
        
        # 验证网格配置
        if not isinstance(self.layout_config['grid_cols'], int) or self.layout_config['grid_cols'] <= 0:
            return False
        if not isinstance(self.layout_config['grid_rows'], int) or self.layout_config['grid_rows'] <= 0:
            return False
        
        # 验证组件配置
        widgets = self.layout_config['widgets']
        if not isinstance(widgets, list):
            return False
        
        for widget in widgets:
            required_widget_fields = ['type', 'x', 'y', 'w', 'h']
            for field in required_widget_fields:
                if field not in widget:
                    return False
            
            # 验证位置和尺寸
            if (widget['x'] < 0 or widget['y'] < 0 or 
                widget['w'] <= 0 or widget['h'] <= 0):
                return False
            
            # 验证是否超出网格范围
            if (widget['x'] + widget['w'] > self.layout_config['grid_cols'] or
                widget['y'] + widget['h'] > self.layout_config['grid_rows']):
                return False
        
        return True
    
    def get_widget_by_type(self, widget_type: str) -> Optional[Dict[str, Any]]:
        """根据类型获取组件配置"""
        if not self.layout_config or 'widgets' not in self.layout_config:
            return None
        
        for widget in self.layout_config['widgets']:
            if widget.get('type') == widget_type:
                return widget
        
        return None
    
    def add_widget(self, widget_config: Dict[str, Any]) -> bool:
        """添加组件到布局"""
        if not self.layout_config:
            self.layout_config = {'grid_cols': 12, 'grid_rows': 8, 'widgets': []}
        
        if 'widgets' not in self.layout_config:
            self.layout_config['widgets'] = []
        
        # 验证组件配置
        required_fields = ['type', 'x', 'y', 'w', 'h']
        for field in required_fields:
            if field not in widget_config:
                return False
        
        # 检查位置冲突
        if self._has_position_conflict(widget_config):
            return False
        
        self.layout_config['widgets'].append(widget_config)
        return True
    
    def remove_widget(self, widget_type: str) -> bool:
        """从布局中移除组件"""
        if not self.layout_config or 'widgets' not in self.layout_config:
            return False
        
        original_count = len(self.layout_config['widgets'])
        self.layout_config['widgets'] = [
            w for w in self.layout_config['widgets'] 
            if w.get('type') != widget_type
        ]
        
        return len(self.layout_config['widgets']) < original_count
    
    def _has_position_conflict(self, new_widget: Dict[str, Any]) -> bool:
        """检查组件位置是否冲突"""
        if not self.layout_config or 'widgets' not in self.layout_config:
            return False
        
        new_x1, new_y1 = new_widget['x'], new_widget['y']
        new_x2, new_y2 = new_x1 + new_widget['w'], new_y1 + new_widget['h']
        
        for widget in self.layout_config['widgets']:
            x1, y1 = widget['x'], widget['y']
            x2, y2 = x1 + widget['w'], y1 + widget['h']
            
            # 检查矩形重叠
            if not (new_x2 <= x1 or new_x1 >= x2 or new_y2 <= y1 or new_y1 >= y2):
                return True
        
        return False