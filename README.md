# Index Rebalance Memo Copilot

## Project Overview

Index Rebalance Memo Copilot is a small GenAI workflow tool for one narrow business use case: helping an index research intern convert rebalance model outputs into a structured review memo.

The project combines deterministic Python calculations, rule-based risk detection, and optional GenAI memo writing. It is designed as a course final project artifact that is simple to run, inspect, and evaluate.

## Context, User, and Problem

The target user is an index research intern or quantitative research assistant.

In a typical index enhancement workflow, the user reviews rebalance outputs from a model and prepares a rebalance review memo for a senior analyst or committee. The raw inputs are usually fragmented across constituent weights, benchmark weights, factor scores, backtest metrics, transaction cost assumptions, and trading constraints.

Manual memo writing is slow and inconsistent. Important risks can be missed when the intern has to copy numbers across spreadsheets, interpret model outputs, and write a business-facing memo under time pressure.

## Solution and Design

The project is implemented as a Streamlit app with a simple review workflow:

- Load demo CSV data or uploaded rebalance files.
- Calculate rebalance metrics with deterministic Python code.
- Detect risk flags using transparent rule-based logic.
- Generate a concise memo using either a mock generator or optional GenAI.
- Display a human review checklist before approval.

The core design principle is:

**Python calculates. Rules detect risks. GenAI writes the memo. Human makes the final decision.**

This separation keeps numerical work and risk checks deterministic while still using GenAI where it is useful: transforming structured inputs into a clear business memo.

If no API key is available, the app falls back to a deterministic mock memo so the project can still run in a grading environment.

## Why GenAI Is Useful

GenAI is useful here because the final artifact is a written business memo, not just a table of metrics. The model can help translate structured quantitative outputs into clear language for a senior analyst.

However, GenAI should not be trusted to calculate metrics, detect all rule-based risks, or make final investment decisions. In this project, those responsibilities stay with Python logic and human review.

## Baselines

The project compares the proposed workflow against two simpler baselines:

- **Manual Excel-style template:** familiar and easy to audit, but slow and inconsistent. It includes metrics with limited interpretation and no robust risk logic.
- **Prompt-only LLM baseline:** flexible for prose generation, but may miss constraints, overlook risk flags, or invent numbers if raw inputs are unclear.
- **Index Rebalance Memo Copilot:** more reliable because metrics are calculated first, risk flags are detected by rules, and GenAI only transforms structured inputs into a memo.

## Evaluation and Results

The evaluation workflow is in `eval/evaluate.py`. It uses 8 realistic synthetic rebalance scenarios:

1. Normal rebalance with stable metrics
2. High tracking error
3. High turnover
4. Suspended stock risk
5. Missing factor data
6. Concentration risk
7. Cost sensitivity risk
8. Poor performance but low risk

For each case, the evaluation compares detected risk categories against `eval/expected_flags.json` and calculates precision, recall, and F1 score. It also includes a 0-2 rubric comparison across:

- Metric accuracy
- Risk flag coverage
- Business usefulness
- Hallucination control
- Human review clarity

Current key results from `eval/evaluation_results.csv`:

| Method | Average Score |
| --- | ---: |
| Manual template baseline | 1.20 / 2.00 |
| Prompt-only baseline | 0.60 / 2.00 |
| Index Rebalance Memo Copilot | 2.00 / 2.00 |

Risk flag performance for the proposed tool:

| Metric | Result |
| --- | ---: |
| Average precision | 1.000 |
| Average recall | 1.000 |
| Average F1 | 1.000 |

What worked: the deterministic rules correctly detected the expected risk categories in the synthetic scenarios, and the structured workflow produced clearer human review outputs than the baselines.

What failed or remains limited: the evaluation uses synthetic cases and hand-scored rubric values. In a real deployment, thresholds and expected flags should be validated with historical rebalance reviews and analyst feedback.

## Artifact Snapshot

Add screenshots here when preparing the final submission:

- `screenshots/app_upload.png`
- `screenshots/memo_output.png`
- `screenshots/evaluation_table.png`

## Setup and Usage

Clone the repository:

```bash
git clone <repo-url>
cd Index-Rebalance-Memo-Copilot
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment on Windows:

```bash
.venv\Scripts\activate
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

Run the evaluation:

```bash
python eval/evaluate.py
```

## API Key Setup

The app works in mock mode without an API key. This is the default and is recommended for grading or local inspection.

If you want LLM-generated memo wording, create a `.env` file in the project root and add an API key:

```text
OPENAI_API_KEY=your_openai_key_here
```

The app also supports Gemini through `GEMINI_API_KEY` or `GOOGLE_API_KEY`:

```text
GEMINI_API_KEY=your_gemini_key_here
```

Do not commit `.env`. The `.gitignore` file excludes it.

## Limitations and Human Review

This project is a prototype using synthetic data. It does not make investment decisions and should not be used as a production index governance system.

A human analyst should review:

- Abnormal tracking error, turnover, cost, or concentration metrics
- Missing factor data
- Suspended, limit-up, or limit-down securities
- Index methodology constraints and eligibility screens
- Final recommendation language before any approval decision

The tool is designed to assist the memo-writing workflow, not replace professional judgment.

## Repository Structure

```text
.
|   app.py
|   README.md
|   requirements.txt
|
+---data
|       demo_backtest_metrics.csv
|       demo_constituents.csv
|       demo_factor_scores.csv
|
+---eval
|       evaluate.py
|       evaluation_results.csv
|       expected_flags.json
|
+---prompts
|       memo_prompt.txt
|
+---screenshots
|       .gitkeep
|
\---src
        baseline.py
        data_loader.py
        memo_generator.py
        metrics.py
        risk_flags.py
        __init__.py
```
