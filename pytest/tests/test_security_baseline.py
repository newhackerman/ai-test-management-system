from __future__ import annotations

import os

import pytest


PROTECTED_ENDPOINTS = [
    "/api/v1/users",
    "/api/v1/projects",
    "/api/v1/test-plans/",
    "/api/v1/test-cases/",
    "/api/v1/test-executions/",
    "/api/v1/test-reports/",
]


@pytest.mark.security
@pytest.mark.api
@pytest.mark.parametrize("path", PROTECTED_ENDPOINTS)
def test_protected_get_endpoints_reject_anonymous_requests(client, path: str) -> None:
    response = client.get(path)

    assert response.status_code in {401, 403}


@pytest.mark.security
def test_repository_does_not_commit_obvious_private_keys(target_root) -> None:
    risky_suffixes = {".pem", ".key", ".p12", ".pfx"}
    excluded_dirs = {".git", "venv", "node_modules", ".pytest_cache"}

    risky_files = []
    for current_root, dirs, files in os.walk(target_root):
        dirs[:] = [item for item in dirs if item not in excluded_dirs]
        for file_name in files:
            if any(file_name.lower().endswith(suffix) for suffix in risky_suffixes):
                risky_files.append(str(os.path.join(current_root, file_name)))

    assert not risky_files, "Potential private key files committed: " + ", ".join(risky_files)


@pytest.mark.security
def test_env_examples_do_not_contain_real_secrets(target_root) -> None:
    suspicious_values = []
    placeholder_tokens = {
        "change",
        "changeme",
        "change-me",
        "example",
        "placeholder",
        "password",
        "secret",
        "test",
        "your",
    }
    for path in target_root.rglob(".env.example"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key_upper = key.upper()
            secret_like_key = (
                key_upper.endswith("PASSWORD")
                or key_upper.endswith("SECRET")
                or key_upper.endswith("SECRET_KEY")
                or key_upper.endswith("API_KEY")
                or key_upper.endswith("ACCESS_KEY")
                or key_upper.endswith("PRIVATE_KEY")
            )
            if secret_like_key:
                value = value.strip().strip('"').strip("'")
                normalized = value.lower().replace("-", "_")
                looks_like_placeholder = any(token in normalized for token in placeholder_tokens)
                if value and not looks_like_placeholder:
                    suspicious_values.append(f"{path}:{key}")

    assert not suspicious_values, "Example env files contain non-placeholder secret values: " + ", ".join(suspicious_values)
