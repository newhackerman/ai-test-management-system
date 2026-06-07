from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_user
from ..core.database import get_async_session

router = APIRouter(tags=["角色管理"])

SYSTEM_ROLE_NAMES = {
    "admin": "管理员",
    "user": "普通用户",
    "SUPER_ADMIN": "超级管理员",
    "SYSTEM_ADMIN": "系统管理员",
    "CONFIG_ADMIN": "配置管理员",
    "PROJECT_MANAGER": "项目经理",
    "DEVELOPER": "开发人员",
    "TESTER": "测试人员",
    "DEVOPS": "运维工程师",
    "READONLY_USER": "只读用户",
}

ALLOWED_SORT_COLUMNS = {
    "id": "r.id",
    "name": "r.name",
    "code": "r.code",
    "created_at": "r.created_at",
    "updated_at": "r.updated_at",
    "sort_order": "r.sort_order",
    "priority": "r.priority",
    "user_count": "user_count",
    "permission_count": "permission_count",
}


def _display_role_name(code: str, name: str) -> str:
    return SYSTEM_ROLE_NAMES.get(code, name)


def _serialize_dt(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _row_to_role(row: Any) -> Dict[str, Any]:
    data = row._mapping if hasattr(row, "_mapping") else row
    name = _display_role_name(data["code"], data["name"])
    return {
        "id": data["id"],
        "name": name,
        "raw_name": data["name"],
        "code": data["code"],
        "description": data["description"] or "",
        "is_active": bool(data["is_active"]),
        "is_system_role": bool(data["is_system_role"]),
        "priority": data.get("priority", 0) if hasattr(data, "get") else data["priority"],
        "sort": data.get("sort_order", 0) if hasattr(data, "get") else data["sort_order"],
        "sort_order": data.get("sort_order", 0) if hasattr(data, "get") else data["sort_order"],
        "user_count": data.get("user_count", 0) if hasattr(data, "get") else data["user_count"],
        "permission_count": data.get("permission_count", 0) if hasattr(data, "get") else data["permission_count"],
        "created_at": _serialize_dt(data["created_at"]),
        "updated_at": _serialize_dt(data["updated_at"]),
    }


def _row_to_permission(row: Any) -> Dict[str, Any]:
    data = row._mapping if hasattr(row, "_mapping") else row
    return {
        "id": data["id"],
        "code": data["code"],
        "name": data["name"],
        "description": data["description"] or "",
        "module": data["module"],
        "type": data["type"],
        "resource": data["resource"],
        "action": data["action"],
        "is_system_permission": bool(data["is_system_permission"]),
        "is_active": bool(data["is_active"]),
        "sort_order": data["sort_order"],
        "parent_id": data["parent_id"],
        "created_at": _serialize_dt(data["created_at"]),
        "updated_at": _serialize_dt(data["updated_at"]),
    }


def _normalize_permission_ids(payload: Any) -> List[int]:
    if isinstance(payload, dict):
        values = payload.get("permission_ids", [])
    else:
        values = payload or []

    if not isinstance(values, list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="permission_ids 必须是数组")

    try:
        return sorted({int(value) for value in values})
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="permission_ids 只能包含数字")


async def _ensure_role_exists(db: AsyncSession, role_id: int) -> Dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT r.*, COUNT(DISTINCT ur.user_id) AS user_count,
                   COUNT(DISTINCT rp.permission_id) AS permission_count
            FROM roles r
            LEFT JOIN user_roles ur ON ur.role_id = r.id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            WHERE r.id = :role_id
            GROUP BY r.id
            """
        ),
        {"role_id": role_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return _row_to_role(row)


async def _get_role_permissions(db: AsyncSession, role_id: int) -> List[Dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT p.id, p.code, p.name, p.description, p.module, p.type,
                   p.resource, p.action, p.is_system_permission, p.is_active,
                   p.sort_order, p.parent_id, p.created_at, p.updated_at
            FROM permissions p
            INNER JOIN role_permissions rp ON rp.permission_id = p.id
            WHERE rp.role_id = :role_id
            ORDER BY p.module, p.sort_order, p.id
            """
        ),
        {"role_id": role_id},
    )
    return [_row_to_permission(row) for row in result.fetchall()]


