"""Jitsi Meet 房间双端验证（2026-11-08，用户决定：音视频改走公开 meet.jit.si）。

MeetingRoom 的音视频层是 Jitsi iframe API 嵌入，房间名 meeting_{会议 code}。
本文件验证：嵌入能加载、能进房、有音视频（假媒体设备），以及两个浏览器
上下文进同一房间能互相看见（双端联调的自动化版）。

本系统外壳（参会人/聊天/文件/白板/录制）不在本文件验证范围——由
test_e2e_meeting_pages.py 与各 API 套件覆盖。

需要互联网（meet.jit.si）：不可达时整文件 skip，不静默改回自研 mesh。
"""

import os
import uuid
from urllib.parse import urlparse

import httpx
import pytest
from playwright.sync_api import expect

from e2e.helpers import ADMIN_PASSWORD, ADMIN_USER, FRONTEND_URL, login, uniq

pytestmark = pytest.mark.e2e

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"
SECOND_PASSWORD = "JitsiTest@123"


def _egress_proxy():
    """本机出站走 hatch-egress-proxy（环境变量里的 http(s)_proxy）。

    直接连会被拦截（SSL wrong version）；httpx 用 trust_env=True 时又会被
    no_proxy 里的 [::1] 搞坏 URL 解析——所以显式传 proxy，且 trust_env=False。
    凭证只从环境变量读，不写进文件。
    """
    raw = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    if not raw:
        return None
    u = urlparse(raw)
    proxy = {"server": f"{u.scheme}://{u.hostname}:{u.port}", "bypass": "localhost,127.0.0.1"}
    if u.username:
        proxy["username"] = u.username
    if u.password:
        proxy["password"] = u.password
    return proxy


def _jitsi_reachable() -> bool:
    raw = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    try:
        kwargs = {
            "timeout": 10,
            "trust_env": False,
            # 出站代理做 TLS 拦截，CA 在 SSL_CERT_FILE（curl 同款）；不用它会
            # CERTIFICATE_VERIFY_FAILED。httpx 默认的 certifi 不含该 CA。
            "verify": os.environ.get("SSL_CERT_FILE") or True,
        }
        if raw:
            kwargs["proxy"] = raw
        resp = httpx.get("https://meet.jit.si/external_api.js", **kwargs)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def _require_jitsi():
    if not _jitsi_reachable():
        pytest.skip("meet.jit.si 不可达，跳过 Jitsi 验证（不要静默改回自研 mesh）")


@pytest.fixture()
def jitsi_browser(pw):
    """Chromium with fake camera/mic so Jitsi can publish real (fake) tracks.

    出站经 egress proxy（见 _egress_proxy）：Chromium 默认直连会被拦截，
    必须显式传 proxy；localhost（:3000 开发服务）走 bypass。
    """
    proxy = _egress_proxy()
    kwargs = {
        "headless": True,
        "args": [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
        ],
    }
    if proxy:
        kwargs["proxy"] = proxy
    browser = pw.chromium.launch(**kwargs)
    yield browser
    browser.close()


@pytest.fixture()
def jitsi_meeting(api, make_project, request):
    """A started meeting; ended + deleted at teardown."""
    project = make_project()
    resp = api.post(
        f"/api/v1/meetings/projects/{project['id']}/meetings",
        json={
            "title": uniq("Jitsi验证会议"),
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
            "auto_invite_team": False,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create meeting failed: {resp.text[:300]}"
    meeting = resp.json()
    assert meeting.get("meeting_code"), f"setup: meeting has no code: {meeting}"
    started = api.post(f"/api/v1/meetings/{meeting['id']}/start", json={"action": "start"})
    assert started.status_code in (200, 201), f"setup: start meeting failed: {started.text[:300]}"

    def _cleanup():
        try:
            api.post(f"/api/v1/meetings/{meeting['id']}/end", json={"action": "end"})
        except Exception:
            pass
        try:
            api.delete(f"/api/v1/meetings/{meeting['id']}")
        except Exception:
            pass

    request.addfinalizer(_cleanup)
    return meeting


@pytest.fixture()
def jitsi_user(api, request):
    """A plain second user (no roles); deleted at teardown."""
    username = f"jitsi-user-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.com", "password": SECOND_PASSWORD},
    )
    assert resp.status_code in (200, 201), f"setup: create user failed: {resp.text[:300]}"
    user = resp.json()
    user_id = user.get("id") or user.get("user", {}).get("id")

    def _cleanup():
        try:
            api.delete(f"/api/v1/users/{user_id}")
        except Exception:
            pass

    request.addfinalizer(_cleanup)
    return {"id": user_id, "username": username, "password": SECOND_PASSWORD}


