"""
角色管理API接口 - 修复版本

提供角色管理的REST API接口，使用简化的数据库查询避免复杂的ORM关系问题
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ...core.database import get_async_session
from ...api.auth import get_current_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["角色管理"])


@router.get("", summary="获取角色列表")
async def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    type: Optional[str] = Query(None, description="角色类型过滤"),
    role_status: Optional[str] = Query(None, description="状态过滤"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_async_session)
):
    """获取角色列表"""
    try:
        # 构建查询条件
        where_conditions = []
        params = {"limit": size, "offset": (page - 1) * size}
        
        if search:
            where_conditions.append("(name LIKE :search OR code LIKE :search OR description LIKE :search)")
            params["search"] = f"%{search}%"
        
        if role_status == "active":
            where_conditions.append("is_active = 1")
        elif role_status == "inactive":
            where_conditions.append("is_active = 0")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # 查询角色列表
        query = f"""
        SELECT id, name, code, description, is_active,
               created_at, updated_at, sort_order
        FROM roles
        WHERE {where_clause}
        ORDER BY {sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}
        LIMIT :limit OFFSET :offset
        """
        
        result = await db.execute(text(query), params)
        roles_data = result.fetchall()
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM roles WHERE {where_clause}"
        count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
        count_result = await db.execute(text(count_query), count_params)
        total = count_result.fetchone().total
        
        # 转换数据格式
        roles = []
        for row in roles_data:
            roles.append({
                "id": row.id,
                "name": row.name,
                "code": row.code,
                "description": row.description or "",
                "is_active": bool(row.is_active),
                "is_system_role": row.code in ["SUPER_ADMIN", "SYSTEM_ADMIN", "CONFIG_ADMIN", "PROJECT_MANAGER"],
                "sort": row.sort_order or 0,
                "user_count": 0,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            })
        
        return {
            "success": True,
            "data": roles,
            "total": total,
            "page": page,
            "size": size
        }
        
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {str(e)}"
        )


@router.get("/{role_id}", summary="获取角色详情")
async def get_role(
    role_id: int = Path(..., description="角色ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取角色详情"""
    try:
        query = """
        SELECT id, name, code, description, is_active,
               created_at, updated_at, sort_order
        FROM roles
        WHERE id = :role_id
        """
        
        result = await db.execute(text(query), {"role_id": role_id})
        role_data = result.fetchone()
        
        if not role_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        
        # 转换数据格式
        role = {
            "id": role_data.id,
            "name": role_data.name,
            "code": role_data.code,
            "description": role_data.description or "",
            "is_active": bool(role_data.is_active),
            "is_system_role": role_data.code in ["SUPER_ADMIN", "SYSTEM_ADMIN", "CONFIG_ADMIN", "PROJECT_MANAGER"],
            "sort": role_data.sort_order or 0,
            "user_count": 0,
            "created_at": role_data.created_at.isoformat() if role_data.created_at else None,
            "updated_at": role_data.updated_at.isoformat() if role_data.updated_at else None
        }
        
        return {
            "success": True,
            "data": role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色详情失败: {str(e)}"
        )


@router.get("/{role_id}/users", summary="获取角色下的用户")
async def get_role_users(
    role_id: int = Path(..., description="角色ID"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取角色下的用户"""
    try:
        # 简化版本，返回空用户列表
        return {
            "success": True,
            "users": [],
            "total": 0,
            "page": page,
            "size": size
        }
        
    except Exception as e:
        logger.error(f"获取角色用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色用户失败: {str(e)}"
        )


@router.get("/system", summary="获取系统角色")
async def get_system_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取系统角色"""
    try:
        system_role_codes = [
            'SUPER_ADMIN', 'SYSTEM_ADMIN', 'CONFIG_ADMIN', 'PROJECT_MANAGER',
            'DEVELOPER', 'TESTER', 'DEVOPS', 'READONLY_USER'
        ]
        
        # 构建IN查询的占位符
        placeholders = ','.join([f':code_{i}' for i in range(len(system_role_codes))])
        params = {f'code_{i}': code for i, code in enumerate(system_role_codes)}
        
        query = f"""
        SELECT id, name, code, description, is_active,
               created_at, updated_at, sort_order
        FROM roles
        WHERE code IN ({placeholders})
        ORDER BY sort_order, created_at
        """
        
        result = await db.execute(text(query), params)
        roles_data = result.fetchall()
        
        # 转换数据格式
        roles = []
        for row in roles_data:
            roles.append({
                "id": row.id,
                "name": row.name,
                "code": row.code,
                "description": row.description or "",
                "is_active": bool(row.is_active),
                "is_system_role": True,
                "sort": row.sort_order or 0,
                "user_count": 0,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            })
        
        return {
            "success": True,
            "roles": roles,
            "total": len(roles),
            "page": 1,
            "size": len(roles)
        }
        
    except Exception as e:
        logger.error(f"获取系统角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统角色失败: {str(e)}"
        )


@router.get("/stats", summary="获取角色统计信息")
async def get_role_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取角色统计信息"""
    try:
        # 查询角色统计
        stats_query = """
        SELECT 
            COUNT(*) as total_roles,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_roles,
            SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_roles
        FROM roles
        """
        
        result = await db.execute(text(stats_query))
        stats_data = result.fetchone()
        
        return {
            "success": True,
            "total_roles": stats_data.total_roles or 0,
            "active_roles": stats_data.active_roles or 0,
            "inactive_roles": stats_data.inactive_roles or 0,
            "average_users_per_role": 0.0,  # 简化版本
            "total_permissions": 0  # 简化版本
        }
        
    except Exception as e:
        logger.error(f"获取角色统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色统计失败: {str(e)}"
        )