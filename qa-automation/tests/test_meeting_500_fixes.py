"""Regression tests for the four meeting-use 500 defects (D-500-1..4),
reported 2026-11-20 ("在使用会议过程中经常报500错误") and fixed on
branch fix/meetings-20261120.

- D-500-1 (P0): POST /api/v1/meetings/{id}/participants (single and
  /batch) returned 500 although the participant row WAS created.
  Root cause: MeetingService.add_participants returned ORM objects
  whose created_at/updated_at are SQL-expression defaults
  (func.now()) that are never loaded into the Python object after
  flush/commit; the route's ParticipantResponse.from_orm read
  updated_at and triggered a lazy load in async context
  (MissingGreenlet) -> pydantic validation error -> 500.
  Fix: refresh each added participant after commit.
- D-500-2 (P1): WSMessageType lacked NOTIFICATION and
  CONNECTION_STATUS, but meeting_notification_service sends
  NOTIFICATION messages and the WS ConnectionManager.connect sends
  CONNECTION_STATUS. Every meeting realtime notification failed
  (AttributeError, retried forever) and no WS connection could be
  established (connect swallowed the error and returned False).
  Fix: add both enum members. No HTTP-observable assertion exists
  for this one (the WS connect path has no route caller; the
  notification path is only observable in the backend journal), so
  it is verified manually: add-participant triggers the
  notification send, and the journal must show no new
  "Error sending WebSocket notification" lines; connect() is
  verified in-process with a fake websocket. See TEST_REPORT.md.
- D-500-3 (P2): ai_operation_log_service wrote via native SQL with
  columns (target_type, operation_data, status, ...) that do not
  exist in ai_operation_logs (MySQL 1054); every AI operation-log
  write failed. Fix: rewrite the INSERT/SELECT mapping to the
  model's real columns (resource_type, result, processing_time,
  cost_amount, request_ip, ...).
- D-500-4 (P1): with OPENAI_API_KEY empty, POST .../summary/generate
  (and .../minutes/generate, same LLM path) returned 500
  "生成会议摘要失败". The empty-key RuntimeError from the LLM layer
  fell into the routes' generic except. Fix: _call_llm_json
  translates a missing-key failure into ConfigurationError and the
  two routes map it to 503 with a clear reason. (Restoring the key
  is the real fix; this makes the failure honest until then.)

Key-state fixture: the D-500-3/D-500-4 tests need the LLM key to be
missing. The module fixture blanks OPENAI_API_KEY in backend/.env
and restores the file byte-for-byte afterwards, same pattern as
test_meeting_analytics.py's llm_stub (the assistant service
re-reads .env on every LLM call, so no backend restart is needed).
"""

import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = REPO_ROOT / "backend" / ".env"

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"
PASSWORD = "Test1234!"


def _set_env_keys(path: Path, updates: dict) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


@pytest.fixture(scope="module")
def empty_llm_key():
    """Blank OPENAI_API_KEY for the module; restore byte-for-byte."""
    original = BACKEND_ENV.read_bytes()
    try:
        _set_env_keys(BACKEND_ENV, {"OPENAI_API_KEY": ""})
        yield
    finally:
        BACKEND_ENV.write_bytes(original)


