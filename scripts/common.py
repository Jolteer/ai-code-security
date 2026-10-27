"""Helpers shared by the scripts."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
SAMPLES_DIR = ROOT / "samples"
RESULTS_DIR = ROOT / "results"

CWE_BY_PREFIX = {
    "cwe89": "CWE-89",
    "cwe78": "CWE-78",
    "cwe22": "CWE-22",
    "cwe798": "CWE-798",
}


def list_tasks(selected=None):
    tasks = sorted(p for p in TASKS_DIR.iterdir() if p.is_dir() and (p / "spec.md").exists())
    if selected and selected != ["all"]:
        tasks = [t for t in tasks if t.name in selected]
    return tasks


def cwe_of(task_name: str) -> str:
    return CWE_BY_PREFIX.get(task_name.split("_")[0], "unknown")


def run_tests(task_dir: Path, test_file: str, app_path: Path, timeout: int = 60) -> bool:
    """Run one test file against one app file. True if every test passes."""
    env = {**os.environ, "APP_PATH": str(Path(app_path).resolve())}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             str(task_dir / test_file)],
            cwd=TASKS_DIR, env=env, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0
