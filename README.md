# Index Rebalance Memo Copilot

## Context, User, and Problem

Index research teams review periodic rebalance model outputs before a committee or senior analyst approves changes. A research intern often needs to convert raw constituent files, factor scores, and backtest metrics into a concise review memo.

This project focuses on one narrow workflow: helping an index research intern draft a structured rebalance review memo with quantitative metrics, risk flags, and a human review checklist.

## Solution and Design

The app is a small Streamlit workflow that:

- Loads demo rebalance inputs from CSV files.
- Computes portfolio, turnover, factor, and backtest summary metrics.
- Detects simple risk flags such as high turnover, concentration, weak liquidity, and adverse backtest behavior.
- Generates a structured memo draft from a prompt template and deterministic baseline logic.
- Keeps the human analyst in charge through a review checklist and explicit limitations.

The current starter version does not require an API key. It is designed to be easy for a grader to run locally and inspect.

## Evaluation and Results

The `eval/evaluate.py` script compares generated risk flags against `eval/expected_flags.json` and writes a lightweight result file to `eval/evaluation_results.csv`.

The starter evaluation measures:

- Expected flag coverage
- Unexpected generated flags
- Basic pass/fail status

## Artifact Snapshot

Primary artifacts:

- Streamlit app: `app.py`
- Demo data: `data/`
- Prompt template: `prompts/memo_prompt.txt`
- Core logic: `src/`
- Evaluation harness: `eval/`
- Screenshot placeholder: `screenshots/.gitkeep`

## Setup and Usage

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

Run the evaluation script:

```bash
python eval/evaluate.py
```

## Limitations and Human Review

This is a course-project prototype, not a production investment system. The memo draft should be reviewed by a qualified human before use.

Known limitations:

- Demo data is synthetic and simplified.
- Risk thresholds are illustrative and should be calibrated.
- The memo generator is deterministic by default and does not call a hosted model.
- The tool does not verify corporate actions, regulatory constraints, index methodology changes, or live liquidity data.
