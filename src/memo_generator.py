from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "memo_prompt.txt"


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def generate_memo(
    metrics: dict[str, float],
    risk_flags: list[dict[str, str]],
    checklist: list[str],
) -> str:
    """Generate a structured memo draft without requiring external API access."""
    flag_text = "\n".join(
        f"- {flag['severity']}: {flag['title']} ({flag['detail']})" for flag in risk_flags
    )
    if not flag_text:
        flag_text = "- No starter-rule risk flags were triggered."

    checklist_text = "\n".join(f"- [ ] {item}" for item in checklist)

    recommendation = "Proceed to senior analyst review before committee approval."
    if any(flag["severity"] == "High" for flag in risk_flags):
        recommendation = "Pause for targeted analyst review before approving the rebalance."

    return f"""# Rebalance Review Memo Draft

## Executive Summary
The proposed rebalance covers {metrics['constituent_count']:.0f} constituents, including {metrics['adds']:.0f} additions and {metrics['deletes']:.0f} deletions. One-way turnover is {metrics['one_way_turnover']:.1%}, and the top five proposed holdings represent {metrics['top5_weight']:.1%} of the index.

## Quantitative Review
- Weighted composite factor score: {metrics['weighted_composite_score']:.1f}
- Median ADV: ${metrics['median_adv_usd_mm']:.1f} million
- Tracking error: {metrics['tracking_error']:.1%}
- Information ratio: {metrics['information_ratio']:.2f}
- Excess annualized return versus benchmark: {metrics['excess_return_bps']:.0f} bps
- Max drawdown: {metrics['max_drawdown']:.1%}

## Risk Flags
{flag_text}

## Human Review Checklist
{checklist_text}

## Recommendation
{recommendation}

## Prompt Template Used
The memo follows the local prompt template in `prompts/memo_prompt.txt`.
"""