def _make_meeting(api, project_id, title):
    resp = api.post(
        f"/api/v1/meetings/projects/{project_id}/meetings",
        json={
            "title": title,
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    return resp.json()


def _make_plain_user(api):
    username = f"u500-user-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
    )
    assert resp.status_code in (200, 201), f"setup: create user failed: {resp.text[:300]}"
    user = resp.json()
    return user.get("id") or user.get("user", {}).get("id")


@pytest.fixture()
def meeting(api, project, request):
    m = _make_meeting(api, project["id"], title=f"500修复测试会议-{uuid.uuid4().hex[:6]}")
    request.addfinalizer(lambda: api.delete(f"/api/v1/meetings/{m['id']}"))
    return m


@pytest.fixture()
def plain_user(api, request):
    user_id = _make_plain_user(api)
    request.addfinalizer(lambda: api.delete(f"/api/v1/users/{user_id}"))
    return user_id


# ---------------------------------------------------------------- D-500-1


def test_add_participant_single_returns_201(api, meeting, plain_user):
    """D-500-1: single add used to 500 (row created anyway)."""
    resp = api.post(
        f"/api/v1/meetings/{meeting['id']}/participants",
        json={"user_id": plain_user},
    )
    assert resp.status_code == 201, f"add participant failed: {resp.status_code} {resp.text[:300]}"
    # Declared shape is AddParticipantResponse{success, participant, message}:
    # the route used to pass data= (silently dropped), so clients got
    # participant=null even on 201.
    data = resp.json()["participant"]
    assert data is not None, f"participant is null: {resp.text[:300]}"
    assert data["user_id"] == plain_user
    # updated_at is the field whose lazy load used to explode.
    assert data.get("updated_at"), f"updated_at missing in response: {data}"
    assert data.get("invited_at"), f"invited_at missing in response: {data}"

    # The participant is really there.
    resp = api.get(f"/api/v1/meetings/{meeting['id']}/participants")
    assert resp.status_code == 200, resp.text[:300]
    participants = resp.json()["participants"]
    assert any(p["user_id"] == plain_user for p in participants)


def test_add_participants_batch_returns_201(api, meeting, plain_user):
    """D-500-1: batch add shares the same broken return path."""
    second_user = _make_plain_user(api)
    try:
        resp = api.post(
            f"/api/v1/meetings/{meeting['id']}/participants/batch",
            json={"participants": [{"user_id": plain_user}, {"user_id": second_user}]},
        )
        assert resp.status_code == 201, (
            f"batch add failed: {resp.status_code} {resp.text[:300]}"
        )
        # Declared shape is AddParticipantsResponse{success, added_count,
        # failed_count, participants, errors}: the route used to pass
        # data/message/failed_users, which failed response-model
        # validation with 3 missing fields (masked by the
        # MissingGreenlet until the refresh fix landed).
        body = resp.json()
        assert body["added_count"] == 2, f"expected added_count 2: {body}"
        assert body["failed_count"] == 0, f"expected failed_count 0: {body}"
        assert len(body["participants"]) == 2, f"expected 2 added: {body}"
        for item in body["participants"]:
            assert item.get("updated_at"), f"updated_at missing: {item}"
    finally:
        api.delete(f"/api/v1/users/{second_user}")


# ---------------------------------------------------------------- D-500-4


def test_summary_generate_missing_key_returns_503(api, meeting, empty_llm_key):
    """D-500-4: empty OPENAI_API_KEY must be a 503 with a clear reason, not a 500."""
    resp = api.post(f"/api/v1/meetings/{meeting['id']}/summary/generate", json={})
    assert resp.status_code == 503, f"expected 503, got {resp.status_code}: {resp.text[:300]}"
    detail = resp.json().get("detail", "")
    assert "API Key" in detail or "API key" in detail or "未配置" in detail, detail


def test_minutes_generate_missing_key_returns_503(api, meeting, empty_llm_key):
    """D-500-4: minutes generation goes through the same LLM seam."""
    resp = api.post(f"/api/v1/meetings/{meeting['id']}/minutes/generate", json={})
    assert resp.status_code == 503, f"expected 503, got {resp.status_code}: {resp.text[:300]}"
    detail = resp.json().get("detail", "")
    assert "API Key" in detail or "API key" in detail or "未配置" in detail, detail


# ---------------------------------------------------------------- D-500-3


def _failure_logs_total(api):
    resp = api.get("/api/v1/ai/operation-logs", params={"result": "failure", "page_size": 1})
    assert resp.status_code == 200, f"query operation logs failed: {resp.text[:300]}"
    return resp.json()["data"]["total"]


def test_ai_query_failure_writes_operation_log(api, empty_llm_key):
    """D-500-3: a failed AI model call must land a FAILURE row in
    ai_operation_logs. Before the fix the INSERT 1054'd (unknown
    column 'target_type') and the failure was only visible in the
    backend journal."""
    before = _failure_logs_total(api)
    resp = api.post(
        "/api/v1/ai-assistant/query",
        json={"content": "你好，用一句话介绍你自己"},
        timeout=120,
    )
    # With the key missing the query itself must fail cleanly (503).
    assert resp.status_code == 503, f"expected 503, got {resp.status_code}: {resp.text[:300]}"
    after = _failure_logs_total(api)
    assert after > before, (
        f"no FAILURE operation log was written (before={before}, after={after}); "
        "the ai_operation_logs INSERT is still broken"
    )
    resp = api.get(
        "/api/v1/ai/operation-logs",
        params={"result": "failure", "page_size": 5, "order_by": "created_at"},
    )
    assert resp.status_code == 200, resp.text[:300]
    # PaginatedResponse (schemas/base.py) carries the list as `data`,
    # not `items`.
    items = resp.json()["data"]["data"]
    assert items, "failure log list is empty despite total > 0"
    assert items[0]["result"] == "FAILURE", f"newest failure row: {items[0]}"
    assert items[0]["operation_type"] == "AI_MODEL_CALL", f"newest failure row: {items[0]}"
