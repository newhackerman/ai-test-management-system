"""Meeting recordings API: global list, update, share, playback, download,
statistics, delete round-trip.

Covers the recording group's backend work (2026-11-08):
- GET /api/v1/meetings/recordings/all (global list; the old
  GET /api/v1/recordings never existed, bare /recordings was shadowed
  by GET /meetings/{meeting_id} -> 422)
- PUT /api/v1/meetings/recordings/{id} (rename / public / password)
- POST /{id}/share (previously 500: the route called a
  RecordingService.share_recording that did not exist)
- GET /{id}/playback (previously 500: response-model/envelope mismatch
  + uncaught ValidationError for non-COMPLETED recordings)
- GET /{id}/download (new; FileResponse, Bearer or playback token)
- GET /statistics (previously 422: registered after /{recording_id})

Fixture note: recordings are created through the real start endpoint on
an IN_PROGRESS meeting. In this headless VM ffmpeg cannot open X11 /
PulseAudio, so the record stays RECORDING (zombie ffmpeg, no file on
disk) and becomes FAILED after stop. Tests therefore assert the honest
behaviour for that state: playback -> 400, download -> 404. The
positive playback/download path (COMPLETED + real file) cannot be
produced here and is NOT faked; it is left unverified, see the report.
Created meetings/recordings are deleted in teardown.
"""

import pytest

from client import ApiClient
from config import BASE_URL

pytestmark = pytest.mark.integration

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"


