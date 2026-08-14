from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

import pytest
import requests

from conftest import LiveCleanupStack


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.business_crud]

AUTO_PREFIX = "PYTEST_AUTO"
PROJECT_ID = 1
ADMIN_USER_ID = 1


def _unique(label: str) -> str:
    return f"{AUTO_PREFIX}_{label}_{uuid.uuid4().hex[:10]}"


def _json(response: requests.Response, expected_status: int, action: str) -> dict[str, Any]:
    assert response.status_code == expected_status, f"{action} failed: {response.status_code} {response.text[:800]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict), f"{action} returned non-object JSON: {payload!r}"
    return payload


def _assert_deleted_response(response: requests.Response, action: str) -> dict[str, Any]:
    return _json(response, 200, action)


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("items", "risks", "tasks", "meetings", "milestones", "projects", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _items(value)
            if nested:
                return nested
    return []


def _data(payload: dict[str, Any], key: str | None = None) -> dict[str, Any]:
    if key:
        value = payload.get(key)
        assert isinstance(value, dict), f"Response missing object {key!r}: {payload!r}"
        return value
    value = payload.get("data")
    if isinstance(value, dict):
        return value
    return payload


def _delete_config(session: requests.Session, base_url: str, config_key: str) -> None:
    response = session.delete(
        f"{base_url}/api/v1/configs/configs/{config_key}",
        params={"environment": "test", "hard_delete": True},
        timeout=10,
    )
    assert response.status_code in {200, 202, 204, 400, 404}, (
        f"cleanup config {config_key} failed: {response.status_code} {response.text[:500]}"
    )


def _delete_id(session: requests.Session, base_url: str, path: str, resource_id: int) -> None:
    response = session.delete(f"{base_url}{path}/{resource_id}", timeout=10)
    assert response.status_code in {200, 202, 204, 400, 404}, (
        f"cleanup {path}/{resource_id} failed: {response.status_code} {response.text[:500]}"
    )


def _delete_config_group(session: requests.Session, base_url: str, group_id: int) -> None:
    response = session.delete(f"{base_url}/api/v1/configs/groups/{group_id}", timeout=10)
    assert response.status_code in {200, 202, 204, 400, 404}, (
        f"cleanup config group {group_id} failed: {response.status_code} {response.text[:500]}"
    )


def _decimal_text(value: Any) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.00")))


def test_config_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    config_key = _unique("CONFIG")
    cleanup = live_cleanup_stack.add(lambda: _delete_config(authenticated_session, base_url, config_key))

    created = _data(
        _json(
            authenticated_session.post(
                f"{base_url}/api/v1/configs/configs",
                json={
                    "config_key": config_key,
                    "config_value": "value-before-update",
                    "config_type": "STRING",
                    "environment": "test",
                    "description": "pytest closed-loop config",
                    "is_core": False,
                    "is_enabled": True,
                    "is_encrypted": False,
                    "is_required": False,
                    "tags": [AUTO_PREFIX, "closed-loop"],
                    "sort_order": 0,
                },
                timeout=10,
            ),
            200,
            "create config",
        )
    )
    assert created["config_key"] == config_key
    assert created["config_value"] == "value-before-update"
    assert created["environment"] == "test"

    detail = _data(
        _json(
            authenticated_session.get(
                f"{base_url}/api/v1/configs/configs/{config_key}",
                params={"environment": "test", "decrypt": False},
                timeout=10,
            ),
            200,
            "get config",
        )
    )
    assert detail["config_key"] == config_key

    updated = _data(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/configs/configs/{config_key}",
                params={"environment": "test"},
                json={
                    "config_value": "value-after-update",
                    "description": "pytest closed-loop config updated",
                    "tags": [AUTO_PREFIX, "updated"],
                    "change_reason": "pytest CRUD closed-loop verification",
                },
                timeout=10,
            ),
            200,
            "update config",
        )
    )
    assert updated["config_key"] == config_key
    assert updated["config_value"] == "value-after-update"
    assert updated["description"] == "pytest closed-loop config updated"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/configs/configs",
            params={"environment": "test", "search": config_key, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search config list",
    )
    assert any(item["config_key"] == config_key for item in _items(listed))

    _assert_deleted_response(
        authenticated_session.delete(
            f"{base_url}/api/v1/configs/configs/{config_key}",
            params={"environment": "test", "hard_delete": True},
            timeout=10,
        ),
        "delete config",
    )
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(
        f"{base_url}/api/v1/configs/configs/{config_key}",
        params={"environment": "test", "decrypt": False},
        timeout=10,
    )
    assert deleted_get.status_code == 404, f"deleted config is still readable: {deleted_get.status_code} {deleted_get.text[:500]}"


