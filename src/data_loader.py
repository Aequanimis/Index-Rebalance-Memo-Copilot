from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

CONSTITUENT_COLUMNS = {
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

FACTOR_COLUMNS = {
    "ticker",
    "momentum_1m_z",
    "quality_cfo_rev_z",
    "idio_momentum_1m_z",
    "final_score",
}

BACKTEST_COLUMNS = {
    "annualized_excess_return",
    "information_ratio",
    "tracking_error",
    "turnover",
    "one_way_cost",
    "max_active_weight",
    "top10_active_share",
}


@dataclass(frozen=True)
class DemoData:
    constituents: pd.DataFrame
    factor_scores: pd.DataFrame
    backtest_metrics: pd.DataFrame


def _read_csv(file: str | Path | BinaryIO) -> pd.DataFrame:
    """Read a CSV from a local path or Streamlit uploaded file."""
    try:
        if hasattr(file, "seek"):
            file.seek(0)
        return pd.read_csv(file)
    except Exception as exc:
        raise ValueError(f"Could not load CSV data from {file!r}: {exc}") from exc


def _validate_columns(df: pd.DataFrame, required_columns: set[str], label: str) -> None:
    """Validate required columns and raise a clear error when any are missing."""
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(
            f"{label} is missing required columns: {', '.join(missing)}"
        )


def load_constituents(file: str | Path | BinaryIO) -> pd.DataFrame:
    """Load and validate a constituents CSV from a path or Streamlit upload."""
    df = _read_csv(file)
    _validate_columns(df, CONSTITUENT_COLUMNS, "Constituents file")
    return df


def load_factor_scores(file: str | Path | BinaryIO) -> pd.DataFrame:
    """Load and validate a factor scores CSV from a path or Streamlit upload."""
    df = _read_csv(file)
    _validate_columns(df, FACTOR_COLUMNS, "Factor scores file")
    return df


def load_backtest_metrics(file: str | Path | BinaryIO) -> pd.DataFrame:
    """Load and validate a backtest metrics CSV from a path or Streamlit upload."""
    df = _read_csv(file)
    _validate_columns(df, BACKTEST_COLUMNS, "Backtest metrics file")
    return df


def load_demo_data(data_dir: str | Path = DATA_DIR) -> DemoData:
    """Load and validate all bundled demo CSV files."""
    data_dir = Path(data_dir)
    return DemoData(
        constituents=load_constituents(data_dir / "demo_constituents.csv"),
        factor_scores=load_factor_scores(data_dir / "demo_factor_scores.csv"),
        backtest_metrics=load_backtest_metrics(data_dir / "demo_backtest_metrics.csv"),
    )


def load_uploaded_or_demo(uploaded_file: BinaryIO | None, demo_frame: pd.DataFrame) -> pd.DataFrame:
    """Use an uploaded CSV when present, otherwise return a copy of demo data."""
    if uploaded_file is None:
        return demo_frame.copy()
    return pd.read_csv(uploaded_file)