async def _replace_role_permissions(
    db: AsyncSession,
    role_id: int,
    permission_ids: List[int],
    current_user_id: Optional[int],
) -> None:
    if permission_ids:
        placeholders = ", ".join(f":permission_id_{idx}" for idx, _ in enumerate(permission_ids))
        params = {f"permission_id_{idx}": permission_id for idx, permission_id in enumerate(permission_ids)}
        result = await db.execute(
            text(f"SELECT id FROM permissions WHERE id IN ({placeholders})"),
            params,
        )
        existing_ids = {row.id for row in result.fetchall()}
        missing_ids = sorted(set(permission_ids) - existing_ids)
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"权限不存在: {', '.join(str(item) for item in missing_ids)}",
            )

    await db.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": role_id})

    for permission_id in permission_ids:
        await db.execute(
            text(
                """
                INSERT INTO role_permissions
                    (role_id, permission_id, created_at, updated_at, created_by, updated_by, granted_by, granted_at)
                VALUES
                    (:role_id, :permission_id, NOW(), NOW(), :user_id, :user_id, :user_id, NOW())
                """
            ),
            {"role_id": role_id, "permission_id": permission_id, "user_id": current_user_id},
        )


async def _load_role_detail(db: AsyncSession, role_id: int) -> Dict[str, Any]:
    role = await _ensure_role_exists(db, role_id)
    role["permissions"] = await _get_role_permissions(db, role_id)
    return role


