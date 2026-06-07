"""
配置审核API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..schemas.config import (
    ConfigAuditCreateRequest, ConfigAuditResponse, ApiResponse
)
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..services.config_permission import config_permission_service
from ..models.config import ConfigAudit, SystemConfig, Environment, PermissionAction
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audits", tags=["配置审核"])


def _enum_value(value):
    if value is None:
        return None
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    if hasattr(value, "name"):
        return value.name
    return value


def _audit_to_dict(audit: ConfigAudit) -> Dict[str, Any]:
    return {
        "id": audit.id,
        "audit_code": audit.audit_code,
        "config_id": audit.config_id,
        "config_key": audit.config_key,
        "environment": _enum_value(audit.environment),
        "old_value": audit.old_value,
        "new_value": audit.new_value,
        "change_type": _enum_value(audit.change_type),
        "audit_status": _enum_value(audit.audit_status),
        "priority": _enum_value(audit.priority) or "MEDIUM",
        "apply_user_id": audit.apply_user_id,
        "audit_user_id": audit.audit_user_id,
        "apply_reason": audit.apply_reason,
        "audit_reason": audit.audit_reason,
        "impact_assessment": audit.impact_assessment,
        "risk_level": _enum_value(audit.risk_level) or "LOW",
        "estimated_downtime": audit.estimated_downtime,
        "rollback_plan": audit.rollback_plan,
        "applied_at": audit.applied_at.isoformat() if audit.applied_at else None,
        "audited_at": audit.audited_at.isoformat() if audit.audited_at else None,
        "executed_at": audit.executed_at.isoformat() if audit.executed_at else None,
        "expires_at": audit.expires_at.isoformat() if audit.expires_at else None,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "updated_at": audit.updated_at.isoformat() if audit.updated_at else None,
        "created_by": audit.created_by,
        "updated_by": audit.updated_by,
    }


def _user_id(user) -> int:
    if isinstance(user, dict):
        return int(user.get("id") or user.get("user_id") or user.get("sub") or 0)
    return int(getattr(user, "id", 0))


def _username(user) -> str:
    if isinstance(user, dict):
        return user.get("username") or user.get("sub") or ""
    return getattr(user, "username", "")


def _model_environment(value) -> Environment:
    raw_value = value.value if hasattr(value, "value") else value
    return Environment(raw_value)


def _build_audit_query(db: Session, filters: Dict[str, Any]):
    query = db.query(ConfigAudit)
    if filters.get("audit_status"):
        query = query.filter(ConfigAudit.audit_status == filters["audit_status"])
    if filters.get("config_key"):
        query = query.filter(ConfigAudit.config_key.contains(filters["config_key"]))
    if filters.get("environment"):
        query = query.filter(ConfigAudit.environment == Environment(filters["environment"]))
    if filters.get("priority"):
        query = query.filter(ConfigAudit.priority == filters["priority"])
    if filters.get("apply_user_id"):
        query = query.filter(ConfigAudit.apply_user_id == filters["apply_user_id"])
    if filters.get("audit_user_id"):
        query = query.filter(ConfigAudit.audit_user_id == filters["audit_user_id"])
    return query


@router.post("", response_model=ApiResponse[dict])
async def create_audit_request(
    request_data: ConfigAuditCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """创建配置审核申请"""
    try:
        # 检查用户是否有提交审核申请的权限
        model_env = _model_environment(request_data.environment)
        operator_id = _user_id(current_user)
        has_permission = await config_permission_service.check_config_permission(
            operator_id, request_data.config_key, model_env, PermissionAction.WRITE
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限提交此配置的审核申请"
            )
        
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == request_data.config_key,
            SystemConfig.environment == model_env,
            SystemConfig.deleted_at.is_(None),
        ).first()

        audit = ConfigAudit(
            audit_code=f"CA{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            config_id=config.id if config else None,
            config_key=request_data.config_key,
            environment=model_env,
            old_value=request_data.old_value,
            new_value=request_data.new_value,
            change_type=request_data.change_type,
            audit_status="PENDING",
            priority=request_data.priority or "MEDIUM",
            apply_user_id=operator_id,
            apply_reason=request_data.apply_reason,
            risk_level="LOW",
            estimated_downtime=request_data.estimated_downtime,
            rollback_plan=request_data.rollback_plan,
            applied_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            created_by=operator_id,
            updated_by=operator_id,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        
        return ApiResponse(success=True, data=_audit_to_dict(audit), message="审核申请创建成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建审核申请失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建审核申请失败: {str(e)}"
        )


@router.get("", response_model=ApiResponse[dict])
async def get_audit_list(
    audit_status: Optional[str] = Query(None, description="审核状态"),
    config_key: Optional[str] = Query(None, description="配置键"),
    environment: Optional[str] = Query(None, description="环境"),
    priority: Optional[str] = Query(None, description="优先级"),
    apply_user_id: Optional[int] = Query(None, description="申请人ID"),
    audit_user_id: Optional[int] = Query(None, description="审核人ID"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审核列表"""
    try:
        # 构建过滤条件
        filters = {}
        if audit_status:
            filters['audit_status'] = audit_status
        if config_key:
            filters['config_key'] = config_key
        if environment:
            filters['environment'] = environment
        if priority:
            filters['priority'] = priority
        if apply_user_id:
            filters['apply_user_id'] = apply_user_id
        if audit_user_id:
            filters['audit_user_id'] = audit_user_id
        
        query = _build_audit_query(db, filters)
        total = query.count()
        audits = query.order_by(ConfigAudit.applied_at.desc(), ConfigAudit.id.desc()).offset(
            (page - 1) * size
        ).limit(size).all()
        result = {
            "items": [_audit_to_dict(audit) for audit in audits],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
        return ApiResponse(success=True, data=result, message="获取审核列表成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审核列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核列表失败: {str(e)}"
        )


@router.get("/pending", response_model=ApiResponse[List[dict]])
async def get_pending_audits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取待审核列表"""
    try:
        audits = db.query(ConfigAudit).filter(
            ConfigAudit.audit_status == "PENDING"
        ).order_by(ConfigAudit.applied_at.desc(), ConfigAudit.id.desc()).all()
        result = [_audit_to_dict(audit) for audit in audits]
        
        return ApiResponse(success=True, data=result, message="获取待审核列表成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取待审核列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待审核列表失败: {str(e)}"
        )


@router.get("/statistics", response_model=ApiResponse[dict])
async def get_audit_statistics(
    time_range: Optional[str] = Query(None, description="时间范围"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审核统计信息"""
    try:
        query = db.query(ConfigAudit)
        if time_range:
            days = {"7d": 7, "30d": 30, "90d": 90}.get(time_range)
            if days:
                query = query.filter(ConfigAudit.applied_at >= datetime.utcnow() - timedelta(days=days))

        total = query.count()
        status_stats = {
            "total": total,
            "pending": query.filter(ConfigAudit.audit_status == "PENDING").count(),
            "approved": query.filter(ConfigAudit.audit_status == "APPROVED").count(),
            "rejected": query.filter(ConfigAudit.audit_status == "REJECTED").count(),
            "cancelled": query.filter(ConfigAudit.audit_status == "CANCELLED").count(),
        }
        priority_stats = {
            "low": query.filter(ConfigAudit.priority == "LOW").count(),
            "medium": query.filter(ConfigAudit.priority == "MEDIUM").count(),
            "high": query.filter(ConfigAudit.priority == "HIGH").count(),
            "urgent": query.filter(ConfigAudit.priority == "URGENT").count(),
        }
        risk_stats = {
            "low": query.filter(ConfigAudit.risk_level == "LOW").count(),
            "medium": query.filter(ConfigAudit.risk_level == "MEDIUM").count(),
            "high": query.filter(ConfigAudit.risk_level == "HIGH").count(),
            "critical": query.filter(ConfigAudit.risk_level == "CRITICAL").count(),
        }
        processed_count = status_stats["approved"] + status_stats["rejected"]
        approval_rate = (status_stats["approved"] / processed_count * 100) if processed_count else 0
        result = {
            "status_stats": status_stats,
            "priority_stats": priority_stats,
            "risk_stats": risk_stats,
            "approval_rate": round(approval_rate, 1),
            "processed_count": processed_count,
        }
        
        return ApiResponse(success=True, data=result, message="获取审核统计成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审核统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核统计失败: {str(e)}"
        )


@router.get("/{audit_id}", response_model=ApiResponse[dict])
async def get_audit_detail(
    audit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审核详情"""
    try:
        audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审核记录不存在"
            )
        
        return ApiResponse(success=True, data=_audit_to_dict(audit), message="获取审核详情成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审核详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核详情失败: {str(e)}"
        )


@router.post("/{audit_id}/approve", response_model=ApiResponse[dict])
async def approve_audit(
    audit_id: int,
    audit_reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """审核通过"""
    try:
        audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录不存在")
        if _enum_value(audit.audit_status) not in ("PENDING", "IN_REVIEW"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前审核状态不允许通过")

        now = datetime.utcnow()
        audit.audit_status = "APPROVED"
        audit.audit_user_id = _user_id(current_user)
        audit.audit_reason = audit_reason
        audit.audited_at = now
        audit.executed_at = now
        audit.updated_by = _user_id(current_user)
        db.commit()
        db.refresh(audit)
        
        return ApiResponse(success=True, data=_audit_to_dict(audit), message="审核通过成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审核通过失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核通过失败: {str(e)}"
        )


@router.post("/{audit_id}/reject", response_model=ApiResponse[dict])
async def reject_audit(
    audit_id: int,
    audit_reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """审核驳回"""
    try:
        if not audit_reason or audit_reason.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="驳回原因不能为空"
            )
        
        audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录不存在")
        if _enum_value(audit.audit_status) not in ("PENDING", "IN_REVIEW"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前审核状态不允许驳回")

        audit.audit_status = "REJECTED"
        audit.audit_user_id = _user_id(current_user)
        audit.audit_reason = audit_reason.strip()
        audit.audited_at = datetime.utcnow()
        audit.updated_by = _user_id(current_user)
        db.commit()
        db.refresh(audit)
        
        return ApiResponse(success=True, data=_audit_to_dict(audit), message="审核驳回成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审核驳回失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核驳回失败: {str(e)}"
        )


@router.post("/{audit_id}/comment", response_model=ApiResponse[dict])
async def add_audit_comment(
    audit_id: int,
    comment: str,
    current_user: User = Depends(get_current_user)
):
    """添加审核意见"""
    try:
        # TODO: 实现添加审核意见功能
        # 可以支持在审核过程中添加多条意见
        
        return ApiResponse(
            success=True, 
            data={"audit_id": audit_id, "comment_added": True}, 
            message="审核意见添加成功"
        )
        
    except Exception as e:
        logger.error(f"添加审核意见失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加审核意见失败: {str(e)}"
        )


@router.post("/{audit_id}/cancel", response_model=ApiResponse[dict])
async def cancel_audit(
    audit_id: int,
    cancel_reason: str,
    current_user: User = Depends(get_current_user)
):
    """取消审核申请"""
    try:
        # TODO: 实现取消审核申请功能
        # 只有申请人或管理员可以取消审核
        
        return ApiResponse(
            success=True, 
            data={"audit_id": audit_id, "cancelled": True}, 
            message="审核申请已取消"
        )
        
    except Exception as e:
        logger.error(f"取消审核申请失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消审核申请失败: {str(e)}"
        )


@router.get("/{audit_id}/history", response_model=ApiResponse[List[dict]])
async def get_audit_history(
    audit_id: int,
    current_user: User = Depends(get_current_user)
):
    """获取审核历史"""
    try:
        # TODO: 实现获取审核历史功能
        # 显示审核过程中的所有操作记录
        
        history = [
            {
                "id": 1,
                "action": "submitted",
                "user_id": _user_id(current_user),
                "user_name": _username(current_user),
                "comment": "提交审核申请",
                "created_at": "2024-01-01T10:00:00Z"
            }
        ]
        
        return ApiResponse(success=True, data=history, message="获取审核历史成功")
        
    except Exception as e:
        logger.error(f"获取审核历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核历史失败: {str(e)}"
        )


# 审核相关的WebSocket通知端点
@router.websocket("/ws/{audit_id}")
async def audit_websocket_endpoint(websocket, audit_id: int):
    """审核状态实时推送"""
    try:
        # TODO: 实现WebSocket连接和实时推送
        pass
    except Exception as e:
        logger.error(f"审核WebSocket连接失败: {e}")
