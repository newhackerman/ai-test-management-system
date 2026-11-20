"""Regression: ending a meeting must be idempotent.

User-reported 2026-11-20: clicking "结束会议" on an already-finished
meeting returned 400 "不能从状态 COMPLETED 转换到 COMPLETED".
`end_meeting` validated the COMPLETED -> COMPLETED transition against a
table where COMPLETED has no legal targets, instead of treating a
repeat end as a no-op success. Repeat ends happen in practice via the
room's emergency-end menu (which was not status-gated), double-clicks
on the confirm button, and stale page state.

Fix: `end_meeting` returns the meeting unchanged when it is already
COMPLETED (after the permission check, so non-organizers still get
403). These tests pin that behavior and the guard that stays:
ending a SCHEDULED meeting is still a 400.
"""

import pytest

pytestmark = pytest.mark.integration

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"


def _make_meeting(api, project_id, request):
    resp = api.post(
        f"/api/v1/meetings/projects/{project_id}/meetings",
        json={
            "title": "结束幂等回归会议",
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    meeting = resp.json()
    request.addfinalizer(lambda: api.delete(f"/api/v1/meetings/{meeting['id']}"))
    return meeting


def test_end_meeting_twice_is_idempotent(api, project, request):
    """End -> 200 COMPLETED; end again -> still 200, same end time."""
    meeting = _make_meeting(api, project["id"], request)
    mid = meeting["id"]

    resp = api.post(f"/api/v1/meetings/{mid}/start")
    assert resp.status_code == 200, f"start failed: {resp.text[:300]}"

    first = api.post(f"/api/v1/meetings/{mid}/end")
    assert first.status_code == 200, f"first end failed: {first.text[:300]}"
    assert first.json()["meeting_status"] == "COMPLETED"
    first_end_time = first.json()["data"]["actual_end_time"]
    assert first_end_time, "first end must record actual_end_time"

    second = api.post(f"/api/v1/meetings/{mid}/end")
    assert second.status_code == 200, (
        f"repeat end must be idempotent, got {second.status_code}: {second.text[:300]}"
    )
    assert second.json()["meeting_status"] == "COMPLETED"
    # The repeat end must not re-run the end flow: end time is untouched.
    assert second.json()["data"]["actual_end_time"] == first_end_time


def test_end_scheduled_meeting_still_rejected(api, project, request):
    """The transition guard stays for genuinely invalid ends."""
    meeting = _make_meeting(api, project["id"], request)
    mid = meeting["id"]

    resp = api.post(f"/api/v1/meetings/{mid}/end")
    assert resp.status_code == 400, f"end on SCHEDULED must be 400, got {resp.status_code}: {resp.text[:300]}"
    assert "SCHEDULED" in resp.text and "COMPLETED" in resp.text
