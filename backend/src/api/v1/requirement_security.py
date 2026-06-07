"""
需求管理安全和权限API接口

提供需求管理模块的安全和权限相关API接口，包括：
- 权限管理接口
- 数据安全接口
- 备份管理接口
- 审计日志接口
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.user import User
from ...models.requirement_permission import (
    RequirementPermissionType, RequirementDataScope, RequirementPermissionEffect,
    RequirementAuditAction, RequirementAuditResult
)
from ...services.requirement_permission_service import RequirementPermissionService
from ...services.requirement_audit_service import RequirementAuditService
from ...services.requirement_data_security_service import RequirementDataSecurityService

router = APIRouter(prefix="/requirement-security", tags=["需求安全管理"])


# Pydantic模型定义
class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    permission_type: RequirementPermissionType
    requirement_id: Optional[int] = None
    project_id: Optional[int] = None
    additional_context: Optional[Dict[str, Any]] = None


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""
    has_permission: bool
    permission_type: str
    requirement_id: Optional[int] = None
    project_id: Optional[int] = None
    checked_at: datetime


class BatchPermissionCheckRequest(BaseModel):
    """批量权限检查请求"""
    permission_types: List[RequirementPermissionType]
    requirement_id: Optional[int] = None
    project_id: Optional[int] = None


class BatchPermissionCheckResponse(BaseModel):
    """批量权限检查响应"""
    permissions: Dict[str, bool]
    requirement_id: Optional[int] = None
    project_id: Optional[int] = None
    checked_at: datetime


class GrantRolePermissionRequest(BaseModel):
    """授予角色权限请求"""
    role_id: int
    permission_type: RequirementPermissionType
    data_scope: RequirementDataScope = RequirementDataScope.ALL
    project_ids: Optional[List[int]] = None
    allowed_statuses: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class GrantUserPermissionRequest(BaseModel):
    """授予用户权限请求"""
    user_id: int
    permission_type: RequirementPermissionType
    data_scope: RequirementDataScope = RequirementDataScope.ALL
    project_ids: Optional[List[int]] = None
    allowed_statuses: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    reason: Optional[str] = None


class CreateBackupRequest(BaseModel):
    """创建备份请求"""
    project_id: Optional[int] = None
    backup_name: Optional[str] = None
    include_audit_logs: bool = True
    compress: bool = True


class RestoreBackupRequest(BaseModel):
    """恢复备份请求"""
    backup_path: str
    target_project_id: Optional[int] = None
    verify_integrity: bool = True
    overwrite_existing: bool = False


class AuditLogQuery(BaseModel):
    """审计日志查询参数"""
    user_id: Optional[int] = None
    action: Optional[RequirementAuditAction] = None
    result: Optional[RequirementAuditResult] = None
    resource_type: Optional[str] = None
    requirement_id: Optional[int] = None
    project_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=1000)
    order_by: str = "created_at"
    order_direction: str = "desc"


# 权限管理接口
@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    request_data: PermissionCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """检查用户权限"""
    permission_service = RequirementPermissionService(db)
    
    has_permission = await permission_service.check_permission(
        user_id=current_user.id,
        permission_type=request_data.permission_type,
        requirement_id=request_data.requirement_id,
        project_id=request_data.project_id,
        additional_context=request_data.additional_context
    )
    
    return PermissionCheckResponse(
        has_permission=has_permission,
        permission_type=request_data.permission_type.value,
        requirement_id=request_data.requirement_id,
        project_id=request_data.project_id,
        checked_at=datetime.utcnow()
    )


@router.post("/permissions/check-batch", response_model=BatchPermissionCheckResponse)
async def check_permissions_batch(
    request_data: BatchPermissionCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量检查用户权限"""
    permission_service = RequirementPermissionService(db)
    
    permissions = await permission_service.check_permissions(
        user_id=current_user.id,
        permission_types=request_data.permission_types,
        requirement_id=request_data.requirement_id,
        project_id=request_data.project_id
    )
    
    # 转换枚举键为字符串
    permissions_dict = {perm_type.value: has_perm for perm_type, has_perm in permissions.items()}
    
    return BatchPermissionCheckResponse(
        permissions=permissions_dict,
        requirement_id=request_data.requirement_id,
        project_id=request_data.project_id,
        checked_at=datetime.utcnow()
    )


