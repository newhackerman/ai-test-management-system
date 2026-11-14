"""Meeting analytics backend: LLM-backed summary/minutes, analytics
persistence, action-items CRUD, report generate+download.

LLM mock: a local stub OpenAI-compatible server (127.0.0.1:18099).
A module-scoped fixture temporarily points the backend at it by
overriding OPENAI_API_KEY/OPENAI_BASE_URL in backend/.env — the
assistant service re-reads .env on every LLM call, so no backend
restart is needed — and restores the original .env byte-for-byte
afterwards. No real API call is ever made in this suite.

The stub records every prompt, so tests assert the prompt contains
real meeting context (title/agenda/chat) and none of the old canned
strings, and that generate -> GET round-trips read persisted rows.
"""

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from assertions import assert_status
from client import ApiClient
from config import BASE_URL

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = REPO_ROOT / "backend" / ".env"
STUB_PORT = 18099
STUB_BASE_URL = f"http://127.0.0.1:{STUB_PORT}"

MEETING_START = "2026-12-01T10:00:00"
MEETING_END = "2026-12-01T11:00:00"

# The stub's fixed LLM reply: plausible content built from the real
# fixture context (login-module sync + payment-module testing).
STUB_SUMMARY = {
    "overview": "本次会议围绕登录模块联调进展展开：登录模块联调已完成，明确下周启动支付模块测试。",
    "key_points": [
        {"title": "登录模块联调完成", "content": "登录模块联调已完成", "importance": 4},
        {"title": "下周启动支付模块测试", "content": "下周开始做支付模块的测试", "importance": 4},
    ],
    "decisions": [
        {
            "title": "下周启动支付模块测试",
            "description": "下周开始做支付模块的测试",
            "decision_maker": "系统管理员",
            "impact_level": "medium",
        }
    ],
    "action_items": [
        {
            "title": "启动支付模块测试",
            "description": "下周开始做支付模块的测试",
            "assignee": None,
            "due_date": None,
            "priority": "high",
        }
    ],
    "next_steps": ["启动支付模块测试"],
}

# Canned strings the old implementation hardcoded; they must never
# appear in a prompt sent to the LLM nor in a generated summary.
CANNED_STRINGS = [
    "项目进展顺利",
    "预计下周完成第一阶段",
    "需要增加人力资源",
    "增加2名开发人员",
    "完成需求文档",
    "这是一个关于项目进展的会议",
    "大家好，今天我们讨论项目进展情况",
    "项目目前进展顺利",
]


class _StubState:
    requests: list = []


