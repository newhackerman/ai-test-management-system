"""Shared fixtures.

- ``api``: session-scoped, logged-in admin client.
- ``anon``: anonymous client (no Authorization header).
- ``make_project`` / ``project``: project factory (function-scoped, auto
  cleanup) and one shared project per module.
- ``make_requirement`` / ``make_case`` / ``make_plan`` / ``make_defect`` /
  ``make_risk``: per-test factories with best-effort cleanup.

Cleanup is best-effort: a leftover row never breaks other tests because
every payload carries a unique name (see factories.uniq).
"""
from __future__ import annotations

import pytest

import factories
from assertions import assert_envelope_ok
from client import AnonymousClient, ApiClient


@pytest.fixture(scope="session")
def api() -> ApiClient:
    client = ApiClient().login_as_admin()
    yield client
    client.close()


@pytest.fixture()
def anon() -> AnonymousClient:
    client = AnonymousClient()
    yield client
    client.close()


def _tracked_delete(api: ApiClient, request, path: str):
    def _cleanup():
        try:
            api.delete(path)
        except Exception:
            pass

    request.addfinalizer(_cleanup)


@pytest.fixture()
def make_project(api, request):
    def _make(**overrides):
        resp = api.post("/api/v1/projects", json=factories.project_payload(**overrides))
        project = assert_envelope_ok(resp, "project")
        _tracked_delete(api, request, f"/api/v1/projects/{project['id']}")
        return project

    return _make


@pytest.fixture(scope="module")
def project(api):
    """One shared project for the whole module."""
    resp = api.post("/api/v1/projects", json=factories.project_payload())
    proj = assert_envelope_ok(resp, "project")
    yield proj
    try:
        api.delete(f"/api/v1/projects/{proj['id']}")
    except Exception:
        pass


@pytest.fixture()
def make_requirement(api, request):
    def _make(project_id: int, **overrides):
        resp = api.post(
            "/api/v1/requirements/",
            json=factories.requirement_payload(project_id, **overrides),
        )
        # NOTE: requirements create returns the plain object (no envelope).
        assert resp.status_code in (200, 201), (
            f"requirement create failed: {resp.status_code} {resp.text[:300]}"
        )
        req = resp.json()
        _tracked_delete(api, request, f"/api/v1/requirements/{req['id']}")
        return req

    return _make


@pytest.fixture()
def make_case(api, request):
    def _make(**overrides):
        resp = api.post("/api/v1/test-cases/", json=factories.test_case_payload(**overrides))
        case = assert_envelope_ok(resp, "data")
        _tracked_delete(api, request, f"/api/v1/test-cases/{case['id']}")
        return case

    return _make


@pytest.fixture()
def make_plan(api, request):
    def _make(project_id: int, **overrides):
        resp = api.post(
            "/api/v1/test-plans/", json=factories.test_plan_payload(project_id, **overrides)
        )
        plan = assert_envelope_ok(resp, "data")
        _tracked_delete(api, request, f"/api/v1/test-plans/{plan['id']}")
        return plan

    return _make


@pytest.fixture()
def make_defect(api, request):
    def _make(**overrides):
        resp = api.post("/api/v1/defects/", json=factories.defect_payload(**overrides))
        defect = assert_envelope_ok(resp, "data")
        _tracked_delete(api, request, f"/api/v1/defects/{defect['id']}")
        return defect

    return _make


@pytest.fixture()
def make_risk(api, request):
    def _make(project_id: int, **overrides):
        resp = api.post("/api/v1/risks/", json=factories.risk_payload(project_id, **overrides))
        assert resp.status_code in (200, 201), (
            f"risk create failed: {resp.status_code} {resp.text[:300]}"
        )
        risk = resp.json()
        _tracked_delete(api, request, f"/api/v1/risks/{risk['id']}")
        return risk

    return _make