@router.get("/permissions/user/{user_id}")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的所有需求权限"""
    permission_service = RequirementPermissionService(db)
    
    # 检查是否有查看权限的权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    permissions = await permission_service.get_user_permissions(user_id)
    return permissions


@router.post("/permissions/roles/grant")
async def grant_role_permission(
    request_data: GrantRolePermissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """为角色授予需求权限"""
    permission_service = RequirementPermissionService(db)
    
    # 检查权限管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    permission = await permission_service.grant_role_permission(
        role_id=request_data.role_id,
        permission_type=request_data.permission_type,
        granted_by=current_user.id,
        data_scope=request_data.data_scope,
        project_ids=request_data.project_ids,
        allowed_statuses=request_data.allowed_statuses,
        conditions=request_data.conditions,
        effective_from=request_data.effective_from,
        effective_to=request_data.effective_to
    )
    
    return permission.to_dict()


@router.post("/permissions/users/grant")
async def grant_user_permission(
    request_data: GrantUserPermissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """为用户直接授予需求权限"""
    permission_service = RequirementPermissionService(db)
    
    # 检查权限管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    permission = await permission_service.grant_user_permission(
        user_id=request_data.user_id,
        permission_type=request_data.permission_type,
        granted_by=current_user.id,
        data_scope=request_data.data_scope,
        project_ids=request_data.project_ids,
        allowed_statuses=request_data.allowed_statuses,
        conditions=request_data.conditions,
        effective_from=request_data.effective_from,
        effective_to=request_data.effective_to,
        reason=request_data.reason
    )
    
    return permission.to_dict()


@router.delete("/permissions/roles/{role_id}/{permission_type}")
async def revoke_role_permission(
    role_id: int,
    permission_type: RequirementPermissionType,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """撤销角色的需求权限"""
    permission_service = RequirementPermissionService(db)
    
    # 检查权限管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    success = await permission_service.revoke_role_permission(
        role_id=role_id,
        permission_type=permission_type,
        revoked_by=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    return {"message": "权限撤销成功"}


@router.delete("/permissions/users/{user_id}/{permission_type}")
async def revoke_user_permission(
    user_id: int,
    permission_type: RequirementPermissionType,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """撤销用户的直接需求权限"""
    permission_service = RequirementPermissionService(db)
    
    # 检查权限管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    success = await permission_service.revoke_user_permission(
        user_id=user_id,
        permission_type=permission_type,
        revoked_by=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    return {"message": "权限撤销成功"}


@router.get("/permissions/accessible-requirements")
async def get_accessible_requirements(
    project_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户可访问的需求ID列表"""
    permission_service = RequirementPermissionService(db)
    
    requirement_ids = await permission_service.get_accessible_requirements(
        user_id=current_user.id,
        project_id=project_id
    )
    
    return {
        "user_id": current_user.id,
        "project_id": project_id,
        "accessible_requirement_ids": requirement_ids,
        "count": len(requirement_ids)
    }


