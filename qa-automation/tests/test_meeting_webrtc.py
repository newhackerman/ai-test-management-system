"""MeetingRoom / WebRTC: config endpoint, room lifecycle, signaling.

Covers the fixes for the MeetingRoom page:
- GET /webrtc/config no longer 500s (WebRTCService.get_webrtc_config
  was missing) and returns the deterministic room_id room_{meeting_id}.
- WS join no longer closes 1011 "room does not exist": the WS entry
  get-or-creates the room before joining, and rooms + WS connections
  are shared across requests (per-request service instances used to
  isolate each connection, so two-party signaling could never arrive).
- Chat send/history round-trip (MeetingService.send_chat_message was
  missing -> 500), whiteboard draw/state round-trip
  (handle_whiteboard_action was missing -> 500), file upload/list,
  screen-share start/stop with a live WS session, and the offer/answer/
  ice-candidate forwarding loop between two connected clients.

Fixtures follow test_meeting_integration.py: one module project, one
meeting, one plain second user. Everything created here is deleted in
teardown (meeting, project, second user).

Note: POST /participants currently returns 500 even though the row is
created (ParticipantResponse.from_orm lazy-loads expired attributes
outside the async greenlet -> MissingGreenlet). That is a pre-existing
participant-routes bug, out of scope here; the fixture accepts the 500
and verifies the row via GET /participants instead.
"""

import json
import uuid

import pytest
import websocket

from client import ApiClient
from config import BASE_URL

pytestmark = pytest.mark.integration

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"
PASSWORD = "TEST@test1"


