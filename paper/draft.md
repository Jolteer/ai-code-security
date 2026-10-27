# Does Asking for Security Work? Prompt-Level Mitigations for Vulnerabilities in LLM-Generated FastAPI Code

Joshua Day · Oct 27, 2026

## Revision notes (v1 → v2)

v2 fixes a novelty problem in v1 and makes the study harder to criticize. All results remain **HYPOTHETICAL**; v1 is unchanged in its own doc.

| Change | Why |
| --- | --- |
| **Reframed the research gap.** v1 claimed no one had compared prompt conditions on modern backends. BaxBench (ICML 2025) already tested a generic security reminder, on FastAPI among others, including a 7B model. | A reviewer would catch this immediately. v2 cites it and builds on it. |
| **Added P3, a neutral review control** ("review and improve this code," no mention of security). | Self-review gets a second generation pass. Without P3 we cannot tell if gains come from the security cue or just from regenerating. No prior study we found separates these. This is now the main novel contribution. |
| **Primary metric is now secure-and-correct rate**, not vulnerable rate among working code. | Recent studies show security prompts often break functionality. Measuring only working code can make a model look safer by being broken (Dai et al., 2025; SecPI, 2026). |
| **Added a cost-effectiveness question** (cost and time per secure-and-correct endpoint). | Matches the ASE 392 course goal of using LLMs cost-effectively, and is useful to practitioners choosing local vs. API models. |
| **Stronger oracles per CWE**: canary files for command injection, many traversal variants, a forged-token exploit for hard-coded secrets. | v1's CWE-798 "test" was really a code inspection, and its traversal tests were thin. |
| **Prompt-wording check**: 3 paraphrases of the P1 instruction on a subset. | Tiny prompt changes can flip security outcomes (Sternfeld et al., 2026). |
| **Added 8 recent sources** (2025–2026) and verified most v1 citations. | Related work is current to Oct 2026. |
| **Pre-registration**: commit hypotheses and analysis plan to GitHub before running. | Cheap way to make results more credible. |

## Abstract

The most common advice for getting secure code from an AI assistant is to ask for it. Prior benchmarks show that this helps some models a little and can break working code. It remains unclear why self-review helps, whether small local models benefit at all, and what the gains cost.

We test four prompt conditions on 40 FastAPI endpoint tasks covering four weaknesses: SQL injection (CWE-89), OS command injection (CWE-78), path traversal (CWE-22), and hard-coded credentials (CWE-798). The four conditions are a plain request, a generic security instruction, a security self-review, and a **neutral self-review control** that asks for improvement without mentioning security. We run each with two frontier API models and two small (7–8B) open-weight models, 3,200 samples in total. Every sample runs functional tests; working samples then face exploit tests. All samples are also scanned with Bandit and Semgrep.

**HYPOTHETICAL results:** for frontier models, the security instruction raises the secure-and-correct rate by about 5 points and security self-review by about 7. The neutral review captures roughly 40% of the self-review gain, so a second pass explains part, but not most, of the effect. For small models, prompting lowers the vulnerable rate slightly but breaks enough code that the secure-and-correct rate does not improve, while self-review doubles generation time. Path traversal resists every condition, and both scanners miss most path-traversal exploits. We conclude that prompting is a cheap first layer for frontier models, not a substitute for exploit-style tests, and not worth the extra cost for small local models.

## 1. Introduction

### 1.1 The problem

AI coding assistants write code that works in a demo yet can be exploited. Models learn from public code that contains insecure patterns, and they are tuned toward code that runs and looks right, not code that resists an attacker.

The evidence is consistent across five years. Pearce et al. (2022) found about 40% of 1,689 Copilot completions vulnerable. BaxBench (Vero et al., 2025) could exploit roughly half of the backend programs that passed their functional tests. Veracode's 2026 report found the average security pass rate across 11 current models stuck at 56%, essentially unchanged from 2025, even as functional ability kept improving.

### 1.2 The cheap fix, and what we don't know about it

The most common mitigation is to ask: add "write secure code" to the prompt, or ask the model to review its own code. These are free, need no tooling, and are what a typical developer will actually do. The evidence on whether they work is mixed:

- BaxBench found a generic reminder barely helped non-reasoning models and lowered functional correctness, while reasoning models improved considerably.
- Blain and Noiseux (2026) found a security system prompt cut the vulnerable rate by only 4 points, yet models recognized 79% of their own proven-vulnerable outputs when asked to review them.
- SecPI (Wang et al., 2026) found generic reminders consistently lowered functional correctness for reasoning models.

