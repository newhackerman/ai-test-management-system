"""
配色方案数据模型

实现ColorScheme SQLAlchemy模型，支持多种配色方案和用户偏好管理
"""

from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON, Integer, Boolean, Index, ForeignKey, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Dict, List, Any, Optional
import re

Base = declarative_base()

class SchemeType(PyEnum):
    """配色方案类型枚举"""
    SYSTEM = "SYSTEM"  # 系统预设方案
    ENTERPRISE = "ENTERPRISE"  # 企业定制方案
    USER_CUSTOM = "USER_CUSTOM"  # 用户自定义方案

class SchemeCategory(PyEnum):
    """配色方案分类枚举"""
    BUSINESS = "BUSINESS"  # 商务风格
    TECHNOLOGY = "TECHNOLOGY"  # 科技风格
    FRESH = "FRESH"  # 清新风格
    CLASSIC = "CLASSIC"  # 经典风格
    MODERN = "MODERN"  # 现代风格
    DARK = "DARK"  # 暗色主题
    LIGHT = "LIGHT"  # 亮色主题
    COLORFUL = "COLORFUL"  # 多彩风格

class ColorScheme(Base):
    """
    配色方案表
    
    管理系统、企业和用户自定义的配色方案
    """
    __tablename__ = 'color_schemes'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='配色方案ID')
    scheme_name = Column(String(100), nullable=False, comment='方案名称')
    scheme_type = Column(Enum(SchemeType), nullable=False, comment='方案类型')
    scheme_category = Column(Enum(SchemeCategory), comment='方案分类')
    
    # 配色信息
    color_palette = Column(JSON, nullable=False, comment='颜色数组JSON')
    description = Column(Text, comment='方案描述')
    preview_image = Column(String(500), comment='预览图片路径')
    
    # 方案属性
    is_default = Column(Boolean, default=False, comment='是否默认方案')
    is_public = Column(Boolean, default=False, comment='是否公开方案')
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 创建者信息
    created_by = Column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'), comment='创建者ID')
    organization_id = Column(BigInteger, comment='组织ID（企业方案）')
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment='使用次数')
    rating = Column(DECIMAL(3, 2), default=0.00, comment='用户评分')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_scheme_type', 'scheme_type'),
        Index('idx_scheme_category', 'scheme_category'),
        Index('idx_is_default', 'is_default'),
        Index('idx_is_public', 'is_public'),
        Index('idx_created_by', 'created_by'),
        Index('idx_organization_id', 'organization_id'),
        Index('idx_usage_count', 'usage_count'),
        Index('idx_type_category', 'scheme_type', 'scheme_category'),
        {'comment': '配色方案表'}
    )
    
    def __repr__(self):
        return f"<ColorScheme(id={self.id}, name='{self.scheme_name}', type='{self.scheme_type.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'scheme_name': self.scheme_name,
            'scheme_type': self.scheme_type.value if self.scheme_type else None,
            'scheme_category': self.scheme_category.value if self.scheme_category else None,
            'color_palette': self.color_palette,
            'description': self.description,
            'preview_image': self.preview_image,
            'is_default': self.is_default,
            'is_public': self.is_public,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'organization_id': self.organization_id,
            'usage_count': self.usage_count,
            'rating': float(self.rating) if self.rating else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def validate_color_format(cls, color: str) -> bool:
        """验证颜色格式是否有效"""
        if not color or not isinstance(color, str):
            return False
        
        # 支持的颜色格式：HEX (#RRGGBB, #RGB), RGB (rgb(r,g,b)), RGBA (rgba(r,g,b,a))
        hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        rgb_pattern = r'^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$'
        rgba_pattern = r'^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0|1|0?\.\d+)\s*\)$'
        
        if re.match(hex_pattern, color):
            return True
        
        if re.match(rgb_pattern, color):
            # 验证RGB值范围
            match = re.match(rgb_pattern, color)
            r, g, b = map(int, match.groups())
            return all(0 <= val <= 255 for val in [r, g, b])
        
        if re.match(rgba_pattern, color):
            # 验证RGBA值范围
            match = re.match(rgba_pattern, color)
            r, g, b, a = match.groups()
            r, g, b = map(int, [r, g, b])
            a = float(a)
            return all(0 <= val <= 255 for val in [r, g, b]) and 0 <= a <= 1
        
        return False
    
    def validate_palette(self) -> bool:
        """验证配色方案是否有效"""
        if not self.color_palette or not isinstance(self.color_palette, list):
            return False
        
        # 至少需要2种颜色，最多16种颜色
        if len(self.color_palette) < 2 or len(self.color_palette) > 16:
            return False
        
        # 验证每个颜色格式
        for color in self.color_palette:
            if not self.validate_color_format(color):
                return False
        
        return True
    
    def calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """计算两个颜色的对比度比值"""
        def hex_to_rgb(hex_color: str) -> tuple:
            """将HEX颜色转换为RGB"""
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def get_luminance(rgb: tuple) -> float:
            """计算颜色亮度"""
            def normalize(c):
                c = c / 255.0
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r, g, b = map(normalize, rgb)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        try:
            # 只处理HEX格式的颜色
            if not (color1.startswith('#') and color2.startswith('#')):
                return 1.0
            
            rgb1 = hex_to_rgb(color1)
            rgb2 = hex_to_rgb(color2)
            
            lum1 = get_luminance(rgb1)
            lum2 = get_luminance(rgb2)
            
            # 确保较亮的颜色在分子位置
            if lum1 < lum2:
                lum1, lum2 = lum2, lum1
            
            return (lum1 + 0.05) / (lum2 + 0.05)
        
        except Exception:
            return 1.0
    
    def check_accessibility(self) -> Dict[str, Any]:
        """检查配色方案的可访问性"""
        if not self.validate_palette():
            return {'valid': False, 'errors': ['Invalid color palette']}
        
        accessibility_report = {
            'valid': True,
            'warnings': [],
            'contrast_ratios': [],
            'min_contrast': float('inf'),
            'max_contrast': 0.0
        }
        
        # 检查相邻颜色的对比度
        for i in range(len(self.color_palette) - 1):
            color1 = self.color_palette[i]
            color2 = self.color_palette[i + 1]
            
            if color1.startswith('#') and color2.startswith('#'):
                contrast_ratio = self.calculate_contrast_ratio(color1, color2)
                accessibility_report['contrast_ratios'].append({
                    'color1': color1,
                    'color2': color2,
                    'ratio': contrast_ratio
                })
                
                accessibility_report['min_contrast'] = min(accessibility_report['min_contrast'], contrast_ratio)
                accessibility_report['max_contrast'] = max(accessibility_report['max_contrast'], contrast_ratio)
                
                # WCAG 2.1 AA标准要求对比度至少为3:1
                if contrast_ratio < 3.0:
                    accessibility_report['warnings'].append(
                        f"Low contrast between {color1} and {color2}: {contrast_ratio:.2f}:1"
                    )
        
        return accessibility_report
    
    @classmethod
    def create_system_schemes(cls) -> List['ColorScheme']:
        """创建系统预设配色方案"""
        system_schemes = [
            # 默认蓝色商务方案
            cls(
                scheme_name='默认蓝色',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.BUSINESS,
                color_palette=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'],
                description='经典的蓝色商务配色方案，适合大多数商业场景',
                is_default=True,
                is_public=True
            ),
            
            # 绿色生态方案
            cls(
                scheme_name='绿色生态',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.FRESH,
                color_palette=['#2ca02c', '#98df8a', '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#d62728', '#ff9896'],
                description='清新的绿色主题，适合环保和健康相关的项目',
                is_public=True
            ),
            
            # 紫色科技方案
            cls(
                scheme_name='紫色科技',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.TECHNOLOGY,
                color_palette=['#9467bd', '#c5b0d5', '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a'],
                description='现代科技感的紫色配色，适合技术和创新项目',
                is_public=True
            ),
            
            # 橙色活力方案
            cls(
                scheme_name='橙色活力',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.MODERN,
                color_palette=['#ff7f0e', '#ffbb78', '#d62728', '#ff9896', '#2ca02c', '#98df8a', '#1f77b4', '#aec7e8'],
                description='充满活力的橙色主题，适合营销和创意项目',
                is_public=True
            ),
            
            # 红色警示方案
            cls(
                scheme_name='红色警示',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.CLASSIC,
                color_palette=['#d62728', '#ff9896', '#ff7f0e', '#ffbb78', '#1f77b4', '#aec7e8', '#2ca02c', '#98df8a'],
                description='醒目的红色警示配色，适合风险监控和紧急情况',
                is_public=True
            ),
            
            # 青色清新方案
            cls(
                scheme_name='青色清新',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.FRESH,
                color_palette=['#17becf', '#9edae5', '#2ca02c', '#98df8a', '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78'],
                description='清新的青色主题，适合数据分析和报告展示',
                is_public=True
            ),
            
            # 极客暗色方案
            cls(
                scheme_name='极客暗色',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.DARK,
                color_palette=['#00ff00', '#00ffff', '#ff00ff', '#ffff00', '#ff6600', '#6600ff', '#0066ff', '#ff0066'],
                description='程序员喜爱的暗色高对比配色，适合开发环境',
                is_public=True
            ),
            
            # 商业经典方案
            cls(
                scheme_name='商业经典',
                scheme_type=SchemeType.SYSTEM,
                scheme_category=SchemeCategory.CLASSIC,
                color_palette=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#592E83', '#1B998B', '#ED217C', '#F4B942'],
                description='经典的商业配色组合，适合正式的商业报告',
                is_public=True
            )
        ]
        
        return system_schemes
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1
    
    def update_rating(self, new_rating: float, total_ratings: int):
        """更新评分"""
        if 0 <= new_rating <= 5:
            current_total = float(self.rating) * (total_ratings - 1)
            self.rating = (current_total + new_rating) / total_ratings