def test_risk_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    risk_name = _unique("RISK")
    risk_id: int | None = None

    created = _json(
        authenticated_session.post(
            f"{base_url}/api/v1/risks/",
            json={
                "risk_name": risk_name,
                "description": "pytest closed-loop project risk",
                "risk_category": "SCHEDULE",
                "risk_level": "LOW",
                "probability": 0.2,
                "impact_score": 2,
                "mitigation_strategy": "MITIGATE",
                "mitigation_plan": "Monitor schedule buffer during CRUD verification.",
                "contingency_plan": "Escalate to project owner if the schedule slips.",
                "owner_id": ADMIN_USER_ID,
                "project_id": PROJECT_ID,
                "target_resolution_date": "2026-12-31",
            },
            timeout=10,
        ),
        200,
        "create risk",
    )
    risk_id = int(created["id"])
    cleanup = live_cleanup_stack.add(lambda: _delete_id(authenticated_session, base_url, "/api/v1/risks", risk_id))

    detail = _json(authenticated_session.get(f"{base_url}/api/v1/risks/{risk_id}", timeout=10), 200, "get risk")
    assert detail["risk_name"] == risk_name
    assert detail["project_id"] == PROJECT_ID
    assert detail["status"] == "IDENTIFIED"

    updated_name = f"{risk_name}_UPDATED"
    updated = _json(
        authenticated_session.put(
            f"{base_url}/api/v1/risks/{risk_id}",
            json={
                "risk_name": updated_name,
                "description": "pytest closed-loop project risk updated",
                "risk_level": "MEDIUM",
                "probability": 0.35,
                "impact_score": 3,
                "status": "MITIGATING",
                "mitigation_strategy": "MITIGATE",
                "mitigation_plan": "Add owner checkpoint after update.",
            },
            timeout=10,
        ),
        200,
        "update risk",
    )
    assert updated["risk_name"] == updated_name
    assert updated["risk_level"] == "MEDIUM"
    assert updated["status"] == "MITIGATING"
    assert _decimal_text(updated["probability"]) == "0.35"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/risks/",
            params={"project_id": PROJECT_ID, "search": risk_name, "page": 1, "page_size": 20},
            timeout=10,
        ),
        200,
        "search risk list",
    )
    assert any(item["id"] == risk_id for item in _items(listed))

    _assert_deleted_response(authenticated_session.delete(f"{base_url}/api/v1/risks/{risk_id}", timeout=10), "delete risk")
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/risks/{risk_id}", timeout=10)
    assert deleted_get.status_code == 404, f"deleted risk is still readable: {deleted_get.status_code} {deleted_get.text[:500]}"


