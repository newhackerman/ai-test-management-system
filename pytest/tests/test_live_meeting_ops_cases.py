from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


OPS_READ_ONLY_ENDPOINTS = [
    "/api/v1/meetings/",
    "/api/v1/meetings/projects/999999999/meetings",
    "/api/v1/meetings/projects/999999999/meeting-schedule",
    "/api/v1/meetings/projects/999999999/meeting-types",
    "/api/v1/meetings/projects/999999999/meeting-statistics",
    "/api/v1/notifications",
    "/api/v1/notifications/unread-count",
    "/api/v1/auto-recovery/monitoring-status",
    "/api/v1/auto-recovery/recovery-history",
    "/api/v1/auto-recovery/statistics",
    "/api/v1/auto-recovery/failure-types",
    "/api/v1/cache-preheating/status",
    "/api/v1/cache-preheating/tasks",
    "/api/v1/cache-preheating/statistics",
    "/api/v1/performance-tests/",
    "/api/v1/security-tests/",
]


NONEXISTENT_RESOURCE_ENDPOINTS = [
    "/api/v1/meetings/999999999",
    "/api/v1/meetings/999999999/participants",
    "/api/v1/meetings/999999999/recordings",
    "/api/v1/performance-tests/999999999",
    "/api/v1/performance-tests/executions/999999999/status",
    "/api/v1/security-tests/executions/999999999/results",
]


INVALID_BODY_ENDPOINTS = [
    "/api/v1/meetings/",
    "/api/v1/auto-recovery/manual-recovery",
    "/api/v1/cache-preheating/manual",
    "/api/v1/performance-tests/execute",
    "/api/v1/security-tests/execute",
]


@pytest.mark.parametrize("path", OPS_READ_ONLY_ENDPOINTS)
def test_meeting_ops_read_only_endpoints_do_not_return_500(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    assert response.status_code < 500, f"{path} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize("path", NONEXISTENT_RESOURCE_ENDPOINTS)
def test_meeting_ops_nonexistent_resources_return_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    assert 400 <= response.status_code < 500, f"{path} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize("path", INVALID_BODY_ENDPOINTS)
def test_meeting_ops_mutations_reject_empty_body_without_500(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.post(f"{base_url}{path}", json={}, timeout=15)

    assert 400 <= response.status_code < 500, f"{path} returned {response.status_code}: {response.text[:300]}"
