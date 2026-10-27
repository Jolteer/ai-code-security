"""Evaluate every generated sample and write results/results.csv.

For each sample:
  1. functional tests  -> functional_pass
  2. exploit tests     -> vulnerable (only meaningful if functional_pass)
  3. Bandit / Semgrep  -> did the scanner flag anything? (if installed)

Primary outcome: secure_correct = passes functional tests AND no exploit succeeds.

Usage: python scripts/evaluate.py [--no-scanners]
"""
import argparse
import json
import shutil
import subprocess

import pandas as pd

from common import RESULTS_DIR, SAMPLES_DIR, TASKS_DIR, run_tests


def bandit_flags(path):
    if not shutil.which("bandit"):
        return None
    proc = subprocess.run(["bandit", "-q", "-f", "json", str(path)],
                          capture_output=True, text=True)
    try:
        issues = json.loads(proc.stdout).get("results", [])
    except json.JSONDecodeError:
        return None
    return ";".join(sorted({f"{i['test_id']}:CWE-{i.get('issue_cwe', {}).get('id', '?')}"
                            for i in issues}))


def semgrep_flags(path):
    if not shutil.which("semgrep"):
        return None
    proc = subprocess.run(
        ["semgrep", "scan", "--config", "p/python", "--config", "p/owasp-top-ten",
         "--json", "--quiet", "--metrics", "off", str(path)],
        capture_output=True, text=True,
    )
    try:
        results = json.loads(proc.stdout).get("results", [])
    except json.JSONDecodeError:
        return None
    return ";".join(sorted({r["check_id"].split(".")[-1] for r in results}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-scanners", action="store_true")
    args = ap.parse_args()

    rows = []
    for meta_path in sorted(SAMPLES_DIR.rglob("s*.json")):
        meta = json.loads(meta_path.read_text())
        code_path = meta_path.with_suffix(".py")
        task_dir = TASKS_DIR / meta["task"]

        functional = run_tests(task_dir, "test_functional.py", code_path)
        exploit_ok = run_tests(task_dir, "test_exploit.py", code_path) if functional else None

        row = {
            "task": meta["task"],
            "cwe": meta["cwe"],
            "model_id": meta["model_id"],
            "model_type": meta["model_type"],
            "model_version": meta["model_version"],
            "condition": meta["condition"],
            "sample": meta["sample"],
            "seconds": meta.get("seconds"),
            "functional_pass": functional,
            # vulnerable is only defined for working code
            "vulnerable": (not exploit_ok) if functional else None,
            "sample_path": str(code_path.relative_to(SAMPLES_DIR)),
        }
        if not args.no_scanners:
            row["bandit"] = bandit_flags(code_path)
            row["semgrep"] = semgrep_flags(code_path)
        rows.append(row)
        print(f"{row['task']} {row['model_id']} {row['condition']} s{row['sample']}: "
              f"functional={functional} vulnerable={row['vulnerable']}")

    if not rows:
        print("No samples found. Run scripts/generate.py first.")
        return

    df = pd.DataFrame(rows)
    # Primary outcome: works AND no exploit succeeded (BaxBench's sec_pass@1).
    df["secure_correct"] = df["functional_pass"] & (df["vulnerable"] == False)  # noqa: E712
    RESULTS_DIR.mkdir(exist_ok=True)
    df.to_csv(RESULTS_DIR / "results.csv", index=False)

    print("\nSecure-and-correct rate, PRIMARY (model x condition):")
    print(df.pivot_table(index="model_id", columns="condition",
                         values="secure_correct", aggfunc="mean").round(3))

    working = df[df["functional_pass"]].copy()
    working["vulnerable"] = working["vulnerable"].astype(bool)
    print("\nFunctional pass rate (model x condition):")
    print(df.pivot_table(index="model_id", columns="condition",
                         values="functional_pass", aggfunc="mean").round(3))
    if len(working):
        print("\nVulnerable rate among working samples (model x condition):")
        print(working.pivot_table(index="model_id", columns="condition",
                                  values="vulnerable", aggfunc="mean").round(3))
        print("\nVulnerable rate by CWE x condition:")
        print(working.pivot_table(index="cwe", columns="condition",
                                  values="vulnerable", aggfunc="mean").round(3))
    print(f"\nWrote {RESULTS_DIR / 'results.csv'}")


if __name__ == "__main__":
    main()
