# Does Asking for Security Work?

**Prompt-level mitigations for vulnerabilities in LLM-generated FastAPI code**

Joshua Day · Northern Kentucky University · Advisor: Dr. Samuel Cho · Fall 2026

> Status: experiment in progress. All numbers in the current paper draft are **hypothetical** and will be replaced with measured results.

## Research question

Does adding a security instruction, or a self-review step, to the prompt reduce security vulnerabilities in backend code written by large language models? How much of any self-review gain comes from the security wording rather than just a second pass? Does the effect differ between frontier API models and small open-weight models, and across vulnerability types?

| | |
|---|---|
| Framework | Python 3, FastAPI, SQLite |
| Vulnerabilities | CWE-89 SQL injection · CWE-78 OS command injection · CWE-22 path traversal · CWE-798 hard-coded credentials |
| Models | 2 frontier (API) · 2 small open-weight (Ollama, fit on an 8 GB GPU) |
| Prompt conditions | **P0** baseline · **P1** generic security instruction · **P2** security self-review · **P3** neutral self-review (control) |
| Detection | functional tests → exploit tests → Bandit, Semgrep → manual review sample |
| Main metric | Secure-and-correct rate: passes functional tests and no exploit succeeds |

## Models

Set in `MODELS` at the top of `scripts/generate.py`. Change them there if needed.

| ID | Model | Access |
|---|---|---|
| m1 | GPT-6.1 Sol (`gpt-6.1-sol`) | OpenAI API |
| m2 | Claude Opus 5.5 (`claude-opus-5-5`) | Anthropic API |
| m3 | Qwen2.5-Coder-7B (`qwen2.5-coder:7b`, ~4.7 GB) | local, Ollama |
| m4 | Qwen3.5-9B (`qwen3.5:9b`, ~6.6 GB) | local, Ollama |

Local models run with an 8,000-token context window so they fit in 8 GB of video memory. Check with `ollama ps` that a model shows 100% GPU while running.

## Repository layout

```
paper/            paper draft (draft.md) and figures
tasks/            one folder per task: spec, tests, secure + insecure reference
  conftest.py     shared pytest fixture: loads the app under test from $APP_PATH
scripts/
  validate_task.py  proves each task's exploit test catches the insecure reference
  generate.py       generates code samples for every task x model x condition
  evaluate.py       runs functional + exploit tests and scanners, writes results CSV
samples/          generated code (one file per sample + metadata)
results/          results.csv and analysis outputs
```

## Each task contains

| File | Purpose |
|---|---|
| `spec.md` | The plain-English endpoint request given to the model. Never mentions security. |
| `setup_env.py` | Creates the database and files the endpoint needs before each test. |
| `test_functional.py` | 3–5 tests: does the endpoint do what was asked? |
| `test_exploit.py` | 1–2 tests: does an attack succeed? A **failing** exploit test means the sample is vulnerable. |
| `reference_secure.py` | Hand-written secure solution. Must pass every test. |
| `reference_insecure.py` | Hand-written vulnerable solution. Must pass functional tests and fail an exploit test. |

To add a task, copy `tasks/cwe89_user_search/`, rename it with its CWE prefix (`cwe78_`, `cwe22_`, `cwe798_`), rewrite the files, and run `validate_task.py`.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Check that every task's tests are valid
python scripts/validate_task.py

# 2. Pull the local models and start Ollama
ollama pull qwen2.5-coder:7b
ollama pull qwen3.5:9b
ollama serve

# 3. Pilot: one task, one local model, one sample
python scripts/generate.py --tasks cwe89_user_search --models m3 --samples 1

# 4. Full run (set OPENAI_API_KEY and ANTHROPIC_API_KEY first)
python scripts/generate.py --tasks all --models all --conditions P0 P1 P2 P3 --samples 5

# 5. Evaluate
python scripts/evaluate.py
```

## Reproducibility

Exact model version strings and run dates are written to each sample's metadata file. Exploit tests run only against local code in a temporary directory.
