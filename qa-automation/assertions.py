"""Shared assertion helpers.

The success envelope is driven by QA_ENVELOPE (see config.py):
  - success (default): {"success": true, "message": ..., "<resource>": {...}}
  - code: {"code": 0, "data": {...}, "message": ...} — code 0 or 200
    means success; the payload lives under "data".
  - bare: no wrapper at all — the body itself is the resource.

Set QA_ENVELOPE once per project and every test follows. Error bodies
are checked by status only (see assert_error_code); most APIs carry
{"detail": ...} or {"message": ...} there, and the status is what the
tests assert on.
"""
from __future__ import annotations

import httpx

from config import ENVELOPE


def assert_status(resp: httpx.Response, expected: int, what: str = "") -> None:
    assert resp.status_code == expected, (
        f"{what or resp.request.url.path}: expected HTTP {expected}, "
        f"got {resp.status_code}: {resp.text[:500]}"
    )


def _unwrap_success(body: dict, resource_key: str | None) -> dict:
    """Pull the resource out of the configured envelope shape."""
    if ENVELOPE == "bare":
        if resource_key:
            assert resource_key in body, f"missing '{resource_key}' in {body}"
            return body[resource_key]
        return body
    if ENVELOPE == "code":
        code = body.get("code")
        assert code in (0, 200), f"expected code 0/200, got: {body}"
        data = body.get("data")
        if resource_key is None:
            return data if data is not None else body
        if isinstance(data, dict) and resource_key in data:
            return data[resource_key]
        # data IS the resource (e.g. data is the created object itself)
        assert isinstance(data, dict), f"missing '{resource_key}' in {body}"
        return data
    # success (default)
    assert body.get("success") is True, f"expected success=true, got: {body}"
    if resource_key:
        assert resource_key in body, f"missing '{resource_key}' in {body}"
        return body[resource_key]
    return body


def assert_envelope_ok(
    resp: httpx.Response,
    resource_key: str | None = None,
    expected: tuple[int, ...] = (200, 201),
) -> dict:
    """Success envelope. Creates return 201, other calls 200.

    Returns the decoded body. If resource_key is given, also returns that
    sub-object (and asserts it is present).
    """
    assert resp.status_code in expected, (
        f"envelope: expected HTTP {expected}, "
        f"got {resp.status_code}: {resp.text[:500]}"
    )
    body = resp.json()
    return _unwrap_success(body, resource_key)


def assert_error_code(resp: httpx.Response, expected_status: int) -> dict:
    """Error responses carry {"detail": {...}} with an inner code/message."""
    assert_status(resp, expected_status, "error response")
    return resp.json()
