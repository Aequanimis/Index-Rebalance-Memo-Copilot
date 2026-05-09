def _backtest_metric(summary: dict, metric_name: str, default: float = 0.0) -> float:
    """Read a metric from summary['backtest_metrics'] or a top-level fallback key."""
    metrics = summary.get("backtest_metrics", {})
    value = metrics.get(metric_name, summary.get(metric_name, default))
    if value is None:
        return default
    return float(value)


def _count(summary: dict, key: str) -> int:
    """Return a non-null integer count from a summary dictionary."""
    return int(summary.get(key, 0) or 0)


def _flag(
    category: str,
    severity: str,
    message: str,
    human_review_required: bool = True,
) -> dict:
    """Create one transparent rule-based risk flag."""
    return {
        "category": category,
        "severity": severity,
        "message": message,
        "human_review_required": human_review_required,
    }


def detect_risk_flags(summary: dict) -> list[dict]:
    """Detect risk flags from a rebalance summary using transparent business rules.

    This function does not call an LLM. It expects the dictionary returned by
    `calculate_rebalance_summary` and returns prompt-safe dictionaries with a
    category, severity, message, and human-review indicator.
    """
    if not isinstance(summary, dict):
        raise ValueError("summary must be a dictionary")

    flags: list[dict] = []

    tracking_error = _backtest_metric(summary, "tracking_error")
    turnover = _backtest_metric(summary, "turnover")
    one_way_cost = _backtest_metric(summary, "one_way_cost")
    annualized_excess_return = _backtest_metric(summary, "annualized_excess_return")
    max_active_weight = _backtest_metric(summary, "max_active_weight")
    top10_active_share = _backtest_metric(summary, "top10_active_share")

    if tracking_error > 0.07:
        flags.append(
            _flag(
                "Tracking error risk",
                "high",
                f"Tracking error is {tracking_error:.1%}, above the 7.0% high-risk threshold.",
            )
        )
    elif tracking_error > 0.05:
        flags.append(
            _flag(
                "Tracking error risk",
                "medium",
                f"Tracking error is {tracking_error:.1%}, above the 5.0% review threshold.",
            )
        )

    if turnover > 0.50:
        flags.append(
            _flag(
                "Turnover and cost risk",
                "high",
                f"Backtest turnover is {turnover:.1%}, above the 50.0% high-risk threshold.",
            )
        )
    elif turnover > 0.30:
        flags.append(
            _flag(
                "Turnover and cost risk",
                "medium",
                f"Backtest turnover is {turnover:.1%}, above the 30.0% review threshold.",
            )
        )

    if one_way_cost >= 0.003 and annualized_excess_return < 0.04:
        flags.append(
            _flag(
                "Turnover and cost risk",
                "medium",
                "One-way cost is at least 0.30% while annualized excess return is below 4.0%.",
            )
        )

    suspended_count = _count(summary, "suspended_count")
    if suspended_count > 0:
        flags.append(
            _flag(
                "Trading feasibility risk",
                "high",
                f"{suspended_count} suspended stock(s) are present in the rebalance universe.",
            )
        )

    limit_up_count = _count(summary, "limit_up_count")
    limit_down_count = _count(summary, "limit_down_count")
    if limit_up_count > 0 or limit_down_count > 0:
        flags.append(
            _flag(
                "Trading feasibility risk",
                "medium",
                f"{limit_up_count} limit-up and {limit_down_count} limit-down stock(s) require execution review.",
            )
        )

    missing_factor_count = _count(summary, "missing_factor_count")
    if missing_factor_count > 0:
        flags.append(
            _flag(
                "Data quality risk",
                "medium",
                f"{missing_factor_count} missing factor value(s) should be resolved or documented.",
            )
        )

    if max_active_weight > 0.05:
        flags.append(
            _flag(
                "Concentration risk",
                "medium",
                f"Maximum single-name active weight is {max_active_weight:.1%}, above the 5.0% review threshold.",
            )
        )

    if top10_active_share > 0.60:
        flags.append(
            _flag(
                "Concentration risk",
                "medium",
                f"Top 10 active share is {top10_active_share:.1%}, above the 60.0% review threshold.",
            )
        )

    return flags


def generate_recommendation(summary: dict, flags: list[dict]) -> str:
    """Return a simple approval recommendation based on generated risk flags."""
    high_flags = [flag for flag in flags if flag.get("severity") == "high"]
    medium_flags = [flag for flag in flags if flag.get("severity") == "medium"]
    high_categories = {flag.get("category") for flag in high_flags}

    if len(high_flags) >= 2:
        return "Reject or rerun model"
    if {"Tracking error risk", "Turnover and cost risk"}.intersection(high_categories):
        return "Reject or rerun model"
    if high_flags or len(medium_flags) >= 3:
        return "Revise before approval"
    return "Approve with monitoring"


def build_review_checklist(risk_flags: list[dict]) -> list[str]:
    """Create a short human-review checklist tied to generated risk flags."""
    checklist = [
        "Confirm proposed weights match the approved rebalance model output.",
        "Validate index methodology constraints and eligibility screens.",
        "Review corporate actions, data quality exceptions, and stale pricing.",
    ]

    categories = {flag.get("category") for flag in risk_flags}
    messages = " ".join(flag.get("message", "") for flag in risk_flags)

    if "Tracking error risk" in categories:
        checklist.append("Review tracking error drivers and active risk budget usage.")
    if "Turnover and cost risk" in categories:
        checklist.append("Confirm turnover and cost assumptions are acceptable.")
    if "Trading feasibility risk" in categories:
        checklist.append("Check suspended, limit-up, and limit-down names before trade scheduling.")
    if "Data quality risk" in categories:
        checklist.append("Resolve or document missing factor values before approval.")
    if "Concentration risk" in categories:
        checklist.append("Confirm single-name and top 10 active exposures are within tolerance.")

    if "HIGH_TURNOVER" in messages:
        checklist.append("Confirm turnover is justified by expected factor improvement.")

    return checklist


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from pprint import pprint

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from src.data_loader import load_demo_data
    from src.metrics import calculate_rebalance_summary

    demo_data = load_demo_data()
    demo_summary = calculate_rebalance_summary(
        demo_data.constituents,
        demo_data.factor_scores,
        demo_data.backtest_metrics,
    )
    demo_flags = detect_risk_flags(demo_summary)
    pprint(demo_flags)
    print(generate_recommendation(demo_summary, demo_flags))
