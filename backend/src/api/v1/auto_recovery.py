"""
自动恢复服务API接口
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam, Body
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError
from ...services.auto_recovery_service import auto_recovery_service, FailureType, RecoveryStatus
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auto-recovery", tags=["自动恢复服务"])
security = HTTPBearer()


# 请求模式
class ManualRecoveryRequest(BaseModel):
    """手动恢复请求"""
    failure_type: str = Field(..., description="故障类型")
    failure_details: Optional[Dict[str, Any]] = Field(None, description="故障详情")
    force_recovery: bool = Field(False, description="是否强制恢复（忽略冷却时间）")


class UpdateThresholdsRequest(BaseModel):
    """更新阈值请求"""
    thresholds: Dict[str, float] = Field(..., description="阈值配置")


# 响应模式
class FailureDetectionResponse(BaseModel):
    """故障检测响应"""
    failures_detected: int = Field(..., description="检测到的故障数量")
    failures: List[Dict[str, Any]] = Field(..., description="故障详情列表")
    detection_time: datetime = Field(..., description="检测时间")


class RecoveryActionResponse(BaseModel):
    """恢复操作响应"""
    recovery_id: str = Field(..., description="恢复操作ID")
    failure_type: str = Field(..., description="故障类型")
    recovery_status: str = Field(..., description="恢复状态")
    recovery_message: str = Field(..., description="恢复消息")
    actions_taken: List[str] = Field(..., description="执行的操作")
    execution_time: datetime = Field(..., description="执行时间")


class RecoveryStatisticsResponse(BaseModel):
    """恢复统计响应"""
    total_recoveries: int = Field(..., description="总恢复次数")
    successful_recoveries: int = Field(..., description="成功恢复次数")
    success_rate: float = Field(..., description="成功率")
    recent_24h_recoveries: int = Field(..., description="最近24小时恢复次数")
    failure_type_statistics: Dict[str, Dict[str, Any]] = Field(..., description="按故障类型统计")
    monitoring_status: str = Field(..., description="监控状态")


class MonitoringStatusResponse(BaseModel):
    """监控状态响应"""
    is_monitoring: bool = Field(..., description="是否正在监控")
    status: str = Field(..., description="状态")
    message: str = Field(..., description="状态消息")
    uptime: Optional[str] = Field(None, description="运行时间")


# API接口实现
@router.post("/start-monitoring", response_model=BaseResponse[MonitoringStatusResponse])
async def start_monitoring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    启动自动恢复监控
    
    开始监控系统故障并执行自动恢复
    """
    try:
        result = await auto_recovery_service.start_monitoring()
        
        response_data = MonitoringStatusResponse(
            is_monitoring=auto_recovery_service.is_monitoring,
            status=result["status"],
            message=result["message"]
        )
        
        return BaseResponse(
            success=result["status"] in ["success", "already_running"],
            message=result["message"],
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"启动自动恢复监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动监控失败: {str(e)}")


@router.post("/stop-monitoring", response_model=BaseResponse[MonitoringStatusResponse])
async def stop_monitoring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    停止自动恢复监控
    
    停止监控系统故障
    """
    try:
        result = await auto_recovery_service.stop_monitoring()
        
        response_data = MonitoringStatusResponse(
            is_monitoring=auto_recovery_service.is_monitoring,
            status=result["status"],
            message=result["message"]
        )
        
        return BaseResponse(
            success=result["status"] == "success",
            message=result["message"],
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"停止自动恢复监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止监控失败: {str(e)}")


@router.get("/monitoring-status", response_model=BaseResponse[MonitoringStatusResponse])
async def get_monitoring_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取监控状态
    
    返回当前自动恢复监控的状态信息
    """
    try:
        response_data = MonitoringStatusResponse(
            is_monitoring=auto_recovery_service.is_monitoring,
            status="active" if auto_recovery_service.is_monitoring else "inactive",
            message="监控正在运行" if auto_recovery_service.is_monitoring else "监控已停止"
        )
        
        return BaseResponse(
            success=True,
            message="获取监控状态成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取监控状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取监控状态失败")


