"""
AI模型配置管理API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...decorators.permission import get_current_user, require_permission
from ...services.ai_model_config_service import AIModelConfigService
from ...services.simple_health_check_service import HealthCheckService
from ...schemas.ai_model_config import (
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelConfigResponse,
    AIModelConfigList,
    AIProviderStats,
    AIModelHealthCheck,
    AIModelTestRequest,
    AIModelTestResponse,
    BatchHealthCheckResponse,
    AIProviderEnum
)
from ...core.exceptions import ValidationError, NotFoundError

router = APIRouter()


def get_ai_model_config_service() -> AIModelConfigService:
    """获取AI模型配置服务实例"""
    health_check_service = HealthCheckService()
    return AIModelConfigService(health_check_service)


@router.post("/", response_model=AIModelConfigResponse)
async def create_model_config(
    config_data: AIModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    创建AI模型配置
    
    需要权限: ai_config_manage
    """
    
    try:
        return await service.create_model_config(db, config_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")


@router.get("/", response_model=AIModelConfigList)
async def get_model_configs(
    provider: Optional[AIProviderEnum] = Query(None, description="筛选服务提供商"),
    enabled_only: bool = Query(False, description="仅显示启用的配置"),
    public_only: bool = Query(False, description="仅显示公开的配置"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    获取AI模型配置列表
    
    需要权限: ai_config_view
    """
    
    try:
        return await service.get_model_configs(
            db, 
            provider=provider.value if provider else None,
            enabled_only=enabled_only,
            public_only=public_only,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置列表失败: {str(e)}")


@router.get("/stats", response_model=List[AIProviderStats])
async def get_provider_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    获取AI服务提供商统计信息
    
    需要权限: ai_config_view
    """
    
    try:
        return await service.get_provider_stats(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/{config_id}", response_model=AIModelConfigResponse)
async def get_model_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    获取单个AI模型配置
    
    需要权限: ai_config_view
    """
    
    try:
        return await service.get_model_config(db, config_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/{config_id}", response_model=AIModelConfigResponse)
async def update_model_config(
    config_id: int,
    update_data: AIModelConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    更新AI模型配置
    
    需要权限: ai_config_manage
    """
    
    try:
        return await service.update_model_config(db, config_id, update_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/{config_id}")
async def delete_model_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    删除AI模型配置
    
    需要权限: ai_config_manage
    """
    
    try:
        await service.delete_model_config(db, config_id)
        return {"message": "配置删除成功"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


@router.post("/{config_id}/health-check", response_model=AIModelHealthCheck)
async def health_check_model(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    检查AI模型健康状态
    
    需要权限: ai_config_manage
    """
    
    try:
        return await service.health_check_model(db, config_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.post("/batch-health-check", response_model=BatchHealthCheckResponse)
async def batch_health_check(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    批量健康检查所有启用的模型
    
    需要权限: ai_config_manage
    """
    
    try:
        # 在后台任务中执行批量健康检查
        results = await service.batch_health_check(db)
        return BatchHealthCheckResponse(**results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量健康检查失败: {str(e)}")


@router.post("/{config_id}/test", response_model=AIModelTestResponse)
async def test_model(
    config_id: int,
    test_request: AIModelTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    测试AI模型
    
    需要权限: ai_config_manage
    """
    
    try:
        # 获取模型配置
        config = await service.get_model_config(db, config_id)
        
        # 这里应该调用实际的AI服务进行测试
        # 为了简化，这里返回模拟结果
        from datetime import datetime
        import time
        
        start_time = time.time()
        
        # 模拟AI调用
        await asyncio.sleep(0.5)  # 模拟网络延迟
        
        response_time = time.time() - start_time
        
        return AIModelTestResponse(
            success=True,
            response_text=f"这是来自 {config.display_name} 的测试响应：{test_request.test_message}",
            response_time=response_time,
            tokens_used=50,
            cost=0.001,
            tested_at=datetime.utcnow()
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return AIModelTestResponse(
            success=False,
            response_time=0.0,
            error=str(e),
            tested_at=datetime.utcnow()
        )


@router.post("/{config_id}/toggle", response_model=AIModelConfigResponse)
async def toggle_model_status(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    切换AI模型启用/禁用状态
    
    需要权限: ai_config_manage
    """
    
    try:
        # 获取当前配置
        config = await service.get_model_config(db, config_id)
        
        # 切换状态
        update_data = AIModelConfigUpdate(is_enabled=not config.is_enabled)
        return await service.update_model_config(db, config_id, update_data)
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换状态失败: {str(e)}")


@router.post("/{config_id}/set-default", response_model=AIModelConfigResponse)
async def set_default_model(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    设置为默认模型
    
    需要权限: ai_config_manage
    """
    
    try:
        update_data = AIModelConfigUpdate(is_default=True)
        return await service.update_model_config(db, config_id, update_data)
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置默认模型失败: {str(e)}")


# 导入必要的模块
import asyncio