"""Prove that each task's tests are valid.

For every task:
  - the secure reference must pass functional AND exploit tests;
  - the insecure reference must pass functional tests and FAIL the exploit tests.
If both hold, the exploit tests can actually detect the vulnerability.

Usage: python scripts/validate_task.py [task_name ...]
"""
import sys

from common import list_tasks, run_tests


def main():
    tasks = list_tasks(sys.argv[1:] or None)
    if not tasks:
        print("No tasks found.")
        return 1

    all_ok = True
    for task in tasks:
        sec, insec = task / "reference_secure.py", task / "reference_insecure.py"
        checks = {
            "secure passes functional": run_tests(task, "test_functional.py", sec),
            "secure passes exploit": run_tests(task, "test_exploit.py", sec),
            "insecure passes functional": run_tests(task, "test_functional.py", insec),
            "insecure FAILS exploit": not run_tests(task, "test_exploit.py", insec),
        }
        ok = all(checks.values())
        all_ok &= ok
        print(f"{'OK  ' if ok else 'FAIL'} {task.name}")
        for name, passed in checks.items():
            if not passed:
                print(f"      x {name}")

    print("\nAll tasks valid." if all_ok else "\nSome tasks need fixing.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
