"""Route-coverage guard: no frontend route may be unaccounted for.

On 2026-11-07 the user found two bugs by logging in and clicking
around while the suite was green — most pages had never been opened by
a test. This guard makes that impossible by construction: it parses
``frontend/src/routes/index.tsx`` and requires every route to sit in
exactly one bucket:

- TOUR_ROUTES: visited by test_e2e_page_tour.py (static pages);
- MODULE_COVERED / PARAM_COVERED: covered by another named E2E test;
- EXCLUDED_STATIC / KNOWN_GAPS_PARAM: deliberately not covered, with a
  written reason (kept in e2e/page_tour_routes.py);
- redirects (``<Navigate ...>``) and the ``*`` catch-all: not pages.

Add a route to the app and this test fails until you put it in a
bucket. That is the point: coverage gaps must be explicit decisions,
never accidents.
"""

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

ROUTES_FILE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "routes" / "index.tsx"

REDIRECTS = {"/test-manager/execution"}


def _routes() -> list[str]:
    text = ROUTES_FILE.read_text()
    paths = re.findall(r"path:\s*'([^']+)'", text)
    assert paths, "no routes parsed — has the router file moved?"
    return paths


def _buckets():
    tour = {p for p, _, _ in TOUR_ROUTES}
    return tour


@pytest.mark.integration
def test_every_static_route_is_accounted_for():
    tour = _buckets()
    for path in _routes():
        if ":" in path or path == "*":
            continue
        full = path if path.startswith("/") else "/" + path
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
            "TOUR_ROUTES, MODULE_COVERED or EXCLUDED_STATIC "
            "(e2e/page_tour_routes.py)"
        )
        assert len(buckets) == 1, f"route {full!r} is in two buckets: {buckets}"


@pytest.mark.integration
def test_every_parameterised_route_is_accounted_for():
    for path in _routes():
        if ":" not in path:
            continue
        full = path if path.startswith("/") else "/" + path
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
            "it to PARAM_COVERED or KNOWN_GAPS_PARAM "
            "(e2e/page_tour_routes.py)"
        )
        assert len(buckets) == 1, f"route {full!r} is in two buckets: {buckets}"


@pytest.mark.integration
def test_buckets_only_reference_real_routes():
    """Stale bucket entries (a removed route) fail loudly too."""
    real = {(p if p.startswith("/") else "/" + p) for p in _routes()}
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
