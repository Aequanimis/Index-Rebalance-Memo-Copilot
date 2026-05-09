import pandas as pd


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def _metric_value(backtest_metrics: pd.DataFrame, metric_name: str, default: float = 0.0) -> float:
    if metric_name in backtest_metrics.columns:
        value = backtest_metrics[metric_name].iloc[0]
        if pd.isna(value):
            return default
        return float(value)

    if not {"metric", "value"}.issubset(backtest_metrics.columns):
        return default

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
    target_weight = constituents["target_weight"].astype(float)
    benchmark_weight = constituents["benchmark_weight"].astype(float)
    weight_change = target_weight - current_weight
    active_weight = target_weight - benchmark_weight

    annualized_excess_return = _metric_value(backtest_metrics, "annualized_excess_return")

    merged_scores = constituents[["ticker", "target_weight"]].merge(
        factor_scores,
        on="ticker",
        how="left",
    )
    valid_scores = merged_scores.dropna(subset=["final_score"])
    weighted_composite = (
        valid_scores["target_weight"].astype(float) * valid_scores["final_score"].astype(float)
    ).sum() / max(valid_scores["target_weight"].sum(), 0.0001)

    return {
        "constituent_count": float(len(constituents)),
        "suspended_count": float(_bool_series(constituents["is_suspended"]).sum()),
        "limit_up_count": float(_bool_series(constituents["is_limit_up"]).sum()),
        "limit_down_count": float(_bool_series(constituents["is_limit_down"]).sum()),
        "missing_factor_values": float(factor_scores.drop(columns=["ticker"], errors="ignore").isna().sum().sum()),
        "current_weight_sum": float(current_weight.sum()),
        "target_weight_sum": float(target_weight.sum()),
        "benchmark_weight_sum": float(benchmark_weight.sum()),
        "one_way_turnover": float(weight_change.abs().sum() / 2),
        "top5_weight": float(target_weight.sort_values(ascending=False).head(5).sum()),
        "median_adv_value": float(constituents["avg_daily_value"].median()),
        "min_adv_value": float(constituents["avg_daily_value"].min()),
        "weighted_composite_score": float(weighted_composite),
        "annualized_excess_return": annualized_excess_return,
        "tracking_error": _metric_value(backtest_metrics, "tracking_error"),
        "information_ratio": _metric_value(backtest_metrics, "information_ratio"),
        "backtest_turnover": _metric_value(backtest_metrics, "turnover"),
        "one_way_cost": _metric_value(backtest_metrics, "one_way_cost"),
        "max_active_weight": _metric_value(
            backtest_metrics,
            "max_active_weight",
            default=float(active_weight.abs().max()),
        ),
        "top10_active_share": _metric_value(backtest_metrics, "top10_active_share"),
        "excess_return_bps": float(annualized_excess_return * 10000),
    }
