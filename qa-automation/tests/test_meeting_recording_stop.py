"""Meeting end auto-stops recordings + stop works on paused recordings.

Regression tests for the user-reported bug (2026-11-20): "会议结束后，也
无法终止录制". Root causes fixed on branch fix/meetings-20261120:

- MeetingService._stop_all_recordings was a log-only stub (defined twice,
  the later definition shadowing the earlier); end/cancel never stopped
  anything. Now end_meeting/cancel_meeting call
  RecordingService.stop_all_recordings_for_meeting, which stops every
  RECORDING/PAUSED recording of the meeting (PAUSED ones are resumed
  first) in an independent session.
- RecordingService.stop_recording rejected PAUSED recordings with
  "录制未在进行中", so a paused recording had no way to be stopped at
  all (the room's stop button calls the same endpoint). It now resumes
  a PAUSED recording first, then stops it.

Fixture note: recordings are created through the real start endpoint on
an IN_PROGRESS meeting. In this headless VM ffmpeg cannot open X11 /
PulseAudio, so the record stays RECORDING (zombie ffmpeg, no file on
disk) and becomes FAILED after stop (post-processing finds no file).
Tests therefore assert the honest behaviour for that state: after the
stop, status is no longer RECORDING/PAUSED. The positive path
(PROCESSING -> COMPLETED with a real file) cannot be produced here and
is NOT faked.

Each test uses its own meeting (ending a meeting is terminal for the
fixture). Created meetings/recordings are deleted in teardown,
best-effort.
"""

import time

import pytest

pytestmark = pytest.mark.integration

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"


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


def _start_meeting(api, meeting_id):
    resp = api.post(f"/api/v1/meetings/{meeting_id}/start")
    assert resp.status_code == 200, f"setup: start meeting failed: {resp.text[:300]}"


def _start_recording(api, meeting_id, name="录制停止测试"):
    resp = api.post(
        f"/api/v1/meetings/recordings/{meeting_id}/recordings/start",
        json={"recording_name": name, "recording_type": "FULL_MEETING", "file_format": "MP4"},
    )
    assert resp.status_code == 201, f"setup: start recording failed: {resp.text[:300]}"
    body = resp.json()
    return body.get("data") or body


def _recording_status(api, recording_id):
    resp = api.get(f"/api/v1/meetings/recordings/{recording_id}")
    assert resp.status_code == 200, f"get recording failed: {resp.text[:300]}"
    return resp.json().get("recording_status")


def _wait_status_left(api, recording_id, statuses, timeout=10.0):
    """Poll until the recording leaves `statuses` (post-processing is async).

    Returns the last observed status. Raises if it is still in `statuses`
    after the timeout.
    """
    deadline = time.time() + timeout
    status = None
    while time.time() < deadline:
        status = _recording_status(api, recording_id)
        if status not in statuses:
            return status
        time.sleep(0.5)
    raise AssertionError(
        f"recording {recording_id} still {status} after {timeout}s (expected to leave {statuses})"
    )


@pytest.fixture()
def live_meeting(api, project):
    """One started meeting; deleted at teardown (best-effort)."""
    meeting = _make_meeting(api, project["id"], "录制停止测试会议")
    _start_meeting(api, meeting["id"])
    yield meeting
    try:
        api.delete(f"/api/v1/meetings/{meeting['id']}")
    except Exception:
        pass


def _cleanup_recording(api, recording_id):
    try:
        api.delete(f"/api/v1/meetings/recordings/{recording_id}")
    except Exception:
        pass


def test_end_meeting_auto_stops_active_recording(api, live_meeting):
    """Bug 2 core: ending the meeting stops its RECORDING recording."""
    rec = _start_recording(api, live_meeting["id"])
    assert _recording_status(api, rec["id"]) == "RECORDING"
    try:
        resp = api.post(f"/api/v1/meetings/{live_meeting['id']}/end")
        assert resp.status_code == 200, f"end meeting failed: {resp.text[:300]}"
        status = _wait_status_left(api, rec["id"], {"RECORDING"})
        assert status in ("PROCESSING", "FAILED", "COMPLETED"), f"unexpected status: {status}"
    finally:
        _cleanup_recording(api, rec["id"])


def test_end_meeting_auto_stops_paused_recording(api, live_meeting):
    """Ending the meeting also stops a PAUSED recording (resume then stop)."""
    rec = _start_recording(api, live_meeting["id"])
    resp = api.post(f"/api/v1/meetings/recordings/{rec['id']}/pause")
    assert resp.status_code == 200, f"pause failed: {resp.text[:300]}"
    assert _recording_status(api, rec["id"]) == "PAUSED"
    try:
        resp = api.post(f"/api/v1/meetings/{live_meeting['id']}/end")
        assert resp.status_code == 200, f"end meeting failed: {resp.text[:300]}"
        status = _wait_status_left(api, rec["id"], {"RECORDING", "PAUSED"})
        assert status in ("PROCESSING", "FAILED", "COMPLETED"), f"unexpected status: {status}"
    finally:
        _cleanup_recording(api, rec["id"])


def test_stop_paused_recording_via_api(api, live_meeting):
    """The stop endpoint accepts a PAUSED recording (previously 400)."""
    rec = _start_recording(api, live_meeting["id"])
    resp = api.post(f"/api/v1/meetings/recordings/{rec['id']}/pause")
    assert resp.status_code == 200, f"pause failed: {resp.text[:300]}"
    try:
        resp = api.post(f"/api/v1/meetings/recordings/{rec['id']}/stop")
        assert resp.status_code == 200, f"stop paused recording failed: {resp.text[:300]}"
        status = _wait_status_left(api, rec["id"], {"RECORDING", "PAUSED"})
        assert status in ("PROCESSING", "FAILED", "COMPLETED"), f"unexpected status: {status}"
    finally:
        _cleanup_recording(api, rec["id"])


def test_stop_recording_while_meeting_in_progress(api, live_meeting):
    """Manual stop (the list/detail page button's API) works while live."""
    rec = _start_recording(api, live_meeting["id"])
    try:
        resp = api.post(f"/api/v1/meetings/recordings/{rec['id']}/stop")
        assert resp.status_code == 200, f"stop failed: {resp.text[:300]}"
        status = _wait_status_left(api, rec["id"], {"RECORDING"})
        assert status in ("PROCESSING", "FAILED", "COMPLETED"), f"unexpected status: {status}"
    finally:
        _cleanup_recording(api, rec["id"])
