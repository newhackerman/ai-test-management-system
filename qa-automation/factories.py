"""Payload factories.

Every builder returns a fresh, valid payload with a unique name/title
(uuid suffix) so tests never collide with each other or with prior runs.
Enum values come from the live OpenAPI spec (verified 2026-11-05).
"""
from __future__ import annotations

import uuid

ADMIN_ID = 1  # admin user created by deployment


def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def project_payload(**overrides) -> dict:
    payload = {
        "project_name": uniq("QA项目"),
        "project_type": "BUSINESS_SYSTEM",
        "planned_start_date": "2026-11-05",
        "planned_end_date": "2026-12-31",
        "project_manager_id": ADMIN_ID,
    }
    payload.update(overrides)
    return payload


def requirement_payload(project_id: int, **overrides) -> dict:
    payload = {
        "project_id": project_id,
        "title": uniq("QA需求"),
        "requirement_type": "FUNCTIONAL",
        "description": "自动化测试创建的需求",
        "priority": "MEDIUM",
    }
    payload.update(overrides)
    return payload


def test_case_payload(**overrides) -> dict:
    payload = {
        "case_title": uniq("QA用例"),
        "case_type": "FUNCTIONAL",
        "module": "登录",
        "priority": "MEDIUM",
        "preconditions": "用户已注册",
        # test_steps must be a list of step objects (schema: List[Dict]).
        "test_steps": [
            {"step_number": 1, "description": "打开登录页", "expected_result": "登录页正常加载"},
            {"step_number": 2, "description": "输入账号密码", "expected_result": "输入框接受输入"},
            {"step_number": 3, "description": "点击登录", "expected_result": "登录成功，进入首页"},
        ],
        "expected_result": "登录成功，进入首页",
    }
    payload.update(overrides)
    return payload


def test_plan_payload(project_id: int, **overrides) -> dict:
    payload = {
        "project_id": project_id,
        "plan_name": uniq("QA计划"),
        "test_type": "FUNCTIONAL",
        "description": "自动化测试创建的测试计划",
        "planned_start_date": "2026-11-05",
        "planned_end_date": "2026-12-31",
    }
    payload.update(overrides)
    return payload


def defect_payload(**overrides) -> dict:
    payload = {
        "title": uniq("QA缺陷"),
        "description": "自动化测试创建的缺陷：登录后首页欢迎语缺失",
        "steps_to_reproduce": "1. 登录\n2. 查看首页",
        "defect_type": "FUNCTIONAL",
        "severity": "MEDIUM",
        "priority": "MEDIUM",
    }
    payload.update(overrides)
    return payload


def risk_payload(project_id: int, **overrides) -> dict:
    payload = {
        "risk_name": uniq("QA风险"),
        "description": "自动化测试创建的风险",
        "risk_category": "SCHEDULE",
        "risk_level": "MEDIUM",
        "probability": 0.5,
        "impact_score": 5,
        "mitigation_strategy": "MITIGATE",
        "owner_id": ADMIN_ID,
        "project_id": project_id,
    }
    payload.update(overrides)
    return payload
