from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_user
from ..core.database import get_async_session
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])

MODULE_RULES: Dict[str, Dict[str, Set[str]]] = {
    "users": {
        "permissions": {"user:view", "user:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "CONFIG_ADMIN", "admin"},
    },
    "roles": {
        "permissions": {"role:view", "role:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "CONFIG_ADMIN", "admin"},
    },
    "settings": {
        "permissions": {"system:settings", "system:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "CONFIG_ADMIN", "admin"},
    },
    "projects": {
        "permissions": {"project:view", "project:read", "project:*", "project_manage"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER", "DEVOPS", "READONLY_USER", "admin"},
    },
    "requirements": {
        "permissions": {"requirement:view", "requirement:read", "requirement:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER", "READONLY_USER", "admin"},
    },
    "tasks": {
        "permissions": {"task:view", "task:read", "task:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER", "DEVOPS", "READONLY_USER", "admin"},
    },
    "testing": {
        "permissions": {"test:view", "test:*", "test_plan:view", "test_case:view", "test_execution:view", "test_case_create"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "TESTER", "DEVELOPER", "READONLY_USER", "admin"},
    },
    "defects": {
        "permissions": {"defect:view", "defect:read", "defect:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "TESTER", "DEVELOPER", "READONLY_USER", "admin"},
    },
    "meetings": {
        "permissions": {"meeting:view", "meeting:read", "meeting:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER", "DEVOPS", "READONLY_USER", "admin"},
    },
    "reports": {
        "permissions": {"report:view", "report:read", "report:*", "test_report:view", "test_report:*"},
        "roles": {"SUPER_ADMIN", "SYSTEM_ADMIN", "PROJECT_MANAGER", "TESTER", "READONLY_USER", "admin"},
    },
}

ACTIVITY_MODULES = {
    "project": "projects",
    "requirement": "requirements",
    "test_case": "testing",
    "defect": "defects",
    "meeting": "meetings",
}


class DashboardQuery:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.sources: List[Dict[str, Any]] = []
        self._table_cache: Dict[str, bool] = {}

    async def table_exists(self, table_name: str) -> bool:
        if table_name not in self._table_cache:
            result = await self.session.execute(
                text(
                    """
                    SELECT COUNT(*) AS count
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            )
            self._table_cache[table_name] = bool(result.scalar() or 0)
        return self._table_cache[table_name]

    async def count(self, table_name: str, where: str = "", params: Optional[Dict[str, Any]] = None) -> int:
        if not await self.table_exists(table_name):
            self._record_source(table_name, False, "表不存在")
            return 0

        sql = f"SELECT COUNT(*) AS count FROM `{table_name}` {where}"
        try:
            result = await self.session.execute(text(sql), params or {})
            self._record_source(table_name, True)
            return int(result.scalar() or 0)
        except Exception as exc:
            logger.warning("Dashboard count failed for %s: %s", table_name, exc)
            self._record_source(table_name, True, str(exc))
            return 0

    async def scalar(self, table_name: str, expression: str, where: str = "", params: Optional[Dict[str, Any]] = None) -> float:
        if not await self.table_exists(table_name):
            self._record_source(table_name, False, "表不存在")
            return 0

        sql = f"SELECT {expression} AS value FROM `{table_name}` {where}"
        try:
            result = await self.session.execute(text(sql), params or {})
            self._record_source(table_name, True)
            value = result.scalar()
            return float(value or 0)
        except Exception as exc:
            logger.warning("Dashboard scalar failed for %s: %s", table_name, exc)
            self._record_source(table_name, True, str(exc))
            return 0

    async def group_count(
        self,
        table_name: str,
        column_name: str,
        where: str = "",
        params: Optional[Dict[str, Any]] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        if not await self.table_exists(table_name):
            self._record_source(table_name, False, "表不存在")
            return []

        sql = (
            f"SELECT `{column_name}` AS name, COUNT(*) AS count "
            f"FROM `{table_name}` {where} "
            f"GROUP BY `{column_name}` ORDER BY count DESC LIMIT {limit}"
        )
        try:
            result = await self.session.execute(text(sql), params or {})
            self._record_source(table_name, True)
            return [{"name": row.name or "UNKNOWN", "count": int(row.count or 0)} for row in result]
        except Exception as exc:
            logger.warning("Dashboard group count failed for %s.%s: %s", table_name, column_name, exc)
            self._record_source(table_name, True, str(exc))
            return []

    async def recent_rows(
        self,
        table_name: str,
        select_sql: str,
        timestamp_column: str = "updated_at",
        where: str = "",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not await self.table_exists(table_name):
            self._record_source(table_name, False, "表不存在")
            return []

        sql = (
            f"SELECT {select_sql} FROM `{table_name}` {where} "
            f"ORDER BY `{timestamp_column}` DESC LIMIT {limit}"
        )
        try:
            result = await self.session.execute(text(sql))
            self._record_source(table_name, True)
            return [dict(row._mapping) for row in result]
        except Exception as exc:
            logger.warning("Dashboard recent rows failed for %s: %s", table_name, exc)
            self._record_source(table_name, True, str(exc))
            return []

    def _record_source(self, table_name: str, available: bool, note: Optional[str] = None) -> None:
        existing = next((item for item in self.sources if item["table"] == table_name), None)
        if existing:
            if note and not existing.get("note"):
                existing["note"] = note
            existing["available"] = existing["available"] and available
            return

        self.sources.append(
            {
                "table": table_name,
                "available": available,
                "note": note,
            }
        )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0
    return round(numerator * 100 / denominator, 2)


def _normalize_datetime(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _get_user_access(session: AsyncSession, user: User) -> Dict[str, Any]:
    if user.is_superuser:
        return {
            "is_superuser": True,
            "permissions": ["*"],
            "roles": ["SUPER_ADMIN"],
            "modules": {module: True for module in MODULE_RULES},
        }

    rows = await session.execute(
        text(
            """
            SELECT DISTINCT r.code AS role_code, p.code AS permission_code
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            LEFT JOIN permissions p ON p.id = rp.permission_id AND p.is_active = 1
            WHERE ur.user_id = :user_id AND r.is_active = 1
            """
        ),
        {"user_id": user.id},
    )

    roles: Set[str] = set()
    permissions: Set[str] = set()

    for row in rows:
        if row.role_code:
            roles.add(str(row.role_code))
        if row.permission_code:
            permissions.add(str(row.permission_code))

    modules = {
        module: _can_access_module(module, roles, permissions)
        for module in MODULE_RULES
    }

    return {
        "is_superuser": False,
        "permissions": sorted(permissions),
        "roles": sorted(roles),
        "modules": modules,
    }


def _can_access_module(module: str, roles: Set[str], permissions: Set[str]) -> bool:
    if "*" in permissions:
        return True

    rules = MODULE_RULES[module]
    if roles.intersection(rules["roles"]):
        return True

    if permissions.intersection(rules["permissions"]):
        return True

    return False


def _empty_distribution() -> List[Dict[str, Any]]:
    return []


def _empty_counts(**values: Any) -> Dict[str, Any]:
    return values


async def _recent_activity(query: DashboardQuery, modules: Dict[str, bool]) -> List[Dict[str, Any]]:
    recent_items: List[Dict[str, Any]] = []

    if modules.get("projects"):
        project_rows = await query.recent_rows(
            "projects",
            "id, project_name AS title, status, updated_at",
            where="WHERE deleted_at IS NULL",
        )
        recent_items.extend(
            {
                "type": "project",
                "title": row.get("title"),
                "status": row.get("status"),
                "occurred_at": _normalize_datetime(row.get("updated_at")),
                "link": f"/projects?id={row.get('id')}",
            }
            for row in project_rows
        )

    if modules.get("requirements"):
        requirement_rows = await query.recent_rows(
            "requirements",
            "id, title, status, updated_at",
        )
        recent_items.extend(
            {
                "type": "requirement",
                "title": row.get("title"),
                "status": row.get("status"),
                "occurred_at": _normalize_datetime(row.get("updated_at")),
                "link": "/requirements",
            }
            for row in requirement_rows
        )

    if modules.get("testing"):
        test_case_rows = await query.recent_rows(
            "test_cases",
            "id, case_title AS title, status, updated_at",
        )
        recent_items.extend(
            {
                "type": "test_case",
                "title": row.get("title"),
                "status": row.get("status"),
                "occurred_at": _normalize_datetime(row.get("updated_at")),
                "link": f"/test-manager/test-cases/{row.get('id')}",
            }
            for row in test_case_rows
        )

    if modules.get("defects"):
        defect_rows = await query.recent_rows(
            "defects",
            "id, title, status, updated_at",
        )
        recent_items.extend(
            {
                "type": "defect",
                "title": row.get("title"),
                "status": row.get("status"),
                "occurred_at": _normalize_datetime(row.get("updated_at")),
                "link": "/test-manager/defects",
            }
            for row in defect_rows
        )

    if modules.get("meetings"):
        meeting_rows = await query.recent_rows(
            "meetings",
            "id, title, status, updated_at",
            where="WHERE deleted_at IS NULL",
        )
        recent_items.extend(
            {
                "type": "meeting",
                "title": row.get("title"),
                "status": row.get("status"),
                "occurred_at": _normalize_datetime(row.get("updated_at")),
                "link": f"/meetings/{row.get('id')}",
            }
            for row in meeting_rows
        )

    return sorted(
        [item for item in recent_items if item.get("occurred_at")],
        key=lambda item: item["occurred_at"],
        reverse=True,
    )[:10]


@router.get("/access")
async def get_dashboard_access(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    access = await _get_user_access(session, current_user)
    return {"success": True, "data": access}


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    query = DashboardQuery(session)
    access = await _get_user_access(session, current_user)
    modules = access["modules"]

    users_total = await query.count("users") if modules.get("users") else 0
    users_active = await query.count("users", "WHERE is_active = 1 AND status = 'ACTIVE'") if modules.get("users") else 0
    users_locked = await query.count("users", "WHERE locked_until IS NOT NULL AND locked_until > NOW()") if modules.get("users") else 0
    users_today_login = await query.count("users", "WHERE DATE(last_login_at) = CURRENT_DATE()") if modules.get("users") else 0
    roles_total = await query.count("roles") if modules.get("roles") else 0

    projects_total = await query.count("projects", "WHERE deleted_at IS NULL") if modules.get("projects") else 0
    projects_active = await query.count(
        "projects",
        "WHERE deleted_at IS NULL AND status IN ('PLANNING', 'IN_PROGRESS', 'ON_HOLD')",
    ) if modules.get("projects") else 0
    projects_completed = await query.count("projects", "WHERE deleted_at IS NULL AND status = 'COMPLETED'") if modules.get("projects") else 0
    projects_overdue = await query.count(
        "projects",
        """
        WHERE deleted_at IS NULL
        AND planned_end_date IS NOT NULL
        AND planned_end_date < CURRENT_DATE()
        AND status NOT IN ('COMPLETED', 'CANCELLED', 'ARCHIVED')
        """,
    ) if modules.get("projects") else 0
    projects_high_risk = await query.count(
        "projects",
        "WHERE deleted_at IS NULL AND risk_level IN ('HIGH', 'CRITICAL')",
    ) if modules.get("projects") else 0
    project_progress = await query.scalar(
        "projects",
        "AVG(progress_percentage)",
        "WHERE deleted_at IS NULL",
    ) if modules.get("projects") else 0

    requirements_total = await query.count("requirements") if modules.get("requirements") else 0
    requirements_active = await query.count(
        "requirements",
        "WHERE status IN ('PENDING_REVIEW', 'REVIEWING', 'NEEDS_REVISION', 'APPROVED', 'IN_DEVELOPMENT', 'TESTING', 'TEST_FAILED')",
    ) if modules.get("requirements") else 0
    requirements_completed = await query.count(
        "requirements",
        "WHERE status IN ('COMPLETED', 'DEPLOYED', 'CLOSED')",
    ) if modules.get("requirements") else 0
    requirements_overdue = await query.count(
        "requirements",
        """
        WHERE planned_end_date IS NOT NULL
        AND planned_end_date < CURRENT_DATE()
        AND status NOT IN ('COMPLETED', 'DEPLOYED', 'CLOSED', 'CANCELLED')
        """,
    ) if modules.get("requirements") else 0

    tasks_total = await query.count("project_tasks") if modules.get("tasks") else 0
    tasks_open = await query.count(
        "project_tasks",
        "WHERE status IN ('TODO', 'ASSIGNED', 'IN_PROGRESS', 'ON_HOLD', 'BLOCKED', 'PENDING_REVIEW')",
    ) if modules.get("tasks") else 0
    tasks_completed = await query.count("project_tasks", "WHERE status = 'COMPLETED'") if modules.get("tasks") else 0
    tasks_overdue = await query.count(
        "project_tasks",
        """
        WHERE planned_end_date IS NOT NULL
        AND planned_end_date < CURRENT_DATE()
        AND status NOT IN ('COMPLETED', 'CANCELLED')
        """,
    ) if modules.get("tasks") else 0

    test_plans_total = await query.count("test_plans") if modules.get("testing") else 0
    test_plans_active = await query.count("test_plans", "WHERE status IN ('APPROVED', 'IN_PROGRESS', 'PAUSED')") if modules.get("testing") else 0
    test_cases_total = await query.count("test_cases") if modules.get("testing") else 0
    test_cases_active = await query.count("test_cases", "WHERE status IN ('APPROVED', 'ACTIVE')") if modules.get("testing") else 0
    executions_total = await query.count("test_executions") if modules.get("testing") else 0
    executions_today = await query.count("test_executions", "WHERE DATE(created_at) = CURRENT_DATE()") if modules.get("testing") else 0
    executions_passed = await query.count("test_executions", "WHERE execution_status = 'PASSED'") if modules.get("testing") else 0
    executions_terminal = await query.count(
        "test_executions",
        "WHERE execution_status IN ('PASSED', 'FAILED', 'BLOCKED', 'SKIPPED')",
    ) if modules.get("testing") else 0

    defects_total = await query.count("defects") if modules.get("defects") else 0
    defects_open = await query.count(
        "defects",
        "WHERE status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'REOPENED')",
    ) if modules.get("defects") else 0
    defects_high_priority = await query.count(
        "defects",
        """
        WHERE severity IN ('CRITICAL', 'HIGH')
        AND status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'REOPENED')
        """,
    ) if modules.get("defects") else 0
    defects_resolved = await query.count("defects", "WHERE status IN ('RESOLVED', 'VERIFIED', 'CLOSED')") if modules.get("defects") else 0

    meetings_total = await query.count("meetings", "WHERE deleted_at IS NULL") if modules.get("meetings") else 0
    meetings_today = await query.count(
        "meetings",
        "WHERE deleted_at IS NULL AND DATE(scheduled_start_time) = CURRENT_DATE()",
    ) if modules.get("meetings") else 0
    meetings_upcoming = await query.count(
        "meetings",
        """
        WHERE deleted_at IS NULL
        AND scheduled_start_time >= NOW()
        AND status IN ('SCHEDULED', 'POSTPONED')
        """,
    ) if modules.get("meetings") else 0
    meetings_running = await query.count("meetings", "WHERE deleted_at IS NULL AND status = 'IN_PROGRESS'") if modules.get("meetings") else 0

    reports_total = await query.count("test_report_records") if modules.get("reports") else 0
    reports_completed = await query.count("test_report_records", "WHERE status IN ('completed', 'COMPLETED', 'success', 'SUCCESS')") if modules.get("reports") else 0
    reports_failed = await query.count("test_report_records", "WHERE status IN ('failed', 'FAILED', 'error', 'ERROR')") if modules.get("reports") else 0

    summary = {
        "generated_at": datetime.now().isoformat(),
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "display_name": getattr(current_user, "real_name", None) or current_user.nickname or current_user.username,
        },
        "access": access,
        "users": {
            "total": users_total,
            "active": users_active,
            "locked": users_locked,
            "today_logins": users_today_login,
            "roles": roles_total,
        },
        "projects": {
            "total": projects_total,
            "active": projects_active,
            "completed": projects_completed,
            "overdue": projects_overdue,
            "high_risk": projects_high_risk,
            "avg_progress": round(project_progress, 2),
            "status_distribution": await query.group_count("projects", "status", "WHERE deleted_at IS NULL") if modules.get("projects") else _empty_distribution(),
        },
        "requirements": {
            "total": requirements_total,
            "active": requirements_active,
            "completed": requirements_completed,
            "overdue": requirements_overdue,
            "completion_rate": _rate(requirements_completed, requirements_total),
            "status_distribution": await query.group_count("requirements", "status") if modules.get("requirements") else _empty_distribution(),
        },
        "tasks": {
            "total": tasks_total,
            "open": tasks_open,
            "completed": tasks_completed,
            "overdue": tasks_overdue,
            "completion_rate": _rate(tasks_completed, tasks_total),
            "status_distribution": await query.group_count("project_tasks", "status") if modules.get("tasks") else _empty_distribution(),
        },
        "testing": {
            "plans_total": test_plans_total,
            "plans_active": test_plans_active,
            "cases_total": test_cases_total,
            "cases_active": test_cases_active,
            "executions_total": executions_total,
            "executions_today": executions_today,
            "passed_executions": executions_passed,
            "pass_rate": _rate(executions_passed, executions_terminal),
            "case_status_distribution": await query.group_count("test_cases", "status") if modules.get("testing") else _empty_distribution(),
            "execution_status_distribution": await query.group_count("test_executions", "execution_status") if modules.get("testing") else _empty_distribution(),
        },
        "defects": {
            "total": defects_total,
            "open": defects_open,
            "high_priority_open": defects_high_priority,
            "resolved": defects_resolved,
            "resolution_rate": _rate(defects_resolved, defects_total),
            "status_distribution": await query.group_count("defects", "status") if modules.get("defects") else _empty_distribution(),
        },
        "meetings": {
            "total": meetings_total,
            "today": meetings_today,
            "upcoming": meetings_upcoming,
            "running": meetings_running,
            "status_distribution": await query.group_count("meetings", "status", "WHERE deleted_at IS NULL") if modules.get("meetings") else _empty_distribution(),
        },
        "reports": {
            "total": reports_total,
            "completed": reports_completed,
            "failed": reports_failed,
        },
        "recent_activity": await _recent_activity(query, modules),
        "data_sources": sorted(query.sources, key=lambda item: item["table"]),
    }

    return {"success": True, "data": summary}
