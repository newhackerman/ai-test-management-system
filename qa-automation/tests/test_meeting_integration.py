"""Meeting <-> project integration: the six service methods that were
missing in U6 (sync-team, milestone review meeting, decisions-to-tasks,
tasks sync, link existing task, update progress), plus the meeting-task
read side they feed.

Each method gets a happy-path test and the matching failure tests
(unknown meeting/task/milestone -> 404, invalid enum -> 400,
unlinked task -> 400, outsider -> 403). The meeting-task link lives in
the new meeting_tasks table (Task has no meeting_id column), so the
read side (GET tasks / GET progress) is asserted too.
"""

import uuid

import pytest

from client import ApiClient
from config import BASE_URL

pytestmark = pytest.mark.integration

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"
MILESTONE_DATE = "2026-12-01"
PASSWORD = "SecTest123!"


def _make_meeting(api, project_id, auto_invite_team=False):
    resp = api.post(
        f"/api/v1/meetings/projects/{project_id}/meetings",
        json={
            "title": "U6 集成测试会议",
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
            "auto_invite_team": auto_invite_team,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    return resp.json()


def _make_milestone(api, project_id, name="U6 里程碑"):
    # Milestone names are unique per project and `project` is a
    # module-scoped fixture, so suffix every name.
    name = f"{name}-{uuid.uuid4().hex[:6]}"
    resp = api.post(
        f"/api/v1/milestones/{project_id}",
        json={
            "milestone_name": name,
            "milestone_type": "EXECUTION",
            "planned_date": MILESTONE_DATE,
            "owner_id": 1,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create milestone failed: {resp.text[:300]}"
    return resp.json()["milestone"]


def _make_task(api, project_id, name):
    resp = api.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "task_name": name,
            "task_type": "REQUIREMENT_ANALYSIS",
        },
    )
    assert resp.status_code in (200, 201), f"setup: create task failed: {resp.text[:300]}"
    return resp.json()["task"]


def _make_plain_user(api):
    """A plain user (no roles) with its own logged-in client."""
    username = f"u6-user-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
    )
    assert resp.status_code in (200, 201), f"setup: create user failed: {resp.text[:300]}"
    user = resp.json()
    user_id = user.get("id") or user.get("user", {}).get("id")
    client = ApiClient(BASE_URL)
    assert client.login(username, PASSWORD), "setup: plain user login failed"
    return {"id": user_id, "username": username, "client": client}


@pytest.fixture
def mi_member(api, project):
    """Plain user added to the project as DEVELOPER."""
    user = _make_plain_user(api)
    resp = api.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": user["id"], "role_in_project": "DEVELOPER", "join_date": "2026-11-05"},
    )
    assert resp.status_code in (200, 201), f"setup: add member failed: {resp.text[:300]}"
    yield user
    api.delete(f"/api/v1/users/{user['id']}")


@pytest.fixture
def mi_outsider(api):
    """Plain user who is not a member of any project."""
    user = _make_plain_user(api)
    yield user
    api.delete(f"/api/v1/users/{user['id']}")


@pytest.fixture
def mi_meeting(api, project):
    """A meeting on the project, created without auto-invite so the
    sync-team tests have something to add."""
    meeting = _make_meeting(api, project["id"], auto_invite_team=False)
    yield meeting


def _base(api, project):
    return f"/api/v1/meetings/projects/{project['id']}"


# ---------------------------------------------------------------- sync-team

def test_sync_team_adds_member(api, project, mi_member, mi_meeting):
    resp = api.post(f"{_base(api, project)}/meetings/{mi_meeting['id']}/sync-team")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    # `project` is module-scoped, so members accumulate across tests:
    # assert relative to the reported total, not a hardcoded count.
    assert body["existing_participants"] == 1  # organizer only
    assert body["added_participants"] == body["total_project_members"] - 1
    assert body["total_project_members"] >= 2  # admin + member(s)
    assert body["success"] is True


def test_sync_team_idempotent(api, project, mi_member, mi_meeting):
    base = f"{_base(api, project)}/meetings/{mi_meeting['id']}/sync-team"
    first = api.post(base)
    assert first.status_code == 200, first.text[:300]
    total = first.json()["total_project_members"]
    assert first.json()["added_participants"] == total - 1
    resp = api.post(base)
    assert resp.status_code == 200
    assert resp.json()["added_participants"] == 0
    assert resp.json()["existing_participants"] == total


def test_sync_team_unknown_meeting(api, project):
    resp = api.post(f"{_base(api, project)}/meetings/999999999/sync-team")
    assert resp.status_code == 404, resp.text[:200]


def test_sync_team_outsider_forbidden(api, project, mi_meeting, mi_outsider):
    resp = mi_outsider["client"].post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/sync-team"
    )
    assert resp.status_code == 403, resp.text[:200]


# ------------------------------------------------- milestone review meeting

