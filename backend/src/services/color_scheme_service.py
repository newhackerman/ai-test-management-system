"""
配色方案服务

实现配色方案管理、预览、应用和分享功能，支持系统预设、企业定制和用户自定义配色
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
import json
import logging
import colorsys
import re
import asyncio
from fastapi import Depends
from PIL import Image, ImageDraw
import io
import base64

from ..models.color_scheme import ColorScheme, UserColorPreference, SchemeType, SchemeCategory
from ..models.user import User
from ..core.database import get_db
from ..services.permission import PermissionService
from ..utils.cache_utils import cache_client

logger = logging.getLogger(__name__)

class CacheManager:
    """简化的缓存管理器"""
    
    def __init__(self):
        self.cache_client = cache_client
    
    async def get(self, key: str):
        """获取缓存"""
        try:
            return await self.cache_client.aget("color_scheme", cache_key=key)
        except:
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        try:
            return await self.cache_client.aset("color_scheme", value, ttl, cache_key=key)
        except:
            return False
    
    async def delete(self, key: str):
        """删除缓存"""
        try:
            return await self.cache_client.adelete("color_scheme", cache_key=key)
        except:
            return False
    
    async def delete_pattern(self, pattern: str):
        """删除匹配模式的缓存"""
        try:
            return await self.cache_client.ainvalidate_pattern(pattern)
        except:
            return 0

class ColorSchemeService:
    """配色方案管理服务"""
    
    def __init__(self, db: Session, cache_manager: CacheManager = None, permission_service: PermissionService = None):
        self.db = db
        self.cache_manager = cache_manager or CacheManager()
        self.permission_service = permission_service or PermissionService(db)
    
    async def get_available_schemes(
        self, 
        user_id: int, 
        scheme_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[ColorScheme]:
        """
        获取用户可用的配色方案列表
        
        Args:
            user_id: 用户ID
            scheme_type: 方案类型过滤
            category: 分类过滤
            
        Returns:
            List[ColorScheme]: 可用配色方案列表
        """
        try:
            # 构建缓存键
            cache_key = f"available_schemes:{user_id}"
            if scheme_type:
                cache_key += f":{scheme_type}"
            if category:
                cache_key += f":{category}"
            
            # 尝试从缓存获取
            cached_schemes = await self.cache_manager.get(cache_key)
            if cached_schemes:
                logger.info(f"Retrieved available schemes from cache for user {user_id}")
                return [self._deserialize_scheme(scheme_data) for scheme_data in cached_schemes]
            
            # 构建查询
            query = self.db.query(ColorScheme).filter(
                ColorScheme.is_active == True
            )
            
            # 添加类型过滤
            if scheme_type:
                try:
                    scheme_type_enum = SchemeType(scheme_type)
                    query = query.filter(ColorScheme.scheme_type == scheme_type_enum)
                except ValueError:
                    logger.warning(f"Invalid scheme type: {scheme_type}")
            
            # 添加分类过滤
            if category:
                try:
                    category_enum = SchemeCategory(category)
                    query = query.filter(ColorScheme.scheme_category == category_enum)
                except ValueError:
                    logger.warning(f"Invalid category: {category}")
            
            # 获取用户信息以确定可访问的方案
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # 构建访问权限过滤条件
            access_conditions = [
                # 系统预设方案（公开）
                and_(
                    ColorScheme.scheme_type == SchemeType.SYSTEM,
                    ColorScheme.is_public == True
                ),
                # 用户自己创建的方案
                ColorScheme.created_by == user_id,
                # 公开的用户自定义方案
                and_(
                    ColorScheme.scheme_type == SchemeType.USER_CUSTOM,
                    ColorScheme.is_public == True
                )
            ]
            
            # 如果用户有组织ID，添加企业方案访问权限
            if hasattr(user, 'organization_id') and user.organization_id:
                access_conditions.append(
                    and_(
                        ColorScheme.scheme_type == SchemeType.ENTERPRISE,
                        ColorScheme.organization_id == user.organization_id
                    )
                )
            
            query = query.filter(or_(*access_conditions))
            
            # 按使用次数和创建时间排序
            schemes = query.order_by(
                desc(ColorScheme.is_default),
                desc(ColorScheme.usage_count),
                desc(ColorScheme.created_at)
            ).all()
            
            # 缓存结果
            scheme_data = [self._serialize_scheme(scheme) for scheme in schemes]
            await self.cache_manager.set(cache_key, scheme_data, ttl=3600)  # 1小时缓存
            
            logger.info(f"Retrieved {len(schemes)} available schemes for user {user_id}")
            return schemes
            
        except Exception as e:
            logger.error(f"Error getting available schemes for user {user_id}: {str(e)}")
            raise
    
    async def create_custom_scheme(
        self, 
        user_id: int, 
        scheme_name: str,
        color_palette: List[str],
        scheme_category: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False
    ) -> ColorScheme:
        """
        创建用户自定义配色方案
        
        Args:
            user_id: 用户ID
            scheme_name: 方案名称
            color_palette: 颜色数组
            scheme_category: 方案分类
            description: 方案描述
            is_public: 是否公开
            
        Returns:
            ColorScheme: 创建的配色方案
        """
        try:
            # 验证用户权限
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # 验证方案名称唯一性（用户范围内）
            existing_scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.created_by == user_id,
                    ColorScheme.scheme_name == scheme_name,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if existing_scheme:
                raise ValueError(f"Color scheme '{scheme_name}' already exists for this user")
            
            # 验证颜色格式
            if not color_palette or len(color_palette) < 2:
                raise ValueError("Color palette must contain at least 2 colors")
            
            if len(color_palette) > 16:
                raise ValueError("Color palette cannot contain more than 16 colors")
            
            for color in color_palette:
                if not ColorScheme.validate_color_format(color):
                    raise ValueError(f"Invalid color format: {color}")
            
            # 解析分类
            category_enum = None
            if scheme_category:
                try:
                    category_enum = SchemeCategory(scheme_category)
                except ValueError:
                    raise ValueError(f"Invalid scheme category: {scheme_category}")
            
            # 创建配色方案
            new_scheme = ColorScheme(
                scheme_name=scheme_name,
                scheme_type=SchemeType.USER_CUSTOM,
                scheme_category=category_enum,
                color_palette=color_palette,
                description=description,
                is_public=is_public,
                created_by=user_id,
                organization_id=getattr(user, 'organization_id', None)
            )
            
            # 验证配色方案
            if not new_scheme.validate_palette():
                raise ValueError("Invalid color palette")
            
            # 检查可访问性
            accessibility_report = new_scheme.check_accessibility()
            if accessibility_report['warnings']:
                logger.warning(f"Accessibility warnings for scheme '{scheme_name}': {accessibility_report['warnings']}")
            
            # 生成预览图片
            preview_image = await self._generate_preview_image(color_palette)
            new_scheme.preview_image = preview_image
            
            # 保存到数据库
            self.db.add(new_scheme)
            self.db.commit()
            self.db.refresh(new_scheme)
            
            # 清除相关缓存
            await self._clear_user_schemes_cache(user_id)
            
            logger.info(f"Created custom color scheme '{scheme_name}' for user {user_id}")
            return new_scheme
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating custom scheme for user {user_id}: {str(e)}")
            raise
    
    async def apply_scheme_to_user(
        self, 
        user_id: int, 
        scheme_id: int,
        apply_to_charts: bool = True,
        apply_to_widgets: bool = True,
        apply_to_theme: bool = False
    ) -> UserColorPreference:
        """
        应用配色方案到用户
        
        Args:
            user_id: 用户ID
            scheme_id: 配色方案ID
            apply_to_charts: 是否应用到图表
            apply_to_widgets: 是否应用到组件
            apply_to_theme: 是否应用到整体主题
            
        Returns:
            UserColorPreference: 用户配色偏好
        """
        try:
            # 验证用户和配色方案
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.id == scheme_id,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if not scheme:
                raise ValueError(f"Color scheme {scheme_id} not found or inactive")
            
            # 检查用户是否有权限访问该配色方案
            has_access = await self._check_scheme_access(user_id, scheme)
            if not has_access:
                raise ValueError(f"User {user_id} does not have access to scheme {scheme_id}")
            
            # 获取或创建用户配色偏好
            preference = self.db.query(UserColorPreference).filter(
                UserColorPreference.user_id == user_id
            ).first()
            
            if preference:
                # 更新现有偏好
                preference.color_scheme_id = scheme_id
                preference.apply_to_charts = apply_to_charts
                preference.apply_to_widgets = apply_to_widgets
                preference.apply_to_theme = apply_to_theme
                preference.updated_at = datetime.utcnow()
            else:
                # 创建新偏好
                preference = UserColorPreference(
                    user_id=user_id,
                    color_scheme_id=scheme_id,
                    apply_to_charts=apply_to_charts,
                    apply_to_widgets=apply_to_widgets,
                    apply_to_theme=apply_to_theme
                )
                self.db.add(preference)
            
            # 增加配色方案使用次数
            scheme.increment_usage()
            
            # 提交更改
            self.db.commit()
            self.db.refresh(preference)
            
            # 清除用户相关缓存
            await self._clear_user_preference_cache(user_id)
            
            logger.info(f"Applied color scheme {scheme_id} to user {user_id}")
            return preference
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error applying scheme {scheme_id} to user {user_id}: {str(e)}")
            raise
    
    async def get_user_preference(self, user_id: int) -> Optional[UserColorPreference]:
        """
        获取用户配色偏好
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[UserColorPreference]: 用户配色偏好
        """
        try:
            # 尝试从缓存获取
            cache_key = f"user_preference:{user_id}"
            cached_preference = await self.cache_manager.get(cache_key)
            if cached_preference:
                return self._deserialize_preference(cached_preference)
            
            # 从数据库查询
            preference = self.db.query(UserColorPreference).filter(
                UserColorPreference.user_id == user_id
            ).first()
            
            if preference:
                # 缓存结果
                preference_data = self._serialize_preference(preference)
                await self.cache_manager.set(cache_key, preference_data, ttl=3600)
            
            return preference
            
        except Exception as e:
            logger.error(f"Error getting user preference for user {user_id}: {str(e)}")
            return None
    
    async def get_effective_colors(self, user_id: int) -> List[str]:
        """
        获取用户的有效配色方案
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[str]: 有效的颜色数组
        """
        try:
            preference = await self.get_user_preference(user_id)
            
            if preference:
                return preference.get_effective_colors()
            
            # 返回默认配色方案
            default_scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.scheme_type == SchemeType.SYSTEM,
                    ColorScheme.is_default == True,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if default_scheme and default_scheme.color_palette:
                return default_scheme.color_palette
            
            # 最后的备用配色
            return ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
            
        except Exception as e:
            logger.error(f"Error getting effective colors for user {user_id}: {str(e)}")
            return ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    
    async def preview_scheme(self, color_palette: List[str]) -> Dict[str, Any]:
        """
        预览配色方案效果
        
        Args:
            color_palette: 颜色数组
            
        Returns:
            Dict[str, Any]: 预览信息
        """
        try:
            # 验证颜色格式
            for color in color_palette:
                if not ColorScheme.validate_color_format(color):
                    raise ValueError(f"Invalid color format: {color}")
            
            # 创建临时配色方案对象进行分析
            temp_scheme = ColorScheme(
                scheme_name="Preview",
                scheme_type=SchemeType.USER_CUSTOM,
                color_palette=color_palette
            )
            
            # 检查可访问性
            accessibility_report = temp_scheme.check_accessibility()
            
            # 生成预览图片
            preview_image = await self._generate_preview_image(color_palette)
            
            # 分析颜色特性
            color_analysis = await self._analyze_color_characteristics(color_palette)
            
            return {
                'color_palette': color_palette,
                'preview_image': preview_image,
                'accessibility': accessibility_report,
                'analysis': color_analysis,
                'recommendations': await self._get_color_recommendations(color_palette)
            }
            
        except Exception as e:
            logger.error(f"Error previewing color scheme: {str(e)}")
            raise
    
    async def share_scheme(self, user_id: int, scheme_id: int, make_public: bool = True) -> bool:
        """
        分享配色方案
        
        Args:
            user_id: 用户ID
            scheme_id: 配色方案ID
            make_public: 是否设为公开
            
        Returns:
            bool: 分享是否成功
        """
        try:
            # 验证用户权限
            scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.id == scheme_id,
                    ColorScheme.created_by == user_id,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if not scheme:
                raise ValueError(f"Color scheme {scheme_id} not found or not owned by user {user_id}")
            
            # 更新公开状态
            scheme.is_public = make_public
            scheme.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # 清除相关缓存
            await self._clear_schemes_cache()
            
            logger.info(f"Scheme {scheme_id} sharing status updated to {make_public} by user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error sharing scheme {scheme_id}: {str(e)}")
            return False
    
    async def rate_scheme(self, user_id: int, scheme_id: int, rating: float) -> bool:
        """
        评价配色方案
        
        Args:
            user_id: 用户ID
            scheme_id: 配色方案ID
            rating: 评分 (0-5)
            
        Returns:
            bool: 评价是否成功
        """
        try:
            if not (0 <= rating <= 5):
                raise ValueError("Rating must be between 0 and 5")
            
            scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.id == scheme_id,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if not scheme:
                raise ValueError(f"Color scheme {scheme_id} not found")
            
            # 检查用户是否有权限访问该配色方案
            has_access = await self._check_scheme_access(user_id, scheme)
            if not has_access:
                raise ValueError(f"User {user_id} does not have access to scheme {scheme_id}")
            
            # 这里应该有一个评分记录表，简化处理直接更新平均评分
            # 实际项目中应该创建 scheme_ratings 表来记录每个用户的评分
            total_ratings = 1  # 简化处理，实际应该查询评分记录数
            scheme.update_rating(rating, total_ratings)
            
            self.db.commit()
            
            logger.info(f"User {user_id} rated scheme {scheme_id} with {rating}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rating scheme {scheme_id}: {str(e)}")
            return False
    
    async def delete_custom_scheme(self, user_id: int, scheme_id: int) -> bool:
        """
        删除用户自定义配色方案
        
        Args:
            user_id: 用户ID
            scheme_id: 配色方案ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.id == scheme_id,
                    ColorScheme.created_by == user_id,
                    ColorScheme.scheme_type == SchemeType.USER_CUSTOM,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if not scheme:
                raise ValueError(f"Custom color scheme {scheme_id} not found or not owned by user {user_id}")
            
            # 软删除
            scheme.is_active = False
            scheme.updated_at = datetime.utcnow()
            
            # 更新使用该方案的用户偏好
            preferences = self.db.query(UserColorPreference).filter(
                UserColorPreference.color_scheme_id == scheme_id
            ).all()
            
            for preference in preferences:
                preference.color_scheme_id = None
                preference.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # 清除相关缓存
            await self._clear_user_schemes_cache(user_id)
            
            logger.info(f"Deleted custom color scheme {scheme_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting scheme {scheme_id}: {str(e)}")
            return False
    
    async def initialize_system_schemes(self) -> bool:
        """
        初始化系统预设配色方案
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 检查是否已经初始化
            existing_count = self.db.query(ColorScheme).filter(
                ColorScheme.scheme_type == SchemeType.SYSTEM
            ).count()
            
            if existing_count > 0:
                logger.info("System color schemes already initialized")
                return True
            
            # 创建系统预设方案
            system_schemes = ColorScheme.create_system_schemes()
            
            for scheme in system_schemes:
                # 生成预览图片
                if scheme.color_palette:
                    scheme.preview_image = await self._generate_preview_image(scheme.color_palette)
                
                self.db.add(scheme)
            
            self.db.commit()
            
            # 清除缓存
            await self._clear_schemes_cache()
            
            logger.info(f"Initialized {len(system_schemes)} system color schemes")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initializing system schemes: {str(e)}")
            return False
    
    # 私有辅助方法
    
    async def _check_scheme_access(self, user_id: int, scheme: ColorScheme) -> bool:
        """检查用户是否有权限访问配色方案"""
        try:
            # 系统公开方案
            if scheme.scheme_type == SchemeType.SYSTEM and scheme.is_public:
                return True
            
            # 用户自己创建的方案
            if scheme.created_by == user_id:
                return True
            
            # 公开的用户自定义方案
            if scheme.scheme_type == SchemeType.USER_CUSTOM and scheme.is_public:
                return True
            
            # 企业方案权限检查
            if scheme.scheme_type == SchemeType.ENTERPRISE:
                user = self.db.query(User).filter(User.id == user_id).first()
                if user and hasattr(user, 'organization_id') and user.organization_id == scheme.organization_id:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking scheme access: {str(e)}")
            return False
    
    async def _generate_preview_image(self, color_palette: List[str]) -> str:
        """生成配色方案预览图片"""
        try:
            # 创建预览图片 (200x50像素)
            width, height = 200, 50
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)
            
            # 计算每个颜色块的宽度
            color_width = width // len(color_palette)
            
            # 绘制颜色块
            for i, color in enumerate(color_palette):
                if color.startswith('#'):
                    # 处理HEX颜色
                    x1 = i * color_width
                    x2 = (i + 1) * color_width
                    draw.rectangle([x1, 0, x2, height], fill=color)
            
            # 转换为base64字符串
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{image_data}"
            
        except Exception as e:
            logger.error(f"Error generating preview image: {str(e)}")
            return ""
    
    async def _analyze_color_characteristics(self, color_palette: List[str]) -> Dict[str, Any]:
        """分析配色方案的特性"""
        try:
            analysis = {
                'dominant_hue': None,
                'brightness_range': {'min': 1.0, 'max': 0.0},
                'saturation_range': {'min': 1.0, 'max': 0.0},
                'color_harmony': 'unknown',
                'temperature': 'neutral'
            }
            
            hues = []
            brightnesses = []
            saturations = []
            
            for color in color_palette:
                if color.startswith('#'):
                    # 转换HEX到HSV
                    hex_color = color.lstrip('#')
                    if len(hex_color) == 3:
                        hex_color = ''.join([c*2 for c in hex_color])
                    
                    r = int(hex_color[0:2], 16) / 255.0
                    g = int(hex_color[2:4], 16) / 255.0
                    b = int(hex_color[4:6], 16) / 255.0
                    
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    
                    hues.append(h * 360)  # 转换为度数
                    saturations.append(s)
                    brightnesses.append(v)
            
            if hues:
                # 分析主导色调
                avg_hue = sum(hues) / len(hues)
                if avg_hue < 60 or avg_hue > 300:
                    analysis['dominant_hue'] = 'red'
                elif avg_hue < 120:
                    analysis['dominant_hue'] = 'yellow'
                elif avg_hue < 180:
                    analysis['dominant_hue'] = 'green'
                elif avg_hue < 240:
                    analysis['dominant_hue'] = 'cyan'
                elif avg_hue < 300:
                    analysis['dominant_hue'] = 'blue'
                else:
                    analysis['dominant_hue'] = 'magenta'
                
                # 分析亮度和饱和度范围
                analysis['brightness_range'] = {'min': min(brightnesses), 'max': max(brightnesses)}
                analysis['saturation_range'] = {'min': min(saturations), 'max': max(saturations)}
                
                # 分析色彩温度
                warm_colors = sum(1 for h in hues if 0 <= h <= 60 or 300 <= h <= 360)
                cool_colors = sum(1 for h in hues if 180 <= h <= 300)
                
                if warm_colors > cool_colors:
                    analysis['temperature'] = 'warm'
                elif cool_colors > warm_colors:
                    analysis['temperature'] = 'cool'
                else:
                    analysis['temperature'] = 'neutral'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing color characteristics: {str(e)}")
            return {}
    
    async def _get_color_recommendations(self, color_palette: List[str]) -> List[str]:
        """获取配色建议"""
        try:
            recommendations = []
            
            # 检查颜色数量
            if len(color_palette) < 4:
                recommendations.append("建议增加更多颜色以提供更丰富的视觉效果")
            elif len(color_palette) > 8:
                recommendations.append("考虑减少颜色数量以避免视觉混乱")
            
            # 检查对比度
            temp_scheme = ColorScheme(color_palette=color_palette)
            accessibility_report = temp_scheme.check_accessibility()
            
            if accessibility_report.get('min_contrast', 0) < 3.0:
                recommendations.append("部分颜色对比度较低，建议调整以提高可读性")
            
            # 分析颜色特性
            analysis = await self._analyze_color_characteristics(color_palette)
            
            if analysis.get('saturation_range', {}).get('max', 0) > 0.9:
                recommendations.append("部分颜色饱和度过高，可能造成视觉疲劳")
            
            if analysis.get('brightness_range', {}).get('min', 1) < 0.2:
                recommendations.append("部分颜色过暗，在某些背景下可能不易识别")
            
            if not recommendations:
                recommendations.append("配色方案整体平衡良好")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting color recommendations: {str(e)}")
            return ["无法生成建议"]
    
    def _serialize_scheme(self, scheme: ColorScheme) -> Dict[str, Any]:
        """序列化配色方案对象"""
        return scheme.to_dict()
    
    def _deserialize_scheme(self, scheme_data: Dict[str, Any]) -> ColorScheme:
        """反序列化配色方案对象"""
        scheme = ColorScheme()
        for key, value in scheme_data.items():
            if hasattr(scheme, key):
                setattr(scheme, key, value)
        return scheme
    
    def _serialize_preference(self, preference: UserColorPreference) -> Dict[str, Any]:
        """序列化用户偏好对象"""
        return preference.to_dict()
    
    def _deserialize_preference(self, preference_data: Dict[str, Any]) -> UserColorPreference:
        """反序列化用户偏好对象"""
        preference = UserColorPreference()
        for key, value in preference_data.items():
            if hasattr(preference, key):
                setattr(preference, key, value)
        return preference
    
    async def _clear_user_schemes_cache(self, user_id: int):
        """清除用户配色方案相关缓存"""
        try:
            cache_patterns = [
                f"available_schemes:{user_id}*",
                f"user_preference:{user_id}"
            ]
            
            for pattern in cache_patterns:
                await self.cache_manager.delete_pattern(pattern)
                
        except Exception as e:
            logger.error(f"Error clearing user schemes cache: {str(e)}")
    
    async def _clear_user_preference_cache(self, user_id: int):
        """清除用户偏好缓存"""
        try:
            cache_key = f"user_preference:{user_id}"
            await self.cache_manager.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error clearing user preference cache: {str(e)}")
    
    async def _clear_schemes_cache(self):
        """清除所有配色方案缓存"""
        try:
            await self.cache_manager.delete_pattern("available_schemes:*")
            
        except Exception as e:
            logger.error(f"Error clearing schemes cache: {str(e)}")
# 全局服务实例

_color_scheme_service = None


def get_color_scheme_service(db: Session = Depends(get_db)) -> ColorSchemeService:
    """
    获取配色方案服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        ColorSchemeService: 配色方案服务实例
    """
    return ColorSchemeService(db)


