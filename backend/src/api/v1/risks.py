"""
Project risk management API.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...api.auth import get_current_user
from ...core.database import get_db
from ...schemas.risk import (
    AutoRiskDetectionResult,
    CreateRiskRequest,
    RiskAnalysisResponse,
    RiskCategory,
    RiskLevel,
    RiskListQuery,
    RiskListResponse,
    RiskResponse,
    RiskStatus,
    RiskTrendResponse,
    UpdateRiskRequest,
)
from ...services.risk_monitoring_service import RiskMonitoringService
from ...services.risk_service import RiskService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/risks", tags=["风险管理"])


def _current_user_id(current_user: Any) -> int:
    if hasattr(current_user, "id"):
        return int(current_user.id)
    if isinstance(current_user, dict):
        return int(current_user.get("user_id") or current_user.get("id"))
    return int(current_user)


@router.get("/health", summary="风险管理服务健康检查")
async def health_check():
    return {"status": "ok", "service": "risk_management"}


@router.get("/", response_model=RiskListResponse, summary="获取风险列表")
async def list_risks(
    project_id: Optional[int] = Query(None, description="项目ID"),
    search: Optional[str] = Query(None, description="搜索风险名称、描述或应对计划"),
    risk_category: Optional[RiskCategory] = Query(None, description="风险类别"),
    risk_level: Optional[RiskLevel] = Query(None, description="风险等级"),
    status: Optional[RiskStatus] = Query(None, description="风险状态"),
    owner_id: Optional[int] = Query(None, description="负责人ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        query = RiskListQuery(
            project_id=project_id,
            search=search,
            risk_category=risk_category,
            risk_level=risk_level,
            status=status,
            owner_id=owner_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        result = await RiskService(db).list_risks(query)
        return RiskListResponse(**result)
    except Exception as exc:
        logger.error("获取风险列表失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取风险列表失败")


@router.post("/", response_model=RiskResponse, summary="创建项目风险")
async def create_risk(
    risk_data: CreateRiskRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = _current_user_id(current_user)
        result = await RiskService(db).create_risk(risk_data, user_id)
        logger.info("用户%s创建风险: %s", user_id, result.id)
        return result
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        if "validation" in message.lower() or "必须" in message or "无效" in message:
            raise HTTPException(status_code=400, detail=message)
        logger.error("创建风险失败: %s", exc)
        raise HTTPException(status_code=500, detail="创建风险失败")


@router.post("/auto-detect", response_model=AutoRiskDetectionResult, summary="自动识别项目风险")
async def auto_detect_risks(
    project_id: int = Query(..., description="项目ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = await RiskService(db).auto_detect_risks(project_id)
        logger.info("用户%s执行项目%s风险自动识别", _current_user_id(current_user), project_id)
        return result
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        logger.error("自动风险识别失败: %s", exc)
        raise HTTPException(status_code=500, detail="自动风险识别失败")


@router.get("/analysis/{project_id}", response_model=RiskAnalysisResponse, summary="获取风险分析报告")
async def get_risk_analysis(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await RiskService(db).get_risk_analysis(project_id)
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        logger.error("获取风险分析失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取风险分析失败")


@router.get("/trend/{project_id}", response_model=RiskTrendResponse, summary="获取风险趋势")
async def get_risk_trend(
    project_id: int,
    days: int = Query(30, ge=1, le=365, description="分析天数"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await RiskService(db).get_risk_trend(project_id, days)
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        logger.error("获取风险趋势失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取风险趋势失败")


@router.post("/monitor/start", summary="启动风险监控")
async def start_risk_monitoring(
    project_id: int = Query(..., description="项目ID"),
    interval_hours: int = Query(24, ge=1, le=168, description="监控间隔（小时）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        monitoring_service = RiskMonitoringService(db)
        config = {"alert_thresholds": {"check_interval": interval_hours * 3600}}
        await monitoring_service.start_monitoring(project_id, config)
        logger.info("用户%s启动项目%s风险监控", _current_user_id(current_user), project_id)
        return {"message": "风险监控已启动", "project_id": project_id, "interval_hours": interval_hours}
    except Exception as exc:
        logger.error("启动风险监控失败: %s", exc)
        raise HTTPException(status_code=500, detail="启动风险监控失败")


@router.post("/monitor/stop", summary="停止风险监控")
async def stop_risk_monitoring(
    project_id: int = Query(..., description="项目ID"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await RiskMonitoringService(db).stop_monitoring(project_id)
        logger.info("用户%s停止项目%s风险监控", _current_user_id(current_user), project_id)
        return {"message": "风险监控已停止", "project_id": project_id}
    except Exception as exc:
        logger.error("停止风险监控失败: %s", exc)
        raise HTTPException(status_code=500, detail="停止风险监控失败")


@router.get("/monitor/status/{project_id}", summary="获取风险监控状态")
async def get_monitoring_status(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"project_id": project_id, "enabled": False, "message": "当前项目未启用定时风险监控"}


@router.get("/alerts/{project_id}", summary="获取风险预警")
async def get_risk_alerts(
    project_id: int,
    days: int = Query(7, ge=1, le=30, description="查询天数"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        monitoring_service = RiskMonitoringService(db)
        alerts = await monitoring_service.check_project_risks(project_id)
        alert_history = await monitoring_service.get_alert_history(project_id, days)
        critical_alerts = len([alert for alert in alerts if alert.severity == "CRITICAL"])
        high_alerts = len([alert for alert in alerts if alert.severity == "HIGH"])
        return {
            "project_id": project_id,
            "alerts": [
                {
                    "risk_id": alert.risk_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "recommendation": alert.recommendation,
                    "created_at": alert.created_at.isoformat(),
                }
                for alert in alerts
            ],
            "total_alerts": len(alerts),
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "query_days": days,
            "alert_history": alert_history,
        }
    except Exception as exc:
        logger.error("获取风险预警失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取风险预警失败")


@router.get("/{risk_id}", response_model=RiskResponse, summary="获取风险详情")
async def get_risk(
    risk_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await RiskService(db).get_risk(risk_id)
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        logger.error("获取风险详情失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取风险详情失败")


@router.put("/{risk_id}", response_model=RiskResponse, summary="更新项目风险")
async def update_risk(
    risk_id: int,
    risk_data: UpdateRiskRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = _current_user_id(current_user)
        result = await RiskService(db).update_risk(risk_id, risk_data, user_id)
        logger.info("用户%s更新风险: %s", user_id, risk_id)
        return result
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        if "validation" in message.lower() or "必须" in message or "无效" in message:
            raise HTTPException(status_code=400, detail=message)
        logger.error("更新风险失败: %s", exc)
        raise HTTPException(status_code=500, detail="更新风险失败")


@router.delete("/{risk_id}", summary="删除项目风险")
async def delete_risk(
    risk_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await RiskService(db).delete_risk(risk_id)
        logger.info("用户%s删除风险: %s", _current_user_id(current_user), risk_id)
        return {"message": "风险删除成功"}
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() or "不存在" in message:
            raise HTTPException(status_code=404, detail=message)
        logger.error("删除风险失败: %s", exc)
        raise HTTPException(status_code=500, detail="删除风险失败")
