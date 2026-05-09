import pandas as pd


def _metric_value(backtest_metrics: pd.DataFrame, metric_name: str, default: float = 0.0) -> float:
    matches = backtest_metrics.loc[backtest_metrics["metric"] == metric_name, "value"]
    if matches.empty:
        return default
    return float(matches.iloc[0])


def calculate_summary_metrics(
    constituents: pd.DataFrame,
    factor_scores: pd.DataFrame,
    backtest_metrics: pd.DataFrame,
) -> dict[str, float]:
    """Calculate starter metrics used by the memo and risk flags."""
    current_weight = constituents["current_weight"].astype(float)
    proposed_weight = constituents["proposed_weight"].astype(float)
    weight_change = proposed_weight - current_weight

    annualized_return = _metric_value(backtest_metrics, "annualized_return")
    benchmark_return = _metric_value(backtest_metrics, "benchmark_annualized_return")
    max_drawdown = _metric_value(backtest_metrics, "max_drawdown")
    benchmark_drawdown = _metric_value(backtest_metrics, "benchmark_max_drawdown")

    merged_scores = constituents[["ticker", "proposed_weight"]].merge(
        factor_scores,
        on="ticker",
        how="left",
    )
    weighted_composite = (
        merged_scores["proposed_weight"].astype(float) * merged_scores["composite_score"].astype(float)
    ).sum() / max(merged_scores["proposed_weight"].sum(), 0.0001)

    return {
        "constituent_count": float(len(constituents)),
        "adds": float((constituents["action"] == "Add").sum()),
        "deletes": float((constituents["action"] == "Delete").sum()),
        "one_way_turnover": float(weight_change.abs().sum() / 2),
        "top5_weight": float(proposed_weight.sort_values(ascending=False).head(5).sum()),
        "median_adv_usd_mm": float(constituents["median_adv_usd_mm"].median()),
        "weighted_composite_score": float(weighted_composite),
        "tracking_error": _metric_value(backtest_metrics, "tracking_error"),
        "information_ratio": _metric_value(backtest_metrics, "information_ratio"),
        "max_drawdown": max_drawdown,
        "drawdown_gap": float(abs(max_drawdown) - abs(benchmark_drawdown)),
        "excess_return_bps": float((annualized_return - benchmark_return) * 10000),
    }