def test_milestone_meeting_defaults(api, project):
    milestone = _make_milestone(api, project["id"], name="U6 交付里程碑")
    resp = api.post(
        f"{_base(api, project)}/milestones/{milestone['id']}/meeting", json={}
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["title"] == f"{milestone['milestone_name']}评审会议"
    assert body["meeting_type"] == "PROGRESS_SYNC"
    assert body["project_id"] == project["id"]
    assert body["scheduled_start_time"].startswith("2026-12-01T10:00")
    assert body["meeting_code"]


def test_milestone_meeting_config_override(api, project):
    milestone = _make_milestone(api, project["id"])
    resp = api.post(
        f"{_base(api, project)}/milestones/{milestone['id']}/meeting",
        json={
            "title": "定制评审会",
            "meeting_type": "TEST_REVIEW",
            "scheduled_start_time": "2026-12-02T14:00:00",
            "scheduled_end_time": "2026-12-02T15:30:00",
        },
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["title"] == "定制评审会"
    assert body["meeting_type"] == "TEST_REVIEW"
    assert body["scheduled_start_time"].startswith("2026-12-02T14:00")


def test_milestone_meeting_unknown_milestone(api, project):
    resp = api.post(
        f"{_base(api, project)}/milestones/999999999/meeting", json={}
    )
    assert resp.status_code == 404, resp.text[:200]


def test_milestone_meeting_invalid_type(api, project):
    milestone = _make_milestone(api, project["id"])
    resp = api.post(
        f"{_base(api, project)}/milestones/{milestone['id']}/meeting",
        json={"meeting_type": "NOPE"},
    )
    assert resp.status_code == 400, resp.text[:200]


# ------------------------------------------------------- decisions to tasks

def test_decisions_to_tasks_creates_only_flagged(api, project, mi_meeting):
    mid = mi_meeting["id"]
    resp = api.post(
        f"{_base(api, project)}/meetings/{mid}/decisions-to-tasks",
        json={"decisions": [
            {"title": "D1 任务", "create_task": True, "task_type": "TEST_DESIGN", "priority": "HIGH"},
            {"title": "D2 不建任务", "create_task": False},
            {"title": "D3 任务", "create_task": True},
        ]},
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["tasks_created"] == 2
    assert body["total_decisions"] == 3
    assert len(body["created_task_ids"]) == 2
    # The created tasks are visible through the meeting-task read side.
    listed = api.get(f"{_base(api, project)}/meetings/{mid}/tasks")
    assert listed.status_code == 200
    assert listed.json()["total_count"] == 2
    names = {t["task_name"] for t in listed.json()["tasks"]}
    assert names == {"D1 任务", "D3 任务"}


def test_decisions_to_tasks_empty(api, project, mi_meeting):
    resp = api.post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/decisions-to-tasks",
        json={"decisions": []},
    )
    assert resp.status_code == 200, resp.text[:200]
    assert resp.json()["tasks_created"] == 0


def test_decisions_to_tasks_unknown_meeting(api, project):
    resp = api.post(
        f"{_base(api, project)}/meetings/999999999/decisions-to-tasks",
        json={"decisions": [{"title": "x", "create_task": True}]},
    )
    assert resp.status_code == 404, resp.text[:200]


def test_decisions_to_tasks_invalid_task_type(api, project, mi_meeting):
    resp = api.post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/decisions-to-tasks",
        json={"decisions": [{"title": "坏类型", "create_task": True, "task_type": "NOPE"}]},
    )
    assert resp.status_code == 400, resp.text[:200]


# ---------------------------------------------------------- link existing task

def test_link_existing_task(api, project, mi_meeting):
    task = _make_task(api, project["id"], "待关联任务")
    resp = api.post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/{task['id']}/link"
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["task"]["task_code"] == task["task_code"]
    listed = api.get(f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks")
    assert listed.json()["total_count"] == 1


def test_link_existing_task_idempotent(api, project, mi_meeting):
    task = _make_task(api, project["id"], "幂等任务")
    url = f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/{task['id']}/link"
    assert api.post(url).status_code == 200
    assert api.post(url).status_code == 200
    listed = api.get(f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks")
    assert listed.json()["total_count"] == 1


def test_link_existing_task_unknown_task(api, project, mi_meeting):
    resp = api.post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/999999999/link"
    )
    assert resp.status_code == 404, resp.text[:200]


def test_link_existing_task_unknown_meeting(api, project):
    task = _make_task(api, project["id"], "无会议任务")
    resp = api.post(
        f"{_base(api, project)}/meetings/999999999/tasks/{task['id']}/link"
    )
    assert resp.status_code == 404, resp.text[:200]


def test_link_existing_task_other_project(api, project, mi_meeting, make_project):
    other = make_project()
    task = _make_task(api, other["id"], "别项目任务")
    resp = api.post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/{task['id']}/link"
    )
    assert resp.status_code == 400, resp.text[:200]


def test_link_existing_task_outsider_forbidden(api, project, mi_meeting, mi_outsider):
    task = _make_task(api, project["id"], "越权任务")
    resp = mi_outsider["client"].post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/{task['id']}/link"
    )
    assert resp.status_code == 403, resp.text[:200]


