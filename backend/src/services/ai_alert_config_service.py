"""
AI告警配置服务
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_, update, delete
from sqlalchemy.orm import selectinload

from ..models.ai_alert_config import AIAlertConfig, AIAlertHistory, AIAlertSuppression, AlertType, AlertLevel, AlertStatus
from ..models.ai_usage_stats import AIUsageStats
from ..models.ai_model_config import AIModelConfig
from ..schemas.ai_alert_config import (
    AlertConfigCreate, 
    AlertConfigUpdate, 
    AlertConfigResponse,
    AlertConfigList,
    AlertHistoryResponse,
    AlertHistoryList,
    AlertSuppressionCreate,
    AlertSuppressionResponse,
    AlertTestRequest,
    AlertTestResponse,
    AlertStatsResponse,
    AlertTemplateResponse,
    AlertTemplateVariable
)
from ..core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class AIAlertConfigService:
    """AI告警配置服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 告警模板
        self.alert_templates = {
            AlertType.COST_BUDGET: {
                "default_template": "成本预算告警: {alert_name}\n当前成本: ${current_value:.2f}\n预算限制: ${threshold_value:.2f}\n使用率: {percentage:.1%}\n触发时间: {triggered_at}",
                "variables": [
                    AlertTemplateVariable(name="alert_name", description="告警名称", example="系统月度预算"),
                    AlertTemplateVariable(name="current_value", description="当前成本", example="850.50"),
                    AlertTemplateVariable(name="threshold_value", description="预算限制", example="1000.00"),
                    AlertTemplateVariable(name="percentage", description="使用率", example="0.85"),
                    AlertTemplateVariable(name="triggered_at", description="触发时间", example="2024-01-15 10:30:00")
                ]
            },
            AlertType.TOKEN_QUOTA: {
                "default_template": "Token配额告警: {alert_name}\n当前使用: {current_value:,} tokens\n配额限制: {threshold_value:,} tokens\n使用率: {percentage:.1%}\n触发时间: {triggered_at}",
                "variables": [
                    AlertTemplateVariable(name="alert_name", description="告警名称", example="用户日Token配额"),
                    AlertTemplateVariable(name="current_value", description="当前Token数", example="45000"),
                    AlertTemplateVariable(name="threshold_value", description="配额限制", example="50000"),
                    AlertTemplateVariable(name="percentage", description="使用率", example="0.90"),
                    AlertTemplateVariable(name="triggered_at", description="触发时间", example="2024-01-15 10:30:00")
                ]
            },
            AlertType.REQUEST_QUOTA: {
                "default_template": "请求配额告警: {alert_name}\n当前请求数: {current_value:,}\n配额限制: {threshold_value:,}\n使用率: {percentage:.1%}\n触发时间: {triggered_at}",
                "variables": [
                    AlertTemplateVariable(name="alert_name", description="告警名称", example="系统日请求配额"),
                    AlertTemplateVariable(name="current_value", description="当前请求数", example="9500"),
                    AlertTemplateVariable(name="threshold_value", description="配额限制", example="10000"),
                    AlertTemplateVariable(name="percentage", description="使用率", example="0.95"),
                    AlertTemplateVariable(name="triggered_at", description="触发时间", example="2024-01-15 10:30:00")
                ]
            },
            AlertType.RESPONSE_TIME: {
                "default_template": "响应时间告警: {alert_name}\n当前响应时间: {current_value:.2f}秒\n阈值: {threshold_value:.2f}秒\n提供商: {provider}\n触发时间: {triggered_at}",
                "variables": [
                    AlertTemplateVariable(name="alert_name", description="告警名称", example="响应时间过长"),
                    AlertTemplateVariable(name="current_value", description="当前响应时间", example="12.5"),
                    AlertTemplateVariable(name="threshold_value", description="阈值", example="10.0"),
                    AlertTemplateVariable(name="provider", description="AI提供商", example="openai"),
                    AlertTemplateVariable(name="triggered_at", description="触发时间", example="2024-01-15 10:30:00")
                ]
            },
            AlertType.ERROR_RATE: {
                "default_template": "错误率告警: {alert_name}\n当前错误率: {percentage:.1%}\n阈值: {threshold_percentage:.1%}\n提供商: {provider}\n触发时间: {triggered_at}",
                "variables": [
                    AlertTemplateVariable(name="alert_name", description="告警名称", example="错误率过高"),
                    AlertTemplateVariable(name="percentage", description="当前错误率", example="0.15"),
                    AlertTemplateVariable(name="threshold_percentage", description="阈值错误率", example="0.10"),
                    AlertTemplateVariable(name="provider", description="AI提供商", example="anthropic"),
                    AlertTemplateVariable(name="triggered_at", description="触发时间", example="2024-01-15 10:30:00")
                ]
            },
            AlertType.MODEL_HEALTH: {
                "default_template": "模型健康状态告警: {alert_name}\n模型: {model_name}\n状态: {health_status}\n提供商: {provider}\n触发时间: {triggered_at}",
                "variables": [
                    AlertTemplateVariable(name="alert_name", description="告警名称", example="模型不可用"),
                    AlertTemplateVariable(name="model_name", description="模型名称", example="gpt-4"),
                    AlertTemplateVariable(name="health_status", description="健康状态", example="UNHEALTHY"),
                    AlertTemplateVariable(name="provider", description="AI提供商", example="openai"),
                    AlertTemplateVariable(name="triggered_at", description="触发时间", example="2024-01-15 10:30:00")
                ]
            }
        }
    
    async def create_alert_config(
        self, 
        db: AsyncSession, 
        config_data: AlertConfigCreate,
        created_by: int
    ) -> AlertConfigResponse:
        """创建告警配置"""
        # 检查名称是否已存在
        existing = await self._get_config_by_name(db, config_data.name)
        if existing:
            raise ValidationError(f"告警配置名称已存在: {config_data.name}")
        
        # 验证配置
        await self._validate_alert_config(config_data)
        
        # 创建配置
        config = AIAlertConfig(**config_data.dict())
        config.created_by = created_by
        config.created_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"创建告警配置: {config.name} (ID: {config.id})")
        return AlertConfigResponse.from_orm(config)
    
    async def get_alert_configs(
        self,
        db: AsyncSession,
        alert_type: Optional[AlertType] = None,
        alert_level: Optional[AlertLevel] = None,
        status: Optional[AlertStatus] = None,
        created_by: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> AlertConfigList:
        """获取告警配置列表"""
        query = select(AIAlertConfig)
        
        # 添加过滤条件
        conditions = []
        if alert_type:
            conditions.append(AIAlertConfig.alert_type == alert_type)
        if alert_level:
            conditions.append(AIAlertConfig.alert_level == alert_level)
        if status:
            conditions.append(AIAlertConfig.status == status)
        if created_by:
            conditions.append(AIAlertConfig.created_by == created_by)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序和分页
        query = query.order_by(
            desc(AIAlertConfig.alert_level == AlertLevel.CRITICAL),
            desc(AIAlertConfig.alert_level == AlertLevel.WARNING),
            desc(AIAlertConfig.created_at)
        ).offset(skip).limit(limit)
        
        result = await db.execute(query)
        configs = result.scalars().all()
        
        # 获取总数
        count_query = select(func.count(AIAlertConfig.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return AlertConfigList(
            items=[AlertConfigResponse.from_orm(config) for config in configs],
            total=total,
            skip=skip,
            limit=limit
        )
    
    async def get_alert_config(
        self, 
        db: AsyncSession, 
        config_id: int
    ) -> AlertConfigResponse:
        """获取单个告警配置"""
        config = await self._get_config_by_id(db, config_id)
        return AlertConfigResponse.from_orm(config)
    
    async def update_alert_config(
        self, 
        db: AsyncSession, 
        config_id: int, 
        update_data: AlertConfigUpdate
    ) -> AlertConfigResponse:
        """更新告警配置"""
        config = await self._get_config_by_id(db, config_id)
        
        # 检查名称冲突
        if update_data.name and update_data.name != config.name:
            existing = await self._get_config_by_name(db, update_data.name)
            if existing and existing.id != config_id:
                raise ValidationError(f"告警配置名称已存在: {update_data.name}")
        
        # 更新配置
        update_dict = update_data.dict(exclude_unset=True)
        update_dict['updated_at'] = datetime.utcnow()
        
        for field, value in update_dict.items():
            setattr(config, field, value)
        
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"更新告警配置: {config.name} (ID: {config.id})")
        return AlertConfigResponse.from_orm(config)
    
    async def delete_alert_config(self, db: AsyncSession, config_id: int) -> bool:
        """删除告警配置"""
        config = await self._get_config_by_id(db, config_id)
        
        # 检查是否有历史记录
        history_query = select(func.count(AIAlertHistory.id)).where(
            AIAlertHistory.alert_config_id == config_id
        )
        history_result = await db.execute(history_query)
        history_count = history_result.scalar()
        
        if history_count > 0:
            # 软删除：只禁用配置
            config.status = AlertStatus.DISABLED
            config.updated_at = datetime.utcnow()
            await db.commit()
            logger.info(f"软删除告警配置: {config.name} (ID: {config.id})")
        else:
            # 硬删除：完全删除配置
            await db.delete(config)
            await db.commit()
            logger.info(f"删除告警配置: {config.name} (ID: {config.id})")
        
        return True
    
    async def test_alert_config(
        self,
        db: AsyncSession,
        config_id: int,
        test_request: AlertTestRequest
    ) -> AlertTestResponse:
        """测试告警配置"""
        config = await self._get_config_by_id(db, config_id)
        
        # 模拟告警评估
        would_trigger = self._evaluate_threshold(
            test_request.test_value,
            config.threshold_value,
            config.threshold_operator
        )
        
        # 生成告警消息
        alert_message = await self._generate_alert_message(
            config,
            test_request.test_value,
            test_request.test_context or {}
        )
        
        return AlertTestResponse(
            would_trigger=would_trigger,
            alert_message=alert_message,
            alert_level=config.alert_level,
            test_details={
                "test_value": test_request.test_value,
                "threshold_value": config.threshold_value,
                "threshold_operator": config.threshold_operator,
                "evaluation_result": would_trigger,
                "config_name": config.name,
                "config_type": config.alert_type
            }
        )
    
    async def get_alert_history(
        self,
        db: AsyncSession,
        config_id: Optional[int] = None,
        alert_level: Optional[AlertLevel] = None,
        status: Optional[AlertStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> AlertHistoryList:
        """获取告警历史"""
        query = select(AIAlertHistory)
        
        # 添加过滤条件
        conditions = []
        if config_id:
            conditions.append(AIAlertHistory.alert_config_id == config_id)
        if alert_level:
            conditions.append(AIAlertHistory.alert_level == alert_level)
        if status:
            conditions.append(AIAlertHistory.status == status)
        if start_date:
            conditions.append(AIAlertHistory.created_at >= start_date)
        if end_date:
            conditions.append(AIAlertHistory.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序和分页
        query = query.order_by(desc(AIAlertHistory.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        history_records = result.scalars().all()
        
        # 获取总数
        count_query = select(func.count(AIAlertHistory.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return AlertHistoryList(
            items=[AlertHistoryResponse.from_orm(record) for record in history_records],
            total=total,
            skip=skip,
            limit=limit
        )
    
    async def resolve_alert(
        self,
        db: AsyncSession,
        history_id: int,
        resolved_by: int,
        resolution_note: Optional[str] = None
    ) -> AlertHistoryResponse:
        """解决告警"""
        query = select(AIAlertHistory).where(AIAlertHistory.id == history_id)
        result = await db.execute(query)
        alert_history = result.scalar_one_or_none()
        
        if not alert_history:
            raise NotFoundError(f"告警历史记录不存在: {history_id}")
        
        if alert_history.status == AlertStatus.RESOLVED:
            raise ValidationError("告警已经被解决")
        
        # 更新状态
        alert_history.status = AlertStatus.RESOLVED
        alert_history.resolved_at = datetime.utcnow()
        alert_history.resolved_by = resolved_by
        alert_history.resolution_note = resolution_note
        alert_history.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(alert_history)
        
        logger.info(f"解决告警: {history_id} by user {resolved_by}")
        return AlertHistoryResponse.from_orm(alert_history)
    
    async def suppress_alert(
        self,
        db: AsyncSession,
        suppression_data: AlertSuppressionCreate,
        created_by: int
    ) -> AlertSuppressionResponse:
        """抑制告警"""
        # 验证告警配置存在
        await self._get_config_by_id(db, suppression_data.alert_config_id)
        
        # 计算抑制到期时间
        suppressed_until = datetime.utcnow() + timedelta(minutes=suppression_data.suppress_duration_minutes)
        
        # 创建抑制记录
        suppression = AIAlertSuppression(
            alert_config_id=suppression_data.alert_config_id,
            suppression_reason=suppression_data.suppression_reason,
            suppressed_until=suppressed_until,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(suppression)
        await db.commit()
        await db.refresh(suppression)
        
        logger.info(f"抑制告警配置: {suppression_data.alert_config_id} until {suppressed_until}")
        return AlertSuppressionResponse.from_orm(suppression)
    
    async def get_alert_stats(self, db: AsyncSession) -> AlertStatsResponse:
        """获取告警统计"""
        today = date.today()
        
        # 基础统计
        total_configs_query = select(func.count(AIAlertConfig.id))
        total_configs_result = await db.execute(total_configs_query)
        total_configs = total_configs_result.scalar()
        
        active_configs_query = select(func.count(AIAlertConfig.id)).where(
            AIAlertConfig.status == AlertStatus.ACTIVE
        )
        active_configs_result = await db.execute(active_configs_query)
        active_configs = active_configs_result.scalar()
        
        triggered_today_query = select(func.count(AIAlertHistory.id)).where(
            func.date(AIAlertHistory.created_at) == today
        )
        triggered_today_result = await db.execute(triggered_today_query)
        triggered_today = triggered_today_result.scalar()
        
        resolved_today_query = select(func.count(AIAlertHistory.id)).where(
            and_(
                func.date(AIAlertHistory.resolved_at) == today,
                AIAlertHistory.status == AlertStatus.RESOLVED
            )
        )
        resolved_today_result = await db.execute(resolved_today_query)
        resolved_today = resolved_today_result.scalar()
        
        # 按类型统计
        by_type_query = select(
            AIAlertConfig.alert_type,
            func.count(AIAlertConfig.id).label('count')
        ).group_by(AIAlertConfig.alert_type)
        by_type_result = await db.execute(by_type_query)
        by_type = {row.alert_type: row.count for row in by_type_result}
        
        # 按级别统计
        by_level_query = select(
            AIAlertConfig.alert_level,
            func.count(AIAlertConfig.id).label('count')
        ).group_by(AIAlertConfig.alert_level)
        by_level_result = await db.execute(by_level_query)
        by_level = {row.alert_level: row.count for row in by_level_result}
        
        # 按状态统计
        by_status_query = select(
            AIAlertConfig.status,
            func.count(AIAlertConfig.id).label('count')
        ).group_by(AIAlertConfig.status)
        by_status_result = await db.execute(by_status_query)
        by_status = {row.status: row.count for row in by_status_result}
        
        # 每日触发趋势（最近7天）
        seven_days_ago = today - timedelta(days=7)
        daily_triggers_query = select(
            func.date(AIAlertHistory.created_at).label('date'),
            func.count(AIAlertHistory.id).label('count')
        ).where(
            func.date(AIAlertHistory.created_at) >= seven_days_ago
        ).group_by(func.date(AIAlertHistory.created_at)).order_by(func.date(AIAlertHistory.created_at))
        
        daily_triggers_result = await db.execute(daily_triggers_query)
        daily_triggers = [
            {"date": str(row.date), "count": row.count}
            for row in daily_triggers_result
        ]
        
        # 触发最多的配置（前5个）
        top_triggered_query = select(
            AIAlertConfig.id,
            AIAlertConfig.name,
            AIAlertConfig.trigger_count
        ).where(
            AIAlertConfig.trigger_count > 0
        ).order_by(desc(AIAlertConfig.trigger_count)).limit(5)
        
        top_triggered_result = await db.execute(top_triggered_query)
        top_triggered_configs = [
            {"id": row.id, "name": row.name, "trigger_count": row.trigger_count}
            for row in top_triggered_result
        ]
        
        return AlertStatsResponse(
            total_configs=total_configs,
            active_configs=active_configs,
            triggered_today=triggered_today,
            resolved_today=resolved_today,
            by_type=by_type,
            by_level=by_level,
            by_status=by_status,
            daily_triggers=daily_triggers,
            top_triggered_configs=top_triggered_configs
        )
    
    async def get_alert_template(self, alert_type: AlertType) -> AlertTemplateResponse:
        """获取告警模板"""
        if alert_type not in self.alert_templates:
            raise ValidationError(f"不支持的告警类型: {alert_type}")
        
        template_info = self.alert_templates[alert_type]
        return AlertTemplateResponse(
            alert_type=alert_type,
            default_template=template_info["default_template"],
            available_variables=template_info["variables"]
        )
    
    async def toggle_alert_config(
        self,
        db: AsyncSession,
        config_id: int
    ) -> AlertConfigResponse:
        """切换告警配置状态"""
        config = await self._get_config_by_id(db, config_id)
        
        # 切换状态
        if config.status == AlertStatus.ACTIVE:
            config.status = AlertStatus.INACTIVE
        elif config.status == AlertStatus.INACTIVE:
            config.status = AlertStatus.ACTIVE
        else:
            raise ValidationError(f"无法切换状态: {config.status}")
        
        config.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"切换告警配置状态: {config.name} -> {config.status}")
        return AlertConfigResponse.from_orm(config)
    
    async def _get_config_by_id(self, db: AsyncSession, config_id: int) -> AIAlertConfig:
        """根据ID获取配置"""
        query = select(AIAlertConfig).where(AIAlertConfig.id == config_id)
        result = await db.execute(query)
        config = result.scalar_one_or_none()
        
        if not config:
            raise NotFoundError(f"告警配置不存在: {config_id}")
        
        return config
    
    async def _get_config_by_name(self, db: AsyncSession, name: str) -> Optional[AIAlertConfig]:
        """根据名称获取配置"""
        query = select(AIAlertConfig).where(AIAlertConfig.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _validate_alert_config(self, config_data: AlertConfigCreate):
        """验证告警配置"""
        # 验证阈值设置
        if config_data.alert_type in [AlertType.COST_BUDGET, AlertType.TOKEN_QUOTA, AlertType.REQUEST_QUOTA]:
            if not config_data.threshold_value or config_data.threshold_value <= 0:
                raise ValidationError(f"{config_data.alert_type} 类型的告警必须设置正数阈值")
        
        # 验证时间窗口
        if config_data.evaluation_frequency_minutes > config_data.time_window_minutes:
            raise ValidationError("评估频率不能大于时间窗口")
        
        # 验证自动解决配置
        if config_data.auto_resolve and not config_data.auto_resolve_threshold:
            raise ValidationError("启用自动解决时必须设置自动解决阈值")
    
    def _evaluate_threshold(self, current_value: float, threshold_value: float, operator: str) -> bool:
        """评估阈值条件"""
        if operator == ">=":
            return current_value >= threshold_value
        elif operator == "<=":
            return current_value <= threshold_value
        elif operator == ">":
            return current_value > threshold_value
        elif operator == "<":
            return current_value < threshold_value
        elif operator == "==":
            return abs(current_value - threshold_value) < 0.001  # 浮点数比较
        elif operator == "!=":
            return abs(current_value - threshold_value) >= 0.001
        else:
            return False
    
    async def _generate_alert_message(
        self,
        config: AIAlertConfig,
        current_value: float,
        context: Dict[str, Any]
    ) -> str:
        """生成告警消息"""
        template = config.notification_template
        if not template and config.alert_type in self.alert_templates:
            template = self.alert_templates[config.alert_type]["default_template"]
        
        if not template:
            template = "告警触发: {alert_name}\n当前值: {current_value}\n阈值: {threshold_value}"
        
        # 准备模板变量
        variables = {
            "alert_name": config.name,
            "current_value": current_value,
            "threshold_value": config.threshold_value,
            "triggered_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "alert_level": config.alert_level,
            "alert_type": config.alert_type,
            **context
        }
        
        # 计算百分比（如果适用）
        if config.threshold_value and config.threshold_value > 0:
            variables["percentage"] = current_value / config.threshold_value
        
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"模板变量缺失: {e}")
            return f"告警触发: {config.name} (当前值: {current_value}, 阈值: {config.threshold_value})"