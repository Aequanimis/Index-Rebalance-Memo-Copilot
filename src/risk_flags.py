import pandas as pd

from src.metrics import calculate_summary_metrics


def detect_risk_flags(
    constituents: pd.DataFrame,
    factor_scores: pd.DataFrame,
    backtest_metrics: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
) -> list[dict[str, str]]:
    """Apply simple, explainable starter rules to detect review risks."""
    thresholds = thresholds or {}
    turnover_limit = thresholds.get("turnover", 0.20)
    concentration_limit = thresholds.get("top5_weight", 0.45)
    liquidity_limit = thresholds.get("median_adv_usd_mm", 25.0)

    metrics = calculate_summary_metrics(constituents, factor_scores, backtest_metrics)
    flags: list[dict[str, str]] = []

    if metrics["one_way_turnover"] > turnover_limit:
        flags.append(
            {
                "id": "HIGH_TURNOVER",
                "severity": "High",
                "title": "Turnover exceeds review threshold",
                "detail": f"One-way turnover is {metrics['one_way_turnover']:.1%}.",
            }
        )

    if metrics["top5_weight"] > concentration_limit:
        flags.append(
            {
                "id": "TOP_HEAVY",
                "severity": "Medium",
                "title": "Top holdings concentration is elevated",
                "detail": f"Top 5 proposed weight is {metrics['top5_weight']:.1%}.",
            }
        )

    low_liquidity_adds = constituents[
        (constituents["action"] == "Add")
        & (constituents["median_adv_usd_mm"].astype(float) < liquidity_limit)
    ]
    if not low_liquidity_adds.empty:
        tickers = ", ".join(low_liquidity_adds["ticker"].tolist())
        flags.append(
            {
                "id": "LOW_LIQUIDITY_ADDS",
                "severity": "High",
                "title": "New additions have weak liquidity",
                "detail": f"Review trade capacity for {tickers}.",
            }
        )

    if metrics["drawdown_gap"] > 0.03:
        flags.append(
            {
                "id": "WORSE_DRAWDOWN",
                "severity": "Medium",
                "title": "Backtest drawdown is worse than benchmark",
                "detail": f"Drawdown gap is {metrics['drawdown_gap']:.1%}.",
            }
        )

    if metrics["information_ratio"] < 0.25:
        flags.append(
            {
                "id": "LOW_INFORMATION_RATIO",
                "severity": "Medium",
                "title": "Information ratio is below target",
                "detail": f"Information ratio is {metrics['information_ratio']:.2f}.",
            }
        )

    return flags


def build_review_checklist(risk_flags: list[dict[str, str]]) -> list[str]:
    """Create a short checklist tied to generated risk flags."""
    checklist = [
        "Confirm proposed weights match the approved rebalance model output.",
        "Validate index methodology constraints and eligibility screens.",
        "Review corporate actions, data quality exceptions, and stale pricing.",
    ]

    flag_ids = {flag["id"] for flag in risk_flags}
    if "HIGH_TURNOVER" in flag_ids:
        checklist.append("Confirm turnover is justified by expected factor improvement.")
    if "LOW_LIQUIDITY_ADDS" in flag_ids:
        checklist.append("Review liquidity and implementation feasibility for new additions.")
    if "TOP_HEAVY" in flag_ids:
        checklist.append("Confirm concentration remains within index committee tolerance.")
    if "WORSE_DRAWDOWN" in flag_ids:
        checklist.append("Compare stress-period behavior against the benchmark.")

    return checklist
