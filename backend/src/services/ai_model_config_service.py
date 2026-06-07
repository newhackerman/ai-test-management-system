"""
AI模型配置服务
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, update, delete
from sqlalchemy.orm import selectinload

from ..models.ai_model_config import AIModelConfig
from ..models.ai_usage_stats import AIUsageStats
from ..schemas.ai_model_config import (
    AIModelConfigCreate, 
    AIModelConfigUpdate, 
    AIModelConfigResponse,
    AIModelConfigList,
    AIProviderStats,
    AIModelHealthCheck
)
from ..core.exceptions import ValidationError, NotFoundError
from .simple_health_check_service import HealthCheckService

logger = logging.getLogger(__name__)


class AIModelConfigService:
    """AI模型配置服务"""
    
    def __init__(self, health_check_service: HealthCheckService):
        self.health_check_service = health_check_service
    
    async def create_model_config(
        self, 
        db: AsyncSession, 
        config_data: AIModelConfigCreate
    ) -> AIModelConfigResponse:
        """创建AI模型配置"""
        # 检查是否已存在相同的提供商和模型名称组合
        existing = await self._get_existing_config(
            db, config_data.provider, config_data.model_name
        )
        if existing:
            raise ValidationError(
                f"配置已存在: {config_data.provider}/{config_data.model_name}"
            )
        
        # 如果设置为默认模型，需要取消其他默认模型
        if config_data.is_default:
            await self._clear_default_models(db, config_data.provider)
        
        # 创建新配置
        config = AIModelConfig(**config_data.dict())
        config.created_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"创建AI模型配置: {config.provider}/{config.model_name}")
        return AIModelConfigResponse.from_orm(config)
    
    async def get_model_configs(
        self, 
        db: AsyncSession,
        provider: Optional[str] = None,
        enabled_only: bool = False,
        public_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> AIModelConfigList:
        """获取AI模型配置列表"""
        query = select(AIModelConfig)
        
        # 添加过滤条件
        conditions = []
        if provider:
            conditions.append(AIModelConfig.provider == provider)
        if enabled_only:
            conditions.append(AIModelConfig.is_enabled == True)
        if public_only:
            conditions.append(AIModelConfig.is_public == True)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序和分页
        query = query.order_by(
            desc(AIModelConfig.is_default),
            desc(AIModelConfig.priority),
            AIModelConfig.provider,
            AIModelConfig.model_name
        ).offset(skip).limit(limit)
        
        result = await db.execute(query)
        configs = result.scalars().all()
        
        # 获取总数
        count_query = select(func.count(AIModelConfig.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return AIModelConfigList(
            items=[AIModelConfigResponse.from_orm(config) for config in configs],
            total=total,
            skip=skip,
            limit=limit
        )
    
    async def get_model_config(
        self, 
        db: AsyncSession, 
        config_id: int
    ) -> AIModelConfigResponse:
        """获取单个AI模型配置"""
        config = await self._get_config_by_id(db, config_id)
        return AIModelConfigResponse.from_orm(config)
    
    async def update_model_config(
        self, 
        db: AsyncSession, 
        config_id: int, 
        update_data: AIModelConfigUpdate
    ) -> AIModelConfigResponse:
        """更新AI模型配置"""
        config = await self._get_config_by_id(db, config_id)
        
        # 如果设置为默认模型，需要取消其他默认模型
        if update_data.is_default and not config.is_default:
            await self._clear_default_models(db, config.provider)
        
        # 更新配置
        update_dict = update_data.dict(exclude_unset=True)
        update_dict['updated_at'] = datetime.utcnow()
        
        for field, value in update_dict.items():
            setattr(config, field, value)
        
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"更新AI模型配置: {config.provider}/{config.model_name}")
        return AIModelConfigResponse.from_orm(config)
    
    async def delete_model_config(self, db: AsyncSession, config_id: int) -> bool:
        """删除AI模型配置"""
        config = await self._get_config_by_id(db, config_id)
        
        # 检查是否有使用记录
        usage_query = select(func.count(AIUsageStats.id)).where(
            AIUsageStats.model_config_id == config_id
        )
        usage_result = await db.execute(usage_query)
        usage_count = usage_result.scalar()
        
        if usage_count > 0:
            # 软删除：只禁用配置
            config.is_enabled = False
            config.updated_at = datetime.utcnow()
            await db.commit()
            logger.info(f"软删除AI模型配置: {config.provider}/{config.model_name}")
        else:
            # 硬删除：完全删除配置
            await db.delete(config)
            await db.commit()
            logger.info(f"删除AI模型配置: {config.provider}/{config.model_name}")
        
        return True
    
    async def get_provider_stats(self, db: AsyncSession) -> List[AIProviderStats]:
        """获取AI服务提供商统计信息"""
        # 获取每个提供商的配置统计
        from sqlalchemy import case
        config_stats_query = select(
            AIModelConfig.provider,
            func.count(AIModelConfig.id).label('total_models'),
            func.sum(case((AIModelConfig.is_enabled == True, 1), else_=0)).label('enabled_models'),
            func.sum(case((AIModelConfig.is_default == True, 1), else_=0)).label('default_models')
        ).group_by(AIModelConfig.provider)
        
        config_result = await db.execute(config_stats_query)
        config_stats = {row.provider: row for row in config_result}
        
        # 获取使用统计（最近30天）
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        usage_stats_query = select(
            AIModelConfig.provider,
            func.count(AIUsageStats.id).label('total_requests'),
            func.sum(AIUsageStats.input_tokens + AIUsageStats.output_tokens).label('total_tokens'),
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.avg(AIUsageStats.avg_response_time).label('avg_response_time')
        ).select_from(
            AIUsageStats.__table__.join(AIModelConfig.__table__)
        ).where(
            AIUsageStats.created_at >= thirty_days_ago
        ).group_by(AIModelConfig.provider)
        
        usage_result = await db.execute(usage_stats_query)
        usage_stats = {row.provider: row for row in usage_result}
        
        # 合并统计信息
        stats = []
        all_providers = set(config_stats.keys()) | set(usage_stats.keys())
        
        for provider in all_providers:
            config_stat = config_stats.get(provider)
            usage_stat = usage_stats.get(provider)
            
            stats.append(AIProviderStats(
                provider=provider,
                total_models=config_stat.total_models if config_stat else 0,
                enabled_models=config_stat.enabled_models if config_stat else 0,
                default_models=config_stat.default_models if config_stat else 0,
                total_requests=usage_stat.total_requests if usage_stat else 0,
                total_tokens=usage_stat.total_tokens if usage_stat else 0,
                total_cost=float(usage_stat.total_cost) if usage_stat and usage_stat.total_cost else 0.0,
                avg_response_time=float(usage_stat.avg_response_time) if usage_stat and usage_stat.avg_response_time else 0.0
            ))
        
        return sorted(stats, key=lambda x: x.total_requests, reverse=True)
    
    async def health_check_model(
        self, 
        db: AsyncSession, 
        config_id: int
    ) -> AIModelHealthCheck:
        """检查AI模型健康状态"""
        config = await self._get_config_by_id(db, config_id)
        
        # 执行健康检查
        health_result = await self.health_check_service.check_ai_model_health(config)
        
        # 更新健康状态
        config.health_status = health_result.status
        config.last_health_check = datetime.utcnow()
        config.avg_response_time = health_result.response_time
        config.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"健康检查完成: {config.provider}/{config.model_name} - {health_result.status}")
        return health_result
    
    async def batch_health_check(self, db: AsyncSession) -> Dict[str, Any]:
        """批量健康检查所有启用的模型"""
        # 获取所有启用的模型配置
        query = select(AIModelConfig).where(AIModelConfig.is_enabled == True)
        result = await db.execute(query)
        configs = result.scalars().all()
        
        results = {
            'total': len(configs),
            'healthy': 0,
            'unhealthy': 0,
            'unknown': 0,
            'details': []
        }
        
        for config in configs:
            try:
                health_result = await self.health_check_model(db, config.id)
                results['details'].append({
                    'config_id': config.id,
                    'provider': config.provider,
                    'model_name': config.model_name,
                    'status': health_result.status,
                    'response_time': health_result.response_time,
                    'error': health_result.error
                })
                
                if health_result.status == 'HEALTHY':
                    results['healthy'] += 1
                elif health_result.status == 'UNHEALTHY':
                    results['unhealthy'] += 1
                else:
                    results['unknown'] += 1
                    
            except Exception as e:
                logger.error(f"健康检查失败: {config.provider}/{config.model_name} - {e}")
                results['unhealthy'] += 1
                results['details'].append({
                    'config_id': config.id,
                    'provider': config.provider,
                    'model_name': config.model_name,
                    'status': 'ERROR',
                    'response_time': None,
                    'error': str(e)
                })
        
        return results
    
    async def _get_existing_config(
        self, 
        db: AsyncSession, 
        provider: str, 
        model_name: str
    ) -> Optional[AIModelConfig]:
        """检查是否存在相同的配置"""
        query = select(AIModelConfig).where(
            and_(
                AIModelConfig.provider == provider,
                AIModelConfig.model_name == model_name
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_config_by_id(self, db: AsyncSession, config_id: int) -> AIModelConfig:
        """根据ID获取配置"""
        query = select(AIModelConfig).where(AIModelConfig.id == config_id)
        result = await db.execute(query)
        config = result.scalar_one_or_none()
        
        if not config:
            raise NotFoundError(f"AI模型配置不存在: {config_id}")
        
        return config
    
    async def _clear_default_models(self, db: AsyncSession, provider: str):
        """清除指定提供商的默认模型标记"""
        update_query = update(AIModelConfig).where(
            and_(
                AIModelConfig.provider == provider,
                AIModelConfig.is_default == True
            )
        ).values(is_default=False, updated_at=datetime.utcnow())
        
        await db.execute(update_query)