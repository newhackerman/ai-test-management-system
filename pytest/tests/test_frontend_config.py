from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.frontend
def test_frontend_package_json_has_required_scripts(frontend_dir: Path) -> None:
    package_json = json.loads((frontend_dir / "package.json").read_text(encoding="utf-8"))
    scripts = package_json.get("scripts", {})

    for script in ["dev", "build", "test"]:
        assert script in scripts


@pytest.mark.frontend
def test_frontend_uses_vite_react_stack(frontend_dir: Path) -> None:
    package_json = json.loads((frontend_dir / "package.json").read_text(encoding="utf-8"))
    dependencies = {
        **package_json.get("dependencies", {}),
        **package_json.get("devDependencies", {}),
    }

    for package in ["vite", "react", "react-dom", "typescript"]:
        assert package in dependencies


@pytest.mark.frontend
def test_frontend_source_directory_exists(frontend_dir: Path) -> None:
    assert (frontend_dir / "src").exists(), "Frontend should keep application source under src/"
