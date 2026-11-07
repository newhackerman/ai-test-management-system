"""Shared fixtures.

- ``api``: session-scoped, logged-in admin client.
- ``anon``: anonymous client (no Authorization header).
- ``_tracked_delete``: best-effort cleanup helper. Use it in every
  ``make_<entity>`` fixture you add for the new project, following the
  pattern below: create through the API, register the delete, return the
  object. Cleanup is best-effort: a leftover row never breaks other tests
  because every payload carries a unique name (see factories.uniq).
"""
from __future__ import annotations

import pytest

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


# Example domain fixture for the new project. Copy this pattern once per
# entity, replacing the path, the factories.<entity>_payload builder and
# the envelope resource key with the new API's values.
#
# @pytest.fixture()
# def make_widget(api, request):
#     def _make(**overrides):
#         resp = api.post("/api/v1/widgets", json=factories.widget_payload(**overrides))
#         widget = assert_envelope_ok(resp, "widget")
#         _tracked_delete(api, request, f"/api/v1/widgets/{widget['id']}")
#         return widget
#     return _make
