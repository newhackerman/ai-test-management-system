"""Fixture-based tour for the implemented meeting pages.

These routes moved out of KNOWN_GAPS_PARAM (page_tour_routes.py) once
the 11 stub pages were implemented (2026-11-08): each needs a real
meeting (and, for recording detail/player, a real recording row) that
the static tour cannot invent. MeetingRoom stays in KNOWN_GAPS_PARAM:
it needs a live two-party meeting + media, which automation cannot
provide.

Fixture note: recordings are created through the real start endpoint
on an IN_PROGRESS meeting. In this headless VM ffmpeg cannot open X11 /
PulseAudio, so the record stays RECORDING (zombie ffmpeg, no file on
disk). Tests therefore assert the honest behaviour for that state:
detail renders the record + status badge; player renders the
unfinished-playback error state. The positive path (COMPLETED + real
file playing in <video>) cannot be produced here and is NOT faked.
"""

import re

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, assert_page_renders, uniq

pytestmark = pytest.mark.e2e

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"

ANALYTICS_PAGES = [
    ("/meetings/{id}/analytics", "整体效果评分"),
    ("/meetings/{id}/analytics/participation", "参与者明细"),
    ("/meetings/{id}/analytics/summary", "AI 会议摘要"),
    ("/meetings/{id}/analytics/minutes", "结构化会议纪要"),
    ("/meetings/{id}/analytics/actions", "行动项目管理"),
    ("/meetings/{id}/analytics/reports", "生成报告"),
]


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
def e2e_meeting(api, make_project, request):
    """A fresh meeting; deleted at teardown (ended first if started)."""
    project = make_project()
    meeting = _make_meeting(api, project["id"], uniq("巡游会议"))
    state = {"started": False}

    def _cleanup():
        try:
            if state["started"]:
                api.post(f"/api/v1/meetings/{meeting['id']}/end", json={"action": "end"})
        except Exception:
            pass
        try:
            api.delete(f"/api/v1/meetings/{meeting['id']}")
        except Exception:
            pass

    request.addfinalizer(_cleanup)
    meeting["_started"] = state
    return meeting


@pytest.fixture()
def e2e_recording(api, e2e_meeting, request):
    """A RECORDING-status recording on a started meeting.

    Returns (meeting, recording). The record never completes headless
    (no X11/PulseAudio), so tests assert the honest unfinished state.
    """
    meeting = e2e_meeting
    resp = api.post(f"/api/v1/meetings/{meeting['id']}/start")
    assert resp.status_code == 200, f"setup: start meeting failed: {resp.text[:300]}"
    meeting["_started"]["started"] = True
    name = uniq("巡游录制")
    resp = api.post(
        f"/api/v1/meetings/recordings/{meeting['id']}/recordings/start",
        json={"recording_name": name, "recording_type": "FULL_MEETING", "file_format": "MP4"},
    )
    assert resp.status_code == 201, f"setup: start recording failed: {resp.text[:300]}"
    rec = resp.json().get("data") or resp.json()
    rec["recording_name"] = name

    def _cleanup():
        try:
            api.delete(f"/api/v1/meetings/recordings/{rec['id']}")
        except Exception:
            pass

    request.addfinalizer(_cleanup)
    return meeting, rec


@pytest.mark.parametrize("path_tpl,marker", ANALYTICS_PAGES, ids=[p for p, _ in ANALYTICS_PAGES])
def test_meeting_analytics_pages(logged_in_page, e2e_meeting, path_tpl, marker):
    """Each analytics page renders its real content (no placeholder)."""
    path = path_tpl.format(id=e2e_meeting["id"])
    assert_page_renders(logged_in_page, path, marker=marker)


def test_meeting_recordings_list(logged_in_page, e2e_meeting):
    """Per-meeting recording list renders (empty state, no recordings)."""
    assert_page_renders(
        logged_in_page, f"/meetings/{e2e_meeting['id']}/recordings", marker="暂无录制"
    )


def test_meeting_detail_and_edit(logged_in_page, e2e_meeting):
    """Meeting detail shows the meeting title; edit form renders."""
    assert_page_renders(
        logged_in_page, f"/meetings/{e2e_meeting['id']}", marker=e2e_meeting["title"]
    )
    assert_page_renders(logged_in_page, f"/meetings/{e2e_meeting['id']}/edit")


def test_recording_detail(logged_in_page, e2e_recording):
    """Recording detail shows the record name and its status badge."""
    _, rec = e2e_recording
    assert_page_renders(
        logged_in_page,
        f"/meetings/recordings/{rec['id']}",
        marker=rec["recording_name"],
    )


def test_recording_player_unfinished(logged_in_page, e2e_recording):
    """Player on an unfinished recording shows the honest error state.

    Deliberately NOT assert_page_renders: GET /playback returns 400 by
    design for non-COMPLETED recordings, and the tour's error collector
    treats any >= 400 API response as a failure. Here the 400 IS the
    behaviour under test, so assert the rendered error text instead.
    """
    _, rec = e2e_recording
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/meetings/recordings/{rec['id']}/player")
    page.wait_for_load_state("load")
    expect(page.get_by_text("仅已完成的录制可以播放")).to_be_visible(timeout=20000)
    expect(
        page.get_by_text(re.compile(r"录制尚未完成处理|无法播放该录制")).first
    ).to_be_visible(timeout=20000)
    expect(page.get_by_role("link", name="返回录制详情")).to_be_visible(timeout=20000)
