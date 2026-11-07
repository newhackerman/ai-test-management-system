"""Round-6 items 1-4 regression tests (task item 14).

Covers the features implemented in round 6 items 1-4:
- item 1: audit comment / cancel / history (+ WebSocket is covered by the
  item-1 probe in the report; no WS client in this suite)
- item 2: AI file share access + admin-only cleanup
- item 3: /me and /profile return real roles/permissions
- item 4: traceability matrix / impact analysis / coverage on real data

Conventions follow the rest of the suite: admin ``api`` fixture,
``make_project`` / ``make_requirement`` / ``make_case`` factories,
unique names per test, best-effort cleanup (audits and traceability
links have no delete endpoint; they use unique keys and are left
behind as inert rows).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

import factories
from assertions import assert_envelope_ok
from client import ApiClient
from config import BASE_URL

AUDITS = "/api/v1/configs/audits"
FILES = "/api/v1/ai/files"
TRACE = "/api/v1/requirement-traceability"

SEC_PASSWORD = "Test123!@#"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def r6_user(api):
    """A plain user with no roles/permissions (for 403 checks)."""
    username = f"r6-user-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        "/api/v1/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": SEC_PASSWORD,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create user failed: {resp.text[:300]}"
    user = resp.json()
    user_id = user.get("id") or user.get("user", {}).get("id")
    client = ApiClient(BASE_URL)
    token = client.login(username, SEC_PASSWORD).json().get("access_token")
    assert token, "setup: r6 user login failed"
    yield {"id": user_id, "username": username, "client": client}
    client.close()
    api.delete(f"/api/v1/users/{user_id}")


@pytest.fixture()
def audit(api):
    """One PENDING audit created by the admin."""
    key = f"r6.audit.{uuid.uuid4().hex[:8]}"
    resp = api.post(
        AUDITS,
        json={
            "config_key": key,
            "environment": "test",
            "new_value": "on",
            "change_type": "CREATE",
            "apply_reason": "round-6 item-14 probe",
        },
    )
    assert resp.status_code in (200, 201), f"setup: create audit failed: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    item = body.get("data") or body
    assert item.get("id"), f"setup: no audit id in {resp.text[:200]}"
    return item


@pytest.fixture()
def uploaded_file(api):
    """One small uploaded AI file; deleted after the test."""
    resp = api.post(
        f"{FILES}/upload",
        files={"file": ("r6-probe.txt", b"round6 item14 probe content", "text/plain")},
        data={"category": "USER_UPLOAD"},
    )
    assert resp.status_code in (200, 201), f"setup: upload failed: {resp.status_code} {resp.text[:300]}"
    item = resp.json()
    assert item.get("id"), f"setup: no file id in {resp.text[:200]}"
    yield item
    try:
        api.delete(f"{FILES}/{item['id']}")
    except Exception:
        pass


def _share(api, file_id, **overrides):
    payload = {"can_preview": True, "can_download": True}
    payload.update(overrides)
    resp = api.post(f"{FILES}/{file_id}/share", json=payload)
    assert resp.status_code in (200, 201), f"setup: create share failed: {resp.status_code} {resp.text[:300]}"
    return resp.json()


@pytest.fixture()
def linked_requirement(api, make_project, make_requirement, make_case):
    """A requirement linked to a test case (TESTS), for matrix/impact/coverage."""
    project = make_project()
    req = make_requirement(project["id"])
    case = make_case(requirement_id=req["id"])
    resp = api.post(
        f"{TRACE}/links",
        json={
            "source_type": "requirement",
            "source_id": req["id"],
            "target_type": "test_case",
            "target_id": case["id"],
            "link_type": "TESTS",
            "description": "round-6 item-14 probe link",
        },
    )
    assert resp.status_code in (200, 201), f"setup: create link failed: {resp.status_code} {resp.text[:300]}"
    return {"project": project, "requirement": req, "case": case}


# ---------------------------------------------------------------------------
# item 1 — audit comment / cancel / history
# ---------------------------------------------------------------------------


def test_audit_comment_persists_and_shows_in_history(api, audit):
    resp = api.post(f"{AUDITS}/{audit['id']}/comment", params={"comment": "r6 审核意见：同意"})
    assert resp.status_code == 200, resp.text[:300]
    history = api.get(f"{AUDITS}/{audit['id']}/history")
    assert history.status_code == 200, history.text[:300]
    events = history.json()
    events = events.get("data") if isinstance(events, dict) else events
    text = " ".join(str(e) for e in events)
    assert "r6 审核意见：同意" in text


def test_audit_comment_empty_rejected(api, audit):
    resp = api.post(f"{AUDITS}/{audit['id']}/comment", params={"comment": "   "})
    assert resp.status_code == 400, resp.text[:300]


def test_audit_comment_unknown_audit_404(api):
    resp = api.post(f"{AUDITS}/999999/comment", params={"comment": "x"})
    assert resp.status_code == 404, resp.text[:300]


def test_audit_cancel_by_applicant_and_terminal_guard(api, audit):
    resp = api.post(f"{AUDITS}/{audit['id']}/cancel", params={"cancel_reason": "r6 不需要了"})
    assert resp.status_code == 200, resp.text[:300]
    detail = api.get(f"{AUDITS}/{audit['id']}")
    assert detail.status_code == 200
    body = detail.json()
    item = body.get("data") or body
    assert str(item.get("audit_status", "")).upper() == "CANCELLED", item
    # Terminal state: no second cancel, no more comments.
    assert api.post(f"{AUDITS}/{audit['id']}/cancel", params={"cancel_reason": "again"}).status_code == 400
    assert api.post(f"{AUDITS}/{audit['id']}/comment", params={"comment": "late"}).status_code == 400


def test_audit_cancel_forbidden_for_other_user(api, audit, r6_user):
    resp = r6_user["client"].post(f"{AUDITS}/{audit['id']}/cancel", params={"cancel_reason": "not mine"})
    assert resp.status_code == 403, resp.text[:300]


def test_audit_history_is_a_timeline(api, audit):
    api.post(f"{AUDITS}/{audit['id']}/comment", params={"comment": "r6 时间线探针"})
    resp = api.get(f"{AUDITS}/{audit['id']}/history")
    assert resp.status_code == 200
    events = resp.json()
    events = events.get("data") if isinstance(events, dict) else events
    assert isinstance(events, list) and len(events) >= 2
    text = " ".join(str(e) for e in events)
    assert "r6 时间线探针" in text


# ---------------------------------------------------------------------------
# item 2 — AI file share access + admin cleanup
# ---------------------------------------------------------------------------


def test_share_preview_anonymous(api, anon, uploaded_file):
    share = _share(api, uploaded_file["id"])
    assert share.get("share_token"), share
    resp = anon.get(f"{FILES}/share/{share['share_token']}", params={"action": "preview"})
    assert resp.status_code == 200, resp.text[:300]
    assert str(uploaded_file["id"]) in resp.text or "r6-probe.txt" in resp.text


def test_share_password_enforced(api, anon, uploaded_file):
    share = _share(api, uploaded_file["id"], password="r6secret")
    token = share["share_token"]
    assert anon.get(f"{FILES}/share/{token}", params={"action": "preview"}).status_code == 403
    assert anon.get(f"{FILES}/share/{token}", params={"action": "preview", "password": "wrong"}).status_code == 403
    resp = anon.get(f"{FILES}/share/{token}", params={"action": "preview", "password": "r6secret"})
    assert resp.status_code == 200, resp.text[:300]


def test_share_unknown_token_404(anon):
    resp = anon.get(f"{FILES}/share/no-such-token-123", params={"action": "preview"})
    assert resp.status_code == 404, resp.text[:300]


def test_share_max_views_enforced(api, anon, uploaded_file):
    share = _share(api, uploaded_file["id"], max_views=1)
    token = share["share_token"]
    assert anon.get(f"{FILES}/share/{token}", params={"action": "preview"}).status_code == 200
    assert anon.get(f"{FILES}/share/{token}", params={"action": "preview"}).status_code == 403


def test_cleanup_requires_superuser(api, r6_user):
    resp = r6_user["client"].post(f"{FILES}/cleanup", json={})
    assert resp.status_code == 403, resp.text[:300]
    resp = api.post(f"{FILES}/cleanup", json={})
    assert resp.status_code == 200, resp.text[:300]


# ---------------------------------------------------------------------------
# item 3 — /me and /profile return real roles/permissions
# ---------------------------------------------------------------------------


def test_me_returns_real_roles_and_permissions(api):
    resp = api.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text[:300]
    me = resp.json()
    me = me.get("data") if isinstance(me, dict) and "data" in me else me
    roles = me.get("roles") or []
    permissions = me.get("permissions") or []
    role_codes = [r.get("code") if isinstance(r, dict) else r for r in roles]
    assert "admin" in role_codes, roles
    assert len(permissions) >= 45, f"admin should hold all seeded permissions, got {len(permissions)}"
    perm_codes = [p.get("code") if isinstance(p, dict) else p for p in permissions]
    assert "user:view" in perm_codes


def test_profile_returns_real_roles_and_permissions(api):
    resp = api.get("/api/v1/auth/profile")
    assert resp.status_code == 200, resp.text[:300]
    profile = resp.json()
    profile = profile.get("data") if isinstance(profile, dict) and "data" in profile else profile
    roles = profile.get("roles") or []
    permissions = profile.get("permissions") or []
    role_codes = [r.get("code") if isinstance(r, dict) else r for r in roles]
    assert "admin" in role_codes, roles
    assert len(permissions) >= 45


def test_low_priv_user_me_has_no_admin_role(r6_user):
    resp = r6_user["client"].get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text[:300]
    me = resp.json()
    me = me.get("data") if isinstance(me, dict) and "data" in me else me
    roles = me.get("roles") or []
    role_codes = [r.get("code") if isinstance(r, dict) else r for r in roles]
    assert "admin" not in role_codes, roles


# ---------------------------------------------------------------------------
# item 4 — traceability on real data
# ---------------------------------------------------------------------------


def test_traceability_matrix_with_real_link(api, linked_requirement):
    project = linked_requirement["project"]
    req = linked_requirement["requirement"]
    case = linked_requirement["case"]
    resp = api.post(
        f"{TRACE}/matrix",
        json={"project_id": project["id"], "matrix_type": "requirement_to_test", "include_indirect": False},
    )
    assert resp.status_code == 200, resp.text[:300]
    matrix = resp.json()
    text = str(matrix)
    assert str(req["id"]) in text, f"matrix lacks requirement {req['id']}: {text[:400]}"
    assert str(case["id"]) in text, f"matrix lacks case {case['id']}: {text[:400]}"


def test_impact_analysis_with_real_link(api, linked_requirement):
    req = linked_requirement["requirement"]
    case = linked_requirement["case"]
    resp = api.post(
        f"{TRACE}/impact-analysis",
        json={
            "requirement_id": req["id"],
            "change_description": "round-6 item-14 probe change",
            "analysis_depth": 3,
        },
    )
    assert resp.status_code == 200, resp.text[:300]
    result = resp.json()
    assert str(case["id"]) in str(result), f"impact misses linked case: {str(result)[:400]}"


def test_coverage_with_real_requirement(api, linked_requirement):
    project = linked_requirement["project"]
    resp = api.get(f"{TRACE}/coverage/{project['id']}")
    assert resp.status_code == 200, resp.text[:300]
    cov = resp.json()
    stats = cov.get("coverage_stats") or cov
    assert stats.get("total_requirements", 0) >= 1, cov
    assert stats.get("covered_requirements", 0) >= 1, cov
    assert stats.get("coverage_rate", 0) > 0, cov


# ---------------------------------------------------------------------------
# item 5 — recording pause/resume + recording permissions (API level;
# no UI button renders the pause control yet, so there is no honest
# click-through E2E for it — see the report)
# ---------------------------------------------------------------------------

MEETINGS = "/api/v1/meetings"


@pytest.fixture()
def live_recording(api):
    """A meeting with a RECORDING-state recording; stopped + deleted after."""
    title = f"r6-rec-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        f"{MEETINGS}/",
        json={
            "title": title,
            "meeting_type": "TEST_REVIEW",
            # 动态取未来时间：硬编码的日期会在当天稍后过期（曾因此 400）。
            "scheduled_start_time": (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            "scheduled_end_time": (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    meeting = body.get("data") or body
    meeting_id = meeting["id"]
    started = api.post(f"{MEETINGS}/{meeting_id}/start", json={"action": "start"})
    assert started.status_code in (200, 201), f"setup: start meeting failed: {started.status_code} {started.text[:300]}"
    start = api.post(f"{MEETINGS}/recordings/{meeting_id}/recordings/start", json={})
    assert start.status_code in (200, 201), f"setup: start recording failed: {start.status_code} {start.text[:300]}"
    rec = start.json()
    rec = rec.get("data") or rec
    recording_id = rec.get("id") or rec.get("recording_id")
    assert recording_id, f"setup: no recording id in {start.text[:200]}"
    yield {"meeting_id": meeting_id, "recording_id": recording_id}
    try:
        api.post(f"{MEETINGS}/recordings/{recording_id}/stop", json={})
    except Exception:
        pass
    try:
        api.delete(f"{MEETINGS}/{meeting_id}")
    except Exception:
        pass


def test_recording_pause_resume_cycle(api, live_recording):
    rid = live_recording["recording_id"]
    paused = api.post(f"{MEETINGS}/recordings/{rid}/pause", json={})
    assert paused.status_code == 200, paused.text[:300]
    body = paused.json()
    item = body.get("data") or body
    assert str(item.get("recording_status", item.get("status", ""))).upper() == "PAUSED", item
    # Repeat pause is invalid; resume works; repeat resume is invalid.
    assert api.post(f"{MEETINGS}/recordings/{rid}/pause", json={}).status_code == 400
    resumed = api.post(f"{MEETINGS}/recordings/{rid}/resume", json={})
    assert resumed.status_code == 200, resumed.text[:300]
    item = resumed.json()
    item = item.get("data") or item
    assert str(item.get("recording_status", item.get("status", ""))).upper() == "RECORDING", item
    assert api.post(f"{MEETINGS}/recordings/{rid}/resume", json={}).status_code == 400


def test_recording_pause_forbidden_for_other_user(api, live_recording, r6_user):
    rid = live_recording["recording_id"]
    resp = r6_user["client"].post(f"{MEETINGS}/recordings/{rid}/pause", json={})
    assert resp.status_code == 403, resp.text[:300]


def test_recording_permissions_endpoint(api, live_recording):
    resp = api.get(f"{MEETINGS}/{live_recording['meeting_id']}/recording-permissions")
    assert resp.status_code == 200, resp.text[:300]
    perms = resp.json()
    perms = perms.get("data") if isinstance(perms, dict) and "data" in perms else perms
    assert perms.get("canPause") is True, perms
    assert perms.get("canRecord") is True, perms
