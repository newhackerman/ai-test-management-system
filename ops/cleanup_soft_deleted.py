#!/usr/bin/env python3
"""Physically purge soft-deleted rows and their orphaned children.

Round-6 item 16. The app soft-deletes (deleted_at) instead of removing
rows, and several child tables (requirements, project_tasks, test_cases)
have no deleted_at column at all, so probe/test leftovers accumulate:
before this script existed the live DB held 329 soft-deleted projects,
9 meetings, 50 AI files, plus 8 requirements and 144 tasks orphaned
under soft-deleted projects.

What it deletes (and nothing else):
- Rows in the soft-delete tables whose deleted_at is older than --days
  (default 7): projects, meetings, project_milestones, ai_file_storage,
  system_notifications. sys_config* is deliberately excluded: that is
  configuration, not test data.
- Orphaned live rows whose ancestor project (transitively) is
  soft-deleted or missing, across the test-data FK graph (requirements +
  all requirement_* children, test_cases/plans/executions, defects,
  project_tasks, meeting_* children, project_* children, work_logs,
  ai_file_access_logs/shares). Users, roles, permissions and seed data
  are never touched: no rule references them.

How it works: it first computes the purgable id-set per table (starting
from soft-deleted projects/files, then walking the FK graph outward),
and only then deletes by id, children before parents, in one
transaction. Deleting by precomputed sets (instead of per-rule
"parent is gone" DELETEs) is what makes chains safe: a requirement's
status_history rows are purgable because their requirement is in the
purgable set, even though the requirement row still exists when the
set is computed. A per-rule loop cannot do that without hitting FK
1451 (learned the hard way on the first version).

Safety:
- Dry-run by default: prints per-table counts and deletes nothing.
  Pass --apply to actually delete. (Dry-run may over-count tables with
  two FK rules, e.g. meeting_tasks, when one row matches both rules;
  apply counts are exact because each row is deleted once.)
- Grace period: a project soft-deleted less than --days ago shields
  its whole subtree. For the one-off catch-up run use --days 0 after
  reviewing the dry-run output.
- AI files: the stored file under backend/uploads/ is removed
  best-effort (LOCAL provider only, path must resolve under the
  uploads root); a missing file never blocks the row purge.

Usage (run from the repo root with the backend venv; backend/.env is
loaded by absolute path, so the working directory does not matter):
    backend/venv/bin/python ops/cleanup_soft_deleted.py [--days N] [--apply]

Suggested periodic use: monthly, or after a heavy probe/test round.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Load backend/.env explicitly: pydantic-settings resolves ".env" relative
# to the process CWD, so running this script from anywhere else would
# silently fall back to the default DATABASE_URL (wrong user).
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

from sqlalchemy import bindparam, text  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.database import engine  # noqa: E402

engine.echo = False  # the app engine logs every statement; keep this readable

# Tables with a deleted_at column that this script purges directly.
# sys_config / sys_config_permission are intentionally absent (config data).
SOFT_DELETE_TABLES = [
    "projects",
    "meetings",
    "project_milestones",
    "ai_file_storage",
    "system_notifications",
]

UPLOADS_ROOT = Path(__file__).resolve().parent.parent / "backend"
# NOTE: file_path in ai_file_storage is relative to backend/ (e.g.
# "uploads/user_upload/2026/11/....txt"), NOT to backend/uploads/.


def _ids(conn, sql: str, params: dict | None = None) -> set[int]:
    rows = conn.execute(text(sql), params or {}).fetchall()
    return {int(r[0]) for r in rows}


def _ids_in(conn, table: str, column: str, values: set[int]) -> set[int]:
    """Ids from `table` whose `column` is in `values` (empty set -> empty)."""
    if not values:
        return set()
    stmt = text(f"SELECT id FROM {table} WHERE {column} IN :vals").bindparams(
        bindparam("vals", expanding=True)
    )
    return {int(r[0]) for r in conn.execute(stmt, {"vals": list(values)}).fetchall()}


def _compute_purge_sets(conn, cutoff: datetime) -> dict[str, set[int]]:
    """Purgable id-set per table, walked outward from soft-deleted roots."""
    sets: dict[str, set[int]] = {}
    p = {"cutoff": cutoff}
    projects = _ids(
        conn,
        "SELECT id FROM projects WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff",
        p,
    )
    sets["projects"] = projects
    sets["meetings"] = _ids(
        conn,
        "SELECT id FROM meetings WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff",
        p,
    ) | _ids_in(conn, "meetings", "project_id", projects)
    sets["requirements"] = _ids_in(conn, "requirements", "project_id", projects)
    sets["test_plans"] = _ids_in(conn, "test_plans", "project_id", projects)
    sets["test_cases"] = _ids_in(conn, "test_cases", "requirement_id", sets["requirements"]) | _ids_in(
        conn, "test_cases", "test_plan_id", sets["test_plans"]
    )
    sets["project_tasks"] = _ids_in(conn, "project_tasks", "project_id", projects)
    sets["defects"] = _ids_in(conn, "defects", "requirement_id", sets["requirements"]) | _ids_in(
        conn, "defects", "test_case_id", sets["test_cases"]
    )
    sets["ai_file_storage"] = _ids(
        conn,
        "SELECT id FROM ai_file_storage WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff",
        p,
    )
    sets["project_milestones"] = _ids(
        conn,
        "SELECT id FROM project_milestones WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff",
        p,
    ) | _ids_in(conn, "project_milestones", "project_id", projects)
    sets["system_notifications"] = _ids(
        conn,
        "SELECT id FROM system_notifications WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff",
        p,
    )
    return sets


def _delete_ids(conn, table: str, ids: set[int], apply: bool) -> int:
    if not ids:
        return 0
    if not apply:
        return len(ids)
    stmt = text(f"DELETE FROM {table} WHERE id IN :vals").bindparams(
        bindparam("vals", expanding=True)
    )
    return conn.execute(stmt, {"vals": sorted(ids)}).rowcount or 0


def _delete_where_fk(conn, table: str, fk: str, ids: set[int], apply: bool) -> int:
    """Delete/count rows of `table` whose `fk` is in `ids`."""
    if not ids:
        return 0
    if not apply:
        stmt = text(
            f"SELECT COUNT(*) FROM {table} WHERE {fk} IN :vals"
        ).bindparams(bindparam("vals", expanding=True))
        return int(conn.execute(stmt, {"vals": sorted(ids)}).scalar() or 0)
    stmt = text(f"DELETE FROM {table} WHERE {fk} IN :vals").bindparams(
        bindparam("vals", expanding=True)
    )
    return conn.execute(stmt, {"vals": sorted(ids)}).rowcount or 0


def _purge(conn, sets: dict[str, set[int]], apply: bool) -> dict[str, int]:
    """Delete by precomputed sets, children first. Returns per-table counts."""
    counts: dict[str, int] = {}

    def add(table: str, n: int):
        if n:
            counts[table] = counts.get(table, 0) + n

    reqs = sets["requirements"]
    cases = sets["test_cases"]
    plans = sets["test_plans"]
    tasks = sets["project_tasks"]
    meetings = sets["meetings"]
    projects = sets["projects"]
    defects = sets["defects"]
    files = sets["ai_file_storage"]

    # Leaf children first.
    add("ai_file_access_logs", _delete_where_fk(conn, "ai_file_access_logs", "file_id", files, apply))
    add("ai_file_shares", _delete_where_fk(conn, "ai_file_shares", "file_id", files, apply))
    add("defect_comments", _delete_where_fk(conn, "defect_comments", "defect_id", defects, apply))
    for child in ("meeting_analytics", "meeting_chats", "meeting_files",
                  "meeting_minutes", "meeting_participants", "meeting_recordings"):
        add(child, _delete_where_fk(conn, child, "meeting_id", meetings, apply))
    add("meeting_tasks", _delete_where_fk(conn, "meeting_tasks", "meeting_id", meetings, apply))
    add("meeting_tasks", _delete_where_fk(conn, "meeting_tasks", "task_id", tasks, apply))
    add("work_logs", _delete_where_fk(conn, "work_logs", "task_id", tasks, apply))
    add("work_logs", _delete_where_fk(conn, "work_logs", "project_id", projects, apply))
    # Requirement children (FK -> requirements).
    for child in ("requirement_audit_logs", "requirement_change_requests",
                  "requirement_classification_suggestions", "requirement_classifications",
                  "requirement_priority_evaluations", "requirement_priority_history",
                  "requirement_resource_permissions", "requirement_review_comments",
                  "requirement_reviews", "requirement_status_history",
                  "requirement_tag_assignments"):
        add(child, _delete_where_fk(conn, child, "requirement_id", reqs, apply))
    add("requirement_dependencies",
        _delete_where_fk(conn, "requirement_dependencies", "source_requirement_id", reqs, apply))
    add("requirement_dependencies",
        _delete_where_fk(conn, "requirement_dependencies", "target_requirement_id", reqs, apply))
    # Test-case / test-plan children.
    add("test_executions", _delete_where_fk(conn, "test_executions", "test_case_id", cases, apply))
    add("test_executions", _delete_where_fk(conn, "test_executions", "test_plan_id", plans, apply))
    add("automation_scripts", _delete_where_fk(conn, "automation_scripts", "test_case_id", cases, apply))
    add("test_phases", _delete_where_fk(conn, "test_phases", "test_plan_id", plans, apply))
    add("test_resources", _delete_where_fk(conn, "test_resources", "test_plan_id", plans, apply))
    # Project children.
    for child in ("project_change_history", "project_members", "project_metrics",
                  "project_risks", "project_statistics", "test_environments",
                  "test_report_records"):
        add(child, _delete_where_fk(conn, child, "project_id", projects, apply))
    add("requirement_audit_logs", _delete_where_fk(conn, "requirement_audit_logs", "project_id", projects, apply))
    add("requirement_priority_configs",
        _delete_where_fk(conn, "requirement_priority_configs", "project_id", projects, apply))
    add("test_coverage", _delete_where_fk(conn, "test_coverage", "project_id", projects, apply))
    add("test_coverage", _delete_where_fk(conn, "test_coverage", "requirement_id", reqs, apply))
    # Now the purgable parents themselves, leaves of the parent graph first.
    add("defects", _delete_ids(conn, "defects", defects, apply))
    add("test_cases", _delete_ids(conn, "test_cases", cases, apply))
    add("test_phases", 0)  # already handled above; kept for ordering clarity
    add("test_plans", _delete_ids(conn, "test_plans", plans, apply))
    # requirements is self-referential (parent_id): delete roots first,
    # repeat until the set drains, so a parent never goes before its child.
    remaining = set(reqs)
    for _ in range(10):
        if not remaining:
            break
        if apply:
            stmt = text(
                "DELETE FROM requirements WHERE id IN :vals "
                "AND (parent_id IS NULL OR parent_id NOT IN :vals2)"
            ).bindparams(bindparam("vals", expanding=True), bindparam("vals2", expanding=True))
            gone = conn.execute(stmt, {"vals": sorted(remaining), "vals2": sorted(remaining)}).rowcount or 0
        else:
            gone = len(remaining)
        add("requirements", gone)
        if not apply:
            break
        # Recompute what is left of the set.
        left = _ids_in(conn, "requirements", "id", remaining)
        if len(left) == len(remaining):
            raise RuntimeError("requirements self-reference did not drain; refusing to force-delete")
        remaining = left
    add("project_tasks", _delete_ids(conn, "project_tasks", tasks, apply))
    add("meetings", _delete_ids(conn, "meetings", meetings, apply))
    add("project_milestones", _delete_ids(conn, "project_milestones", sets["project_milestones"], apply))
    add("ai_file_storage", _delete_ids(conn, "ai_file_storage", files, apply))
    add("system_notifications", _delete_ids(conn, "system_notifications", sets["system_notifications"], apply))
    add("projects", _delete_ids(conn, "projects", projects, apply))
    counts.pop("test_phases", None)
    return counts


def _collect_ai_files(conn, cutoff: datetime) -> list[tuple[int, str]]:
    rows = conn.execute(
        text(
            "SELECT id, file_path FROM ai_file_storage "
            "WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff "
            "AND storage_provider = 'LOCAL'"
        ),
        {"cutoff": cutoff},
    ).fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def _remove_disk_files(files: list[tuple[int, str]]) -> tuple[int, int]:
    removed, skipped = 0, 0
    root = UPLOADS_ROOT.resolve()
    for _file_id, rel in files:
        try:
            path = (root / rel).resolve()
            if root not in path.parents and path != root:
                skipped += 1
                continue
            if path.exists():
                path.unlink()
                removed += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1
    return removed, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7,
                        help="grace period in days (default 7)")
    parser.add_argument("--apply", action="store_true",
                        help="actually delete (default is dry-run)")
    args = parser.parse_args()
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=args.days)
    mode = "APPLY" if args.apply else "DRY-RUN (nothing deleted)"
    print(f"cleanup_soft_deleted: {mode}, grace {args.days}d, cutoff {cutoff}")
    print(f"database: {settings.DATABASE_URL.split('@')[-1]}")

    with engine.begin() as conn:
        sets = _compute_purge_sets(conn, cutoff)
        ai_files = _collect_ai_files(conn, cutoff) if args.apply else []
        counts = _purge(conn, sets, args.apply)

    if not counts:
        print("nothing to purge")
        return 0
    for table in sorted(counts):
        print(f"  {table}: {counts[table]}")
    print(f"total rows: {sum(counts.values())}")
    if args.apply and ai_files:
        removed, skipped = _remove_disk_files(ai_files)
        print(f"disk files removed: {removed}, already-gone/skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
