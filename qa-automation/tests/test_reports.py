"""Test-report read endpoints (generation is exercised lightly: it depends
on accumulated execution data and can be slow)."""
import pytest

from assertions import assert_envelope_ok, assert_status


@pytest.mark.crud
def test_list_test_reports(api):
    resp = api.get("/api/v1/test-reports/")
    assert_status(resp, 200, "list test reports")
    body = resp.json()
    assert isinstance(body, (list, dict))


@pytest.mark.crud
def test_report_analytics_summary(api):
    resp = api.get("/api/v1/test-reports/analytics/summary")
    assert_status(resp, 200, "report analytics summary")


@pytest.mark.crud
def test_list_report_templates(api):
    resp = api.get("/api/v1/test-reports/templates")
    assert_status(resp, 200, "list report templates")


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_report_returns_404(api):
    resp = api.get("/api/v1/test-reports/999999999")
    assert_status(resp, 404, "get missing report")


@pytest.mark.crud
def test_report_schedules_list(api):
    resp = api.get("/api/v1/test-reports/schedules")
    assert_status(resp, 200, "list report schedules")