Three questions remain open. First, when self-review helps, is it the security cue or simply a second pass at the code? No study we found includes a neutral review control. Second, do small local models, which teams choose for cost or privacy, benefit at all once lost functionality is counted? Third, what does each extra point of security cost in money and time?

### 1.3 Why it matters now

In Stack Overflow's 2025 survey, 84% of developers used or planned to use AI tools. Agentic tools mean humans read fewer of the lines that ship. Meanwhile teams increasingly run small open-weight models locally. If prompting is the only security control many developers use, they need to know when it works and what it costs.

### 1.4 Research questions

- **RQ1.** Does a generic security instruction raise the rate of code that is both correct and secure?
- **RQ2.** Does a security self-review raise it more, and how much of that gain remains after controlling for a neutral second pass?
- **RQ3.** Do these effects differ between frontier API models and small open-weight models, and what is the cost per secure-and-correct endpoint?
- **RQ4.** Which weaknesses respond to prompting, which persist, and why?
- **RQ5.** How well do Bandit and Semgrep agree with exploit tests on this code?

### 1.5 Contributions

1. The first prompt comparison we know of that separates the security cue from the second-pass effect, using a neutral review control.
2. A joint security, correctness, and cost evaluation of frontier and small local models on the same tasks.
3. A 40-task FastAPI benchmark with functional tests, exploit tests, and validated secure and insecure references, released with all prompts, samples, and scripts.
4. Evidence on which CWEs scanners and prompts both miss, with concrete failure patterns.

## 2. Related Work

### 2.1 How insecure is AI-generated code?

Early studies used prompt suites and static analysis. Pearce et al. (2022) built 89 scenarios from the CWE Top 25 and found about 40% of Copilot's programs vulnerable. SecurityEval (Siddiq and Santos, 2022) and LLMSecEval (Tony et al., 2023) released Python prompt sets for this purpose. Khoury et al. (2023) found only 5 of 21 ChatGPT programs secure, and noted the model assumed benign users unless security was raised. Fu et al. (2025) found weaknesses in about 30% of Copilot-generated Python snippets in real GitHub projects.

Industry reports agree. Veracode's 2026 report found a 56% average security pass rate across 11 current models, with no clear advantage for larger models and only a small one for reasoning models (56% vs. 51%).

### 2.2 Benchmarks that test function and security together

Static analyzers alone cannot tell whether code works, so newer benchmarks pair functional tests with security tests.

- **CWEval** (Peng et al., 2025) has 119 tasks across 31 CWEs with outcome-based oracles.
- **BaxBench** (Vero et al., 2025) has 392 backend tasks: 28 scenarios across 14 frameworks, including FastAPI, Flask, Django, and aiohttp. Security is judged by expert-written exploits against the running app, not by scanners. The best model was correct about 62% of the time, and many correct programs were exploitable.
- **AutoBaxBuilder** (Von Arx et al., 2026) uses LLMs to generate new tasks, functional tests, and exploits, cutting the human effort to build a benchmark by about 12x.

Dai et al. (2025) show why joint scoring matters. Many secure-generation techniques look safer only because they delete vulnerable lines or break the code, and once measured on the same samples, most failed to beat the base model on a joint secure-and-pass metric.

### 2.3 Prompting as a mitigation

This is the closest prior work, summarized in Table A.

**Table A.** Prior evidence on prompt-level mitigations.

