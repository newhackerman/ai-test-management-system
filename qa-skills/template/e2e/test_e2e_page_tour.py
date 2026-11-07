"""Page tour (template): log in and open every page, like a user would.

Visits every static route in ``page_tour_routes.TOUR_ROUTES`` and
proves each one renders — no white screen, no error text, no console
errors, no failed API calls. Fill in the route inventory during
adaptation; the guard in ``tests/test_route_coverage.py`` fails the
suite if a route is added to the app without landing in a bucket.
"""

import pytest

from e2e.helpers import assert_page_renders
from e2e.page_tour_routes import TOUR_ROUTES


@pytest.mark.e2e
@pytest.mark.parametrize("path,label,marker", TOUR_ROUTES, ids=[p for p, _, _ in TOUR_ROUTES])
def test_page_tour_renders(logged_in_page, path, label, marker):
    """Every page must render without errors."""
    assert_page_renders(logged_in_page, path, marker=marker)
