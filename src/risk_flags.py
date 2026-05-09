import pandas as pd

from src.metrics import calculate_summary_metrics


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def detect_risk_flags(
    constituents: pd.DataFrame,
    factor_scores: pd.DataFrame,
    backtest_metrics: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
) -> list[dict[str, str]]:
    """Apply simple, explainable starter rules to detect review risks."""
    thresholds = thresholds or {}
    turnover_limit = thresholds.get("turnover", 0.30)
    concentration_limit = thresholds.get("top5_weight", 0.45)
    liquidity_limit = thresholds.get("avg_daily_value", 100_000_000.0)
    max_active_limit = thresholds.get("max_active_weight", 0.04)
    active_share_limit = thresholds.get("top10_active_share", 0.30)

    metrics = calculate_summary_metrics(constituents, factor_scores, backtest_metrics)
    flags: list[dict[str, str]] = []

    if metrics["backtest_turnover"] > turnover_limit:
        flags.append(
            {
                "id": "HIGH_TURNOVER",
                "severity": "High",
                "title": "Turnover exceeds review threshold",
                "detail": f"Backtest turnover is {metrics['backtest_turnover']:.1%}.",
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

    low_liquidity_names = constituents[
        constituents["avg_daily_value"].astype(float) < liquidity_limit
    ]
    if not low_liquidity_names.empty:
        tickers = ", ".join(low_liquidity_names["ticker"].tolist())
        flags.append(
            {
                "id": "LOW_LIQUIDITY",
                "severity": "High",
                "title": "Low liquidity constituents require trade review",
                "detail": f"Review trade capacity for {tickers}.",
            }
        )

    suspended = constituents[_bool_series(constituents["is_suspended"])]
    if not suspended.empty:
        tickers = ", ".join(suspended["ticker"].tolist())
        flags.append(
            {
                "id": "SUSPENDED_SECURITY",
                "severity": "High",
                "title": "Suspended constituent is present",
                "detail": f"Confirm index treatment and tradability for {tickers}.",
            }
        )

    limit_up_increases = constituents[
        _bool_series(constituents["is_limit_up"])
        & (constituents["target_weight"].astype(float) > constituents["current_weight"].astype(float))
    ]
    if not limit_up_increases.empty:
        tickers = ", ".join(limit_up_increases["ticker"].tolist())
        flags.append(
            {
                "id": "LIMIT_UP_INCREASE",
                "severity": "Medium",
                "title": "Target increase on limit-up name",
                "detail": f"Review execution feasibility for {tickers}.",
            }
        )

    limit_down_reductions = constituents[
        _bool_series(constituents["is_limit_down"])
        & (constituents["target_weight"].astype(float) < constituents["current_weight"].astype(float))
    ]
    if not limit_down_reductions.empty:
        tickers = ", ".join(limit_down_reductions["ticker"].tolist())
        flags.append(
            {
                "id": "LIMIT_DOWN_REDUCTION",
                "severity": "Medium",
                "title": "Target reduction on limit-down name",
                "detail": f"Review sale timing and implementation risk for {tickers}.",
            }
        )

    if metrics["missing_factor_values"] > 0:
        flags.append(
            {
                "id": "MISSING_FACTOR_DATA",
                "severity": "Medium",
                "title": "Factor model inputs contain missing values",
                "detail": f"{metrics['missing_factor_values']:.0f} factor values are missing.",
            }
        )

    if metrics["max_active_weight"] > max_active_limit:
        flags.append(
            {
                "id": "MAX_ACTIVE_WEIGHT",
                "severity": "Medium",
                "title": "Largest active weight is elevated",
                "detail": f"Max active weight is {metrics['max_active_weight']:.1%}.",
            }
        )

    if metrics["top10_active_share"] > active_share_limit:
        flags.append(
            {
                "id": "TOP10_ACTIVE_SHARE",
                "severity": "Medium",
                "title": "Active risk is concentrated in top names",
                "detail": f"Top 10 active share is {metrics['top10_active_share']:.1%}.",
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
    if "LOW_LIQUIDITY" in flag_ids:
        checklist.append("Review liquidity and implementation feasibility for low ADV names.")
    if "TOP_HEAVY" in flag_ids:
        checklist.append("Confirm concentration remains within index committee tolerance.")
    if "SUSPENDED_SECURITY" in flag_ids:
        checklist.append("Confirm suspended security treatment with index operations.")
    if "LIMIT_UP_INCREASE" in flag_ids or "LIMIT_DOWN_REDUCTION" in flag_ids:
        checklist.append("Check exchange price-limit constraints before trade scheduling.")
    if "MISSING_FACTOR_DATA" in flag_ids:
        checklist.append("Resolve or document all missing factor values before final approval.")

    return checklist
