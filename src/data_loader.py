from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd


@dataclass(frozen=True)
class DemoData:
    constituents: pd.DataFrame
    factor_scores: pd.DataFrame
    backtest_metrics: pd.DataFrame


def load_demo_data(data_dir: Path) -> DemoData:
    """Load the bundled demo CSV files."""
    return DemoData(
        constituents=pd.read_csv(data_dir / "demo_constituents.csv"),
        factor_scores=pd.read_csv(data_dir / "demo_factor_scores.csv"),
        backtest_metrics=pd.read_csv(data_dir / "demo_backtest_metrics.csv"),
    )


def load_uploaded_or_demo(uploaded_file: BinaryIO | None, demo_frame: pd.DataFrame) -> pd.DataFrame:
    """Use an uploaded CSV when present, otherwise return a copy of demo data."""
    if uploaded_file is None:
        return demo_frame.copy()
    return pd.read_csv(uploaded_file)
