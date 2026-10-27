"""Shared pytest fixture for every task.

The code under test is chosen with the APP_PATH environment variable, so the
same tests run against the secure reference, the insecure reference, and every
generated sample. Each test runs in a fresh temporary directory; if the task
folder has a setup_env.py with a seed(path) function, it is called first to
create the database and any files the endpoint needs.
"""
import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(request, tmp_path, monkeypatch):
    app_path = os.environ.get("APP_PATH")
    if not app_path:
        pytest.fail("Set APP_PATH to the Python file that defines `app`.")

    task_dir = Path(request.fspath).parent
    monkeypatch.chdir(tmp_path)

    setup_file = task_dir / "setup_env.py"
    if setup_file.exists():
        _load_module(setup_file, f"setup_{uuid.uuid4().hex}").seed(tmp_path)

    module = _load_module(Path(app_path).resolve(), f"app_{uuid.uuid4().hex}")
    with TestClient(module.app) as c:
        yield c
