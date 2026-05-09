import json
import os
from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "memo_prompt.txt"


def _format_percent(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1%}"


def _format_bps(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 10000:.0f} bps"


def _json_safe(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def load_prompt_template() -> str:
    """Load the memo prompt template from the prompts directory."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_prompt(summary: dict, flags: list[dict], recommendation: str) -> str:
    """Build the full LLM prompt from calculated summary inputs and risk flags."""
    template = load_prompt_template()
    return (
        template.replace("{{SUMMARY_JSON}}", _json_safe(summary))
        .replace("{{RISK_FLAGS_JSON}}", _json_safe(flags))
        .replace("{{RECOMMENDATION}}", recommendation)
    )


def _format_name_list(names: list[dict], active_label: str) -> str:
    if not names:
        return "- None supplied."

    lines = []
    for item in names:
        ticker = item.get("ticker", "N/A")
        company = item.get("company_name", "N/A")
        sector = item.get("sector", "N/A")
        active_weight = _format_percent(item.get("active_weight"))
        lines.append(f"- {ticker} / {company} ({sector}): {active_label} {active_weight}")
    return "\n".join(lines)


def generate_mock_memo(summary: dict, flags: list[dict], recommendation: str) -> str:
    """Generate a deterministic memo without calling an LLM."""
    backtest = summary.get("backtest_metrics", {})
    flag_lines = [
        f"- {flag.get('severity', 'unknown').title()} - {flag.get('category', 'Risk')}: "
        f"{flag.get('message', '')}"
        for flag in flags
    ]
    if not flag_lines:
        flag_lines = ["- No rule-based risk flags were triggered."]

    human_review_items = [
        f"- Review required: {flag.get('message', '')}"
        for flag in flags
        if flag.get("human_review_required", False)
    ]
    if summary.get("missing_factor_count", 0) > 0:
        human_review_items.append(
            f"- Data limitation: {summary.get('missing_factor_count')} missing factor value(s) are present."
        )
    if not human_review_items:
        human_review_items = ["- Confirm final rebalance output against index methodology."]

    return f"""# Rebalance Review Memo

## Executive Summary
The proposed rebalance covers {summary.get('number_of_names', 'N/A')} names. The rule-based recommendation is **{recommendation}** based on the supplied backtest metrics, trading feasibility indicators, and data quality checks.

## Key Performance Metrics
- Annualized excess return: {_format_bps(backtest.get('annualized_excess_return'))}
- Information ratio: {backtest.get('information_ratio', 'N/A')}
- Tracking error: {_format_percent(backtest.get('tracking_error'))}
- Turnover: {_format_percent(backtest.get('turnover'))}
- One-way cost: {_format_percent(backtest.get('one_way_cost'))}
- Max active weight: {_format_percent(backtest.get('max_active_weight'))}
- Top 10 active share: {_format_percent(backtest.get('top10_active_share'))}
- Absolute turnover estimate from weights: {_format_percent(summary.get('absolute_turnover_estimate'))}

## Main Drivers of the Rebalance
Top overweight names:
{_format_name_list(summary.get('top_overweight_names', []), 'active weight')}

Top underweight names:
{_format_name_list(summary.get('top_underweight_names', []), 'active weight')}

High active weight names:
{_format_name_list(summary.get('high_active_weight_names', []), 'active weight')}

## Risk Flags
{chr(10).join(flag_lines)}

## Trading Feasibility
- Suspended stocks: {summary.get('suspended_count', 0)}
- Limit-up stocks: {summary.get('limit_up_count', 0)}
- Limit-down stocks: {summary.get('limit_down_count', 0)}
- Human review is required for any suspended or price-limited securities before trade scheduling.

## Human Review Checklist
{chr(10).join(human_review_items)}

## Recommendation
{recommendation}
"""


def generate_llm_memo(
    summary: dict,
    flags: list[dict],
    recommendation: str,
    model: str = "gpt-4o-mini",
    provider: str = "openai",
) -> str:
    """Generate a memo with a configured LLM provider when an API key is available."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    prompt = build_prompt(summary, flags, recommendation)
    provider = provider.lower().strip()

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not set")

        try:
            from openai import OpenAI

            client = OpenAI()
            response = client.responses.create(
                model=model,
                input=prompt,
            )
            memo = getattr(response, "output_text", "") or ""
            if not memo.strip():
                raise ValueError("OpenAI response did not include memo text")
            return memo
        except Exception as exc:
            raise RuntimeError(f"OpenAI memo generation failed: {exc}") from exc

    if provider == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not set")

        try:
            from google import genai

            gemini_model = model
            if model == "gpt-4o-mini":
                gemini_model = "gemini-2.5-flash"

            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model=gemini_model,
                contents=prompt,
            )
            memo = getattr(response, "text", "") or ""
            if not memo.strip():
                raise ValueError("Gemini response did not include memo text")
            return memo
        except Exception as exc:
            raise RuntimeError(f"Gemini memo generation failed: {exc}") from exc

    raise ValueError(f"Unsupported LLM provider: {provider}")


def generate_memo(
    summary: dict,
    flags: list[dict],
    recommendation: str,
    use_llm: bool = False,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
) -> str:
    """Generate a rebalance memo, using the mock generator unless LLM use is enabled."""
    if not use_llm:
        return generate_mock_memo(summary, flags, recommendation)

    try:
        return generate_llm_memo(
            summary,
            flags,
            recommendation,
            model=model,
            provider=provider,
        )
    except Exception as exc:
        fallback = generate_mock_memo(summary, flags, recommendation)
        return (
            f"LLM generation was requested but unavailable. Falling back to mock memo. "
            f"Reason: {exc}\n\n{fallback}"
        )
