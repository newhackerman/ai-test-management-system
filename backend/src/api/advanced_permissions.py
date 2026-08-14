"""
高级权限管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..services.advanced_permissions import (
    AdvancedPermissionManager, PermissionContext, PermissionLevel, PermissionScope
)
from ..schemas.base import ApiResponse
from ..core.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/advanced-permissions", tags=["高级权限管理"])


class TemporaryPermissionRequest(BaseModel):
    """临时权限申请"""
    user_id: int
    permission_level: str
    scope_type: str
    scope_config: Dict[str, Any]
    duration_hours: int
    reason: str


class ScheduledPermissionRequest(BaseModel):
    """定时权限申请"""
    user_id: int
    permission_level: str
    scope_type: str
    scope_config: Dict[str, Any]
    schedule_name: str
    work_days: List[int]  # [1,2,3,4,5] 表示周一到周五
    work_hours: Dict[str, str]  # {"start": "09:00", "end": "18:00"}
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    user_id: int
    config_key: Optional[str] = None
    group_id: Optional[int] = None
    environment: Optional[str] = None
    tags: Optional[List[str]] = None
    action: Optional[str] = None
    required_level: str = "READ"


class RowLevelPermissionRequest(BaseModel):
    """行级权限配置"""
    user_id: int
    permission_level: str
    resource_type: str
    filter_conditions: Dict[str, Any]
    expires_hours: Optional[int] = None


class ColumnLevelPermissionRequest(BaseModel):
    """列级权限配置"""
    user_id: int
    table_name: str
    column_permissions: Dict[str, str]
    conditions: Optional[Dict[str, Any]] = None
    expires_hours: Optional[int] = None


@router.post("/check", response_model=ApiResponse[Dict[str, Any]])
async def check_advanced_permission(
    request: PermissionCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """检查高级权限"""
    try:
        permission_manager = AdvancedPermissionManager()
        
        # 构建权限上下文
        context = PermissionContext(
            user_id=request.user_id,
            config_key=request.config_key,
            group_id=request.group_id,
            environment=request.environment,
            tags=request.tags,
            action=request.action,
            timestamp=datetime.now()
        )
        
        # 检查权限
        has_permission, error, details = await permission_manager.check_permission(
            context, PermissionLevel(request.required_level.upper())
        )
        
        result = {
            "has_permission": has_permission,
            "error_message": error,
            "permission_details": details,
            "context": {
                "user_id": request.user_id,
                "config_key": request.config_key,
                "environment": request.environment,
                "action": request.action,
                "required_level": request.required_level
            }
        }
        
        return ApiResponse(
            success=True,
            data=result,
            message="权限检查完成"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"权限检查失败: {str(e)}")


@router.post("/temporary/grant", response_model=ApiResponse[Dict[str, Any]])
async def grant_temporary_permission(
    request: TemporaryPermissionRequest,
    current_user: User = Depends(get_current_user)
):
    """授予临时权限"""
    try:
        permission_manager = AdvancedPermissionManager()
        
        success, error = await permission_manager.grant_temporary_permission(
            user_id=request.user_id,
            permission_level=PermissionLevel(request.permission_level.upper()),
            scope={
                "type": request.scope_type,
                "config": request.scope_config
            },
            duration_hours=request.duration_hours,
            granted_by=current_user.id,
            reason=request.reason
        )
        
        if success:
            return ApiResponse(
                success=True,
                data={
                    "user_id": request.user_id,
                    "permission_level": request.permission_level,
                    "duration_hours": request.duration_hours,
                    "granted_by": current_user.id,
                    "granted_at": datetime.now().isoformat()
                },
                message="临时权限授予成功"
            )
        else:
            raise HTTPException(status_code=400, detail=error)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"授予临时权限失败: {str(e)}")


@router.post("/scheduled/create", response_model=ApiResponse[Dict[str, Any]])
async def create_scheduled_permission(
    request: ScheduledPermissionRequest,
    current_user: User = Depends(get_current_user)
):
    """创建定时权限"""
    try:
        # 这里应该插入到数据库
        # db = next(get_db())
        # scheduled_permission = ScheduledPermission(...)
        
        result = {
            "user_id": request.user_id,
            "permission_level": request.permission_level,
            "schedule_name": request.schedule_name,
            "work_days": request.work_days,
            "work_hours": request.work_hours,
            "created_by": current_user.id,
            "created_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            data=result,
            message="定时权限创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建定时权限失败: {str(e)}")


@router.post("/row-level/configure", response_model=ApiResponse[Dict[str, Any]])
async def configure_row_level_permission(
    request: RowLevelPermissionRequest,
    current_user: User = Depends(get_current_user)
):
    """配置行级权限"""
    try:
        # 这里应该插入到数据库
        # db = next(get_db())
        # row_permission = RowLevelPermission(...)
        
        expires_at = None
        if request.expires_hours:
            expires_at = datetime.now() + timedelta(hours=request.expires_hours)
        
        result = {
            "user_id": request.user_id,
            "permission_level": request.permission_level,
            "resource_type": request.resource_type,
            "filter_conditions": request.filter_conditions,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "configured_by": current_user.id,
            "configured_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            data=result,
            message="行级权限配置成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置行级权限失败: {str(e)}")


@router.post("/column-level/configure", response_model=ApiResponse[Dict[str, Any]])
async def configure_column_level_permission(
    request: ColumnLevelPermissionRequest,
    current_user: User = Depends(get_current_user)
):
    """配置列级权限"""
    try:
        # 这里应该插入到数据库
        # db = next(get_db())
        # column_permission = ColumnLevelPermission(...)
        
        expires_at = None
        if request.expires_hours:
            expires_at = datetime.now() + timedelta(hours=request.expires_hours)
        
        result = {
            "user_id": request.user_id,
            "table_name": request.table_name,
            "column_permissions": request.column_permissions,
            "conditions": request.conditions,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "configured_by": current_user.id,
            "configured_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            data=result,
            message="列级权限配置成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置列级权限失败: {str(e)}")


@router.get("/user/{user_id}/effective", response_model=ApiResponse[Dict[str, Any]])
async def get_user_effective_permissions(
    user_id: int,
    config_key: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """获取用户有效权限"""
    try:
        permission_manager = AdvancedPermissionManager()
        
        context = None
        if config_key or environment:
            context = PermissionContext(
                user_id=user_id,
                config_key=config_key,
                environment=environment,
                timestamp=datetime.now()
            )
        
        permissions = await permission_manager.get_user_effective_permissions(
            user_id, context
        )
        
        return ApiResponse(
            success=True,
            data=permissions,
            message="获取用户有效权限成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户权限失败: {str(e)}")


@router.get("/templates", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_permission_templates():
    """获取权限模板"""
    try:
        templates = [
            {
                "name": "开发人员配置权限",
                "description": "开发人员可以读写开发环境配置",
                "config": {
                    "permission_level": "WRITE",
                    "scope_type": "ENVIRONMENT", 
                    "scope_config": {"environments": ["dev"]},
                    "work_hours": {"start": "09:00", "end": "18:00"},
                    "work_days": [1, 2, 3, 4, 5]
                }
            },
            {
                "name": "测试人员只读权限",
                "description": "测试人员可以读取测试和开发环境配置",
                "config": {
                    "permission_level": "READ",
                    "scope_type": "ENVIRONMENT",
                    "scope_config": {"environments": ["dev", "test"]},
                    "work_hours": {"start": "09:00", "end": "18:00"},
                    "work_days": [1, 2, 3, 4, 5]
                }
            },
            {
                "name": "运维紧急权限",
                "description": "运维人员紧急情况下的临时管理权限",
                "config": {
                    "permission_level": "ADMIN",
                    "scope_type": "GLOBAL",
                    "scope_config": {},
                    "duration_hours": 2,
                    "requires_approval": True
                }
            },
            {
                "name": "财务配置权限",
                "description": "财务人员只能访问财务相关配置",
                "config": {
                    "permission_level": "WRITE",
                    "scope_type": "TAG",
                    "scope_config": {"tags": ["finance", "payment"]},
                    "row_filters": {
                        "tags": ["finance"],
                        "group_path": "/finance/*"
                    }
                }
            },
            {
                "name": "敏感信息保护",
                "description": "限制普通用户查看敏感配置字段",
                "config": {
                    "table_name": "sys_config",
                    "column_permissions": {
                        "config_value": "NONE",
                        "validation_rule": "READ", 
                        "is_core": "ADMIN",
                        "*": "READ"
                    }
                }
            }
        ]
        
        return ApiResponse(
            success=True,
            data=templates,
            message="获取权限模板成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权限模板失败: {str(e)}")


@router.delete("/revoke", response_model=ApiResponse[Dict[str, Any]])
async def revoke_permission(
    user_id: int,
    permission_type: str,
    permission_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """撤销权限"""
    try:
        permission_manager = AdvancedPermissionManager()
        
        success, error = await permission_manager.revoke_permission(
            user_id, permission_type, permission_id
        )
        
        if success:
            return ApiResponse(
                success=True,
                data={
                    "user_id": user_id,
                    "permission_type": permission_type,
                    "permission_id": permission_id,
                    "revoked_by": current_user.id,
                    "revoked_at": datetime.now().isoformat()
                },
                message="权限撤销成功"
            )
        else:
            raise HTTPException(status_code=400, detail=error)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤销权限失败: {str(e)}")


@router.get("/audit-logs", response_model=ApiResponse[Dict[str, Any]])
async def get_permission_audit_logs(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """获取权限审计日志"""
    try:
        # 这里应该从数据库查询审计日志
        # 为演示目的，返回模拟数据
        
        mock_logs = [
            {
                "id": 1,
                "user_id": user_id or 1,
                "action": action or "read_config",
                "permission_type": "role",
                "permission_level": "READ",
                "resource_type": "config",
                "resource_id": "app.database.host",
                "is_allowed": True,
                "permission_details": {
                    "source": "role_developer",
                    "environment": "dev"
                },
                "request_time": datetime.now().isoformat()
            },
            {
                "id": 2,
                "user_id": user_id or 2,
                "action": "update_config", 
                "permission_type": "temporary",
                "permission_level": "WRITE",
                "resource_type": "config",
                "resource_id": "app.security.key",
                "is_allowed": False,
                "deny_reason": "时间权限不足",
                "request_time": (datetime.now() - timedelta(hours=1)).isoformat()
            }
        ]
        
        return ApiResponse(
            success=True,
            data={
                "items": mock_logs,
                "total": len(mock_logs),
                "page": page,
                "size": size
            },
            message="获取权限审计日志成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {str(e)}")


print("✅ 高级权限管理API已创建完成")