def test_config_group_create_update_list_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    group_code = f"{AUTO_PREFIX}_GROUP_{suffix}".lower()
    group_name = f"{AUTO_PREFIX}_Group_{suffix}"

    created = _data(
        _json(
            authenticated_session.post(
                f"{base_url}/api/v1/configs/groups",
                json={
                    "group_name": group_name,
                    "group_code": group_code,
                    "parent_id": 0,
                    "level": 1,
                    "sort_order": 99,
                    "description": "pytest closed-loop config group",
                    "icon": "setting",
                    "color": "#1677ff",
                    "is_system": False,
                    "is_enabled": True,
                },
                timeout=10,
            ),
            200,
            "create config group",
        )
    )
    group_id = int(created["id"])
    cleanup = live_cleanup_stack.add(lambda: _delete_config_group(authenticated_session, base_url, group_id))
    assert created["group_code"] == group_code
    assert created["group_name"] == group_name
    assert created["is_enabled"] is True

    listed = _json(
        authenticated_session.get(f"{base_url}/api/v1/configs/groups", timeout=10),
        200,
        "list config groups",
    )
    assert any(item["id"] == group_id and item["group_code"] == group_code for item in _items(listed))

    updated_name = f"{group_name}_UPDATED"
    updated = _data(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/configs/groups/{group_id}",
                json={
                    "group_name": updated_name,
                    "description": "pytest closed-loop config group updated",
                    "icon": "tool",
                    "color": "#52c41a",
                    "sort_order": 100,
                    "is_enabled": True,
                },
                timeout=10,
            ),
            200,
            "update config group",
        )
    )
    assert updated["group_name"] == updated_name
    assert updated["description"] == "pytest closed-loop config group updated"
    assert updated["color"] == "#52c41a"
    assert updated["sort_order"] == 100

    _assert_deleted_response(
        authenticated_session.delete(f"{base_url}/api/v1/configs/groups/{group_id}", timeout=10),
        "delete config group",
    )
    live_cleanup_stack.discard(cleanup)

    after_delete = _json(
        authenticated_session.get(f"{base_url}/api/v1/configs/groups", timeout=10),
        200,
        "list config groups after delete",
    )
    assert not any(item["id"] == group_id for item in _items(after_delete)), (
        f"deleted config group is still visible in enabled list: {group_id}"
    )


def test_task_create_read_update_patch_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    task_name = _unique("TASK")
    task_id: int | None = None

    created = _data(
        _json(
            authenticated_session.post(
                f"{base_url}/api/v1/tasks",
                json={
                    "project_id": PROJECT_ID,
                    "task_name": task_name,
                    "description": "pytest closed-loop task",
                    "task_type": "TEST_EXECUTION",
                    "priority": "LOW",
                    "status": "TODO",
                    "assignee_id": ADMIN_USER_ID,
                    "reporter_id": ADMIN_USER_ID,
                    "planned_start_date": "2026-12-01",
                    "planned_end_date": "2026-12-31",
                    "estimated_hours": 1,
                    "acceptance_criteria": "The task can be created, updated, listed, and deleted.",
                    "tags": [AUTO_PREFIX, "closed-loop"],
                },
                timeout=10,
            ),
            201,
            "create task",
        ),
        "task",
    )
    task_id = int(created["id"])
    cleanup = live_cleanup_stack.add(lambda: _delete_id(authenticated_session, base_url, "/api/v1/tasks", task_id))

    detail = _json(authenticated_session.get(f"{base_url}/api/v1/tasks/{task_id}", timeout=10), 200, "get task")
    assert detail["task_name"] == task_name
    assert detail["project_id"] == PROJECT_ID
    assert detail["status"] == "TODO"

    updated_name = f"{task_name}_UPDATED"
    updated = _data(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/tasks/{task_id}",
                json={
                    "task_name": updated_name,
                    "description": "pytest closed-loop task updated",
                    "task_type": "TEST_EXECUTION",
                    "priority": "MEDIUM",
                    "status": "TODO",
                    "assignee_id": ADMIN_USER_ID,
                    "reporter_id": ADMIN_USER_ID,
                    "planned_start_date": "2026-12-01",
                    "planned_end_date": "2026-12-31",
                    "estimated_hours": 2,
                    "tags": [AUTO_PREFIX, "updated"],
                },
                timeout=10,
            ),
            200,
            "update task",
        ),
        "task",
    )
    assert updated["task_name"] == updated_name
    assert updated["priority"] == "MEDIUM"
    assert _decimal_text(updated["estimated_hours"]) == "2.00"

    patched = _data(
        _json(
            authenticated_session.patch(
                f"{base_url}/api/v1/tasks/{task_id}",
                json={"description": "pytest closed-loop task patched"},
                timeout=10,
            ),
            200,
            "patch task",
        ),
        "task",
    )
    assert patched["description"] == "pytest closed-loop task patched"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/tasks",
            params={"project_id": PROJECT_ID, "search": task_name, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search task list",
    )
    assert any(item["id"] == task_id for item in _items(listed))

    _assert_deleted_response(authenticated_session.delete(f"{base_url}/api/v1/tasks/{task_id}", timeout=10), "delete task")
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/tasks/{task_id}", timeout=10)
    assert deleted_get.status_code == 404, f"deleted task is still readable: {deleted_get.status_code} {deleted_get.text[:500]}"


