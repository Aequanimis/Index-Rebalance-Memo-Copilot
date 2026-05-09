from pathlib import Path

import streamlit as st

from src.data_loader import load_demo_data, load_uploaded_or_demo
from src.memo_generator import generate_memo
from src.metrics import calculate_summary_metrics
from src.risk_flags import build_review_checklist, detect_risk_flags


st.set_page_config(
    page_title="Index Rebalance Memo Copilot",
    page_icon="IR",
    layout="wide",
)


DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    st.title("Index Rebalance Memo Copilot")
    st.caption("Draft a rebalance review memo from model outputs, metrics, and risk flags.")

    with st.sidebar:
        st.header("Inputs")
        st.write("Use the demo files or upload replacement CSVs with the same column names.")
        constituents_file = st.file_uploader("Constituents CSV", type="csv")
        factor_scores_file = st.file_uploader("Factor scores CSV", type="csv")
        backtest_metrics_file = st.file_uploader("Backtest metrics CSV", type="csv")

        st.header("Review Settings")
        turnover_threshold = st.slider("High turnover threshold", 0.05, 0.60, 0.30, 0.01)
        concentration_threshold = st.slider("Top 5 weight threshold", 0.20, 0.70, 0.45, 0.01)
        liquidity_threshold = st.number_input("Minimum ADV (CNY millions)", 1.0, 500.0, 100.0, 5.0)

    demo_data = load_demo_data(DATA_DIR)
    constituents = load_uploaded_or_demo(constituents_file, demo_data.constituents)
    factor_scores = load_uploaded_or_demo(factor_scores_file, demo_data.factor_scores)
    backtest_metrics = load_uploaded_or_demo(backtest_metrics_file, demo_data.backtest_metrics)

    thresholds = {
        "turnover": turnover_threshold,
        "top5_weight": concentration_threshold,
        "avg_daily_value": liquidity_threshold * 1_000_000,
    }

    summary_metrics = calculate_summary_metrics(
        constituents=constituents,
        factor_scores=factor_scores,
        backtest_metrics=backtest_metrics,
    )
    risk_flags = detect_risk_flags(
        constituents=constituents,
        factor_scores=factor_scores,
        backtest_metrics=backtest_metrics,
        thresholds=thresholds,
    )
    checklist = build_review_checklist(risk_flags)
    memo = generate_memo(summary_metrics, risk_flags, checklist)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Names", f"{summary_metrics['constituent_count']:.0f}")
    metric_cols[1].metric("Backtest Turnover", f"{summary_metrics['backtest_turnover']:.1%}")
    metric_cols[2].metric("Top 5 Weight", f"{summary_metrics['top5_weight']:.1%}")
    metric_cols[3].metric("Backtest Excess Return", f"{summary_metrics['excess_return_bps']:.0f} bps")

    tab_data, tab_flags, tab_memo = st.tabs(["Model Outputs", "Risk Flags", "Memo Draft"])

    with tab_data:
        st.subheader("Constituents")
        st.dataframe(constituents, use_container_width=True)
        st.subheader("Factor Scores")
        st.dataframe(factor_scores, use_container_width=True)
        st.subheader("Backtest Metrics")
        st.dataframe(backtest_metrics, use_container_width=True)

    with tab_flags:
        if risk_flags:
            for flag in risk_flags:
                st.warning(f"{flag['severity']}: {flag['title']} - {flag['detail']}")
        else:
            st.success("No starter-rule risk flags were triggered.")

        st.subheader("Human Review Checklist")
        for item in checklist:
            st.checkbox(item, value=False)

    with tab_memo:
        st.text_area("Draft memo", memo, height=520)
        st.download_button(
            "Download memo",
            data=memo,
            file_name="rebalance_review_memo.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