def _make_meeting(api, project_id):
    resp = api.post(
        f"/api/v1/meetings/projects/{project_id}/meetings",
        json={
            "title": "录制测试会议",
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    return resp.json()


def _start_recording(api, meeting_id, name="录制测试"):
    resp = api.post(
        f"/api/v1/meetings/recordings/{meeting_id}/recordings/start",
        json={"recording_name": name, "recording_type": "FULL_MEETING", "file_format": "MP4"},
    )
    assert resp.status_code == 201, f"setup: start recording failed: {resp.text[:300]}"
    body = resp.json()
    return body.get("data") or body


@pytest.fixture(scope="module")
def rec_meeting(api, project):
    """One started meeting shared by the module's recording tests."""
    meeting = _make_meeting(api, project["id"])
    resp = api.post(f"/api/v1/meetings/{meeting['id']}/start")
    assert resp.status_code == 200, f"setup: start meeting failed: {resp.text[:300]}"
    yield meeting
    api.delete(f"/api/v1/meetings/{meeting['id']}")


@pytest.fixture()
def recording(api, rec_meeting):
    """One fresh recording; deleted (soft) at teardown, best-effort."""
    rec = _start_recording(api, rec_meeting["id"])
    yield rec
    try:
        api.delete(f"/api/v1/meetings/recordings/{rec['id']}")
    except Exception:
        pass


def _detail(api, recording_id):
    resp = api.get(f"/api/v1/meetings/recordings/{recording_id}")
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


# ---------------------------------------------------------------- global list

def test_global_list_contains_recording(api, recording):
    resp = api.get("/api/v1/meetings/recordings/all")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["total"] >= 1
    assert any(r["id"] == recording["id"] for r in body["recordings"])


def test_global_list_keyword_filter(api, recording):
    resp = api.get("/api/v1/meetings/recordings/all", params={"keyword": "录制测试"})
    assert resp.status_code == 200, resp.text[:300]
    assert any(r["id"] == recording["id"] for r in resp.json()["recordings"])

    resp = api.get("/api/v1/meetings/recordings/all", params={"keyword": "不存在的关键词-zzz"})
    assert resp.status_code == 200, resp.text[:300]
    assert all(r["id"] != recording["id"] for r in resp.json()["recordings"])


def test_global_list_status_filter(api, recording):
    resp = api.get("/api/v1/meetings/recordings/all", params={"status": "RECORDING"})
    assert resp.status_code == 200, resp.text[:300]
    assert any(r["id"] == recording["id"] for r in resp.json()["recordings"])

    resp = api.get("/api/v1/meetings/recordings/all", params={"status": "COMPLETED"})
    assert resp.status_code == 200, resp.text[:300]
    assert all(r["id"] != recording["id"] for r in resp.json()["recordings"])


def test_meeting_list(api, rec_meeting, recording):
    resp = api.get(f"/api/v1/meetings/recordings/{rec_meeting['id']}/recordings")
    assert resp.status_code == 200, resp.text[:300]
    assert any(r["id"] == recording["id"] for r in resp.json()["recordings"])

    resp = api.get("/api/v1/meetings/recordings/999999/recordings")
    assert resp.status_code == 404, resp.text[:300]


def test_statistics_reachable(api, rec_meeting, recording):
    resp = api.get("/api/v1/meetings/recordings/statistics")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["total_recordings"] >= 1
    assert body["by_type"].get("FULL_MEETING", 0) >= 1

    resp = api.get(
        "/api/v1/meetings/recordings/statistics",
        params={"meeting_id": rec_meeting["id"]},
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["total_recordings"] >= 1


# ---------------------------------------------------------------- detail/update

def test_detail_update_roundtrip(api, recording):
    rid = recording["id"]
    assert _detail(api, rid)["recording_name"] == "录制测试"

    resp = api.put(
        f"/api/v1/meetings/recordings/{rid}",
        json={"recording_name": "录制测试-改名", "is_public": True},
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["recording_name"] == "录制测试-改名"
    assert resp.json()["is_public"] is True

    # persisted, not just echoed
    assert _detail(api, rid)["recording_name"] == "录制测试-改名"
    assert _detail(api, rid)["is_public"] is True


def test_update_validation(api, recording):
    rid = recording["id"]
    resp = api.put(
        f"/api/v1/meetings/recordings/{rid}", json={"recording_name": "   "}
    )
    assert resp.status_code == 422, resp.text[:300]

    resp = api.put(
        "/api/v1/meetings/recordings/999999", json={"recording_name": "x"}
    )
    assert resp.status_code == 404, resp.text[:300]


def test_detail_unknown_and_anon(api, anon):
    resp = api.get("/api/v1/meetings/recordings/999999")
    assert resp.status_code == 404, resp.text[:300]

    resp = anon.get("/api/v1/meetings/recordings/1")
    assert resp.status_code == 401, resp.text[:300]


# ---------------------------------------------------------------- share

def test_share_roundtrip(api, recording):
    rid = recording["id"]
    resp = api.post(
        f"/api/v1/meetings/recordings/{rid}/share", json={"is_public": True}
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["success"] is True
    assert str(rid) in body["share_url"]
    assert body.get("share_code")

    assert _detail(api, rid)["is_public"] is True

    # private share without a password must be rejected (422)
    resp = api.post(
        f"/api/v1/meetings/recordings/{rid}/share", json={"is_public": False}
    )
    assert resp.status_code == 422, resp.text[:300]

    resp = api.post(
        f"/api/v1/meetings/recordings/{rid}/share",
        json={"is_public": False, "access_password": "pw123456"},
    )
    assert resp.status_code == 200, resp.text[:300]
    assert _detail(api, rid)["is_public"] is False


# ---------------------------------------------------------------- playback/download

def test_playback_not_completed_is_400(api, recording):
    # RECORDING (headless: no file yet) is honestly a 400, not a 500.
    resp = api.get(f"/api/v1/meetings/recordings/{recording['id']}/playback")
    assert resp.status_code == 400, resp.text[:300]
    assert "尚未完成" in resp.text


def test_playback_unknown_is_404(api):
    resp = api.get("/api/v1/meetings/recordings/999999/playback")
    assert resp.status_code == 404, resp.text[:300]


def test_download_no_file_is_404(api, recording):
    # Headless recording produced no file on disk: 404, never an empty file.
    resp = api.get(f"/api/v1/meetings/recordings/{recording['id']}/download")
    assert resp.status_code == 404, resp.text[:300]

    resp = api.get("/api/v1/meetings/recordings/999999/download")
    assert resp.status_code == 404, resp.text[:300]


def test_download_anon_and_bad_token(api, anon, recording):
    resp = anon.get(f"/api/v1/meetings/recordings/{recording['id']}/download")
    assert resp.status_code in (401, 403), resp.text[:300]

    resp = anon.get(
        f"/api/v1/meetings/recordings/{recording['id']}/download",
        params={"token": "badtoken"},
    )
    assert resp.status_code == 403, resp.text[:300]


# ---------------------------------------------------------------- delete

def test_delete_roundtrip(api, rec_meeting):
    rec = _start_recording(api, rec_meeting["id"], name="待删除录制")
    rid = rec["id"]
    resp = api.delete(f"/api/v1/meetings/recordings/{rid}")
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["success"] is True

    resp = api.get(f"/api/v1/meetings/recordings/{rid}")
    assert resp.status_code == 404, resp.text[:300]

    resp = api.delete(f"/api/v1/meetings/recordings/{rid}")
    assert resp.status_code == 404, resp.text[:300]
