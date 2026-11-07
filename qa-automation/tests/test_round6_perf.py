"""Round-6 item 15: performance baseline (smoke level, NOT a load test).

Measured baseline on this VM (localhost, warm, 2026-11-07):
- login: median 0.53s (max 0.56s over 3 runs)
- GET /projects: median 0.018s
- GET /requirements?limit=20: median 0.018s
- GET /test-cases?limit=20: median 0.044s
- POST 10 MB text upload (AI file storage, USER_UPLOAD): 0.12s

Thresholds below are deliberately loose (5-10x the measured values):
this suite runs on a shared VM whose speed varies, so the tests guard
against regressions and 5xx, not against millisecond jitter. Tighten
them only with a stable-runner baseline.
"""

from __future__ import annotations

import io
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from client import ApiClient

pytestmark = pytest.mark.perf

# Loose smoke thresholds (seconds); see module docstring for measured values.
LOGIN_LIMIT = 3.0
LIST_LIMIT = 2.0
UPLOAD_LIMIT = 30.0
CONCURRENT_LIMIT = 5.0
CONCURRENCY = 5


def test_login_latency_baseline(api):
    """Three logins: median well under the smoke threshold."""
    durations = []
    for _ in range(3):
        started = time.time()
        ApiClient(timeout=60).login_as_admin()
        durations.append(time.time() - started)
    median = statistics.median(durations)
    assert median < LOGIN_LIMIT, f"login median {median:.2f}s >= {LOGIN_LIMIT}s"


def test_list_latency_baseline(api):
    """Hot list endpoints answer in well under 2s."""
    for path, params in [
        ("/api/v1/projects", None),
        ("/api/v1/requirements/", {"skip": 0, "limit": 20}),
        ("/api/v1/test-cases/", {"skip": 0, "limit": 20}),
    ]:
        durations = []
        for _ in range(3):
            started = time.time()
            resp = api.get(path, params=params)
            durations.append(time.time() - started)
            assert resp.status_code == 200, f"{path}: {resp.status_code}"
        median = statistics.median(durations)
        assert median < LIST_LIMIT, f"{path} median {median:.2f}s >= {LIST_LIMIT}s"


def test_large_file_upload_baseline(api):
    """10 MB upload completes fast and the stored size matches."""
    payload = b"x" * (10 * 1024 * 1024)
    started = time.time()
    resp = api.post(
        "/api/v1/ai/files/upload",
        files={"file": ("perf-10mb.txt", io.BytesIO(payload), "text/plain")},
        data={"category": "USER_UPLOAD"},
    )
    elapsed = time.time() - started
    assert resp.status_code == 200, f"upload: {resp.status_code} {resp.text[:200]}"
    assert elapsed < UPLOAD_LIMIT, f"upload took {elapsed:.2f}s >= {UPLOAD_LIMIT}s"
    body = resp.json()
    file_id = body.get("id") or (body.get("data") or {}).get("id")
    assert body.get("file_size") == len(payload), body
    assert file_id, body
    try:
        api.delete(f"/api/v1/ai/files/{file_id}")
    except Exception:
        pass


def test_small_concurrency_no_5xx():
    """5 parallel clients listing projects: no 5xx, all answer in time."""

    def _one(_index: int):
        client = ApiClient(timeout=60).login_as_admin()
        started = time.time()
        try:
            resp = client.get("/api/v1/projects")
            return resp.status_code, time.time() - started
        finally:
            client.close()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = list(pool.map(_one, range(CONCURRENCY)))
    assert len(results) == CONCURRENCY
    for status, elapsed in results:
        assert status == 200, f"concurrent list returned {status}"
        assert elapsed < CONCURRENT_LIMIT, f"concurrent list took {elapsed:.2f}s"