def test_meeting_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    title = _unique("MEETING")
    meeting_id: int | None = None
    start_time = (dt.datetime.utcnow() + dt.timedelta(days=30)).replace(microsecond=0)
    end_time = start_time + dt.timedelta(hours=1)

    created = _data(
        _json(
            authenticated_session.post(
                f"{base_url}/api/v1/meetings/",
                json={
                    "title": title,
                    "description": "pytest closed-loop meeting",
                    "meeting_type": "PROGRESS_SYNC",
                    "scheduled_start_time": start_time.isoformat(),
                    "scheduled_end_time": end_time.isoformat(),
                    "timezone": "UTC",
                    "max_participants": 10,
                    "project_id": PROJECT_ID,
                    "meeting_settings": {
                        "auto_record": False,
                        "mute_on_join": True,
                        "video_on_join": False,
                        "allow_screen_share": True,
                        "allow_chat": True,
                        "allow_file_share": True,
                        "waiting_room_enabled": True,
                        "password_required": False,
                        "recording_auto_start": False,
                    },
                    "is_recording_enabled": False,
                    "is_waiting_room_enabled": True,
                    "is_password_protected": False,
                },
                timeout=10,
            ),
            201,
            "create meeting",
        )
    )
    meeting_id = int(created["id"])
    cleanup = live_cleanup_stack.add(lambda: _delete_id(authenticated_session, base_url, "/api/v1/meetings", meeting_id))

    detail = _json(authenticated_session.get(f"{base_url}/api/v1/meetings/{meeting_id}", timeout=10), 200, "get meeting")
    assert detail["title"] == title
    assert detail["project_id"] == PROJECT_ID
    assert detail["status"] == "SCHEDULED"

    updated_title = f"{title}_UPDATED"
    updated = _data(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/meetings/{meeting_id}",
                json={
                    "title": updated_title,
                    "description": "pytest closed-loop meeting updated",
                    "meeting_type": "PROGRESS_SYNC",
                    "max_participants": 12,
                    "is_waiting_room_enabled": False,
                },
                timeout=10,
            ),
            200,
            "update meeting",
        )
    )
    assert updated["title"] == updated_title
    assert updated["max_participants"] == 12
    assert updated["is_waiting_room_enabled"] is False

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/meetings/",
            params={"keyword": title, "page": 1, "page_size": 20},
            timeout=10,
        ),
        200,
        "search meeting list",
    )
    assert any(item["id"] == meeting_id for item in _items(listed))

    _assert_deleted_response(authenticated_session.delete(f"{base_url}/api/v1/meetings/{meeting_id}", timeout=10), "delete meeting")
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/meetings/{meeting_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted meeting should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )


