"""Regression for the AI assistant AttributeError (reported 2026-11-07).

Root cause: commit c206253 inserted the module-level helper
``_parse_model_list`` in the middle of the ``AIAssistantService`` class
body. A column-0 ``def`` ends the class, so every method defined after
it (42 of them, including ``_call_openai_compatible_service``) became
dead nested functions inside the helper and never attached to the
class. The file still compiled, and the existing tests never sent a
query with a configured API key, so the bug shipped silently — the
user hit it on the real AI assistant page while the suite was green.

These tests guard the exact failure:
- the class must expose every method its source defines;
- the full ``_call_ai_service`` path must return a real AIResponse
  (mocked HTTP, no network);
- the live ``/ai-assistant/query`` endpoint must never answer with an
  AttributeError (one short real provider call; a clean provider error
  is accepted, the AttributeError is not).
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

SERVICE_SRC = BACKEND_DIR / "src" / "services" / "ai_assistant_service.py"


def _class_method_names() -> list[str]:
    """Method names defined inside the AIAssistantService class body."""
    lines = SERVICE_SRC.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("class AIAssistantService:"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^(class|def) ", lines[i]):
            end = i
            break
    return re.findall(r"^    (?:async )?def (\w+)", "\n".join(lines[start:end]), re.M)


@pytest.mark.integration
def test_service_exposes_every_method_defined_in_source():
    """A helper inserted at column 0 used to cut the class body in half.

    If a future edit breaks the class body again, this fails before any
    user hits the missing method at runtime.
    """
    from src.services.ai_assistant_service import AIAssistantService

    names = _class_method_names()
    assert len(names) > 40, f"unexpectedly few methods parsed: {len(names)}"
    missing = [n for n in names if not hasattr(AIAssistantService, n)]
    assert not missing, f"methods defined in source but missing on the class: {missing}"


@pytest.mark.integration
def test_call_ai_service_returns_response_with_mocked_http():
    """The full call path that used to die with AttributeError."""
    from src.services.ai_assistant_service import (
        AIAssistantService,
        AIProvider,
    )

    class FakeResp:
        status = 200

        async def text(self):
            return json.dumps({"choices": [{"message": {"content": "mocked reply"}}]})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return FakeResp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    async def run():
        svc = AIAssistantService()
        svc.ai_configs = {
            AIProvider.OPENAI: {
                "api_key": "dummy-key-for-test",
                "api_endpoint": "https://example.invalid/v1",
                "models": ["gpt-4"],
            }
        }
        with patch(
            "src.services.ai_assistant_service.aiohttp.ClientSession", FakeSession
        ):
            return await svc._call_ai_service("hello", AIProvider.OPENAI)

    resp = asyncio.run(run())
    assert resp.content == "mocked reply"


@pytest.mark.integration
def test_query_endpoint_never_returns_attribute_error(api):
    """Live endpoint, one short real provider call.

    Accepts a real answer (200) or a clean provider error (500/503);
    the only failure is the AttributeError the user reported.
    """
    resp = api.post(
        "/api/v1/ai-assistant/query",
        json={"content": "你好，用一句话介绍你自己"},
        timeout=120,
    )
    assert "AttributeError" not in resp.text, resp.text[:500]
    assert "has no attribute" not in resp.text, resp.text[:500]
    assert resp.status_code in (200, 500, 503), f"{resp.status_code} {resp.text[:300]}"
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("success") is True
        assert data.get("content")
