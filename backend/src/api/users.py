"""
用户管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging
import io
import csv
from datetime import datetime

from ..core.database import get_async_session
from ..services.user import UserService
from ..services.auth import AuthService
from ..models.user import User
from ..schemas.user import (
    UserResponse, UserCreate, UserUpdate, UserListResponse,
    UserPermissionsResponse, BatchUserOperation, BatchOperationResponse,
    PasswordResetRequest, UserLockRequest, UserRoleAssignment
)
from ..utils.error_responses import (
    unauthorized_error, not_found_error, bad_request_error, 
    internal_server_error, forbidden_error
)
from ..api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_user_service(session: AsyncSession = Depends(get_async_session)) -> UserService:
    """获取用户服务实例"""
    return UserService(session)

@router.get("", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="用户状态"),
    role: Optional[str] = Query(None, description="角色筛选"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户列表"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        result = await user_service.get_users_paginated(
            skip=skip,
            limit=limit,
            search=search,
            status=status,
            role=role,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return UserListResponse(
            users=[UserResponse.from_orm(user) for user in result["users"]],
            total=result["total"],
            page=skip // limit + 1,
            page_size=limit,
            total_pages=(result["total"] + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise internal_server_error("获取用户列表失败", str(e))

@router.post("/batch", response_model=BatchOperationResponse)
async def batch_update_users_static(
    operation: BatchUserOperation,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """批量操作用户"""
    try:
        result = await user_service.batch_operation(
            user_ids=operation.user_ids,
            action=operation.action,
            role_id=operation.role_id,
            reason=operation.reason
        )
        return BatchOperationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise internal_server_error("批量操作失败", str(e))

@router.get("/export")
async def export_users_static(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """导出用户数据"""
    try:
        users = await user_service.export_users(search=search, status=status, role=role)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "用户名", "邮箱", "昵称", "手机号", "状态", "是否启用", "角色", "创建时间", "最后登录时间"])
        for user in users:
            roles = ",".join([role.get("name") or role.get("code") for role in getattr(user, "_role_items", [])])
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.nickname or "",
                user.phone or "",
                user.status.value if user.status else "",
                "是" if user.is_active else "否",
                roles,
                user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
                user.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if user.last_login_at else ""
            ])

        content = output.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        logger.error(f"导出用户数据失败: {e}")
        raise internal_server_error("导出用户数据失败", str(e))

@router.post("/import")
async def import_users_static(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """导入用户数据"""
    try:
        if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
            raise bad_request_error("只支持 CSV、XLSX 文件")

        content = await file.read()
        result = await user_service.import_users(content, file.filename)
        return {
            "message": "用户导入完成",
            "success_count": result.get("success_count", 0),
            "failed_count": result.get("failed_count", 0),
            "total_count": result.get("total_count", 0),
            "failed_users": result.get("failed_users", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入用户数据失败: {e}")
        raise internal_server_error("导入用户数据失败", str(e))

@router.get("/{user_id:int}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户详情"""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}")
        raise internal_server_error("获取用户详情失败", str(e))

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """创建用户"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        new_user = await user_service.create_user(user_data.dict())
        return UserResponse.from_orm(new_user)
        
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise internal_server_error("创建用户失败", str(e))

@router.put("/{user_id:int}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """更新用户信息"""
    try:
        # 检查权限
        if current_user.id != user_id and not current_user.is_superuser:
            # TODO: 检查是否有管理权限
            pass
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        updated_user = await user_service.update_user(user_id, user_data.dict(exclude_unset=True))
        return UserResponse.from_orm(updated_user)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        raise internal_server_error("更新用户失败", str(e))

@router.delete("/{user_id:int}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """删除用户"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        # 不能删除自己
        if current_user.id == user_id:
            raise bad_request_error("不能删除自己的账户")
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        await user_service.delete_user(user_id)
        return {"message": "用户删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise internal_server_error("删除用户失败", str(e))

@router.post("/{user_id:int}/lock")
async def lock_user(
    user_id: int,
    request: UserLockRequest = Body(default=UserLockRequest()),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """锁定用户"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        # 不能锁定自己
        if current_user.id == user_id:
            raise bad_request_error("不能锁定自己的账户")
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        await user_service.lock_user(user_id, request.reason)
        return {"message": "用户锁定成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"锁定用户失败: {e}")
        raise internal_server_error("锁定用户失败", str(e))

@router.post("/{user_id:int}/unlock")
async def unlock_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """解锁用户"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        await user_service.unlock_user(user_id)
        return {"message": "用户解锁成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解锁用户失败: {e}")
        raise internal_server_error("解锁用户失败", str(e))

@router.post("/{user_id:int}/reset-password")
async def reset_user_password(
    user_id: int,
    request: PasswordResetRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """重置用户密码"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        await user_service.reset_password(user_id, request.new_password, request.force_change)
        return {"message": "密码重置成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        raise internal_server_error("重置密码失败", str(e))

@router.get("/{user_id:int}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户权限"""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        permissions = await user_service.get_user_permissions(user_id)
        return UserPermissionsResponse(
            user_id=str(user_id),
            username=user.username,
            roles=permissions.get("roles", []),
            all_permissions=permissions.get("permissions", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        raise internal_server_error("获取用户权限失败", str(e))

@router.post("/{user_id:int}/roles")
async def assign_roles_to_user(
    user_id: int,
    request: UserRoleAssignment,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """为用户分配角色"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        result = await user_service.assign_roles(user_id, request.role_ids)
        return {
            "message": "角色分配成功",
            "user_id": str(user_id),
            "assigned_count": result.get("assigned_count", 0),
            "failed_roles": result.get("failed_roles", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配角色失败: {e}")
        raise internal_server_error("分配角色失败", str(e))

@router.delete("/{user_id:int}/roles/{role_id:int}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """移除用户角色"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise not_found_error("用户不存在")
        
        await user_service.remove_role(user_id, role_id)
        return {"message": "角色移除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除角色失败: {e}")
        raise internal_server_error("移除角色失败", str(e))

@router.post("/batch", response_model=BatchOperationResponse)
async def batch_update_users(
    operation: BatchUserOperation,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """批量操作用户"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        result = await user_service.batch_operation(
            user_ids=operation.user_ids,
            action=operation.action,
            role_id=operation.role_id,
            reason=operation.reason
        )
        
        return BatchOperationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise internal_server_error("批量操作失败", str(e))

@router.get("/export")
async def export_users(
    search: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="用户状态"),
    role: Optional[str] = Query(None, description="角色筛选"),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """导出用户数据"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        users = await user_service.export_users(
            search=search,
            status=status,
            role=role
        )
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow([
            'ID', '用户名', '邮箱', '昵称', '手机号', '状态', 
            '是否激活', '是否超级用户', '创建时间', '最后登录时间'
        ])
        
        # 写入数据行
        for user in users:
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.nickname or '',
                user.phone or '',
                user.status.value if user.status else '',
                '是' if user.is_active else '否',
                '是' if user.is_superuser else '否',
                user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
                user.last_login_at.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_at else ''
            ])
        
        # 创建响应
        output.seek(0)
        content = output.getvalue().encode('utf-8-sig')  # 使用BOM以支持Excel
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"导出用户数据失败: {e}")
        raise internal_server_error("导出用户数据失败", str(e))

@router.post("/import")
async def import_users(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """导入用户数据"""
    try:
        # 检查权限
        # TODO: 添加权限检查逻辑
        
        # 检查文件类型
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise bad_request_error("只支持CSV和Excel文件")
        
        # 读取文件内容
        content = await file.read()
        
        result = await user_service.import_users(content, file.filename)
        
        return {
            "message": "用户导入完成",
            "success_count": result.get("success_count", 0),
            "failed_count": result.get("failed_count", 0),
            "total_count": result.get("total_count", 0),
            "failed_users": result.get("failed_users", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入用户数据失败: {e}")
        raise internal_server_error("导入用户数据失败", str(e))

# 高级用户管理功能

@router.get("/statistics")
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户统计信息"""
    try:
        # TODO: 检查权限
        
        stats = await user_service.get_user_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise internal_server_error("获取用户统计失败", str(e))

@router.post("/search/advanced")
async def advanced_user_search(
    filters: dict,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """高级用户搜索"""
    try:
        # TODO: 检查权限
        
        result = await user_service.search_users_advanced(
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return {
            "users": [UserResponse.from_orm(user) for user in result["users"]],
            "total": result["total"],
            "filters_applied": result["filters_applied"]
        }
        
    except Exception as e:
        logger.error(f"高级用户搜索失败: {e}")
        raise internal_server_error("高级用户搜索失败", str(e))

@router.get("/{user_id:int}/activity")
async def get_user_activity(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户活动日志"""
    try:
        # 检查权限：只能查看自己的活动或管理员权限
        if current_user.id != user_id and not current_user.is_superuser:
            # TODO: 检查管理权限
            pass
        
        activity_logs = await user_service.get_user_activity_log(user_id, limit)
        return {"activity_logs": activity_logs}
        
    except Exception as e:
        logger.error(f"获取用户活动失败: {e}")
        raise internal_server_error("获取用户活动失败", str(e))

@router.put("/{user_id:int}/profile")
async def update_user_profile(
    user_id: int,
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """更新用户个人资料"""
    try:
        # 检查权限：只能修改自己的资料
        if current_user.id != user_id:
            raise forbidden_error("只能修改自己的个人资料")
        
        updated_user = await user_service.update_user_profile(user_id, profile_data)
        if not updated_user:
            raise not_found_error("用户不存在")
        
        return UserResponse.from_orm(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}")
        raise internal_server_error("更新用户资料失败", str(e))

@router.post("/{user_id:int}/change-password")
async def change_user_password(
    user_id: int,
    password_data: dict,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """用户修改密码"""
    try:
        # 检查权限：只能修改自己的密码
        if current_user.id != user_id:
            raise forbidden_error("只能修改自己的密码")
        
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        
        if not current_password or not new_password:
            raise bad_request_error("缺少必需参数")
        
        await user_service.change_user_password(user_id, current_password, new_password)
        return {"message": "密码修改成功"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise internal_server_error("修改密码失败", str(e))

@router.post("/{user_id:int}/mfa/enable")
async def enable_user_mfa(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """启用多因素认证"""
    try:
        # 检查权限：只能为自己启用MFA
        if current_user.id != user_id:
            raise forbidden_error("只能为自己启用多因素认证")
        
        mfa_data = await user_service.enable_user_mfa(user_id)
        return mfa_data
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"启用MFA失败: {e}")
        raise internal_server_error("启用MFA失败", str(e))

@router.post("/{user_id:int}/mfa/verify")
async def verify_and_enable_mfa(
    user_id: int,
    verification_data: dict,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """验证并启用MFA"""
    try:
        # 检查权限：只能为自己验证MFA
        if current_user.id != user_id:
            raise forbidden_error("只能为自己验证多因素认证")
        
        verification_code = verification_data.get("verification_code")
        if not verification_code:
            raise bad_request_error("缺少验证码")
        
        success = await user_service.verify_and_enable_mfa(user_id, verification_code)
        return {"message": "多因素认证启用成功" if success else "验证失败"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"验证MFA失败: {e}")
        raise internal_server_error("验证MFA失败", str(e))

@router.post("/{user_id:int}/mfa/disable")
async def disable_user_mfa(
    user_id: int,
    verification_data: dict,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """禁用多因素认证"""
    try:
        # 检查权限：只能为自己禁用MFA
        if current_user.id != user_id:
            raise forbidden_error("只能为自己禁用多因素认证")
        
        verification_code = verification_data.get("verification_code")
        if not verification_code:
            raise bad_request_error("缺少验证码")
        
        success = await user_service.disable_user_mfa(user_id, verification_code)
        return {"message": "多因素认证禁用成功" if success else "验证失败"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"禁用MFA失败: {e}")
        raise internal_server_error("禁用MFA失败", str(e))

@router.get("/{user_id:int}/sessions")
async def get_user_sessions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """获取用户会话列表"""
    try:
        # 检查权限：只能查看自己的会话或管理员权限
        if current_user.id != user_id and not current_user.is_superuser:
            raise forbidden_error("只能查看自己的会话")
        
        sessions = await user_service.get_user_sessions(user_id)
        return {"sessions": sessions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户会话失败: {e}")
        raise internal_server_error("获取用户会话失败", str(e))

@router.delete("/{user_id:int}/sessions/{session_id:int}")
async def revoke_user_session(
    user_id: int,
    session_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """撤销用户会话"""
    try:
        # 检查权限：只能撤销自己的会话或管理员权限
        if current_user.id != user_id and not current_user.is_superuser:
            raise forbidden_error("只能撤销自己的会话")
        
        success = await user_service.revoke_user_session(user_id, session_id)
        if success:
            return {"message": "会话撤销成功"}
        else:
            raise not_found_error("会话不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撤销用户会话失败: {e}")
        raise internal_server_error("撤销用户会话失败", str(e))
