"""
配置审核API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..schemas.config import (
    ConfigAuditCreateRequest, ConfigAuditResponse, ApiResponse
)
from ..core.database import get_db, SessionLocal
from ..core.security import get_current_user
from ..models.user import User
from ..services.config_permission import config_permission_service
from ..models.config import ConfigAudit, ConfigAuditComment, SystemConfig, Environment, PermissionAction
from ..utils.jwt import verify_token
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


def _is_superuser(db: Session, user_id: int) -> bool:
    """查库判断用户是否为超级管理员。

    注意：JWT 里不含 is_superuser，token 解析出的该字段恒为 False，
    因此管理员判断必须查库，不能信任 current_user.is_superuser。
    """
    if not user_id:
        return False
    row = db.query(User.is_superuser).filter(User.id == user_id).first()
    return bool(row and row[0])


def _audit_usernames(db: Session, user_ids) -> Dict[int, str]:
    """批量取用户名，用于历史记录展示。"""
    ids = [uid for uid in set(user_ids) if uid]
    if not ids:
        return {}
    rows = db.query(User.id, User.username).filter(User.id.in_(ids)).all()
    return {row[0]: row[1] for row in rows}


def _comment_to_dict(comment: ConfigAuditComment) -> Dict[str, Any]:
    return {
        "id": comment.id,
        "audit_id": comment.audit_id,
        "user_id": comment.user_id,
        "user_name": comment.username,
        "comment": comment.comment,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加审核意见"""
    try:
        if not comment or comment.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="审核意见不能为空"
            )

        audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审核记录不存在"
            )
        if _enum_value(audit.audit_status) not in ("PENDING", "IN_REVIEW"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前审核状态不允许添加意见"
            )

        record = ConfigAuditComment(
            audit_id=audit_id,
            user_id=_user_id(current_user),
            username=_username(current_user) or _audit_usernames(db, [_user_id(current_user)]).get(_user_id(current_user), ""),
            comment=comment.strip(),
            created_by=_user_id(current_user),
            updated_by=_user_id(current_user),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return ApiResponse(
            success=True,
            data=_comment_to_dict(record),
            message="审核意见添加成功"
        )

    except HTTPException:
        raise
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消审核申请"""
    try:
        audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审核记录不存在"
            )

        operator_id = _user_id(current_user)
        if audit.apply_user_id != operator_id and not _is_superuser(db, operator_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有申请人或管理员可以取消审核"
            )
        if _enum_value(audit.audit_status) not in ("PENDING", "IN_REVIEW"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前审核状态不允许取消"
            )

        audit.audit_status = "CANCELLED"
        audit.audit_user_id = operator_id
        audit.audit_reason = cancel_reason
        audit.updated_by = operator_id
        db.commit()
        db.refresh(audit)

        return ApiResponse(
            success=True,
            data=_audit_to_dict(audit),
            message="审核申请已取消"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消审核申请失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消审核申请失败: {str(e)}"
        )


@router.get("/{audit_id}/history", response_model=ApiResponse[List[dict]])
async def get_audit_history(
    audit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审核历史"""
    try:
        audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审核记录不存在"
            )

        comments = db.query(ConfigAuditComment).filter(
            ConfigAuditComment.audit_id == audit_id
        ).order_by(ConfigAuditComment.created_at.asc(), ConfigAuditComment.id.asc()).all()

        user_ids = [audit.apply_user_id, audit.audit_user_id]
        user_ids += [c.user_id for c in comments]
        names = _audit_usernames(db, user_ids)

        def _event(action: str, user_id, comment: str, when, seq: int):
            return {
                "id": None,
                "action": action,
                "user_id": user_id,
                "user_name": names.get(user_id, ""),
                "comment": comment,
                "created_at": when.isoformat() if when else None,
                "_sort": when or datetime.min,
                "_seq": seq,
            }

        events = [_event("submitted", audit.apply_user_id, "提交审核申请", audit.applied_at, 0)]
        status_value = _enum_value(audit.audit_status)
        if audit.audited_at:
            action = "approved" if status_value == "APPROVED" else (
                "rejected" if status_value == "REJECTED" else "reviewed"
            )
            events.append(_event(action, audit.audit_user_id, audit.audit_reason or "", audit.audited_at, 2))
        if status_value == "CANCELLED":
            events.append(_event("cancelled", audit.audit_user_id, audit.audit_reason or "取消审核申请", audit.updated_at, 3))
        if audit.executed_at and status_value == "APPROVED":
            events.append(_event("executed", audit.audit_user_id, "审核通过后执行", audit.executed_at, 4))
        for c in comments:
            events.append({
                "id": c.id,
                "action": "comment",
                "user_id": c.user_id,
                "user_name": c.username or names.get(c.user_id, ""),
                "comment": c.comment,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "_sort": c.created_at or datetime.min,
                "_seq": 1,
            })

        events.sort(key=lambda e: (e["_sort"], e["_seq"]))
        for e in events:
            e.pop("_sort", None)
            e.pop("_seq", None)

        return ApiResponse(success=True, data=events, message="获取审核历史成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审核历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核历史失败: {str(e)}"
        )


# 审核相关的WebSocket通知端点
@router.websocket("/ws/{audit_id}")
async def audit_websocket_endpoint(websocket: WebSocket, audit_id: int, token: Optional[str] = Query(None)):
    """审核状态实时推送

    连接时用 ?token=<JWT> 鉴权，握手后先推送一次当前审核状态快照；
    客户端发送任意文本消息（例如 "status"）即再次推送最新快照，
    发送 "ping" 回复 "pong"。断开即结束。
    """
    if not token:
        await websocket.close(code=4001, reason="未提供认证令牌")
        return
    payload = verify_token(token)
    if not payload or payload.get("sub") is None:
        await websocket.close(code=4001, reason="认证令牌无效或已过期")
        return

    await websocket.accept()
    db = SessionLocal()
    try:
        def _snapshot():
            audit = db.query(ConfigAudit).filter(ConfigAudit.id == audit_id).first()
            if not audit:
                return {"type": "audit_status", "audit_id": audit_id, "exists": False}
            data = _audit_to_dict(audit)
            data["type"] = "audit_status"
            data["exists"] = True
            return data

        await websocket.send_json(_snapshot())
        while True:
            try:
                message = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            if message.strip().lower() == "ping":
                await websocket.send_text("pong")
            else:
                db.expire_all()
                await websocket.send_json(_snapshot())
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"审核WebSocket连接失败: {e}")
    finally:
        db.close()