# ------------------------------------------------------------- sync tasks

def test_sync_tasks_counts_linked(api, project, mi_meeting):
    mid = mi_meeting["id"]
    task = _make_task(api, project["id"], "同步任务 1")
    api.post(f"{_base(api, project)}/meetings/{mid}/tasks/{task['id']}/link")
    api.post(
        f"{_base(api, project)}/meetings/{mid}/decisions-to-tasks",
        json={"decisions": [
            {"title": "同步任务 2", "create_task": True},
            {"title": "同步任务 3", "create_task": True},
        ]},
    )
    resp = api.post(f"{_base(api, project)}/meetings/{mid}/tasks/sync")
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["linked_tasks"] == 3
    assert resp.json()["moved_tasks"] == 0


def test_sync_tasks_unknown_meeting(api, project):
    resp = api.post(f"{_base(api, project)}/meetings/999999999/tasks/sync")
    assert resp.status_code == 404, resp.text[:200]


# ---------------------------------------------------------- update progress

def test_update_progress_status_and_hours(api, project, mi_meeting):
    mid = mi_meeting["id"]
    task = _make_task(api, project["id"], "进度任务")
    api.post(f"{_base(api, project)}/meetings/{mid}/tasks/{task['id']}/link")
    resp = api.put(
        f"{_base(api, project)}/meetings/{mid}/tasks/update-progress",
        json=[{"task_id": task["id"], "status": "IN_PROGRESS", "actual_hours": 2.5}],
    )
    assert resp.status_code == 200, resp.text[:300]
    updated = resp.json()["updated_tasks"][0]
    assert updated["status"] == "IN_PROGRESS"
    assert float(updated["actual_hours"]) == 2.5
    listed = api.get(f"{_base(api, project)}/meetings/{mid}/tasks")
    row = listed.json()["tasks"][0]
    assert row["status"] == "IN_PROGRESS"
    assert row["progress_percentage"] == 50


def test_update_progress_percentage_maps_to_completed(api, project, mi_meeting):
    mid = mi_meeting["id"]
    task = _make_task(api, project["id"], "百分比任务")
    api.post(f"{_base(api, project)}/meetings/{mid}/tasks/{task['id']}/link")
    resp = api.put(
        f"{_base(api, project)}/meetings/{mid}/tasks/update-progress",
        json=[{"task_id": task["id"], "progress_percentage": 100}],
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["updated_tasks"][0]["status"] == "COMPLETED"


def test_update_progress_unlinked_task(api, project, mi_meeting):
    task = _make_task(api, project["id"], "未关联任务")
    resp = api.put(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/update-progress",
        json=[{"task_id": task["id"], "status": "IN_PROGRESS"}],
    )
    assert resp.status_code == 400, resp.text[:200]


def test_update_progress_invalid_status(api, project, mi_meeting):
    task = _make_task(api, project["id"], "坏状态任务")
    api.post(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/{task['id']}/link"
    )
    resp = api.put(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks/update-progress",
        json=[{"task_id": task["id"], "status": "NOPE"}],
    )
    assert resp.status_code == 400, resp.text[:200]


def test_update_progress_unknown_meeting(api, project):
    resp = api.put(
        f"{_base(api, project)}/meetings/999999999/tasks/update-progress",
        json=[{"task_id": 1, "status": "TODO"}],
    )
    assert resp.status_code == 404, resp.text[:200]


# ------------------------------------------------------- read side / summary

def test_get_tasks_lists_linked_only(api, project, mi_meeting):
    mid = mi_meeting["id"]
    linked = _make_task(api, project["id"], "已关联")
    _make_task(api, project["id"], "未关联")
    api.post(f"{_base(api, project)}/meetings/{mid}/tasks/{linked['id']}/link")
    resp = api.get(f"{_base(api, project)}/meetings/{mid}/tasks")
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 1
    assert resp.json()["tasks"][0]["task_name"] == "已关联"


def test_get_tasks_outsider_forbidden(api, project, mi_meeting, mi_outsider):
    resp = mi_outsider["client"].get(
        f"{_base(api, project)}/meetings/{mi_meeting['id']}/tasks"
    )
    assert resp.status_code == 403, resp.text[:200]


def test_get_progress_summary_counts(api, project, mi_meeting):
    mid = mi_meeting["id"]
    done = _make_task(api, project["id"], "已完成任务")
    todo = _make_task(api, project["id"], "待办任务")
    for task in (done, todo):
        api.post(f"{_base(api, project)}/meetings/{mid}/tasks/{task['id']}/link")
    api.put(
        f"{_base(api, project)}/meetings/{mid}/tasks/update-progress",
        json=[{"task_id": done["id"], "status": "COMPLETED"}],
    )
    resp = api.get(f"{_base(api, project)}/meetings/{mid}/tasks/progress")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["total_tasks"] == 2
    assert body["completed_tasks"] == 1
    assert body["overall_progress"] == 50.0