def _login(page, username, password):
    """UI login without assuming the dashboard shows 项目总数 (plain users may not)."""
    page.goto(f"{FRONTEND_URL}/login")
    page.locator("#username").fill(username)
    page.locator("#password").fill(password)
    page.get_by_role("button", name="登录", exact=True).click()
    page.wait_for_url(lambda url: "/login" not in url, timeout=20000)


def _join_jitsi_room(page, code):
    """Open the room page and wait until Jitsi reports videoConferenceJoined."""
    page.goto(f"{FRONTEND_URL}/meetings/join/{code}")
    expect(page.get_by_test_id("jitsi-container")).to_be_visible(timeout=20000)
    page.wait_for_function("() => window.__jitsiJoined === true", timeout=90000)


def _jitsi_state(page):
    return page.evaluate(
        """async () => {
        const api = window.__jitsiApi;
        if (!api) return null;
        const info = await api.getParticipantsInfo();
        return {
            participants: info.map((p) => p.displayName),
            audioMuted: api.isAudioMuted(),
            videoMuted: api.isVideoMuted(),
        };
    }"""
    )


def test_jitsi_single_end_joins_with_media(jitsi_browser, jitsi_meeting):
    """单端：嵌入加载、进房、假音视频轨道处于未静音（live）状态。"""
    context = jitsi_browser.new_context(
        viewport={"width": 1440, "height": 900},
        # 出站代理做 TLS 拦截，其 CA 不在 Chromium 的系统库里；测试上下文忽略证书错误。
        ignore_https_errors=True,
    )
    page = context.new_page()
    try:
        login(page)
        _join_jitsi_room(page, jitsi_meeting["meeting_code"])
        # iframe 确实来自 meet.jit.si，而不是本地占位。
        frame = page.frame_locator("iframe[src*='meet.jit.si']").first
        expect(frame.locator("body")).to_be_visible(timeout=30000)
        state = _jitsi_state(page)
        assert state is not None, "Jitsi API 未挂载到 window.__jitsiApi"
        assert len(state["participants"]) >= 1, f"房内无人: {state}"
        assert state["audioMuted"] is False, f"音频被静音（假麦克风未发布）: {state}"
        assert state["videoMuted"] is False, f"视频被静音（假摄像头未发布）: {state}"
    finally:
        context.close()


def test_jitsi_dual_end_same_room(jitsi_browser, jitsi_meeting, jitsi_user):
    """双端：两个浏览器上下文进同一 Jitsi 房间，互相看见对方。"""
    ctx_a = jitsi_browser.new_context(
        viewport={"width": 1440, "height": 900}, ignore_https_errors=True
    )
    ctx_b = jitsi_browser.new_context(
        viewport={"width": 1440, "height": 900}, ignore_https_errors=True
    )
    page_a = ctx_a.new_page()
    page_b = ctx_b.new_page()
    try:
        _login(page_a, ADMIN_USER, ADMIN_PASSWORD)
        _join_jitsi_room(page_a, jitsi_meeting["meeting_code"])
        _login(page_b, jitsi_user["username"], jitsi_user["password"])
        _join_jitsi_room(page_b, jitsi_meeting["meeting_code"])

        def _both_see_two():
            a = _jitsi_state(page_a)
            b = _jitsi_state(page_b)
            return (
                a is not None
                and b is not None
                and len(a["participants"]) >= 2
                and len(b["participants"]) >= 2
            )

        # 轮询双方的参与者列表，直到两边都看到 2 人（Jitsi 加入传播需几秒）。
        import time

        deadline = time.time() + 90
        last_a = last_b = None
        while time.time() < deadline:
            last_a = _jitsi_state(page_a)
            last_b = _jitsi_state(page_b)
            if (
                last_a
                and last_b
                and len(last_a["participants"]) >= 2
                and len(last_b["participants"]) >= 2
            ):
                break
            time.sleep(2)
        assert last_a and len(last_a["participants"]) >= 2, f"A 只看到 {last_a}"
        assert last_b and len(last_b["participants"]) >= 2, f"B 只看到 {last_b}"
        # 双方都处于未静音（假音视频 live）。
        assert last_a["audioMuted"] is False and last_a["videoMuted"] is False, last_a
        assert last_b["audioMuted"] is False and last_b["videoMuted"] is False, last_b
    finally:
        ctx_a.close()
        ctx_b.close()
