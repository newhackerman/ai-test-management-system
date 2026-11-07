"""E2E: AI assistant page — the real user flow (regression, 2026-11-07).

The previous suite had no E2E test on this page at all, and the API
tests never sent a query with a configured key, so a broken query path
shipped while the suite was green. This test drives the flow the user
actually hit: open /ai-assistant, type a question, send, and wait for
the assistant reply (or a clean error message). The page must never
show the AttributeError text.

One short real provider call per run; a clean provider error is
accepted, the AttributeError is not.
"""

import pytest
from playwright.sync_api import expect

from config import FRONTEND_URL

QUESTION_INPUT = "输入问题，例如：请结合附件生成登录功能测试点，覆盖边界值和异常路径"


@pytest.mark.e2e
def test_ai_assistant_answers_without_attribute_error(logged_in_page):
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/ai-assistant")

    box = page.get_by_placeholder(QUESTION_INPUT)
    expect(box).to_be_visible(timeout=20000)
    box.fill("你好，用一句话介绍你自己")
    page.get_by_role("button", name="发送", exact=True).click()

    # The button reads 停止 while the provider call is in flight; it
    # returns to 发送 when the reply (or a clean error) is rendered.
    expect(page.get_by_role("button", name="发送", exact=True)).to_be_visible(
        timeout=120000
    )

    text = page.locator("body").inner_text()
    assert "AttributeError" not in text
    assert "has no attribute" not in text
