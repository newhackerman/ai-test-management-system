"""Route-coverage guard (template): no frontend route may be unaccounted for.

Parses the router file (``QA_ROUTES_FILE``, default
``frontend/src/routes/index.tsx`` relative to the repository root) and
requires every route to sit in exactly one bucket in
``e2e/page_tour_routes.py``: tour / module-covered / excluded /
param-covered / known-gap. Redirects and the ``*`` catch-all are not
pages. Add a route to the app and this test fails until you put it in
a bucket.
"""

import os
import re
from pathlib import Path

import pytest

from e2e.page_tour_routes import (
    EXCLUDED_STATIC,
    KNOWN_GAPS_PARAM,
    MODULE_COVERED,
    PARAM_COVERED,
    TOUR_ROUTES,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_FILE = Path(os.environ.get("QA_ROUTES_FILE", REPO_ROOT / "frontend" / "src" / "routes" / "index.tsx"))

REDIRECTS: set[str] = set()


def _routes() -> list[str]:
    text = ROUTES_FILE.read_text()
    paths = re.findall(r"path:\s*'([^']+)'", text)
    assert paths, "no routes parsed — set QA_ROUTES_FILE or fix the router path"
    return paths


def _norm(path: str) -> str:
    return path if path.startswith("/") else "/" + path


@pytest.mark.integration
def test_every_static_route_is_accounted_for():
    tour = {p for p, _, _ in TOUR_ROUTES}
    for path in _routes():
        if ":" in path or path == "*":
            continue
        full = _norm(path)
        buckets = [
            name
            for name, members in (
                ("tour", tour),
                ("module-covered", MODULE_COVERED),
                ("excluded", EXCLUDED_STATIC),
                ("redirect", REDIRECTS),
            )
            if full in members
        ]
        assert buckets, (
            f"route {full!r} is in no coverage bucket — add it to "
            "TOUR_ROUTES, MODULE_COVERED or EXCLUDED_STATIC"
        )
        assert len(buckets) == 1, f"route {full!r} is in two buckets: {buckets}"


@pytest.mark.integration
def test_every_parameterised_route_is_accounted_for():
    for path in _routes():
        if ":" not in path:
            continue
        full = _norm(path)
        buckets = [
            name
            for name, members in (
                ("param-covered", PARAM_COVERED),
                ("known-gap", KNOWN_GAPS_PARAM),
            )
            if full in members
        ]
        assert buckets, (
            f"parameterised route {full!r} is in no coverage bucket — add "
            "it to PARAM_COVERED or KNOWN_GAPS_PARAM"
        )
        assert len(buckets) == 1, f"route {full!r} is in two buckets: {buckets}"


@pytest.mark.integration
def test_buckets_only_reference_real_routes():
    """Stale bucket entries (a removed route) fail loudly too."""
    real = {_norm(p) for p in _routes()}
    for name, members in (
        ("TOUR_ROUTES", {p for p, _, _ in TOUR_ROUTES}),
        ("MODULE_COVERED", MODULE_COVERED),
        ("EXCLUDED_STATIC", EXCLUDED_STATIC),
        ("PARAM_COVERED", PARAM_COVERED),
        ("KNOWN_GAPS_PARAM", KNOWN_GAPS_PARAM),
    ):
        stale = set(members) - real
        assert not stale, f"{name} references routes that no longer exist: {sorted(stale)}"
    for path, reason in list(EXCLUDED_STATIC.items()) + list(KNOWN_GAPS_PARAM.items()):
        assert reason.strip(), f"exclusion for {path!r} needs a written reason"