class UserColorPreference(Base):
    """
    用户配色偏好表
    
    存储用户的配色偏好和自定义设置
    """
    __tablename__ = 'user_color_preferences'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='偏好ID')
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, comment='用户ID')
    color_scheme_id = Column(BigInteger, ForeignKey('color_schemes.id', ondelete='SET NULL'), comment='选择的配色方案ID')
    
    # 自定义颜色
    custom_colors = Column(JSON, comment='用户自定义颜色JSON')
    
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
    
    # 关系
    color_scheme = relationship("ColorScheme", backref="user_preferences")
    
    # 索引优化
    __table_args__ = (
        Index('idx_color_scheme_id', 'color_scheme_id'),
        {'comment': '用户配色偏好表'}
    )
    
    def __repr__(self):
        return f"<UserColorPreference(id={self.id}, user_id={self.user_id}, scheme_id={self.color_scheme_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'color_scheme_id': self.color_scheme_id,
            'custom_colors': self.custom_colors,
            'auto_switch_dark_mode': self.auto_switch_dark_mode,
            'accessibility_mode': self.accessibility_mode,
            'high_contrast': self.high_contrast,
            'apply_to_charts': self.apply_to_charts,
            'apply_to_widgets': self.apply_to_widgets,
            'apply_to_theme': self.apply_to_theme,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_effective_colors(self) -> List[str]:
        """获取有效的配色方案"""
        if self.custom_colors and isinstance(self.custom_colors, list):
            return self.custom_colors
        
        if self.color_scheme and self.color_scheme.color_palette:
            return self.color_scheme.color_palette
        
        # 返回默认配色
        return ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']