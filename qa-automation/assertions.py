"""Shared assertion helpers."""
from __future__ import annotations

import httpx


def assert_status(resp: httpx.Response, expected: int, what: str = "") -> None:
    assert resp.status_code == expected, (
        f"{what or resp.request.url.path}: expected HTTP {expected}, "
        f"got {resp.status_code}: {resp.text[:500]}"
    )


def assert_envelope_ok(
    resp: httpx.Response,
    resource_key: str | None = None,
    expected: tuple[int, ...] = (200, 201),
) -> dict:
    """Success envelope: {"success": true, "message": ..., "<resource>": {...}}.

    Creates return 201, other calls 200 — both are accepted. Returns the
    decoded body. If resource_key is given, also returns that sub-object
    (and asserts it is present).
    """
    assert resp.status_code in expected, (
        f"envelope: expected HTTP {expected}, "
        f"got {resp.status_code}: {resp.text[:500]}"
    )
    body = resp.json()
    assert body.get("success") is True, f"expected success=true, got: {body}"
    if resource_key:
        assert resource_key in body, f"missing '{resource_key}' in {body}"
        return body[resource_key]
    return body


def assert_error_code(resp: httpx.Response, expected_status: int) -> dict:
    """Error responses carry {"detail": {...}} with an inner code/message."""
    assert_status(resp, expected_status, "error response")
    return resp.json()