def test_requirement_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    title = _unique("REQ")
    requirement_id: int | None = None

    created = _json(
        authenticated_session.post(
            f"{base_url}/api/v1/requirements/",
            json={
                "project_id": PROJECT_ID,
                "title": title,
                "description": "pytest closed-loop requirement",
                "acceptance_criteria": "Requirement CRUD can create, update, search, and delete safely.",
                "requirement_type": "FUNCTIONAL",
                "category": "pytest",
                "priority": "LOW",
                "business_value": "NORMAL",
                "complexity": "SIMPLE",
                "estimated_effort": 1,
                "assignee_id": ADMIN_USER_ID,
                "reviewer_id": ADMIN_USER_ID,
                "planned_start_date": "2026-12-01",
                "planned_end_date": "2026-12-31",
                "tags": [AUTO_PREFIX, "closed-loop"],
                "custom_fields": {"source": "pytest"},
            },
            timeout=10,
        ),
        201,
        "create requirement",
    )
    requirement_id = int(created["id"])
    cleanup = live_cleanup_stack.add(
        lambda: _delete_id(authenticated_session, base_url, "/api/v1/requirements", requirement_id)
    )

    detail = _json(
        authenticated_session.get(f"{base_url}/api/v1/requirements/{requirement_id}", timeout=10),
        200,
        "get requirement",
    )
    assert detail["title"] == title
    assert detail["project_id"] == PROJECT_ID
    assert detail["status"] == "DRAFT"

    updated_title = f"{title}_UPDATED"
    updated = _json(
        authenticated_session.put(
            f"{base_url}/api/v1/requirements/{requirement_id}",
            json={
                "title": updated_title,
                "description": "pytest closed-loop requirement updated",
                "priority": "MEDIUM",
                "business_value": "IMPORTANT",
                "complexity": "MEDIUM",
                "estimated_effort": 2,
                "tags": [AUTO_PREFIX, "updated"],
            },
            timeout=10,
        ),
        200,
        "update requirement",
    )
    assert updated["title"] == updated_title
    assert updated["priority"] == "MEDIUM"
    assert updated["business_value"] == "IMPORTANT"
    assert _decimal_text(updated["estimated_effort"]) == "2.00"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/requirements/",
            params={"project_id": PROJECT_ID, "keyword": title, "skip": 0, "limit": 20},
            timeout=10,
        ),
        200,
        "search requirement list",
    )
    assert any(item["id"] == requirement_id for item in _items(listed))

    delete_response = authenticated_session.delete(f"{base_url}/api/v1/requirements/{requirement_id}", timeout=10)
    assert delete_response.status_code == 204, (
        f"delete requirement failed: {delete_response.status_code} {delete_response.text[:500]}"
    )
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/requirements/{requirement_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted requirement should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )


def test_milestone_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    milestone_name = _unique("MILESTONE")
    milestone_id: int | None = None

    create_response = authenticated_session.post(
        f"{base_url}/api/v1/milestones/{PROJECT_ID}",
        json={
            "milestone_name": milestone_name,
            "description": "pytest closed-loop milestone",
            "milestone_type": "REQUIREMENT",
            "planned_date": "2026-12-20",
            "owner_id": ADMIN_USER_ID,
            "deliverables": [
                {
                    "name": "pytest deliverable",
                    "type": "document",
                    "description": "closed-loop deliverable",
                    "owner_id": ADMIN_USER_ID,
                    "due_date": "2026-12-19",
                }
            ],
            "acceptance_criteria": "Milestone CRUD can create, update, search, and delete safely.",
            "dependencies": [],
            "tags": [AUTO_PREFIX, "closed-loop"],
            "custom_fields": {"source": "pytest"},
        },
        timeout=10,
    )
    created = _json(create_response, 200, "create milestone")
    milestone = _data(created, "milestone")
    milestone_id = int(milestone["id"])
    cleanup = live_cleanup_stack.add(
        lambda: _delete_id(authenticated_session, base_url, "/api/v1/milestones", milestone_id)
    )

    detail = _json(
        authenticated_session.get(f"{base_url}/api/v1/milestones/detail/{milestone_id}", timeout=10),
        200,
        "get milestone",
    )
    assert detail["milestone_name"] == milestone_name
    assert detail["project_id"] == PROJECT_ID
    assert detail["status"] == "PENDING"

    updated_name = f"{milestone_name}_UPDATED"
    updated = _data(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/milestones/{milestone_id}",
                json={
                    "milestone_name": updated_name,
                    "description": "pytest closed-loop milestone updated",
                    "milestone_type": "DESIGN",
                    "status": "IN_PROGRESS",
                    "planned_date": "2026-12-21",
                    "owner_id": ADMIN_USER_ID,
                    "deliverables": [],
                    "tags": [AUTO_PREFIX, "updated"],
                },
                timeout=10,
            ),
            200,
            "update milestone",
        ),
        "milestone",
    )
    assert updated["milestone_name"] == updated_name
    assert updated["milestone_type"] == "DESIGN"
    assert updated["status"] == "IN_PROGRESS"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/milestones/{PROJECT_ID}",
            params={"search": milestone_name, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search milestone list",
    )
    assert any(item["id"] == milestone_id for item in _items(listed))

    _assert_deleted_response(
        authenticated_session.delete(f"{base_url}/api/v1/milestones/{milestone_id}", timeout=10),
        "delete milestone",
    )
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/milestones/detail/{milestone_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted milestone should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )


def test_ai_model_config_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    model_name = f"pytest-auto-model-{suffix}"
    config_id: int | None = None

    create_response = authenticated_session.post(
        f"{base_url}/api/v1/ai-model-config/",
        json={
            "provider": "custom",
            "model_name": model_name,
            "display_name": f"{AUTO_PREFIX} Model {suffix}",
            "description": "pytest closed-loop AI model config",
            "version": "v1",
            "api_endpoint": "http://127.0.0.1/mock-ai",
            "api_key": "pytest-key",
            "max_tokens": 1000,
            "temperature": 0.2,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "is_enabled": False,
            "is_default": False,
            "is_public": False,
            "priority": 0,
            "concurrent_limit": 1,
            "timeout_seconds": 5,
            "retry_count": 0,
            "tags": [AUTO_PREFIX, "closed-loop"],
            "custom_config": {"source": "pytest"},
        },
        timeout=10,
    )
    created = _json(create_response, 200, "create AI model config")
    config_id = int(created["id"])
    cleanup = live_cleanup_stack.add(
        lambda: _delete_id(authenticated_session, base_url, "/api/v1/ai-model-config", config_id)
    )

    detail = _json(
        authenticated_session.get(f"{base_url}/api/v1/ai-model-config/{config_id}", timeout=10),
        200,
        "get AI model config",
    )
    assert detail["model_name"] == model_name
    assert detail["provider"] == "custom"
    assert detail["is_enabled"] is False

    updated = _json(
        authenticated_session.put(
            f"{base_url}/api/v1/ai-model-config/{config_id}",
            json={
                "display_name": f"{AUTO_PREFIX} Model {suffix} Updated",
                "description": "pytest closed-loop AI model config updated",
                "max_tokens": 1200,
                "is_enabled": False,
                "priority": 1,
            },
            timeout=10,
        ),
        200,
        "update AI model config",
    )
    assert updated["display_name"].endswith("Updated")
    assert updated["max_tokens"] == 1200
    assert updated["priority"] == 1

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/ai-model-config/",
            params={"provider": "custom", "skip": 0, "limit": 100},
            timeout=10,
        ),
        200,
        "search AI model config list",
    )
    assert any(item["id"] == config_id for item in _items(listed))

    _assert_deleted_response(
        authenticated_session.delete(f"{base_url}/api/v1/ai-model-config/{config_id}", timeout=10),
        "delete AI model config",
    )
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/ai-model-config/{config_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted AI model config should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )
