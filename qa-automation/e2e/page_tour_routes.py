"""Page-tour inventory: every user-facing route the E2E suite must visit.

Why this file exists: on 2026-11-07 the user found two bugs just by
logging in and clicking around (AI assistant AttributeError, report
download dead button) while the suite was green at 302/302 — because
most pages had never been opened by a test at all. A page that no test
visits is a page nobody watches. This list is the single source of
truth for the tour; ``tests/test_route_coverage.py`` fails the suite if
a route in ``frontend/src/routes/index.tsx`` is missing from every
bucket (tour / module-covered / excluded-with-reason).

TOUR_ROUTES: (path, sidebar label, marker). ``marker`` is page text
that must be visible once the page loads; None means generic checks
only (non-blank body, no error boundary, no console errors, no failed
API responses). Keep markers to text verified on the real page.
"""

# Static routes visited by test_e2e_page_tour.py.
TOUR_ROUTES = [
    ("/", "仪表盘", "项目总数"),
    ("/projects", "项目管理", None),
    ("/tasks", "任务管理", None),
    ("/requirements", "需求管理", None),
    ("/risks", "风险管理", None),
    ("/ai-assistant", "AI 助手", None),
    ("/test-manager", "测试概览", None),
    ("/test-manager/test-plans", "测试计划", None),
    ("/test-manager/test-cases", "测试用例", None),
    ("/test-manager/executions", "执行管理", None),
    ("/test-manager/executions/automation", "自动化执行", None),
    ("/test-manager/defects", "缺陷管理", None),
    ("/test-manager/defects/analytics", "缺陷分析", None),
    ("/test-manager/reports", "测试报告", None),
    ("/test-manager/reports/generate", "生成报告", None),
    ("/test-manager/performance", "性能测试", None),
    ("/test-manager/security", "安全测试", None),
    ("/meetings", "会议", None),
    ("/meetings/create", "新建会议", None),
    ("/meetings/analytics/comparison", "会议对比", None),
    ("/meetings/recordings", "录制", None),
    ("/users", "用户管理", None),
    ("/roles", "角色管理", None),
    ("/roles/eight", "八角色管理", None),
    ("/settings", "系统设置", None),
    ("/config", "配置项", None),
    ("/config/groups", "配置分组", None),
    ("/config/audits", "审计日志", None),
    ("/auto-recovery", "自动恢复", None),
    ("/statistics", "数据统计", None),
    ("/profile", "个人资料", None),
    ("/allure-reports", "Allure 报告", None),
    ("/reports", "报告", None),
]

# Static routes NOT in the tour because another E2E test covers them.
# value: the covering test file.
MODULE_COVERED = {
    "/test-manager/test-plans/create": "test_e2e_test_plans.py (create flow)",
    "/test-manager/test-cases/create": "test_e2e_test_cases.py (create flow)",
    "/test-manager/executions/manual": "test_e2e_full_chain.py (manual execution via fixture case)",
}

# Static routes deliberately not visited, with the reason.
# A new route must land in TOUR_ROUTES, MODULE_COVERED or here — never
# nowhere. Keep this list short and honest.
EXCLUDED_STATIC = {
    "/login": "covered by test_e2e_login.py (login form itself)",
    "/auth/login": "same login page, alternate path",
    "/auth/forgot-password": "password-reset flow needs a mailbox; out of E2E scope",
    "/auth/reset-password": "password-reset flow needs a mailbox; out of E2E scope",
}

# Parameterised routes (contain :param). The tour cannot visit them
# without a fixture entity; they are covered by fixture-based tests or
# listed here as known gaps with a reason.
PARAM_COVERED = {
    "/test-manager/test-plans/:id": "test_e2e_full_chain.py (plan detail after create)",
    "/test-manager/test-cases/:id": "test_e2e_full_chain.py (case detail after create)",
    "/test-manager/executions/manual/:testCaseId": "test_e2e_full_chain.py (manual_execution_ui)",
}

KNOWN_GAPS_PARAM = {
    "/meetings/recordings/:recordingId": "no fixture recording exists in E2E; recording needs a desktop session",
    "/meetings/recordings/:recordingId/player": "same as above",
    "/meetings/room/:meetingId": "live meeting room needs a running meeting + media",
    "/meetings/join/:meetingCode": "same as above",
    "/meetings/:id/edit": "no meeting fixture in E2E yet",
    "/meetings/:id/analytics": "no meeting fixture in E2E yet",
    "/meetings/:id/analytics/participation": "no meeting fixture in E2E yet",
    "/meetings/:id/analytics/summary": "no meeting fixture in E2E yet",
    "/meetings/:id/analytics/minutes": "no meeting fixture in E2E yet",
    "/meetings/:id/analytics/actions": "no meeting fixture in E2E yet",
    "/meetings/:id/analytics/reports": "no meeting fixture in E2E yet",
    "/meetings/:id/recordings": "no meeting fixture in E2E yet",
    "/meetings/:id": "no meeting fixture in E2E yet",
    "/test-manager/test-plans/:id/edit": "edit flow not covered; create + detail are",
    "/test-manager/test-cases/:id/edit": "edit flow not covered; create + detail are",
    "/test-manager/executions/:executionId": "no execution fixture asserted on detail page yet",
}
