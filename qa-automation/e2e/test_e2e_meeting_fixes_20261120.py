"""E2E for the 2026-11-20 meeting fixes + project priority colours.

Covers the frontend half of the user-reported bugs (branch
fix/meetings-20261120):

- Bug 2: recording list / detail now have a stop button for RECORDING
  (and PAUSED) recordings, so a recording can be stopped after leaving
  the room or after the meeting ended. The list test clicks it for real
  (accepting the confirm dialog) and asserts the button disappears and
  the recording leaves RECORDING.
- Bug 3: meeting detail shows the full join link and a copy button
  ("复制会议链接"); previously generateMeetingLink had zero callers and
  no page showed the link at all.
- Project list: priority is now a coloured Badge per level (URGENT red,
  HIGH orange, MEDIUM amber, LOW green) instead of plain text.

Fixture note: recordings are created through the real start endpoint on
an IN_PROGRESS meeting. Headless ffmpeg cannot capture, so the record
stays RECORDING until stopped and becomes FAILED after stop (no file).
Tests assert the honest behaviour for that state.
"""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, uniq

pytestmark = pytest.mark.e2e

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
            "auto_invite_team": False,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    return resp.json()


@pytest.fixture()
def fx_meeting(api, make_project, request):
    """A fresh (not started) meeting; deleted at teardown."""
    project = make_project()
    meeting = _make_meeting(api, project["id"], uniq("修复验证会议"))
    request.addfinalizer(lambda: api.delete(f"/api/v1/meetings/{meeting['id']}"))
    return meeting


@pytest.fixture()
def fx_recording(api, fx_meeting, request):
    """A RECORDING-status recording on a started meeting.

    Returns (meeting, recording). The meeting is ended at teardown
    (which now also auto-stops any recording still running).
    """
    meeting = fx_meeting
    resp = api.post(f"/api/v1/meetings/{meeting['id']}/start")
    assert resp.status_code == 200, f"setup: start meeting failed: {resp.text[:300]}"
    name = uniq("修复验证录制")
    resp = api.post(
        f"/api/v1/meetings/recordings/{meeting['id']}/recordings/start",
        json={"recording_name": name, "recording_type": "FULL_MEETING", "file_format": "MP4"},
    )
    assert resp.status_code == 201, f"setup: start recording failed: {resp.text[:300]}"
    rec = resp.json().get("data") or resp.json()
    rec["recording_name"] = name

    def _cleanup():
        try:
            api.post(f"/api/v1/meetings/{meeting['id']}/end", json={"action": "end"})
        except Exception:
            pass
        try:
            api.delete(f"/api/v1/meetings/recordings/{rec['id']}")
        except Exception:
            pass

    request.addfinalizer(_cleanup)
    return meeting, rec


def test_meeting_detail_shows_copy_link_and_url(logged_in_page, fx_meeting):
    """Bug 3: detail page shows the join link text + a copy button."""
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/meetings/{fx_meeting['id']}")
    expect(page.get_by_role("button", name="复制会议链接")).to_be_visible(timeout=15000)
    # The full link is rendered as text (not just behind the button).
    expect(page.get_by_text("/meetings/join/", exact=False).first).to_be_visible(timeout=15000)


def test_recording_list_stop_button_stops_recording(api, logged_in_page, fx_recording):
    """Bug 2: the list stop button really stops the recording."""
    meeting, rec = fx_recording
    page = logged_in_page
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(f"{FRONTEND_URL}/meetings/{meeting['id']}/recordings")
    expect(page.get_by_text(rec["recording_name"])).to_be_visible(timeout=15000)
    stop_btn = page.locator('button[title="停止录制"]')
    expect(stop_btn).to_have_count(1, timeout=15000)
    stop_btn.click()
    # After stopping, the row leaves RECORDING, so the button disappears.
    expect(stop_btn).to_have_count(0, timeout=20000)
    resp = api.get(f"/api/v1/meetings/recordings/{rec['id']}")
    assert resp.status_code == 200
    assert resp.json().get("recording_status") not in ("RECORDING", "PAUSED")


def test_recording_detail_shows_stop_button(logged_in_page, fx_recording):
    """Bug 2: the detail page also offers a stop button while recording."""
    _, rec = fx_recording
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/meetings/recordings/{rec['id']}")
    expect(page.get_by_role("button", name="停止录制")).to_be_visible(timeout=15000)


def test_project_list_priority_badge_colored(api, logged_in_page, make_project):
    """Project list: URGENT priority shows as a red Badge, not plain text."""
    project = make_project(priority="URGENT")
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/projects")
    row = page.locator("tr", has_text=project["project_name"])
    expect(row).to_have_count(1, timeout=15000)
    badge = row.locator(".bg-red-100")
    expect(badge).to_have_count(1, timeout=5000)
    expect(badge).to_contain_text("紧急")
