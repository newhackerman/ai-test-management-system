"""
布局管理服务

实现拖拽布局的保存和恢复、响应式布局、多设备适配和布局模板管理
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
import json
import logging
import copy

from ..models.dashboard_config import DashboardConfig, RoleType
from ..models.widget_definition import WidgetDefinition
from ..core.database import get_db
from ..utils.redis_client import RedisCache

logger = logging.getLogger(__name__)

class LayoutService:
    """布局管理服务"""
    
    def __init__(self, db: Session, cache_manager: RedisCache = None):
        self.db = db
        self.cache_manager = cache_manager or RedisCache("layout")
        
        # 响应式断点配置
        self.breakpoints = {
            'xs': {'max_width': 575, 'cols': 4},
            'sm': {'max_width': 767, 'cols': 6},
            'md': {'max_width': 991, 'cols': 8},
            'lg': {'max_width': 1199, 'cols': 10},
            'xl': {'max_width': float('inf'), 'cols': 12}
        }
    
    async def save_layout(
        self, 
        user_id: int, 
        role_type: str, 
        layout_config: Dict[str, Any],
        device_type: str = 'desktop'
    ) -> DashboardConfig:
        """
        保存布局配置
        
        Args:
            user_id: 用户ID
            role_type: 角色类型
            layout_config: 布局配置
            device_type: 设备类型
            
        Returns:
            DashboardConfig: 保存后的配置对象
        """
        try:
            # 验证布局配置
            validation_result = await self.validate_layout(layout_config)
            if not validation_result['valid']:
                raise ValueError(f"Invalid layout: {', '.join(validation_result['errors'])}")
            
            # 获取或创建配置
            config = self.db.query(DashboardConfig).filter(
                and_(
                    DashboardConfig.user_id == user_id,
                    DashboardConfig.role_type == RoleType(role_type)
                )
            ).first()
            
            if not config:
                config = DashboardConfig(
                    user_id=user_id,
                    role_type=RoleType(role_type),
                    dashboard_name=f"{role_type}_dashboard",
                    is_default=False,
                    layout_config={},
                    widget_configs=[],
                    theme_config={},
                    is_active=True
                )
                self.db.add(config)
            
            # 保存设备特定的布局
            if not config.layout_config:
                config.layout_config = {}
            
            config.layout_config[device_type] = layout_config
            config.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(config)
            
            # 清除缓存
            cache_key = f"layout:{user_id}:{role_type}:{device_type}"
            await self.cache_manager.delete(cache_key)
            
            logger.info(f"Saved layout for user {user_id}, role {role_type}, device {device_type}")
            return config
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving layout: {str(e)}")
            raise
    
    async def get_layout(
        self, 
        user_id: int, 
        role_type: str, 
        device_type: str = 'desktop'
    ) -> Optional[Dict[str, Any]]:
        """
        获取布局配置
        
        Args:
            user_id: 用户ID
            role_type: 角色类型
            device_type: 设备类型
            
        Returns:
            Dict[str, Any]: 布局配置
        """
        try:
            # 尝试从缓存获取
            cache_key = f"layout:{user_id}:{role_type}:{device_type}"
            cached_layout = await self.cache_manager.get(cache_key)
            if cached_layout:
                logger.info(f"Retrieved layout from cache for user {user_id}, role {role_type}, device {device_type}")
                return cached_layout
            
            # 从数据库获取
            config = self.db.query(DashboardConfig).filter(
                and_(
                    DashboardConfig.user_id == user_id,
                    DashboardConfig.role_type == RoleType(role_type),
                    DashboardConfig.is_active == True
                )
            ).first()
            
            if not config or not config.layout_config:
                # 返回默认布局
                default_layout = await self._get_default_layout(role_type, device_type)
                return default_layout
            
            # 获取设备特定布局
            device_layout = config.layout_config.get(device_type)
            if not device_layout:
                # 尝试获取桌面版布局并适配
                desktop_layout = config.layout_config.get('desktop')
                if desktop_layout:
                    device_layout = await self._adapt_layout_for_device(desktop_layout, device_type)
                else:
                    device_layout = await self._get_default_layout(role_type, device_type)
            
            # 缓存结果
            await self.cache_manager.set(cache_key, device_layout, ttl=1800)
            
            logger.info(f"Retrieved layout for user {user_id}, role {role_type}, device {device_type}")
            return device_layout
            
        except Exception as e:
            logger.error(f"Error getting layout: {str(e)}")
            return None
    
    async def validate_layout(self, layout_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证布局配置
        
        Args:
            layout_config: 布局配置
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        errors = []
        warnings = []
        
        try:
            # 检查必需字段
            required_fields = ['grid_cols', 'grid_rows', 'widgets']
            for field in required_fields:
                if field not in layout_config:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # 验证网格配置
            grid_cols = layout_config['grid_cols']
            grid_rows = layout_config['grid_rows']
            
            if not isinstance(grid_cols, int) or grid_cols <= 0:
                errors.append("grid_cols must be a positive integer")
            
            if not isinstance(grid_rows, int) or grid_rows <= 0:
                errors.append("grid_rows must be a positive integer")
            
            # 验证组件配置
            widgets = layout_config['widgets']
            if not isinstance(widgets, list):
                errors.append("widgets must be a list")
            else:
                # 检查组件重叠
                overlap_result = self._check_widget_overlaps(widgets)
                if overlap_result['has_overlaps']:
                    errors.extend(overlap_result['errors'])
                
                # 验证每个组件
                for i, widget in enumerate(widgets):
                    widget_errors = self._validate_widget_layout(widget, grid_cols, grid_rows)
                    if widget_errors:
                        errors.extend([f"Widget {i}: {error}" for error in widget_errors])
                
                # 检查组件是否超出网格
                out_of_bounds = self._check_widgets_bounds(widgets, grid_cols, grid_rows)
                if out_of_bounds:
                    errors.extend(out_of_bounds)
            
            # 性能警告
            if len(widgets) > 20:
                warnings.append("Large number of widgets may affect performance")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating layout: {str(e)}")
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': warnings
            }
    
    async def auto_layout_widgets(
        self, 
        widgets: List[Dict[str, Any]], 
        grid_cols: int = 12, 
        grid_rows: int = 8
    ) -> Dict[str, Any]:
        """
        自动布局组件
        
        Args:
            widgets: 组件列表
            grid_cols: 网格列数
            grid_rows: 网格行数
            
        Returns:
            Dict[str, Any]: 自动布局后的配置
        """
        try:
            # 按优先级和尺寸排序组件
            sorted_widgets = sorted(widgets, key=lambda w: (
                -w.get('priority', 0),  # 优先级降序
                -w.get('w', 4) * w.get('h', 3)  # 面积降序
            ))
            
            # 初始化网格占用矩阵
            grid = [[False for _ in range(grid_cols)] for _ in range(grid_rows)]
            
            positioned_widgets = []
            
            for widget in sorted_widgets:
                width = widget.get('w', 4)
                height = widget.get('h', 3)
                
                # 确保组件尺寸不超过网格
                width = min(width, grid_cols)
                height = min(height, grid_rows)
                
                # 寻找合适的位置
                position = self._find_best_position(grid, width, height, grid_cols, grid_rows)
                
                if position:
                    x, y = position
                    
                    # 标记网格占用
                    for row in range(y, y + height):
                        for col in range(x, x + width):
                            if row < grid_rows and col < grid_cols:
                                grid[row][col] = True
                    
                    # 添加位置信息
                    positioned_widget = widget.copy()
                    positioned_widget.update({
                        'x': x,
                        'y': y,
                        'w': width,
                        'h': height
                    })
                    positioned_widgets.append(positioned_widget)
                else:
                    logger.warning(f"Could not find position for widget: {widget.get('type', 'unknown')}")
            
            return {
                'grid_cols': grid_cols,
                'grid_rows': grid_rows,
                'widgets': positioned_widgets
            }
            
        except Exception as e:
            logger.error(f"Error in auto layout: {str(e)}")
            raise
    
    async def optimize_layout(self, layout_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化布局配置
        
        Args:
            layout_config: 原始布局配置
            
        Returns:
            Dict[str, Any]: 优化后的布局配置
        """
        try:
            optimized_config = copy.deepcopy(layout_config)
            widgets = optimized_config['widgets']
            
            # 1. 移除空隙
            widgets = self._compact_layout(widgets)
            
            # 2. 对齐组件
            widgets = self._align_widgets(widgets)
            
            # 3. 优化网格尺寸
            min_rows = self._calculate_min_rows(widgets)
            if min_rows < optimized_config['grid_rows']:
                optimized_config['grid_rows'] = min_rows
            
            optimized_config['widgets'] = widgets
            
            logger.info("Layout optimization completed")
            return optimized_config
            
        except Exception as e:
            logger.error(f"Error optimizing layout: {str(e)}")
            return layout_config
    
    async def create_responsive_layouts(
        self, 
        base_layout: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        创建响应式布局
        
        Args:
            base_layout: 基础布局（通常是桌面版）
            
        Returns:
            Dict[str, Dict[str, Any]]: 各设备的布局配置
        """
        try:
            responsive_layouts = {}
            
            for breakpoint, config in self.breakpoints.items():
                adapted_layout = await self._adapt_layout_for_breakpoint(
                    base_layout, 
                    config['cols']
                )
                responsive_layouts[breakpoint] = adapted_layout
            
            logger.info("Created responsive layouts for all breakpoints")
            return responsive_layouts
            
        except Exception as e:
            logger.error(f"Error creating responsive layouts: {str(e)}")
            raise
    
    async def detect_and_fix_conflicts(self, layout_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测并修复布局冲突
        
        Args:
            layout_config: 布局配置
            
        Returns:
            Dict[str, Any]: 修复后的布局配置
        """
        try:
            fixed_config = copy.deepcopy(layout_config)
            widgets = fixed_config['widgets']
            
            # 检测重叠
            overlaps = self._find_overlapping_widgets(widgets)
            
            if overlaps:
                logger.info(f"Found {len(overlaps)} overlapping widget pairs, fixing...")
                
                # 修复重叠
                widgets = self._resolve_overlaps(widgets, overlaps)
                fixed_config['widgets'] = widgets
            
            # 检测越界
            out_of_bounds = self._find_out_of_bounds_widgets(
                widgets, 
                fixed_config['grid_cols'], 
                fixed_config['grid_rows']
            )
            
            if out_of_bounds:
                logger.info(f"Found {len(out_of_bounds)} out-of-bounds widgets, fixing...")
                
                # 修复越界
                widgets = self._fix_out_of_bounds(
                    widgets, 
                    fixed_config['grid_cols'], 
                    fixed_config['grid_rows']
                )
                fixed_config['widgets'] = widgets
            
            return fixed_config
            
        except Exception as e:
            logger.error(f"Error detecting and fixing conflicts: {str(e)}")
            return layout_config
    
    async def _get_default_layout(self, role_type: str, device_type: str) -> Dict[str, Any]:
        """获取默认布局"""
        # 获取角色默认配置
        default_config = DashboardConfig.create_default_config(0, RoleType(role_type))
        base_layout = default_config.layout_config
        
        if device_type == 'desktop':
            return base_layout
        else:
            return await self._adapt_layout_for_device(base_layout, device_type)
    
    async def _adapt_layout_for_device(
        self, 
        desktop_layout: Dict[str, Any], 
        device_type: str
    ) -> Dict[str, Any]:
        """为特定设备适配布局"""
        if device_type == 'mobile':
            return await self._adapt_layout_for_breakpoint(desktop_layout, 4)
        elif device_type == 'tablet':
            return await self._adapt_layout_for_breakpoint(desktop_layout, 8)
        else:
            return desktop_layout
    
    async def _adapt_layout_for_breakpoint(
        self, 
        layout: Dict[str, Any], 
        target_cols: int
    ) -> Dict[str, Any]:
        """为特定断点适配布局"""
        adapted_layout = copy.deepcopy(layout)
        adapted_layout['grid_cols'] = target_cols
        
        widgets = adapted_layout['widgets']
        
        # 重新计算组件位置和尺寸
        for widget in widgets:
            # 缩放宽度
            original_cols = layout['grid_cols']
            scale_factor = target_cols / original_cols
            
            widget['w'] = max(1, int(widget['w'] * scale_factor))
            widget['x'] = int(widget['x'] * scale_factor)
            
            # 确保不超出边界
            if widget['x'] + widget['w'] > target_cols:
                widget['w'] = target_cols - widget['x']
                if widget['w'] <= 0:
                    widget['x'] = 0
                    widget['w'] = min(4, target_cols)
        
        # 重新布局以避免重叠
        adapted_layout = await self.auto_layout_widgets(
            widgets, 
            target_cols, 
            adapted_layout['grid_rows']
        )
        
        return adapted_layout
    
    def _validate_widget_layout(
        self, 
        widget: Dict[str, Any], 
        grid_cols: int, 
        grid_rows: int
    ) -> List[str]:
        """验证单个组件布局"""
        errors = []
        
        required_fields = ['type', 'x', 'y', 'w', 'h']
        for field in required_fields:
            if field not in widget:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return errors
        
        # 验证数值类型
        for field in ['x', 'y', 'w', 'h']:
            if not isinstance(widget[field], int):
                errors.append(f"{field} must be an integer")
        
        # 验证位置和尺寸
        if widget['x'] < 0 or widget['y'] < 0:
            errors.append("Position cannot be negative")
        
        if widget['w'] <= 0 or widget['h'] <= 0:
            errors.append("Size must be positive")
        
        # 验证边界
        if widget['x'] + widget['w'] > grid_cols:
            errors.append(f"Widget extends beyond grid width ({grid_cols})")
        
        if widget['y'] + widget['h'] > grid_rows:
            errors.append(f"Widget extends beyond grid height ({grid_rows})")
        
        return errors
    
    def _check_widget_overlaps(self, widgets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查组件重叠"""
        overlaps = []
        
        for i, widget1 in enumerate(widgets):
            for j, widget2 in enumerate(widgets[i+1:], i+1):
                if self._widgets_overlap(widget1, widget2):
                    overlaps.append((i, j))
        
        return {
            'has_overlaps': len(overlaps) > 0,
            'overlaps': overlaps,
            'errors': [f"Widgets {i} and {j} overlap" for i, j in overlaps]
        }
    
    def _widgets_overlap(self, widget1: Dict[str, Any], widget2: Dict[str, Any]) -> bool:
        """检查两个组件是否重叠"""
        x1, y1, w1, h1 = widget1['x'], widget1['y'], widget1['w'], widget1['h']
        x2, y2, w2, h2 = widget2['x'], widget2['y'], widget2['w'], widget2['h']
        
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)
    
    def _check_widgets_bounds(
        self, 
        widgets: List[Dict[str, Any]], 
        grid_cols: int, 
        grid_rows: int
    ) -> List[str]:
        """检查组件是否超出边界"""
        errors = []
        
        for i, widget in enumerate(widgets):
            if widget['x'] + widget['w'] > grid_cols:
                errors.append(f"Widget {i} extends beyond grid width")
            
            if widget['y'] + widget['h'] > grid_rows:
                errors.append(f"Widget {i} extends beyond grid height")
        
        return errors
    
    def _find_best_position(
        self, 
        grid: List[List[bool]], 
        width: int, 
        height: int, 
        grid_cols: int, 
        grid_rows: int
    ) -> Optional[Tuple[int, int]]:
        """寻找组件的最佳位置"""
        for y in range(grid_rows - height + 1):
            for x in range(grid_cols - width + 1):
                if self._can_place_widget(grid, x, y, width, height):
                    return (x, y)
        return None
    
    def _can_place_widget(
        self, 
        grid: List[List[bool]], 
        x: int, 
        y: int, 
        width: int, 
        height: int
    ) -> bool:
        """检查是否可以在指定位置放置组件"""
        for row in range(y, y + height):
            for col in range(x, x + width):
                if row >= len(grid) or col >= len(grid[0]) or grid[row][col]:
                    return False
        return True
    
    def _compact_layout(self, widgets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩布局，移除空隙"""
        # 按Y坐标排序
        sorted_widgets = sorted(widgets, key=lambda w: (w['y'], w['x']))
        
        # 向上移动组件
        for widget in sorted_widgets:
            min_y = 0
            
            # 找到可以移动到的最高位置
            for other in sorted_widgets:
                if (other != widget and 
                    other['x'] < widget['x'] + widget['w'] and 
                    other['x'] + other['w'] > widget['x']):
                    min_y = max(min_y, other['y'] + other['h'])
            
            widget['y'] = min_y
        
        return sorted_widgets
    
    def _align_widgets(self, widgets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对齐组件"""
        # 简单的左对齐实现
        for widget in widgets:
            # 可以添加更复杂的对齐逻辑
            pass
        
        return widgets
    
    def _calculate_min_rows(self, widgets: List[Dict[str, Any]]) -> int:
        """计算最小行数"""
        if not widgets:
            return 1
        
        max_bottom = max(widget['y'] + widget['h'] for widget in widgets)
        return max(1, max_bottom)
    
    def _find_overlapping_widgets(self, widgets: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """找到重叠的组件对"""
        overlaps = []
        
        for i, widget1 in enumerate(widgets):
            for j, widget2 in enumerate(widgets[i+1:], i+1):
                if self._widgets_overlap(widget1, widget2):
                    overlaps.append((i, j))
        
        return overlaps
    
    def _resolve_overlaps(
        self, 
        widgets: List[Dict[str, Any]], 
        overlaps: List[Tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """解决重叠问题"""
        # 简单的解决方案：移动后面的组件
        for i, j in overlaps:
            widget1, widget2 = widgets[i], widgets[j]
            
            # 将widget2移动到widget1下方
            widgets[j]['y'] = widget1['y'] + widget1['h']
        
        return widgets
    
    def _find_out_of_bounds_widgets(
        self, 
        widgets: List[Dict[str, Any]], 
        grid_cols: int, 
        grid_rows: int
    ) -> List[int]:
        """找到越界的组件"""
        out_of_bounds = []
        
        for i, widget in enumerate(widgets):
            if (widget['x'] + widget['w'] > grid_cols or 
                widget['y'] + widget['h'] > grid_rows):
                out_of_bounds.append(i)
        
        return out_of_bounds
    
    def _fix_out_of_bounds(
        self, 
        widgets: List[Dict[str, Any]], 
        grid_cols: int, 
        grid_rows: int
    ) -> List[Dict[str, Any]]:
        """修复越界组件"""
        for widget in widgets:
            # 调整位置
            if widget['x'] + widget['w'] > grid_cols:
                widget['x'] = max(0, grid_cols - widget['w'])
                if widget['x'] < 0:
                    widget['w'] = grid_cols
                    widget['x'] = 0
            
            if widget['y'] + widget['h'] > grid_rows:
                widget['y'] = max(0, grid_rows - widget['h'])
                if widget['y'] < 0:
                    widget['h'] = grid_rows
                    widget['y'] = 0
        
        return widgets