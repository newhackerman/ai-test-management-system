"""Page-tour inventory (template).

Fill this in from the target project's router file and sidebar menu
during adaptation. Every static route must land in exactly one bucket
(see tests/test_route_coverage.py): TOUR_ROUTES, MODULE_COVERED,
EXCLUDED_STATIC, PARAM_COVERED or KNOWN_GAPS_PARAM. A route in no
bucket fails the suite — that is the point: coverage gaps must be
explicit decisions, never accidents.

TOUR_ROUTES: (path, label, marker). ``marker`` is page text that must
be visible once the page loads; None means generic checks only
(non-blank body, no error text, no console errors, no failed API
responses).
"""

# Static routes visited by test_e2e_page_tour.py. Replace the examples
# with the project's real routes.
TOUR_ROUTES = [
    ("/", "Dashboard", None),
    ("/projects", "Projects", None),
]

# Static routes NOT in the tour because another E2E test covers them.
# value: the covering test file.
MODULE_COVERED = {
    # "/items/create": "test_e2e_items.py (create flow)",
}

# Static routes deliberately not visited, with the reason.
EXCLUDED_STATIC = {
    "/login": "covered by test_e2e_smoke.py (login form itself)",
}

# Parameterised routes covered by fixture-based tests.
PARAM_COVERED = {
    # "/items/:id": "test_e2e_items.py (detail after create)",
}

# Parameterised routes not covered yet, with the reason.
KNOWN_GAPS_PARAM = {
    # "/items/:id/edit": "edit flow not covered; create + detail are",
}