class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            payload = {}
        _StubState.requests.append(payload)
        content = json.dumps(STUB_SUMMARY, ensure_ascii=False)
        resp = {
            "id": "chatcmpl-stub",
            "object": "chat.completion",
            "created": 1,
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        data = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


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
def llm_stub():
    """Run the stub OpenAI server and point the backend at it via .env."""
    _StubState.requests.clear()
    server = ThreadingHTTPServer(("127.0.0.1", STUB_PORT), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original = BACKEND_ENV.read_bytes()
    try:
        _set_env_keys(
            BACKEND_ENV,
            {"OPENAI_API_KEY": "test-dummy-key", "OPENAI_BASE_URL": STUB_BASE_URL},
        )
        yield server
    finally:
        BACKEND_ENV.write_bytes(original)
        server.shutdown()
        server.server_close()


def _prompts_text() -> str:
    chunks = []
    for req in _StubState.requests:
        for msg in req.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(part.get("text", "") for part in content)
            chunks.append(str(content))
    return "\n".join(chunks)


def _make_meeting(api, project_id, title="分析测试会议"):
    resp = api.post(
        f"/api/v1/meetings/projects/{project_id}/meetings",
        json={
            "title": title,
            "description": "登录模块联调进度同步",
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": MEETING_START,
            "scheduled_end_time": MEETING_END,
            "agenda": [
                {"title": "登录模块联调进展", "duration_minutes": 30, "order": 1},
                {"title": "支付模块测试计划", "duration_minutes": 30, "order": 2},
            ],
        },
    )
    assert_status(resp, 200, "setup: create meeting")
    return resp.json()


@pytest.fixture()
def meeting(api, project, request):
    m = _make_meeting(api, project["id"], title=f"分析测试会议-{uuid.uuid4().hex[:6]}")
    request.addfinalizer(lambda: api.delete(f"/api/v1/meetings/{m['id']}"))
    return m


@pytest.fixture()
def meeting_with_chat(api, meeting):
    resp = api.post(
        f"/api/v1/meetings/{meeting['id']}/chat/send",
        json={"content": "本周完成了登录模块的联调，下周开始做支付模块的测试。"},
    )
    assert_status(resp, 200, "setup: send chat")
    return meeting


def test_summary_generate_then_get_reads_persisted(api, llm_stub, meeting_with_chat):
    mid = meeting_with_chat["id"]
    before = len(_StubState.requests)
    resp = api.post(f"/api/v1/meetings/{mid}/summary/generate", json={})
    assert_status(resp, 200, "summary generate")
    data = resp.json()["data"]
    assert data["overview"] == STUB_SUMMARY["overview"]
    assert data["meeting_id"] == mid
    assert [k["title"] for k in data["key_points"]] == ["登录模块联调完成", "下周启动支付模块测试"]
    assert data["decisions"][0]["title"] == "下周启动支付模块测试"
    assert data["action_items"][0]["title"] == "启动支付模块测试"
    assert data["generation_method"] == "llm"

    # The LLM was really called (stub saw a new request), and the prompt
    # carried real context, not canned text.
    assert len(_StubState.requests) > before, "stub LLM was not called"
    prompt = _prompts_text()
    assert meeting_with_chat["title"] in prompt
    assert "登录模块联调" in prompt
    assert "本周完成了登录模块的联调" in prompt
    assert "不得编造" in prompt
    for canned in CANNED_STRINGS:
        assert canned not in prompt, f"canned string in prompt: {canned}"
        assert canned not in data["overview"]

    # GET reads the persisted row (no longer an empty placeholder).
    resp = api.get(f"/api/v1/meetings/{mid}/summary")
    assert_status(resp, 200, "summary get")
    assert resp.json()["overview"] == STUB_SUMMARY["overview"]
    assert resp.json()["key_points"][0]["title"] == "登录模块联调完成"


def test_summary_generate_unknown_meeting_404(api, llm_stub):
    resp = api.post("/api/v1/meetings/999999/summary/generate", json={})
    assert_status(resp, 404, "summary generate unknown meeting")


def test_minutes_generate_then_get_reads_persisted(api, llm_stub, meeting_with_chat):
    mid = meeting_with_chat["id"]
    resp = api.post(f"/api/v1/meetings/{mid}/minutes/generate", json={})
    assert_status(resp, 200, "minutes generate")
    data = resp.json()["data"]
    assert data["meeting_id"] == mid
    assert data["id"]
    assert data["title"].startswith(meeting_with_chat["title"])
    assert "无转录文本" in data["content"]
    assert data["summary"] == STUB_SUMMARY["overview"]
    assert data["status"] == "DRAFT"

    resp = api.get(f"/api/v1/meetings/{mid}/minutes")
    assert_status(resp, 200, "minutes get")
    rows = resp.json()
    assert len(rows) == 1, f"minutes list should have the persisted row: {resp.text[:300]}"
    assert rows[0]["id"] == data["id"]
    assert rows[0]["key_points"][0]["title"] == "登录模块联调完成"


def test_analytics_generate_persists_and_get_still_works(api, meeting):
    mid = meeting["id"]
    resp = api.post(f"/api/v1/meetings/{mid}/analytics/generate")
    assert_status(resp, 200, "analytics generate")
    data = resp.json()["data"]
    assert data["meeting_id"] == mid
    # No fabricated sentiment: without a transcript the analysis says so.
    assert data["sentiment_analysis"]["overall_sentiment"] == "unknown"
    assert data["sentiment_analysis"]["sentiment_score"] is None
    assert data["data_sources"]["sentiment"].startswith("无转录文本")
    # Regenerate is an upsert, not a duplicate error.
    resp = api.post(f"/api/v1/meetings/{mid}/analytics/generate")
    assert_status(resp, 200, "analytics regenerate")

    resp = api.get(f"/api/v1/meetings/{mid}/analytics")
    assert_status(resp, 200, "analytics get")
    assert resp.json()["data"]["meeting_id"] == mid
    assert isinstance(resp.json()["data"]["participation_metrics"], list)


def test_analytics_unknown_meeting_404(api):
    resp = api.get("/api/v1/meetings/999999/analytics")
    assert_status(resp, 404, "analytics get unknown meeting")
    resp = api.post("/api/v1/meetings/999999/analytics/generate")
    assert_status(resp, 404, "analytics generate unknown meeting")


def test_transcription_stays_honest_404(api, meeting):
    # No recording + no STT pipeline: no fabricated transcript.
    resp = api.get(f"/api/v1/meetings/{meeting['id']}/transcription")
    assert_status(resp, 404, "transcription without source")


def test_action_items_crud(api, meeting):
    mid = meeting["id"]
    resp = api.get(f"/api/v1/meetings/{mid}/action-items")
    assert_status(resp, 200, "action items list empty")
    assert resp.json() == []

    resp = api.post(
        f"/api/v1/meetings/{mid}/action-items",
        json={"title": "启动支付模块测试", "description": "下周开始", "priority": "high"},
    )
    assert_status(resp, 201, "action item create")
    item = resp.json()
    assert item["title"] == "启动支付模块测试"
    assert item["priority"] == "high"
    assert item["status"] == "pending"
    aid = item["action_id"]

    resp = api.get(f"/api/v1/meetings/{mid}/action-items")
    assert_status(resp, 200, "action items list")
    assert [i["action_id"] for i in resp.json()] == [aid]

    resp = api.patch(
        f"/api/v1/meetings/{mid}/action-items/{aid}",
        json={"status": "in_progress", "title": "启动支付模块测试-改"},
    )
    assert_status(resp, 200, "action item patch")
    assert resp.json()["status"] == "in_progress"
    assert resp.json()["title"] == "启动支付模块测试-改"

    resp = api.patch(f"/api/v1/meetings/{mid}/action-items/999999", json={"status": "completed"})
    assert_status(resp, 404, "action item patch unknown")

    resp = api.delete(f"/api/v1/meetings/{mid}/action-items/{aid}")
    assert_status(resp, 204, "action item delete")
    resp = api.get(f"/api/v1/meetings/{mid}/action-items")
    assert resp.json() == []
    resp = api.delete(f"/api/v1/meetings/{mid}/action-items/{aid}")
    assert_status(resp, 404, "action item delete twice")

    resp = api.post(f"/api/v1/meetings/{mid}/action-items", json={"title": "   "})
    assert_status(resp, 400, "action item empty title")
    resp = api.post("/api/v1/meetings/999999/action-items", json={"title": "x"})
    assert_status(resp, 404, "action item unknown meeting")


def test_action_items_patch_is_merge_safe(api, meeting):
    """Regression: PATCH with only {status} must keep a registered assignee.

    Found during coordinator integration review: a status-only PATCH was
    suspected of nulling unpassed fields (frontend observed assignee
    '张三' -> None). The real mechanism is different — PATCH already
    merges (route passes exclude_unset=True, service only touches
    provided keys). '张三' vanished because it is not a registered user:
    _resolve_assignee stores no assignee_id for unknown names and only
    echoes the name in the create response. A registered assignee must
    survive a partial PATCH; that is what this guards.
    """
    mid = meeting["id"]
    resp = api.post(
        f"/api/v1/meetings/{mid}/action-items",
        json={"title": "回归：PATCH 合并语义", "assignee": "admin", "priority": "medium"},
    )
    assert_status(resp, 201, "action item create with registered assignee")
    item = resp.json()
    assert item["assignee"] == "系统管理员", item
    aid = item["action_id"]

    resp = api.patch(
        f"/api/v1/meetings/{mid}/action-items/{aid}",
        json={"status": "in_progress"},
    )
    assert_status(resp, 200, "action item patch status only")
    assert resp.json()["status"] == "in_progress"
    assert resp.json()["assignee"] == "系统管理员", resp.json()

    resp = api.get(f"/api/v1/meetings/{mid}/action-items")
    assert_status(resp, 200, "action items list after patch")
    assert resp.json()[0]["assignee"] == "系统管理员", resp.json()

    resp = api.delete(f"/api/v1/meetings/{mid}/action-items/{aid}")
    assert_status(resp, 204, "action item delete")


def test_report_generate_and_download(api, meeting_with_chat):
    mid = meeting_with_chat["id"]
    resp = api.post(
        f"/api/v1/meetings/{mid}/analytics/reports/generate",
        json={"report_type": "full", "format": "markdown"},
    )
    assert_status(resp, 200, "report generate markdown")
    report = resp.json()
    assert report["meeting_id"] == mid
    assert report["format"] == "markdown"
    assert report["download_url"].endswith("/download")

    resp = api.get(report["download_url"])
    assert_status(resp, 200, "report download markdown")
    assert "会议分析报告" in resp.text
    assert meeting_with_chat["title"] in resp.text
    assert "无转录文本" in resp.text

    resp = api.post(
        f"/api/v1/meetings/{mid}/analytics/reports/generate",
        json={"report_type": "full", "format": "html"},
    )
    assert_status(resp, 200, "report generate html")
    resp = api.get(resp.json()["download_url"])
    assert_status(resp, 200, "report download html")
    assert "<h1>" in resp.text and meeting_with_chat["title"] in resp.text

    resp = api.post(
        f"/api/v1/meetings/{mid}/analytics/reports/generate",
        json={"report_type": "full", "format": "pdf"},
    )
    assert_status(resp, 422, "report format pdf rejected")

    resp = api.get(f"/api/v1/meetings/{mid}/analytics/reports/{'0' * 32}/download")
    assert_status(resp, 404, "report download unknown")