# 审计日志接口
@router.post("/audit/logs/query")
async def query_audit_logs(
    query_params: AuditLogQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查询审计日志"""
    permission_service = RequirementPermissionService(db)
    audit_service = RequirementAuditService(db)
    
    # 检查查看审计日志权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.VIEW_ANALYTICS
    )
    
    logs, total_count = await audit_service.get_audit_logs(
        user_id=query_params.user_id,
        action=query_params.action,
        result=query_params.result,
        resource_type=query_params.resource_type,
        requirement_id=query_params.requirement_id,
        project_id=query_params.project_id,
        start_date=query_params.start_date,
        end_date=query_params.end_date,
        ip_address=query_params.ip_address,
        page=query_params.page,
        page_size=query_params.page_size,
        order_by=query_params.order_by,
        order_direction=query_params.order_direction
    )
    
    return {
        "logs": [log.to_dict() for log in logs],
        "total_count": total_count,
        "page": query_params.page,
        "page_size": query_params.page_size,
        "total_pages": (total_count + query_params.page_size - 1) // query_params.page_size
    }


@router.get("/audit/users/{user_id}/activity")
async def get_user_activity_summary(
    user_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户活动摘要"""
    permission_service = RequirementPermissionService(db)
    audit_service = RequirementAuditService(db)
    
    # 检查查看审计日志权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.VIEW_ANALYTICS
    )
    
    summary = await audit_service.get_user_activity_summary(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return summary


@router.get("/audit/requirements/{requirement_id}/trail")
async def get_requirement_audit_trail(
    requirement_id: int,
    include_related: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取需求的完整审计轨迹"""
    permission_service = RequirementPermissionService(db)
    audit_service = RequirementAuditService(db)
    
    # 检查查看需求权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.VIEW, requirement_id=requirement_id
    )
    
    trail = await audit_service.get_requirement_audit_trail(
        requirement_id=requirement_id,
        include_related=include_related
    )
    
    return trail


@router.get("/audit/projects/{project_id}/summary")
async def get_project_audit_summary(
    project_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目审计摘要"""
    permission_service = RequirementPermissionService(db)
    audit_service = RequirementAuditService(db)
    
    # 检查查看分析权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.VIEW_ANALYTICS, project_id=project_id
    )
    
    summary = await audit_service.get_project_audit_summary(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return summary


@router.get("/audit/suspicious-activities")
async def detect_suspicious_activities(
    lookback_hours: int = Query(24, ge=1, le=168),
    threshold_operations: int = Query(100, ge=1),
    threshold_failures: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """检测可疑活动"""
    permission_service = RequirementPermissionService(db)
    audit_service = RequirementAuditService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    suspicious = await audit_service.detect_suspicious_activities(
        lookback_hours=lookback_hours,
        threshold_operations=threshold_operations,
        threshold_failures=threshold_failures
    )
    
    return {
        "suspicious_activities": suspicious,
        "detection_parameters": {
            "lookback_hours": lookback_hours,
            "threshold_operations": threshold_operations,
            "threshold_failures": threshold_failures
        },
        "detected_at": datetime.utcnow().isoformat()
    }


@router.get("/audit/compliance-report")
async def generate_compliance_report(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    project_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成合规性报告"""
    permission_service = RequirementPermissionService(db)
    audit_service = RequirementAuditService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    report = await audit_service.generate_compliance_report(
        start_date=start_date,
        end_date=end_date,
        project_id=project_id
    )
    
    return report


# 数据安全和备份接口
@router.post("/backup/create")
async def create_backup(
    request_data: CreateBackupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建需求数据备份"""
    permission_service = RequirementPermissionService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    security_service = RequirementDataSecurityService(db)
    
    # 在后台任务中执行备份
    def create_backup_task():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            backup_info = loop.run_until_complete(
                security_service.create_requirement_backup(
                    project_id=request_data.project_id,
                    backup_name=request_data.backup_name,
                    include_audit_logs=request_data.include_audit_logs,
                    compress=request_data.compress
                )
            )
            return backup_info
        finally:
            loop.close()
    
    background_tasks.add_task(create_backup_task)
    
    return {
        "message": "备份任务已启动",
        "project_id": request_data.project_id,
        "backup_name": request_data.backup_name,
        "started_at": datetime.utcnow().isoformat()
    }


@router.get("/backup/list")
async def list_backups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """列出所有备份"""
    permission_service = RequirementPermissionService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    security_service = RequirementDataSecurityService(db)
    backups = await security_service.list_backups()
    
    return {
        "backups": backups,
        "count": len(backups)
    }


@router.post("/backup/restore")
async def restore_backup(
    request_data: RestoreBackupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """恢复需求数据备份"""
    permission_service = RequirementPermissionService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    security_service = RequirementDataSecurityService(db)
    
    # 在后台任务中执行恢复
    def restore_backup_task():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            restore_info = loop.run_until_complete(
                security_service.restore_requirement_backup(
                    backup_path=request_data.backup_path,
                    target_project_id=request_data.target_project_id,
                    verify_integrity=request_data.verify_integrity,
                    overwrite_existing=request_data.overwrite_existing
                )
            )
            return restore_info
        finally:
            loop.close()
    
    background_tasks.add_task(restore_backup_task)
    
    return {
        "message": "恢复任务已启动",
        "backup_path": request_data.backup_path,
        "target_project_id": request_data.target_project_id,
        "started_at": datetime.utcnow().isoformat()
    }


@router.delete("/backup/{backup_name}")
async def delete_backup(
    backup_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除备份"""
    permission_service = RequirementPermissionService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    security_service = RequirementDataSecurityService(db)
    success = await security_service.delete_backup(backup_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="备份不存在")
    
    return {"message": "备份删除成功"}


@router.post("/backup/cleanup")
async def cleanup_old_backups(
    keep_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """清理旧备份"""
    permission_service = RequirementPermissionService(db)
    
    # 检查管理权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.MANAGE_PERMISSIONS
    )
    
    security_service = RequirementDataSecurityService(db)
    result = await security_service.cleanup_old_backups(keep_days=keep_days)
    
    return result


# 数据加密接口
@router.post("/encryption/encrypt-requirement/{requirement_id}")
async def encrypt_requirement_data(
    requirement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """加密需求敏感数据"""
    permission_service = RequirementPermissionService(db)
    
    # 检查编辑权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.EDIT, requirement_id=requirement_id
    )
    
    # 获取需求
    from sqlalchemy import select
    from ...models.requirement import Requirement
    
    query = select(Requirement).where(Requirement.id == requirement_id)
    result = await db.execute(query)
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    # 加密敏感字段
    security_service = RequirementDataSecurityService(db)
    encrypted_requirement = await security_service.encrypt_requirement_sensitive_fields(requirement)
    
    # 保存更改
    await db.commit()
    
    return {
        "message": "需求敏感数据加密成功",
        "requirement_id": requirement_id,
        "encrypted_at": datetime.utcnow().isoformat()
    }


@router.post("/encryption/decrypt-requirement/{requirement_id}")
async def decrypt_requirement_data(
    requirement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """解密需求敏感数据（仅用于查看）"""
    permission_service = RequirementPermissionService(db)
    
    # 检查查看权限
    await permission_service.require_permission(
        current_user.id, RequirementPermissionType.VIEW, requirement_id=requirement_id
    )
    
    # 获取需求
    from sqlalchemy import select
    from ...models.requirement import Requirement
    
    query = select(Requirement).where(Requirement.id == requirement_id)
    result = await db.execute(query)
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    # 解密敏感字段（仅用于返回，不保存到数据库）
    security_service = RequirementDataSecurityService(db)
    decrypted_requirement = await security_service.decrypt_requirement_sensitive_fields(requirement)
    
    return {
        "requirement_id": requirement_id,
        "title": decrypted_requirement.title,
        "description": decrypted_requirement.description,
        "acceptance_criteria": decrypted_requirement.acceptance_criteria,
        "custom_fields": decrypted_requirement.custom_fields,
        "decrypted_at": datetime.utcnow().isoformat()
    }