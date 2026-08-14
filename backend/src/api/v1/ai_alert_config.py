"""
AI告警配置管理API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...decorators.permission import get_current_user, require_permission
from ...services.ai_alert_config_service import AIAlertConfigService
from ...schemas.ai_alert_config import (
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
    AlertTemplateResponse
)
from ...models.ai_alert_config import AlertType, AlertLevel, AlertStatus
from ...core.exceptions import ValidationError, NotFoundError

router = APIRouter()


def get_alert_config_service() -> AIAlertConfigService:
    """获取告警配置服务实例"""
    return AIAlertConfigService()


@router.post("/", response_model=AlertConfigResponse)
async def create_alert_config(
    config_data: AlertConfigCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    创建告警配置
    
    需要权限: ai_config_manage
    """
    try:
        return await service.create_alert_config(db, config_data, current_user.id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建告警配置失败: {str(e)}")


@router.get("/", response_model=AlertConfigList)
async def get_alert_configs(
    alert_type: Optional[AlertType] = Query(None, description="告警类型筛选"),
    alert_level: Optional[AlertLevel] = Query(None, description="告警级别筛选"),
    status: Optional[AlertStatus] = Query(None, description="状态筛选"),
    created_by: Optional[int] = Query(None, description="创建者筛选"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    获取告警配置列表
    
    需要权限: ai_config_view
    """
    try:
        return await service.get_alert_configs(
            db,
            alert_type=alert_type,
            alert_level=alert_level,
            status=status,
            created_by=created_by,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警配置列表失败: {str(e)}")


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    获取告警统计信息
    
    需要权限: ai_config_view
    """
    try:
        return await service.get_alert_stats(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警统计失败: {str(e)}")


@router.get("/templates/{alert_type}", response_model=AlertTemplateResponse)
async def get_alert_template(
    alert_type: AlertType,
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    获取告警模板
    
    需要权限: ai_config_view
    """
    try:
        return await service.get_alert_template(alert_type)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警模板失败: {str(e)}")


@router.get("/{config_id}", response_model=AlertConfigResponse)
async def get_alert_config(
    config_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    获取单个告警配置
    
    需要权限: ai_config_view
    """
    try:
        return await service.get_alert_config(db, config_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警配置失败: {str(e)}")


@router.put("/{config_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    config_id: int,
    update_data: AlertConfigUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    更新告警配置
    
    需要权限: ai_config_manage
    """
    try:
        return await service.update_alert_config(db, config_id, update_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新告警配置失败: {str(e)}")


@router.delete("/{config_id}")
async def delete_alert_config(
    config_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    删除告警配置
    
    需要权限: ai_config_manage
    """
    try:
        await service.delete_alert_config(db, config_id)
        return {"message": "告警配置删除成功"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除告警配置失败: {str(e)}")


@router.post("/{config_id}/test", response_model=AlertTestResponse)
async def test_alert_config(
    config_id: int,
    test_request: AlertTestRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    测试告警配置
    
    需要权限: ai_config_manage
    """
    try:
        return await service.test_alert_config(db, config_id, test_request)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试告警配置失败: {str(e)}")


@router.post("/{config_id}/toggle", response_model=AlertConfigResponse)
async def toggle_alert_config(
    config_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    切换告警配置状态
    
    需要权限: ai_config_manage
    """
    try:
        return await service.toggle_alert_config(db, config_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换告警配置状态失败: {str(e)}")


@router.get("/{config_id}/history", response_model=AlertHistoryList)
async def get_alert_history(
    config_id: int,
    alert_level: Optional[AlertLevel] = Query(None, description="告警级别筛选"),
    status: Optional[AlertStatus] = Query(None, description="状态筛选"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    获取告警历史记录
    
    需要权限: ai_config_view
    """
    try:
        return await service.get_alert_history(
            db,
            config_id=config_id,
            alert_level=alert_level,
            status=status,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警历史失败: {str(e)}")


@router.get("/history/all", response_model=AlertHistoryList)
async def get_all_alert_history(
    alert_level: Optional[AlertLevel] = Query(None, description="告警级别筛选"),
    status: Optional[AlertStatus] = Query(None, description="状态筛选"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    获取所有告警历史记录
    
    需要权限: ai_config_view
    """
    try:
        return await service.get_alert_history(
            db,
            config_id=None,
            alert_level=alert_level,
            status=status,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警历史失败: {str(e)}")


@router.post("/history/{history_id}/resolve", response_model=AlertHistoryResponse)
async def resolve_alert(
    history_id: int,
    resolution_note: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    解决告警
    
    需要权限: ai_config_manage
    """
    try:
        return await service.resolve_alert(
            db, 
            history_id, 
            current_user.id, 
            resolution_note
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解决告警失败: {str(e)}")


@router.post("/suppressions", response_model=AlertSuppressionResponse)
async def suppress_alert(
    suppression_data: AlertSuppressionCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    抑制告警
    
    需要权限: ai_config_manage
    """
    try:
        return await service.suppress_alert(db, suppression_data, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"抑制告警失败: {str(e)}")


@router.post("/batch-toggle")
async def batch_toggle_alert_configs(
    config_ids: List[int],
    target_status: AlertStatus,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    批量切换告警配置状态
    
    需要权限: ai_config_manage
    """
    try:
        results = []
        for config_id in config_ids:
            try:
                # 获取当前配置
                config = await service.get_alert_config(db, config_id)
                
                # 如果状态不同，则更新
                if config.status != target_status:
                    update_data = AlertConfigUpdate(status=target_status)
                    updated_config = await service.update_alert_config(db, config_id, update_data)
                    results.append({
                        "config_id": config_id,
                        "success": True,
                        "old_status": config.status,
                        "new_status": updated_config.status
                    })
                else:
                    results.append({
                        "config_id": config_id,
                        "success": True,
                        "message": "状态未变更"
                    })
            except Exception as e:
                results.append({
                    "config_id": config_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "message": f"批量操作完成，处理了 {len(config_ids)} 个配置",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


@router.post("/batch-delete")
async def batch_delete_alert_configs(
    config_ids: List[int],
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    批量删除告警配置
    
    需要权限: ai_config_manage
    """
    try:
        results = []
        for config_id in config_ids:
            try:
                await service.delete_alert_config(db, config_id)
                results.append({
                    "config_id": config_id,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "config_id": config_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "message": f"批量删除完成，处理了 {len(config_ids)} 个配置",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.get("/export/configs")
async def export_alert_configs(
    alert_type: Optional[AlertType] = Query(None, description="告警类型筛选"),
    status: Optional[AlertStatus] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_permission("ai_config_manage")),
    service: AIAlertConfigService = Depends(get_alert_config_service)
):
    """
    导出告警配置
    
    需要权限: ai_config_manage
    """
    try:
        configs = await service.get_alert_configs(
            db,
            alert_type=alert_type,
            status=status,
            skip=0,
            limit=10000  # 导出所有匹配的配置
        )
        
        # 转换为导出格式
        export_data = {
            "export_time": datetime.utcnow().isoformat(),
            "total_configs": configs.total,
            "configs": [
                {
                    "name": config.name,
                    "description": config.description,
                    "alert_type": config.alert_type,
                    "alert_level": config.alert_level,
                    "threshold_value": config.threshold_value,
                    "threshold_operator": config.threshold_operator,
                    "threshold_unit": config.threshold_unit,
                    "time_window_minutes": config.time_window_minutes,
                    "evaluation_frequency_minutes": config.evaluation_frequency_minutes,
                    "target_providers": config.target_providers,
                    "target_models": config.target_models,
                    "notification_channels": config.notification_channels,
                    "notification_recipients": config.notification_recipients,
                    "suppress_duration_minutes": config.suppress_duration_minutes,
                    "max_alerts_per_hour": config.max_alerts_per_hour,
                    "auto_resolve": config.auto_resolve,
                    "auto_resolve_threshold": config.auto_resolve_threshold,
                    "created_at": config.created_at.isoformat(),
                    "trigger_count": config.trigger_count
                }
                for config in configs.items
            ]
        }
        
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出告警配置失败: {str(e)}")