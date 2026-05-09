def _format_percent(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1%}"


def _format_bps(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 10000:.0f} bps"


def generate_manual_template_baseline(summary: dict) -> str:
    """Simulate a simple manual Excel-style memo template.

    This baseline includes calculated metrics but gives only minimal
    interpretation. It intentionally does not include robust risk flag logic.
    """
    backtest = summary.get("backtest_metrics", {})

    return f"""# Manual Template Baseline

## Rebalance Summary
- Number of names: {summary.get("number_of_names", "N/A")}
- Overweights: {summary.get("number_of_overweights", "N/A")}
- Underweights: {summary.get("number_of_underweights", "N/A")}
- Absolute turnover estimate: {_format_percent(summary.get("absolute_turnover_estimate"))}

## Backtest Metrics
- Annualized excess return: {_format_bps(backtest.get("annualized_excess_return"))}
- Information ratio: {backtest.get("information_ratio", "N/A")}
- Tracking error: {_format_percent(backtest.get("tracking_error"))}
- Turnover: {_format_percent(backtest.get("turnover"))}
- One-way cost: {_format_percent(backtest.get("one_way_cost"))}

## Notes
Review the rebalance output and confirm final approval with the index committee.
"""


def generate_prompt_only_baseline(raw_text: str) -> str:
    """Simulate directly asking an LLM to write a memo from raw text.

    In evaluation, this represents a prompt-only approach without deterministic
    Python calculations or rule-based risk checks. It is a placeholder so the
    project can run without an API key.
    """
    cleaned_text = raw_text.strip() or "No raw input text was provided."

    return f"""# Prompt-Only Baseline Memo

## Summary
The rebalance information was provided as unstructured text. A generic memo would summarize the main points and ask the analyst to verify the details.

## Raw Input Provided
{cleaned_text}

## Review Note
This baseline may be useful for drafting language, but it does not independently calculate metrics, validate constraints, or apply deterministic risk checks.
"""


def summarize_baseline_limitations() -> dict:
    """Return concise evaluation notes comparing baselines with this project."""
    return {
        "manual_template_baseline": (
            "Familiar and easy to audit, but slow, repetitive, and inconsistent "
            "when interns manually copy metrics and write interpretation."
        ),
        "prompt_only_baseline": (
            "Flexible for prose generation, but may miss index constraints, skip "
            "important risk checks, or invent numbers when raw inputs are unclear."
        ),
        "our_tool": (
            "More structured because Python calculates metrics first, deterministic "
            "rules detect risk flags, and GenAI only transforms the structured "
            "inputs into a business-facing memo."
        ),
    }