def _make_meeting(api, project_id):
    resp = api.post(
        f"/api/v1/meetings/projects/{project_id}/meetings",
        json={
            "title": "WebRTC 探针会议",
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    return resp.json()


def _make_plain_user(api):
    username = f"mr-user-{uuid.uuid4().hex[:8]}"
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


@pytest.fixture(scope="module")
def wr_project(api):
    import factories
    from assertions import assert_envelope_ok

    resp = api.post("/api/v1/projects", json=factories.project_payload())
    proj = assert_envelope_ok(resp, "project")
    yield proj
    try:
        api.delete(f"/api/v1/projects/{proj['id']}")
    except Exception:
        pass


@pytest.fixture(scope="module")
def wr_meeting(api, wr_project):
    meeting = _make_meeting(api, wr_project["id"])
    yield meeting
    try:
        api.delete(f"/api/v1/meetings/{meeting['id']}")
    except Exception:
        pass


@pytest.fixture(scope="module")
def wr_second(api, wr_project, wr_meeting):
    """Plain user, project member, meeting participant (row verified via GET)."""
    user = _make_plain_user(api)
    resp = api.post(
        f"/api/v1/projects/{wr_project['id']}/members",
        json={"user_id": user["id"], "role_in_project": "DEVELOPER", "join_date": "2026-11-05"},
    )
    assert resp.status_code in (200, 201), f"setup: add member failed: {resp.text[:300]}"
    api.post(
        f"/api/v1/meetings/{wr_meeting['id']}/participants",
        json={"user_id": user["id"], "participant_role": "PARTICIPANT"},
    )
    # POST /participants returns 500 on response serialization (pre-existing
    # bug) but the row is created; verify it is listed.
    listed = api.get(f"/api/v1/meetings/{wr_meeting['id']}/participants")
    assert listed.status_code == 200
    assert any(p.get("user_id") == user["id"] for p in listed.json().get("participants", [])), (
        "setup: second user not in participant list"
    )
    yield user
    try:
        api.delete(f"/api/v1/users/{user['id']}")
    except Exception:
        pass


@pytest.fixture(scope="module")
def wr_outsider(api):
    user = _make_plain_user(api)
    yield user
    try:
        api.delete(f"/api/v1/users/{user['id']}")
    except Exception:
        pass


def _ws_url(meeting_id, token):
    base = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
    return f"{base}/api/v1/meetings/{meeting_id}/webrtc/ws?token={token}"


def _connect(meeting_id, token, timeout=5):
    ws = websocket.create_connection(_ws_url(meeting_id, token), timeout=timeout)
    return ws


def _recv_json(ws, timeout=5):
    ws.settimeout(timeout)
    return json.loads(ws.recv())


# ---------------------------------------------------------------- config

def test_webrtc_config_ok(api, wr_meeting):
    mid = wr_meeting["id"]
    resp = api.get(f"/api/v1/meetings/{mid}/webrtc/config")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["ice_servers"], "config must carry at least one ICE server"
    assert body["room_config"]["room_id"] == f"room_{mid}"
    assert body["media_constraints"]["audio"]["echoCancellation"] is True
    assert body["session_config"]["heartbeat_interval"] == 30


def test_webrtc_config_unknown_meeting_404(api):
    resp = api.get("/api/v1/meetings/999999/webrtc/config")
    assert resp.status_code == 404


def test_get_meeting_by_code_ok(api, wr_meeting):
    resp = api.get(f"/api/v1/meetings/code/{wr_meeting['meeting_code']}")
    assert resp.status_code == 200, resp.text[:200]
    assert resp.json()["id"] == wr_meeting["id"]


def test_get_meeting_by_code_unknown_404(api):
    resp = api.get("/api/v1/meetings/code/NOPE1234")
    assert resp.status_code == 404


def test_webrtc_config_anon_401(anon):
    resp = anon.get("/api/v1/meetings/1/webrtc/config")
    assert resp.status_code == 401


# ---------------------------------------------------------------- REST signaling

def test_offer_unknown_session_404(api, wr_meeting):
    resp = api.post(
        f"/api/v1/meetings/{wr_meeting['id']}/webrtc/offer",
        json={"session_id": "no-such-session", "sdp": "v=0"},
    )
    assert resp.status_code == 404, resp.text[:200]


def test_ice_unknown_session_404(api, wr_meeting):
    resp = api.post(
        f"/api/v1/meetings/{wr_meeting['id']}/webrtc/ice",
        json={"session_id": "no-such-session", "candidate": "candidate:1"},
    )
    assert resp.status_code == 404, resp.text[:200]


def test_media_control_unknown_session_404(api, wr_meeting):
    resp = api.post(
        f"/api/v1/meetings/{wr_meeting['id']}/webrtc/media-control",
        json={"session_id": "no-such-session", "media_type": "audio", "action": "mute"},
    )
    assert resp.status_code == 404, resp.text[:200]


# ---------------------------------------------------------------- chat

def test_chat_send_and_history_roundtrip(api, wr_meeting):
    mid = wr_meeting["id"]
    content = f"webrtc probe {uuid.uuid4().hex[:8]}"
    resp = api.post(
        f"/api/v1/meetings/{mid}/chat/send",
        json={"content": content, "message_type": "TEXT"},
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["data"]["content"] == content

    history = api.get(f"/api/v1/meetings/{mid}/chat/history")
    assert history.status_code == 200
    assert any(m["content"] == content for m in history.json()["messages"])


# ---------------------------------------------------------------- whiteboard

def test_whiteboard_draw_and_state_roundtrip(api, wr_meeting):
    mid = wr_meeting["id"]
    stroke_id = f"s-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        f"/api/v1/meetings/{mid}/whiteboard/action",
        json={"action_type": "draw", "user_id": 1, "data": {"id": stroke_id, "points": [[0, 0], [10, 10]]}},
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["data"]["content"]["strokes"][-1]["id"] == stroke_id

    state = api.get(f"/api/v1/meetings/{mid}/whiteboard/state")
    assert state.status_code == 200
    assert any(s.get("id") == stroke_id for s in state.json()["content"].get("strokes", []))


def test_whiteboard_unknown_action_400(api, wr_meeting):
    resp = api.post(
        f"/api/v1/meetings/{wr_meeting['id']}/whiteboard/action",
        json={"action_type": "bogus", "user_id": 1, "data": {}},
    )
    assert resp.status_code == 400, resp.text[:200]


# ---------------------------------------------------------------- files

def test_file_upload_and_list(api, wr_meeting):
    mid = wr_meeting["id"]
    name = f"webrtc-probe-{uuid.uuid4().hex[:8]}.txt"
    resp = api._client.post(
        f"/api/v1/meetings/{mid}/files/upload",
        files={"file": (name, b"hello meeting file\n", "text/plain")},
        data={"is_public": "true"},
        headers=api.auth_headers(),
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["data"]["file_name"] == name

    listing = api.get(f"/api/v1/meetings/{mid}/files")
    assert listing.status_code == 200
    assert any(f["file_name"] == name for f in listing.json()["files"])


# ---------------------------------------------------------------- WS single client

def test_ws_join_and_ping_pong(api, wr_meeting):
    mid = wr_meeting["id"]
    ws = _connect(mid, api.access_token)
    try:
        joined = _recv_json(ws)
        assert joined["type"] == "room-joined"
        assert joined["room_id"] == f"room_{mid}"
        assert joined["session_id"].startswith("session_")
        ws.send(json.dumps({"type": "ping"}))
        pong = _recv_json(ws)
        assert pong["type"] == "pong"
    finally:
        ws.close()


def test_ws_invalid_token_rejected(api, wr_meeting):
    with pytest.raises(websocket.WebSocketBadStatusException):
        _connect(wr_meeting["id"], "definitely-not-a-token")


def test_ws_outsider_rejected(api, wr_meeting, wr_outsider):
    # Valid token, no access to the meeting: handshake must be rejected
    # (HTTP 403 before accept) instead of joining the room.
    with pytest.raises(websocket.WebSocketBadStatusException):
        _connect(wr_meeting["id"], wr_outsider["client"].access_token)


# ---------------------------------------------------------------- WS two-party signaling

def test_ws_two_party_signaling(api, wr_meeting, wr_second):
    mid = wr_meeting["id"]
    ws_a = _connect(mid, api.access_token)
    ws_b = _connect(mid, wr_second["client"].access_token)
    try:
        joined_a = _recv_json(ws_a)
        assert joined_a["type"] == "room-joined"
        joined_b = _recv_json(ws_b)
        assert joined_b["type"] == "room-joined"
        # B sees A already in the room; A is told B joined.
        assert any(p["user_id"] == 1 for p in joined_b["participants"])
        seen = _recv_json(ws_a)
        assert seen["type"] == "participant-joined"
        assert seen["user_id"] == wr_second["id"]

        # offer A -> B
        ws_a.send(json.dumps({
            "type": "offer",
            "target_user_id": wr_second["id"],
            "sdp": {"type": "offer", "sdp": "v=0 fake-offer"},
        }))
        offer = _recv_json(ws_b)
        assert offer["type"] == "offer"
        assert offer["from_user_id"] == 1
        assert offer["sdp"]["sdp"] == "v=0 fake-offer"

        # answer B -> A
        ws_b.send(json.dumps({
            "type": "answer",
            "target_user_id": 1,
            "sdp": {"type": "answer", "sdp": "v=0 fake-answer"},
        }))
        answer = _recv_json(ws_a)
        assert answer["type"] == "answer"
        assert answer["from_user_id"] == wr_second["id"]

        # ICE B -> A
        ws_b.send(json.dumps({
            "type": "ice-candidate",
            "target_user_id": 1,
            "candidate": "candidate:1 1 udp 1 1.2.3.4 5000 typ host",
        }))
        ice = _recv_json(ws_a)
        assert ice["type"] == "ice-candidate"
        assert ice["candidate"].startswith("candidate:1")
    finally:
        ws_a.close()
        ws_b.close()


# ---------------------------------------------------------------- screen share (needs a live WS session)

def test_screen_share_start_stop_with_live_session(api, wr_meeting):
    mid = wr_meeting["id"]
    ws = _connect(mid, api.access_token)
    try:
        joined = _recv_json(ws)
        session_id = joined["session_id"]
        start = api.post(
            f"/api/v1/meetings/{mid}/screen-share/start",
            json={"session_id": session_id, "share_type": "screen"},
        )
        assert start.status_code == 200, start.text[:300]
        share_id = start.json()["share_id"]
        assert share_id.startswith("screen_")

        stop = api.post(
            f"/api/v1/meetings/{mid}/screen-share/stop",
            json={"session_id": session_id, "share_id": share_id},
        )
        assert stop.status_code == 200, stop.text[:200]
    finally:
        ws.close()


def test_screen_share_unknown_session_404(api, wr_meeting):
    resp = api.post(
        f"/api/v1/meetings/{wr_meeting['id']}/screen-share/start",
        json={"session_id": "no-such-session", "share_type": "screen"},
    )
    assert resp.status_code == 404, resp.text[:200]
