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


@pytest.mark.crud
@pytest.mark.negative
def test_download_imported_unknown_id_returns_404(api):
    resp = api.get("/api/v1/reports/imported/00000000-0000-0000-0000-000000000000/download")
    assert_status(resp, 404, "download unknown imported report")


@pytest.mark.crud
@pytest.mark.negative
def test_download_imported_traversal_rejected(api):
    # Encoded dots reach the handler as ".." (a literal ".." segment
    # would be normalised away by the HTTP client before it arrives).
    resp = api.get("/api/v1/reports/imported/%2E%2E/download")
    assert_status(resp, 400, "download with traversal import id")


@pytest.mark.crud
@pytest.mark.negative
def test_download_imported_requires_auth(anon):
    resp = anon.get("/api/v1/reports/imported/00000000-0000-0000-0000-000000000000/download")
    assert_status(resp, 401, "download imported report without auth")


@pytest.mark.crud
def test_download_imported_round_trip(api):
    """Import a small HTML report, download it back byte-identical.

    Covers the endpoint the OpenAPI inventory gained with the report
    download fix (PR #5): the tour only clicks the button, this proves
    the preserved original file comes back unchanged.
    """
    import uuid

    marker = uuid.uuid4().hex[:8]
    html = (
        f"<html><head><title>QA download {marker}</title></head>"
        f"<body><h1>probe-{marker}</h1></body></html>"
    ).encode()
    import_id = None
    try:
        resp = api.post(
            "/api/v1/reports/import",
            files={"file": (f"qa-download-{marker}.html", html, "text/html")},
            data={"source_type": "custom"},
        )
        data = assert_envelope_ok(resp, "data", expected=(200, 201))
        import_id = data["import_id"]
        resp = api.get(f"/api/v1/reports/imported/{import_id}/download")
        assert_status(resp, 200, "download imported report")
        assert resp.content == html, "downloaded bytes differ from the uploaded file"
        assert "attachment" in resp.headers.get("content-disposition", "")
    finally:
        if import_id:
            try:
                api.delete(f"/api/v1/reports/imported/{import_id}")
            except Exception:
                pass