@router.post("/detect-failures", response_model=BaseResponse[FailureDetectionResponse])
async def detect_failures(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动检测系统故障
    
    立即执行一次系统故障检测
    """
    try:
        failures = await auto_recovery_service.detect_failures()
        
        # 转换故障数据格式
        failure_list = []
        for failure in failures:
            failure_dict = {
                "failure_type": failure["failure_type"].value,
                "severity": failure["severity"],
                "message": failure["message"],
                "detected_at": failure["detected_at"].isoformat(),
                "details": failure.get("details", {})
            }
            failure_list.append(failure_dict)
        
        response_data = FailureDetectionResponse(
            failures_detected=len(failures),
            failures=failure_list,
            detection_time=datetime.now()
        )
        
        return BaseResponse(
            success=True,
            message=f"故障检测完成，发现 {len(failures)} 个故障",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"故障检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"故障检测失败: {str(e)}")


@router.post("/manual-recovery", response_model=BaseResponse[RecoveryActionResponse])
async def manual_recovery(
    request: ManualRecoveryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动执行恢复操作
    
    手动触发指定类型的故障恢复
    """
    try:
        # 验证故障类型
        try:
            failure_type = FailureType(request.failure_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的故障类型: {request.failure_type}")
        
        # 如果强制恢复，临时清除冷却时间
        if request.force_recovery:
            auto_recovery_service.last_recovery_times.pop(failure_type, None)
        
        # 构建故障详情
        failure_details = request.failure_details or {
            "failure_type": failure_type,
            "severity": "medium",
            "message": f"手动触发的 {failure_type.value} 恢复",
            "detected_at": datetime.now(),
            "details": {"manual_trigger": True}
        }
        
        # 执行恢复
        recovery_result = await auto_recovery_service.auto_recover(failure_type, failure_details)
        
        response_data = RecoveryActionResponse(
            recovery_id=f"manual_{int(datetime.now().timestamp())}",
            failure_type=failure_type.value,
            recovery_status=recovery_result["status"].value,
            recovery_message=recovery_result.get("message", ""),
            actions_taken=recovery_result.get("actions_taken", []),
            execution_time=datetime.now()
        )
        
        return BaseResponse(
            success=recovery_result["status"] == RecoveryStatus.SUCCESS,
            message=f"手动恢复操作完成: {recovery_result['status'].value}",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"手动恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动恢复失败: {str(e)}")


@router.get("/recovery-history", response_model=PaginatedResponse[Dict[str, Any]])
async def get_recovery_history(
    limit: int = Query(50, ge=1, le=200, description="返回记录数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取恢复历史记录
    
    返回系统自动恢复的历史记录
    """
    try:
        history = await auto_recovery_service.get_recovery_history(limit)
        
        return PaginatedResponse(
            success=True,
            message="获取恢复历史成功",
            data=history,
            total=len(history),
            page=1,
            page_size=limit
        )
        
    except Exception as e:
        logger.error(f"获取恢复历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取恢复历史失败")


@router.get("/statistics", response_model=BaseResponse[RecoveryStatisticsResponse])
async def get_recovery_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取恢复统计信息
    
    返回自动恢复系统的统计数据
    """
    try:
        stats = await auto_recovery_service.get_recovery_statistics()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        
        response_data = RecoveryStatisticsResponse(
            total_recoveries=stats["total_recoveries"],
            successful_recoveries=stats["successful_recoveries"],
            success_rate=stats["success_rate"],
            recent_24h_recoveries=stats["recent_24h_recoveries"],
            failure_type_statistics=stats["failure_type_statistics"],
            monitoring_status=stats["monitoring_status"]
        )
        
        return BaseResponse(
            success=True,
            message="获取恢复统计成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取恢复统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取恢复统计失败")


@router.get("/failure-types", response_model=BaseResponse[List[Dict[str, str]]])
async def get_failure_types(
    current_user: User = Depends(get_current_user)
):
    """
    获取支持的故障类型
    
    返回系统支持的所有故障类型列表
    """
    try:
        failure_types = []
        for failure_type in FailureType:
            failure_types.append({
                "value": failure_type.value,
                "name": failure_type.name,
                "description": _get_failure_type_description(failure_type)
            })
        
        return BaseResponse(
            success=True,
            message="获取故障类型成功",
            data=failure_types
        )
        
    except Exception as e:
        logger.error(f"获取故障类型失败: {e}")
        raise HTTPException(status_code=500, detail="获取故障类型失败")


@router.get("/thresholds", response_model=BaseResponse[Dict[str, float]])
async def get_failure_thresholds(
    current_user: User = Depends(get_current_user)
):
    """
    获取故障阈值配置
    
    返回当前的故障检测阈值设置
    """
    try:
        thresholds = {}
        for failure_type, threshold in auto_recovery_service.failure_thresholds.items():
            thresholds[failure_type.value] = threshold
        
        return BaseResponse(
            success=True,
            message="获取故障阈值成功",
            data=thresholds
        )
        
    except Exception as e:
        logger.error(f"获取故障阈值失败: {e}")
        raise HTTPException(status_code=500, detail="获取故障阈值失败")


@router.put("/thresholds", response_model=BaseResponse[Dict[str, float]])
async def update_failure_thresholds(
    request: UpdateThresholdsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新故障阈值配置
    
    更新系统故障检测的阈值设置
    """
    try:
        updated_thresholds = {}
        
        for failure_type_str, threshold in request.thresholds.items():
            try:
                failure_type = FailureType(failure_type_str)
                
                # 使用率和错误率按百分比校验，响应时间按毫秒校验。
                max_threshold = 60000 if failure_type == FailureType.SLOW_RESPONSE else 100
                if threshold < 0 or threshold > max_threshold:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"阈值 {threshold} 超出有效范围 (0-{max_threshold})"
                    )
                
                auto_recovery_service.failure_thresholds[failure_type] = threshold
                updated_thresholds[failure_type_str] = threshold
                
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的故障类型: {failure_type_str}"
                )
        
        return BaseResponse(
            success=True,
            message=f"成功更新 {len(updated_thresholds)} 个阈值配置",
            data=updated_thresholds
        )
        
    except Exception as e:
        logger.error(f"更新故障阈值失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新故障阈值失败: {str(e)}")


@router.get("/health-check", response_model=BaseResponse[Dict[str, Any]])
async def health_check(
    current_user: User = Depends(get_current_user)
):
    """
    自动恢复服务健康检查
    
    检查自动恢复服务的健康状态
    """
    try:
        health_status = {
            "service_status": "healthy",
            "monitoring_active": auto_recovery_service.is_monitoring,
            "recovery_strategies_count": len(auto_recovery_service.recovery_strategies),
            "failure_thresholds_count": len(auto_recovery_service.failure_thresholds),
            "last_check_time": datetime.now().isoformat()
        }
        
        return BaseResponse(
            success=True,
            message="自动恢复服务健康检查完成",
            data=health_status
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败")


def _get_failure_type_description(failure_type: FailureType) -> str:
    """获取故障类型描述"""
    descriptions = {
        FailureType.DATABASE_CONNECTION: "数据库连接故障",
        FailureType.REDIS_CONNECTION: "Redis连接故障",
        FailureType.HIGH_CPU_USAGE: "CPU使用率过高",
        FailureType.HIGH_MEMORY_USAGE: "内存使用率过高",
        FailureType.DISK_FULL: "磁盘空间不足",
        FailureType.SERVICE_UNAVAILABLE: "服务不可用",
        FailureType.SLOW_RESPONSE: "响应时间过慢",
        FailureType.ERROR_RATE_HIGH: "错误率过高"
    }
    return descriptions.get(failure_type, "未知故障类型")
