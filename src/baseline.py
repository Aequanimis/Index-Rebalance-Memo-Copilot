from src.metrics import calculate_summary_metrics
from src.risk_flags import build_review_checklist, detect_risk_flags


def run_baseline(constituents, factor_scores, backtest_metrics) -> dict:
    """Run the deterministic baseline workflow used for evaluation."""
    metrics = calculate_summary_metrics(constituents, factor_scores, backtest_metrics)
    flags = detect_risk_flags(constituents, factor_scores, backtest_metrics)
    checklist = build_review_checklist(flags)
    return {
        "metrics": metrics,
        "flags": flags,
        "checklist": checklist,
    }
