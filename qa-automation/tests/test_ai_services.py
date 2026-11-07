"""U3 regression: the AI service method and the stats factory that the
codebase calls but never defined.

- ``AIAssistantService.generate_test_strategy`` is called by
  TestPlanService / TestStrategyService; without a configured AI provider
  it must return the empty structure instead of raising.
- ``get_usage_statistics_service`` is imported by the cache-preheating
  scheduler; the service it returns must also expose
  ``get_system_overview`` (both were missing).

These tests import backend modules directly (no HTTP), so they load
backend/.env explicitly: pytest runs from qa-automation, not backend.
"""

import asyncio
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

EMPTY_STRATEGY = {
    "strategy": "",
    "overview": "",
    "key_points": [],
    "risks": [],
    "resource_suggestions": [],
    "approach": {},
    "levels": [],
}


@pytest.mark.integration
def test_generate_test_strategy_exists_and_degrades_without_key():
    from src.services.ai_assistant_service import AIAssistantService

    svc = AIAssistantService()
    assert callable(getattr(svc, "generate_test_strategy", None))
    # No AI keys configured in this environment: must degrade gracefully.
    result = asyncio.run(svc.generate_test_strategy("基于项目信息提供测试策略建议"))
    assert result == EMPTY_STRATEGY


@pytest.mark.integration
def test_usage_statistics_factory_and_overview():
    from src.services.enhanced_usage_statistics_service import (
        get_usage_statistics_service,
    )

    async def run():
        stats = await get_usage_statistics_service()
        try:
            return await stats.get_system_overview()
        finally:
            # 工厂返回短生命周期会话，用完须关闭（根因修复后）
            await stats.aclose()

    overview = asyncio.run(run())
    assert overview["period"] == "daily"
    for key in (
        "total_requests",
        "total_tokens",
        "total_cost",
        "active_users",
        "avg_response_time",
        "error_rate",
        "availability",
        "models",
        "top_users",
        "performance",
    ):
        assert key in overview, f"overview missing {key!r}"
