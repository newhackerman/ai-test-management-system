from __future__ import annotations

import ast
import tokenize
from pathlib import Path

import pytest


IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "allure-results",
    "reports",
    "test_reports",
    "venv",
}


@pytest.mark.structure
def test_expected_backend_entrypoints_exist(backend_dir: Path) -> None:
    expected = [
        backend_dir / "src" / "main.py",
        backend_dir / "src" / "api" / "__init__.py",
        backend_dir / "src" / "core" / "config.py",
        backend_dir / "requirements.txt",
    ]

    missing = [str(path) for path in expected if not path.exists()]
    assert not missing, "Missing backend entrypoints: " + ", ".join(missing)


@pytest.mark.structure
def test_backend_python_sources_are_syntax_valid(backend_dir: Path) -> None:
    src_dir = backend_dir / "src"
    failures: list[str] = []

    for path in sorted(src_dir.rglob("*.py")):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            with tokenize.open(path) as file:
                ast.parse(file.read(), filename=str(path))
        except Exception as exc:  # pragma: no cover - assertion path
            failures.append(f"{path}: {type(exc).__name__}: {exc}")

    assert not failures, "Python syntax errors found:\n" + "\n".join(failures[:50])


@pytest.mark.structure
def test_backend_requirements_include_test_dependencies(backend_dir: Path) -> None:
    requirements = (backend_dir / "requirements.txt").read_text(encoding="utf-8").lower()
    required_packages = ["pytest", "pytest-asyncio", "httpx", "pytest-cov"]

    missing = [package for package in required_packages if package not in requirements]
    assert not missing


@pytest.mark.structure
def test_environment_template_is_available(backend_dir: Path) -> None:
    assert (backend_dir / ".env.example").exists(), "Backend should provide .env.example"
