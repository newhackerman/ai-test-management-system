"""Payload factories.

Every builder returns a fresh, valid payload with a unique name/title
(uuid suffix) so tests never collide with each other or with prior runs.

Add one builder per domain entity of the new project, following the
``widget_payload`` example. Enum values should come from the live OpenAPI
spec of the new project, never from memory.
"""
from __future__ import annotations

import uuid


def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def widget_payload(**overrides) -> dict:
    """Example builder. Replace with the new project's real entities."""
    payload = {
        "name": uniq("QA-widget"),
        "description": "created by qa-automation template smoke run",
    }
    payload.update(overrides)
    return payload