@router.get("", summary="获取角色列表")
async def get_roles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    skip: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=100),
    search: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    role_status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if limit is not None:
        size = limit
    if skip is not None:
        page = skip // size + 1
    offset = (page - 1) * size

    where_clauses = []
    params: Dict[str, Any] = {"limit": size, "offset": offset}

    if search:
        where_clauses.append("(r.name LIKE :search OR r.code LIKE :search OR r.description LIKE :search)")
        params["search"] = f"%{search}%"

    if type == "system":
        where_clauses.append("r.is_system_role = 1")
    elif type == "custom":
        where_clauses.append("r.is_system_role = 0")

    normalized_status = status_filter or role_status
    if normalized_status == "active":
        where_clauses.append("r.is_active = 1")
    elif normalized_status == "inactive":
        where_clauses.append("r.is_active = 0")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sort_column = ALLOWED_SORT_COLUMNS.get(sort_by, "r.created_at")
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"

    count_result = await db.execute(text(f"SELECT COUNT(*) AS total FROM roles r {where_sql}"), params)
    total = count_result.fetchone().total

    result = await db.execute(
        text(
            f"""
            SELECT r.id, r.name, r.code, r.description, r.is_system_role, r.is_active,
                   r.priority, r.sort_order, r.created_at, r.updated_at,
                   COUNT(DISTINCT ur.user_id) AS user_count,
                   COUNT(DISTINCT rp.permission_id) AS permission_count
            FROM roles r
            LEFT JOIN user_roles ur ON ur.role_id = r.id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            {where_sql}
            GROUP BY r.id
            ORDER BY {sort_column} {direction}, r.id ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    roles = [_row_to_role(row) for row in result.fetchall()]
    total_pages = (total + size - 1) // size if size else 0

    return {
        "success": True,
        "data": roles,
        "roles": roles,
        "items": roles,
        "total": total,
        "page": page,
        "size": size,
        "page_size": size,
        "total_pages": total_pages,
    }


@router.get("/all", summary="获取全部角色")
async def get_all_roles(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        text(
            """
            SELECT r.id, r.name, r.code, r.description, r.is_system_role, r.is_active,
                   r.priority, r.sort_order, r.created_at, r.updated_at,
                   COUNT(DISTINCT ur.user_id) AS user_count,
                   COUNT(DISTINCT rp.permission_id) AS permission_count
            FROM roles r
            LEFT JOIN user_roles ur ON ur.role_id = r.id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            GROUP BY r.id
            ORDER BY r.sort_order ASC, r.id ASC
            """
        )
    )
    return [_row_to_role(row) for row in result.fetchall()]


@router.get("/system", summary="获取系统角色")
async def get_system_roles(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        text(
            """
            SELECT r.id, r.name, r.code, r.description, r.is_system_role, r.is_active,
                   r.priority, r.sort_order, r.created_at, r.updated_at,
                   COUNT(DISTINCT ur.user_id) AS user_count,
                   COUNT(DISTINCT rp.permission_id) AS permission_count
            FROM roles r
            LEFT JOIN user_roles ur ON ur.role_id = r.id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            WHERE r.is_system_role = 1
            GROUP BY r.id
            ORDER BY r.sort_order ASC, r.id ASC
            """
        )
    )
    roles = [_row_to_role(row) for row in result.fetchall()]
    return {"success": True, "data": roles, "roles": roles, "total": len(roles), "page": 1, "size": len(roles)}


@router.get("/stats", summary="获取角色统计信息")
async def get_role_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_roles,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_roles,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS inactive_roles,
                SUM(CASE WHEN is_system_role = 1 THEN 1 ELSE 0 END) AS system_roles,
                SUM(CASE WHEN is_system_role = 0 THEN 1 ELSE 0 END) AS custom_roles
            FROM roles
            """
        )
    )
    stats = result.fetchone()

    users_result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS assigned_users
            FROM user_roles
            """
        )
    )
    assigned_users = users_result.fetchone().assigned_users or 0

    permissions_result = await db.execute(text("SELECT COUNT(*) AS total_permissions FROM permissions"))
    total_permissions = permissions_result.fetchone().total_permissions or 0

    total_roles = stats.total_roles or 0
    return {
        "total_roles": total_roles,
        "active_roles": stats.active_roles or 0,
        "inactive_roles": stats.inactive_roles or 0,
        "system_roles": stats.system_roles or 0,
        "custom_roles": stats.custom_roles or 0,
        "average_users_per_role": round(assigned_users / total_roles, 2) if total_roles else 0,
        "total_permissions": total_permissions,
    }


@router.get("/permissions/catalog", summary="获取可分配权限")
async def get_permission_catalog(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        text(
            """
            SELECT id, code, name, description, module, type, resource, action,
                   is_system_permission, is_active, sort_order, parent_id,
                   created_at, updated_at
            FROM permissions
            WHERE is_active = 1
            ORDER BY module ASC, sort_order ASC, id ASC
            """
        )
    )
    permissions = [_row_to_permission(row) for row in result.fetchall()]
    return {"success": True, "data": permissions, "permissions": permissions, "total": len(permissions)}


@router.get("/{role_id}", summary="获取角色详情")
async def get_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    role = await _load_role_detail(db, role_id)
    return {"success": True, "data": role, **role}


@router.post("", status_code=status.HTTP_201_CREATED, summary="创建角色")
async def create_role(
    role_data: Dict[str, Any] = Body(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    name = str(role_data.get("name", "")).strip()
    code = str(role_data.get("code", "")).strip().upper()
    description = role_data.get("description") or ""
    is_active = bool(role_data.get("is_active", True))
    priority = int(role_data.get("priority") or 0)
    sort_order = int(role_data.get("sort_order", role_data.get("sort", 0)) or 0)
    permission_ids = _normalize_permission_ids(role_data)

    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="角色名称不能为空")
    if not code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="角色代码不能为空")

    duplicate = await db.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": code})
    if duplicate.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色代码已存在")

    result = await db.execute(
        text(
            """
            INSERT INTO roles
                (name, code, description, is_system_role, is_active, priority, sort_order,
                 created_at, updated_at, created_by, updated_by)
            VALUES
                (:name, :code, :description, 0, :is_active, :priority, :sort_order,
                 NOW(), NOW(), :user_id, :user_id)
            """
        ),
        {
            "name": name,
            "code": code,
            "description": description,
            "is_active": is_active,
            "priority": priority,
            "sort_order": sort_order,
            "user_id": getattr(current_user, "id", None),
        },
    )
    role_id = result.lastrowid
    await _replace_role_permissions(db, role_id, permission_ids, getattr(current_user, "id", None))
    await db.commit()

    role = await _load_role_detail(db, role_id)
    return {"success": True, "message": "角色创建成功", "data": role, **role}


@router.put("/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    role_data: Dict[str, Any] = Body(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    existing = await _ensure_role_exists(db, role_id)
    fields: Dict[str, Any] = {"role_id": role_id, "user_id": getattr(current_user, "id", None)}
    assignments: List[str] = []

    if "name" in role_data and str(role_data["name"]).strip():
        assignments.append("name = :name")
        fields["name"] = str(role_data["name"]).strip()
    if "description" in role_data:
        assignments.append("description = :description")
        fields["description"] = role_data.get("description") or ""
    if "is_active" in role_data:
        if existing["code"] == "SUPER_ADMIN" and not bool(role_data["is_active"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="超级管理员角色不能停用")
        assignments.append("is_active = :is_active")
        fields["is_active"] = bool(role_data["is_active"])
    if "priority" in role_data:
        assignments.append("priority = :priority")
        fields["priority"] = int(role_data.get("priority") or 0)
    if "sort_order" in role_data or "sort" in role_data:
        assignments.append("sort_order = :sort_order")
        fields["sort_order"] = int(role_data.get("sort_order", role_data.get("sort", 0)) or 0)

    if assignments:
        assignments.extend(["updated_at = NOW()", "updated_by = :user_id"])
        await db.execute(
            text(f"UPDATE roles SET {', '.join(assignments)} WHERE id = :role_id"),
            fields,
        )

    if "permission_ids" in role_data:
        permission_ids = _normalize_permission_ids(role_data)
        await _replace_role_permissions(db, role_id, permission_ids, getattr(current_user, "id", None))

    await db.commit()
    role = await _load_role_detail(db, role_id)
    return {"success": True, "message": "角色更新成功", "data": role, **role}


@router.delete("/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    role = await _ensure_role_exists(db, role_id)
    if role["is_system_role"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统角色不能删除")
    if role["user_count"] > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色仍有关联用户，不能删除")

    await db.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": role_id})
    await db.execute(text("DELETE FROM roles WHERE id = :role_id"), {"role_id": role_id})
    await db.commit()
    return {"success": True, "message": "角色删除成功"}


@router.post("/{role_id}/activate", summary="启用角色")
async def activate_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _ensure_role_exists(db, role_id)
    await db.execute(
        text("UPDATE roles SET is_active = 1, updated_at = NOW(), updated_by = :user_id WHERE id = :role_id"),
        {"role_id": role_id, "user_id": getattr(current_user, "id", None)},
    )
    await db.commit()
    return {"success": True, "message": "角色启用成功"}


@router.post("/{role_id}/deactivate", summary="停用角色")
async def deactivate_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    role = await _ensure_role_exists(db, role_id)
    if role["code"] == "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="超级管理员角色不能停用")

    await db.execute(
        text("UPDATE roles SET is_active = 0, updated_at = NOW(), updated_by = :user_id WHERE id = :role_id"),
        {"role_id": role_id, "user_id": getattr(current_user, "id", None)},
    )
    await db.commit()
    return {"success": True, "message": "角色停用成功"}


@router.get("/{role_id}/permissions", summary="获取角色权限")
async def get_role_permissions(
    role_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _ensure_role_exists(db, role_id)
    permissions = await _get_role_permissions(db, role_id)
    return {"success": True, "permissions": permissions, "data": permissions, "total": len(permissions)}


@router.post("/{role_id}/permissions", summary="分配角色权限")
@router.put("/{role_id}/permissions", summary="替换角色权限")
async def assign_permissions_to_role(
    role_id: int,
    payload: Any = Body(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _ensure_role_exists(db, role_id)
    permission_ids = _normalize_permission_ids(payload)
    await _replace_role_permissions(db, role_id, permission_ids, getattr(current_user, "id", None))
    await db.commit()
    permissions = await _get_role_permissions(db, role_id)
    return {"success": True, "message": "权限分配成功", "permissions": permissions, "data": permissions}


@router.delete("/{role_id}/permissions/{permission_id}", summary="移除角色权限")
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _ensure_role_exists(db, role_id)
    await db.execute(
        text("DELETE FROM role_permissions WHERE role_id = :role_id AND permission_id = :permission_id"),
        {"role_id": role_id, "permission_id": permission_id},
    )
    await db.commit()
    return {"success": True, "message": "权限移除成功"}


@router.get("/{role_id}/users", summary="获取角色用户")
async def get_role_users(
    role_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _ensure_role_exists(db, role_id)
    offset = (page - 1) * size

    count_result = await db.execute(
        text("SELECT COUNT(*) AS total FROM user_roles WHERE role_id = :role_id"),
        {"role_id": role_id},
    )
    total = count_result.fetchone().total

    result = await db.execute(
        text(
            """
            SELECT u.id, u.username, u.email, u.nickname, u.status, u.is_active,
                   u.created_at, u.updated_at, u.last_login_at
            FROM users u
            INNER JOIN user_roles ur ON ur.user_id = u.id
            WHERE ur.role_id = :role_id
            ORDER BY u.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"role_id": role_id, "limit": size, "offset": offset},
    )
    users = [
        {
            "id": row.id,
            "username": row.username,
            "email": row.email,
            "nickname": row.nickname,
            "status": row.status,
            "is_active": bool(row.is_active),
            "created_at": _serialize_dt(row.created_at),
            "updated_at": _serialize_dt(row.updated_at),
            "last_login_at": _serialize_dt(row.last_login_at),
        }
        for row in result.fetchall()
    ]

    return {
        "success": True,
        "users": users,
        "data": users,
        "total": total,
        "page": page,
        "size": size,
        "page_size": size,
        "total_pages": (total + size - 1) // size if size else 0,
    }
