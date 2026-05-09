import pandas as pd


REQUIRED_CONSTITUENT_COLUMNS = {
    "ticker",
    "company_name",
    "sector",
    "current_weight",
    "target_weight",
    "benchmark_weight",
    "avg_daily_value",
    "is_suspended",
    "is_limit_up",
    "is_limit_down",
}

REQUIRED_FACTOR_COLUMNS = {
    "ticker",
    "momentum_1m_z",
    "quality_cfo_rev_z",
    "idio_momentum_1m_z",
    "final_score",
}

HIGH_ACTIVE_WEIGHT_THRESHOLD = 0.02


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def _validate_columns(df: pd.DataFrame, required_columns: set[str], label: str) -> None:
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def _float_or_none(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


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


def _active_name_records(df: pd.DataFrame, n: int = 5) -> list[dict[str, object]]:
    """Convert active-weight rows into prompt-safe records."""
    return [
        {
            "ticker": str(row["ticker"]),
            "company_name": str(row["company_name"]),
            "sector": str(row["sector"]),
            "active_weight": float(row["active_weight"]),
            "target_weight": float(row["target_weight"]),
            "benchmark_weight": float(row["benchmark_weight"]),
            "final_score": _float_or_none(row.get("final_score")),
        }
        for _, row in df.head(n).iterrows()
    ]


def calculate_rebalance_summary(
    constituents_df: pd.DataFrame,
    factor_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
) -> dict[str, object]:
    """Calculate a prompt-safe rebalance summary from constituent, factor, and backtest data.

    The function merges constituents and factor scores by ticker, calculates active
    weights and turnover, identifies common review flags, and flattens the first
    backtest metrics row into plain Python values.
    """
    try:
        _validate_columns(constituents_df, REQUIRED_CONSTITUENT_COLUMNS, "constituents_df")
        _validate_columns(factor_df, REQUIRED_FACTOR_COLUMNS, "factor_df")
        if metrics_df.empty:
            raise ValueError("metrics_df must contain at least one row")

        merged = constituents_df.merge(factor_df, on="ticker", how="left")
        for column in ["current_weight", "target_weight", "benchmark_weight", "avg_daily_value"]:
            merged[column] = pd.to_numeric(merged[column], errors="coerce")

        merged["active_weight"] = merged["target_weight"] - merged["benchmark_weight"]
        merged["weight_change"] = merged["target_weight"] - merged["current_weight"]
        merged["abs_active_weight"] = merged["active_weight"].abs()

        missing_factor_columns = [
            "momentum_1m_z",
            "quality_cfo_rev_z",
            "idio_momentum_1m_z",
            "final_score",
        ]
        missing_factor_count = int(merged[missing_factor_columns].isna().sum().sum())

        high_active_weight = merged[
            merged["abs_active_weight"] >= HIGH_ACTIVE_WEIGHT_THRESHOLD
        ].sort_values(
            "abs_active_weight",
            ascending=False,
        )
        high_active_weight_names = [
            {
                "ticker": str(row["ticker"]),
                "company_name": str(row["company_name"]),
                "sector": str(row["sector"]),
                "active_weight": float(row["active_weight"]),
            }
            for _, row in high_active_weight.iterrows()
        ]

        backtest_metrics = {
            str(column): _float_or_none(metrics_df.iloc[0][column])
            for column in metrics_df.columns
        }

        return {
            "number_of_names": int(len(merged)),
            "number_of_overweights": int((merged["active_weight"] > 0).sum()),
            "number_of_underweights": int((merged["active_weight"] < 0).sum()),
            "missing_factor_count": missing_factor_count,
            "suspended_count": int(_bool_series(merged["is_suspended"]).sum()),
            "limit_up_count": int(_bool_series(merged["is_limit_up"]).sum()),
            "limit_down_count": int(_bool_series(merged["is_limit_down"]).sum()),
            "absolute_turnover_estimate": float(merged["weight_change"].abs().sum() / 2),
            "current_weight_sum": float(merged["current_weight"].sum()),
            "target_weight_sum": float(merged["target_weight"].sum()),
            "benchmark_weight_sum": float(merged["benchmark_weight"].sum()),
            "top_overweight_names": _active_name_records(
                merged.sort_values("active_weight", ascending=False),
            ),
            "top_underweight_names": _active_name_records(
                merged.sort_values("active_weight", ascending=True),
            ),
            "high_active_weight_names": high_active_weight_names,
            "backtest_metrics": backtest_metrics,
        }
    except KeyError as exc:
        raise ValueError(f"Could not calculate rebalance summary. Missing column: {exc}") from exc
    except TypeError as exc:
        raise ValueError(f"Could not calculate rebalance summary: {exc}") from exc


def calculate_summary_metrics(
    constituents: pd.DataFrame,
    factor_scores: pd.DataFrame,
    backtest_metrics: pd.DataFrame,
) -> dict[str, float]:
    """Compatibility wrapper for the starter Streamlit app and risk flag rules."""
    summary = calculate_rebalance_summary(constituents, factor_scores, backtest_metrics)

    target_weight = constituents["target_weight"].astype(float)
    valid_scores = constituents[["ticker", "target_weight"]].merge(
        factor_scores,
        on="ticker",
        how="left",
    ).dropna(subset=["final_score"])
    weighted_composite = (
        valid_scores["target_weight"].astype(float) * valid_scores["final_score"].astype(float)
    ).sum() / max(valid_scores["target_weight"].sum(), 0.0001)
    annualized_excess_return = _metric_value(backtest_metrics, "annualized_excess_return")

    return {
        "constituent_count": float(summary["number_of_names"]),
        "suspended_count": float(summary["suspended_count"]),
        "limit_up_count": float(summary["limit_up_count"]),
        "limit_down_count": float(summary["limit_down_count"]),
        "missing_factor_values": float(summary["missing_factor_count"]),
        "current_weight_sum": float(summary["current_weight_sum"]),
        "target_weight_sum": float(summary["target_weight_sum"]),
        "benchmark_weight_sum": float(summary["benchmark_weight_sum"]),
        "one_way_turnover": float(summary["absolute_turnover_estimate"]),
        "top5_weight": float(target_weight.sort_values(ascending=False).head(5).sum()),
        "median_adv_value": float(constituents["avg_daily_value"].median()),
        "min_adv_value": float(constituents["avg_daily_value"].min()),
        "weighted_composite_score": float(weighted_composite),
        "annualized_excess_return": annualized_excess_return,
        "tracking_error": _metric_value(backtest_metrics, "tracking_error"),
        "information_ratio": _metric_value(backtest_metrics, "information_ratio"),
        "backtest_turnover": _metric_value(backtest_metrics, "turnover"),
        "one_way_cost": _metric_value(backtest_metrics, "one_way_cost"),
        "max_active_weight": _metric_value(backtest_metrics, "max_active_weight"),
        "top10_active_share": _metric_value(backtest_metrics, "top10_active_share"),
        "excess_return_bps": float(annualized_excess_return * 10000),
    }