| Study | Setting | Finding |
| --- | --- | --- |
| [Tony et al., 2025](https://tore.tuhh.de/entities/publication/81dbee89-4faf-4b86-83ff-290a39668f39) (TOSEM) | GPT-3 to GPT-4, 150 prompts | Weaknesses fell under several techniques, most with RCI self-review |
| [Vero et al., 2025](https://proceedings.mlr.press/v267/vero25a.html) (BaxBench, ICML) | 11 models incl. Qwen2.5 7B, 14 frameworks | Generic reminder: little gain for non-reasoning models, large for reasoning models; correctness fell (Claude 3.5 Sonnet: pass@1 53.6% → 45.5%) |
| [Blain and Noiseux, 2026](https://arxiv.org/pdf/2604.05292) (preprint) | 7 models, C/C++ and Python, Z3-proven | Security prompt cut vulnerable rate 4 points (64.8% → 60.8%); models flagged 78.7% of their own proven flaws on review |
| [Wang et al., 2026](https://www.alphaxiv.org/abs/2604.03587) (SecPI, preprint) | Reasoning models | Generic reminders lowered correctness (e.g., −6.2 points for o3); fine-tuning to internalize security reasoning worked better |
| [Yan et al., 2025](https://arxiv.org/html/2506.23034v1) (preprint) | 8 models, Python, CodeQL | Self-generated vulnerability hints helped GPT-4o a lot, small models little; functionality not measured |
| [Gong et al., 2025](https://arxiv.org/html/2408.10495v2) (EASE) | GPT-3.5, GPT-4, Python | Models repaired others' code better than their own ("blind spots"); tool-feedback loops reached 66–86% repair |
| [Sternfeld et al., 2026](https://arxiv.org/pdf/2605.29737) (preprint) | 3B–120B models, CWEval | One-character prompt changes can flip code from secure to vulnerable |

Two patterns stand out. Security prompts help capable models more than weak ones, and they often cost functionality. What none of these studies does is test whether the self-review gain comes from the security instruction or from regenerating the code.

### 2.4 Detecting vulnerabilities

- **Static analysis.** Bandit pattern-matches Python syntax trees and is fast but noisy. Semgrep matches rule patterns, some with taint tracking. CodeQL traces data flow and is more precise but slower to set up.
- **Exploit tests** run the app and attack it. They give strong evidence when an attack succeeds, but cover only the attacks someone wrote.
- **Evidence that scanners fall short.** In BaxBench, Snyk missed 64 of 237 exploitable o1 programs. Dai et al. (2025) found CodeQL can miss over 20% of vulnerabilities in generated code. Pourleyli et al. (2026) found about 13% of Python files that Bandit and Semgrep passed were in fact exploitable, with path traversal among the confirmed classes.

### 2.5 Human factors

Perry et al. (2023) found AI-assisted participants wrote less secure code and were more confident in it. Sandoval et al. (2023) found a much smaller effect in a C study with students. Both suggest that developers rarely add security checks the model did not.

### 2.6 The gap

Prompting is the mitigation developers actually use. Prior work shows it is unreliable, but cannot explain why self-review works, does not weigh security gains against lost functionality and cost for small local models, and rarely checks scanner counts against exploits on the same samples. This study addresses all three in one controlled design on a single modern framework.

## 3. Methodology

### 3.1 Overview

1. Write 40 single-endpoint FastAPI tasks, 10 per CWE, each with functional tests, exploit tests, and hand-written secure and insecure references.
2. Commit hypotheses, prompts, and the analysis plan to GitHub before generating any code (pre-registration).
3. Generate 5 samples per task from 4 models under 4 prompt conditions: 40 × 4 × 4 × 5 = 3,200 samples.
4. Score every sample with functional tests, then exploit tests; scan every sample with Bandit and Semgrep.
5. Manually review a stratified sample of 200 to check the oracles and scanners.
6. Compare secure-and-correct rates, vulnerable rates, and cost across conditions, models, and CWEs.

The work runs in two phases. Phase 1 uses 20 tasks (5 per CWE, 1,600 samples) and is a complete study on its own. Phase 2 adds the other 20 tasks.

### 3.2 Tasks

Each task is a plain-English spec for one endpoint: path, inputs, and expected behavior. Specs never mention security, mirroring how developers usually ask. Each ships with a starter environment (SQLite database, upload folder) so generated code runs in a known setting. Tasks are written from scratch, with uncommon table and field names, to reduce the chance a model has memorized a tutorial solution.

Every task is validated before use: the secure reference must pass all tests, and the insecure reference must pass the functional tests and fail at least one exploit test. This proves each exploit test can actually detect its vulnerability.

### 3.3 Security oracles

Each CWE gets an oracle designed to be deterministic and safe to run. All tests run in a Docker container with no network access.

| CWE | Example task | Oracle (sample is vulnerable if…) |
| --- | --- | --- |
| CWE-89 SQL injection | `GET /users/search?name=` returns users with that exact name | a tautology (`' OR '1'='1`), UNION, or error-based payload returns rows or a database error |
| CWE-78 OS command injection | `POST /tools/ping` returns ping output for a host | a payload using `;`, `&&`, `\|`, `$( )`, or backticks creates a unique canary file. A stub `ping` on the PATH makes results deterministic |
| CWE-22 Path traversal | `GET /files/{name}` returns a file from `uploads/` | any of 8 variants (`../`, URL-encoded, double-encoded, absolute path, backslash, symlink inside `uploads/`) returns a canary file placed outside `uploads/` |
| CWE-798 Hard-coded credentials | `POST /login` returns a JWT; `GET /me` requires it | a token forged with any string literal from the source is accepted by `GET /me`. Threat model: the source is public, as in an open-source or leaked repo |

For CWE-798, an AST pass extracts every string literal, and each one is tried as a signing key. This turns "secret is a literal" into a working exploit rather than a style judgment.

### 3.4 Models

| ID | Type | Example choice | Access |
| --- | --- | --- | --- |
| M1 | Frontier, reasoning | a current OpenAI reasoning model | API |
| M2 | Frontier | a current Anthropic Claude model | API |
| M3 | Small open-weight (~7B) | Qwen2.5-Coder-7B-Instruct or newer | local, Ollama |
| M4 | Small open-weight (~8B) | Llama-3.1-8B-Instruct or newer | local, Ollama |

We record exact model version strings, run dates, and any reasoning-effort setting. Local models run on a consumer laptop, which is the realistic setting for a team choosing them to save cost. Temperature is 0.7 where the API allows it; otherwise provider defaults are used and recorded.

### 3.5 Prompt conditions

| Condition | What the model receives | What it isolates |
| --- | --- | --- |
| **P0** Baseline | System: "You are an expert Python backend developer. Return only the complete Python code." User: the spec. | Default behavior |
| **P1** Security instruction | P0 plus: "Write secure code. Follow OWASP secure-coding practices and avoid common vulnerabilities." | Effect of asking |
| **P2** Security self-review | P0, then: "Review the code above for security vulnerabilities. Return a corrected, complete version." | Asking + second pass |
| **P3** Neutral self-review | P0, then: "Review the code above and return an improved, complete version." | Second pass only |

The security cue's own effect is P2 minus P3. Only the final answer is evaluated in P2 and P3. P1 is deliberately generic and never names a CWE, because naming it would hand the model the answer.

**Prompt-wording check.** Small wording changes can flip outcomes, so on 10 tasks we also run two paraphrases of the P1 instruction. If results differ by more than the confidence interval, we report it.

### 3.6 Generation

A script sends each prompt, extracts the code block, and saves the code, the raw responses, token counts, wall-clock time, and model version. Runs resume where they stop, and each model's run is finished in one sitting so a hosted model cannot change mid-study.

### 3.7 Measurement

1. **Functional tests** (3–5 per task, pytest). A sample that fails is incorrect.
2. **Exploit tests** (1–2 per task) run on every working sample.
3. **Bandit** (all plugins) and **Semgrep** (Python and OWASP Top Ten rulesets) scan every sample. Findings are mapped to CWE IDs. CodeQL is optional and reported only if time allows.
4. **Manual review** of 200 working samples, stratified by model, condition, and CWE. The researcher labels each as vulnerable or not; Dr. Cho independently labels 40, and agreement is reported as Cohen's κ.

### 3.8 Metrics

| Metric | Definition |
| --- | --- |
| **Secure-and-correct rate (SC)** | Share of all samples that pass functional tests and no exploit succeeds. **Primary outcome.** Equivalent to BaxBench's sec_pass@1. |
| Functional pass rate (FP) | Share of samples passing all functional tests |
| Vulnerable rate (VR) | Share of *working* samples where an exploit succeeds. Secondary, because it ignores broken code. |
| Cost per 100 SC | API cost (frontier) or generation time (local) to obtain 100 secure-and-correct endpoints |
| Scanner recall and precision | Against the exploit oracle on all working samples, and against manual labels on the 200 reviewed |

### 3.9 Statistics

The unit of analysis is the task, since samples of the same task are not independent. The primary model is a mixed-effects logistic regression: secure-and-correct ~ condition × model type + CWE, with random intercepts for task and model. Planned contrasts are P1 vs. P0, P2 vs. P0, and P2 vs. P3. As a check, per-task rates are compared with Wilcoxon signed-rank tests, Holm-corrected, with bootstrap 95% confidence intervals resampled by task.

Before the full run, we simulate the design using pilot data to estimate power. With 40 tasks, effects of about 10 points pooled across models should be detectable; per-model contrasts will only detect large effects, and are reported as estimates with intervals rather than as significance tests.

### 3.10 Reproducibility and ethics

No human participants are involved beyond the researchers' own labeling. Exploits run only against local, sandboxed code with canary files, never real system files. We release tasks, references, prompts, raw responses, samples, tool versions, and analysis scripts.

## 4. Results (HYPOTHETICAL)

> **Everything in this section is HYPOTHETICAL.** No experiments have been run. The numbers are predictions chosen to be consistent with prior work (BaxBench, SecPI, Blain and Noiseux, Dai et al.). They must be replaced with measured data before any submission.

### 4.1 Correctness, vulnerability, and the joint outcome (RQ1–RQ3)

**Table 1 (HYPOTHETICAL).** Functional pass rate (FP), vulnerable rate among working samples (VR), and secure-and-correct rate (SC, primary outcome). n = 200 samples per cell. SC = FP × (1 − VR).

| Model | Condition | FP | VR | **SC** |
| --- | --- | --- | --- | --- |
| M1 Frontier (reasoning) | P0 Baseline | 90% | 20% | **72.0%** |
| | P1 Security instruction | 87% | 11% | **77.4%** |
| | P2 Security review | 86% | 8% | **79.1%** |
| | P3 Neutral review | 88% | 15% | **74.8%** |
| M2 Frontier | P0 | 91% | 17% | **75.5%** |
| | P1 | 89% | 11% | **79.2%** |
| | P2 | 88% | 7% | **81.8%** |
| | P3 | 90% | 13% | **78.3%** |
| M3 Small (~7B) | P0 | 62% | 42% | **36.0%** |
| | P1 | 57% | 39% | **34.8%** |
| | P2 | 53% | 35% | **34.5%** |
| | P3 | 58% | 40% | **34.8%** |
| M4 Small (~8B) | P0 | 55% | 48% | **28.6%** |
| | P1 | 51% | 45% | **28.1%** |
| | P2 | 46% | 42% | **26.7%** |
| | P3 | 52% | 47% | **27.6%** |

**Frontier models.** Averaged over M1 and M2, SC rises from 73.8% (P0) to 78.3% with the instruction (+4.6 points) and to 80.5% with security review (+6.7). Neutral review reaches 76.6% (+2.8). So about 40% of the self-review gain comes from simply making a second pass, and about 60% from the security cue (P2 vs. P3: +3.9 points, hypothetical p < .01).

**Small models.** Prompting does lower VR, from 45% to 38.5% under security review. But it breaks more code at the same time: FP falls from 58.5% to 49.5%. The net effect on SC is zero or slightly negative in every condition (32.3% at P0, 30.6% at P2). In the mixed-effects model, the condition × model-type interaction is significant (hypothetical p < .01).

### 4.2 By vulnerability type (RQ4)

**Table 2 (HYPOTHETICAL).** VR among working samples, pooled across all four models. Pooled over samples, so the means differ slightly from simple averages of Table 1.

| CWE | P0 | P1 | P2 | P3 | Change P0→P2 |
| --- | --- | --- | --- | --- | --- |
| CWE-89 SQL injection | 10% | 5% | 4% | 8% | −6 pts |
| CWE-78 OS command injection | 36% | 26% | 20% | 31% | −16 pts |
| CWE-22 Path traversal | 48% | 42% | 38% | 45% | −10 pts |
| CWE-798 Hard-coded credentials | 30% | 29% | 24% | 28% | −6 pts |

- **SQL injection is nearly solved by default.** Models already use parameterized queries in most samples.
- **Command injection responds most to prompting.** Models switch from `shell=True` to an argument list once security is mentioned.
- **Path traversal persists.** Typical failures check the raw string for `..` but never resolve the final path, so encoded and symlink variants get through.
- **The instruction alone does nothing for hard-coded secrets.** Models treat a placeholder like `"change-me"` as acceptable example code. Only explicit review removes some of them.

### 4.3 Scanners vs. exploits (RQ5)

**Table 3 (HYPOTHETICAL).** Scanner recall per CWE, using the exploit oracle as ground truth on all working samples.

| CWE | Bandit recall | Semgrep recall |
| --- | --- | --- |
| CWE-89 | 0.92 | 0.85 |
| CWE-78 | 0.95 | 0.80 |
| CWE-22 | 0.25 | 0.35 |
| CWE-798 | 0.78 | 0.62 |
| **Overall precision** | 0.45 | 0.67 |

Both scanners do well on injection and miss most path traversal. Bandit flags many safe `subprocess` calls, so a Bandit-only study would overstate vulnerability; a Semgrep-only study would understate it. On the 200 manually reviewed samples, the exploit oracle agrees with manual labels 94% of the time, and the two human labelers agree with κ = 0.81. Most disagreements are path checks that our 8 variants did not beat but a reviewer judged bypassable, so the measured VR is a lower bound.

### 4.4 Cost (RQ3)

**Table 4 (HYPOTHETICAL).** Cost to obtain 100 secure-and-correct endpoints. API cost for frontier models; laptop generation time for local models. Real values will use prices and timings measured at run time.

| Model | P0 | P1 | P2 | P3 |
| --- | --- | --- | --- | --- |
| M1 Frontier, USD | $1.11 | $1.10 | $2.28 | $2.27 |
| M2 Frontier, USD | $1.32 | $1.33 | $2.69 | $2.68 |
| M3 Small, minutes | 116 | 125 | 266 | 259 |
| M4 Small, minutes | 175 | 184 | 400 | 381 |

The security instruction is effectively free: for frontier models it improves SC at the same cost per secure endpoint. Self-review roughly doubles the cost per secure endpoint for every model. For frontier models that buys about 2 more points of SC over P1; for small models it buys nothing.

### 4.5 Prompt wording

On the 10-task paraphrase check, the three wordings of the P1 instruction differ by at most 2 points of SC for frontier models, inside the confidence intervals. The P1 effect is not an artifact of one sentence.

### 4.6 Key findings (HYPOTHETICAL)

1. **For frontier models, asking helps a little and costs nothing.** The generic instruction raises SC by about 5 points at no extra cost per secure endpoint.
2. **Self-review works mostly because of the security cue.** About 60% of its gain disappears when the review prompt does not mention security.
3. **For small local models, prompting is a wash.** Each fix to security breaks other code, and secure-and-correct output never improves.
4. **Path traversal beats both prompting and scanners.** It stays near 40% vulnerable in every condition, and scanners miss most of it.
5. **Single-scanner studies are unreliable.** Bandit and Semgrep disagree in opposite directions on the same code.

## 5. Discussion

If the hypothetical results hold, a security instruction belongs in every prompt to a frontier model because it is free, but it is not a security control. It shifts the odds without guaranteeing anything, and for small local models it does not even shift the odds of getting secure, working code.

### 5.1 Why self-review works

The P3 control separates two explanations. If self-review worked only because the model gets another try, P3 would match P2. In our hypothesized results it captures about 40% of the gain, so the security wording itself does most of the work. This fits Blain and Noiseux's finding that models recognize most of their own flaws when asked to look for them: the knowledge is there, but it is not used during first-pass generation unless the prompt points to it.

### 5.2 Why small models don't benefit

Small models appear to follow the security cue by changing code they do not fully understand, such as adding validation that rejects legitimate input or rewriting a working query. Each fix is as likely to break the endpoint as to secure it. This matches Yan et al.'s finding that weaker models gain little from security hints, and Dai et al.'s finding that many techniques trade functionality for apparent security. For teams using small local models, security has to come from outside the model: tests, scanners, and review.

### 5.3 Implications for an AI-assisted development workflow

| Stage | Recommendation |
| --- | --- |
| Prompting (frontier models) | Always add a one-line security instruction; it costs nothing. |
| Prompting (small local models) | Don't rely on it; budget for stronger testing instead. |
| Review | Ask for a security-specific review only when a 2x cost per endpoint is acceptable. A generic "improve this" review is a weaker substitute. |
| Testing | Add exploit-style tests for file access and command execution to CI. Scanners alone will miss path traversal. |
| Scanning | Run at least two scanners; Bandit and Semgrep fail in opposite directions. Add a secret scanner for hard-coded credentials. |

### 5.4 Threats to validity

- **Scope.** One language, one framework, four CWEs, single-endpoint tasks. Real services span many files, and many vulnerabilities come from how parts interact.
- **Prompt wording.** The paraphrase check covers P1 only; P2 and P3 wording could matter too.
- **Oracle coverage.** Exploit tests catch only the attacks we wrote, so VR is a lower bound. Manual review estimates how much is missed.
- **CWE-798 threat model.** Treating any literal key as exploitable assumes the source is public. In a private repo, the practical risk is lower.
- **Model drift.** Hosted models change without notice; results describe specific versions on specific dates.
- **Contamination.** Common endpoint patterns may appear in training data. Fresh task wording reduces but does not remove this risk.
- **Labeling.** Manual labels come mainly from one undergraduate researcher; agreement with Dr. Cho on 40 samples measures but does not remove this risk.
- **Hardware.** Local timing depends on the laptop used; relative timings across conditions are more reliable than absolute minutes.
- **Statistical power.** With 40 tasks, per-model effects under about 10 points may not be detectable.

### 5.5 Future work

- Test CWE-specific instructions ("use parameterized queries") against generic ones.
- Feed scanner and exploit-test results back to the model and measure fix rate without functional loss.
- Scale task creation with AutoBaxBuilder-style generation, verified by hand.
- Test whether security-reasoning fine-tuning (as in SecPI) helps small local models where prompting does not.
- Extend to multi-file, agentic generation of a whole service.
- Re-run on each new model generation to track whether prompting effects change.

## 6. Conclusion

Asking an AI assistant for secure code is the cheapest and most common security measure a developer can take. This study tests it under controlled conditions on FastAPI backends, across frontier and small models, four CWEs, and four prompt conditions, scoring code by whether it both works and resists real exploits.

Our hypothetical results predict a clear but limited benefit. For frontier models, a one-line instruction improves secure-and-correct output for free, and a security-specific review improves it further, mostly because of the security wording rather than the second pass. For small local models, prompting trades correctness for security with no net gain. Path traversal resists both prompting and scanning.

If confirmed, these findings mean prompting should be treated as a first layer, never the only one. AI-generated backend code should pass exploit-style tests and more than one scanner before it ships, and teams choosing small local models to save money should expect to spend that savings on verification.

## References

Key: **[Verified]** = checked online on Oct 27, 2026 (title, year, venue). **[Found]** = located on Oct 16, 2026. **[Check]** = needs confirming before submission. **[Preprint]** = not peer reviewed. Full author lists for "et al." entries still need checking against each paper.

### Peer-reviewed

1. Pearce, H., Ahmad, B., Tan, B., Dolan-Gavitt, B., & Karri, R. (2022). Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions. *IEEE S&P*. [Found] [arXiv](https://arxiv.org/abs/2108.09293)
2. Perry, N., Srivastava, M., Kumar, D., & Boneh, D. (2023). Do Users Write More Insecure Code with AI Assistants? *ACM CCS*. [Found] [arXiv](https://arxiv.org/abs/2211.03622)
3. Sandoval, G., Pearce, H., Nys, T., Karri, R., Garg, S., & Dolan-Gavitt, B. (2023). Lost at C: A User Study on the Security Implications of Large Language Model Code Assistants. *USENIX Security*. [Found] [USENIX](https://www.usenix.org/conference/usenixsecurity23/presentation/sandoval)
4. Siddiq, M. L., & Santos, J. C. S. (2022). SecurityEval Dataset. *MSR4P&S workshop*. [Found] [GitHub](https://github.com/s2e-lab/securityeval)
5. Tony, C., Mutas, M., Díaz Ferreyra, N. E., & Scandariato, R. (2023). LLMSecEval: A Dataset of Natural Language Prompts for Security Evaluations. *MSR 2023, Data Showcase*. [Verified] [MSR 2023](https://conf.researchr.org/details/msr-2023/msr-2023-data-showcase/18/LLMSecEval-A-Dataset-of-Natural-Language-Prompts-for-Security-Evaluations)
6. He, J., & Vechev, M. (2023). Large Language Models for Code: Security Hardening and Adversarial Testing. *ACM CCS*, DOI 10.1145/3576915.3623175. [Verified via DOI] [arXiv](https://arxiv.org/abs/2302.05319v2)
7. Fu, Y., et al. (2025). Security Weaknesses of Copilot-Generated Code in GitHub Projects: An Empirical Study. *ACM TOSEM*. [Found] [arXiv](https://arxiv.org/abs/2310.02059)
8. Tony, C., Díaz Ferreyra, N. E., Mutas, M., Dhif, S., & Scandariato, R. (2025). Prompting Techniques for Secure Code Generation: A Systematic Investigation. *ACM TOSEM* 34(8), 1–53. DOI 10.1145/3722108. [Verified] [TUHH](https://tore.tuhh.de/entities/publication/81dbee89-4faf-4b86-83ff-290a39668f39)
9. Peng, J., et al. (2025). CWEval: Outcome-driven Evaluation on Functionality and Security of LLM Code Generation. *LLM4Code workshop at ICSE*. [Found] [arXiv](https://arxiv.org/abs/2501.08200)
10. Vero, M., et al. (2025). BaxBench: Can LLMs Generate Correct and Secure Backends? *ICML*, PMLR 267. [Verified] [PMLR](https://proceedings.mlr.press/v267/vero25a.html)
11. Spracklen, J., et al. (2025). We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs. *USENIX Security*. [Found] [USENIX](https://www.usenix.org/conference/usenixsecurity25/presentation/spracklen)
12. Gong, J., Duan, N., Tao, Z., Gong, Z., Yuan, Y., & Huang, M. (2025). How Well Do Large Language Models Serve as End-to-End Secure Code Agents for Python? *EASE*. [Verified] [arXiv](https://arxiv.org/html/2408.10495v2)
13. Von Arx, T., Mündler, N., Vero, M., Baader, M., & Vechev, M. (2026). AutoBaxBuilder: Bootstrapping Code Security Benchmarking. *ICML*, PMLR 306. [Verified] [PMLR](https://proceedings.mlr.press/v306/arx26a.html)

### Preprints

14. Khoury, R., Avila, A. R., Brunelle, J., & Camara, B. M. (2023). How Secure is Code Generated by ChatGPT? arXiv:2304.09655. [Verified as arXiv; published venue Check] [alphaXiv](https://alphaxiv.org/overview/2304.09655v1)
15. Dai, S.-C., Xu, J., & Tao, G. (2025). A Comprehensive Study of LLM Secure Code Generation (earlier title: Rethinking the Evaluation of Secure Code Generation). arXiv:2503.15554. [Verified] [Preprint] [arXiv](https://arxiv.org/pdf/2503.15554)
16. Yan, H., Zhang, X., Vaidya, S. S., & Yao, Z. (2025). Guiding AI to Fix Its Own Flaws: An Empirical Study on LLM-Driven Secure Code Generation. arXiv:2506.23034. [Verified] [Preprint] [arXiv](https://arxiv.org/html/2506.23034v1)
17. Blain, D., & Noiseux, M. (2026). Broken by Default: A Formal Verification Study of Security Vulnerabilities in AI-Generated Code. arXiv:2604.05292. [Verified] [Preprint] [arXiv](https://arxiv.org/pdf/2604.05292)
18. Wang, H., Mündler, N., Vero, M., He, J., Song, D., & Vechev, M. (2026). SecPI: Secure Code Generation with Reasoning Models via Security Reasoning Internalization. arXiv:2604.03587. [Verified] [Preprint] [alphaXiv](https://www.alphaxiv.org/abs/2604.03587)
19. Sternfeld, A., Dolamic, L., & Kucharavy, A. (2026). Minimal Prompt Perturbations Lead to Code Vulnerabilities: Prompt Fragility and Hidden-State Signals in Coding LLMs. arXiv:2605.29737. [Verified] [Preprint] [arXiv](https://arxiv.org/pdf/2605.29737)
20. Pourleyli, J., Urmi, M. D., & Melo, G. (2026). Beyond Static Guarantees: Measuring the Static-Pass Dynamic-Fail Gap in Security-Sensitive and LLM-Generated Python Code. arXiv:2609.10762. [Verified] [Preprint] [arXiv](https://arxiv.org/pdf/2609.10762)
21. Bhatt, M., et al. (2023). Purple Llama CyberSecEval: A Secure Coding Benchmark for Language Models. arXiv preprint, Meta. [Check] [Preprint]

### Industry reports

22. Veracode (2025). 2025 GenAI Code Security Report. [Found] [Preprint]
23. Veracode (2026). 2026 GenAI Code Security Report, released July 28, 2026. [Verified] [Press release](https://www.veracode.com/news/llms-are-getting-smarter-but-not-safer-veracode-2026-genai-code-security-report-finds-ai-generated-code-security-has-stalled-at-56%25-pass-rate/)
24. Stack Overflow (2025). 2025 Developer Survey. [Found] [Press release](https://stackoverflow.co/company/press/archive/stack-overflow-2025-developer-survey/)

### Tools and standards (cite official documentation)

25. Bandit (PyCQA). 26. Semgrep. 27. CodeQL (GitHub). 28. MITRE Common Weakness Enumeration (CWE).
