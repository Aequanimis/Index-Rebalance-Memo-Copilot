import os

import streamlit as st

from src.data_loader import (
    load_backtest_metrics,
    load_constituents,
    load_demo_data,
    load_factor_scores,
)
from src.memo_generator import generate_memo
from src.metrics import calculate_rebalance_summary
from src.risk_flags import build_review_checklist, detect_risk_flags, generate_recommendation


st.set_page_config(
    page_title="Index Rebalance Memo Copilot",
    page_icon="IR",
    layout="wide",
)


def main() -> None:
    st.title("Index Rebalance Memo Copilot")
    st.caption("Draft a rebalance review memo from model outputs, metrics, and risk flags.")

    with st.sidebar:
        st.header("Inputs")
        st.write("Use the demo files or upload replacement CSVs with the same column names.")
        constituents_file = st.file_uploader("Constituents CSV", type="csv")
        factor_scores_file = st.file_uploader("Factor scores CSV", type="csv")
        backtest_metrics_file = st.file_uploader("Backtest metrics CSV", type="csv")

        st.header("Memo Generation")
        use_llm = st.toggle("Use LLM for memo", value=False)
        provider_label = st.selectbox("LLM provider", ["Gemini", "OpenAI"], disabled=not use_llm)
        default_model = "gemini-2.5-flash" if provider_label == "Gemini" else "gpt-4o-mini"
        model = st.text_input("Model", value=default_model, disabled=not use_llm)
        api_key = st.text_input("API key", type="password", disabled=not use_llm)
        st.caption("API keys are used only for this session and are not written to project files.")
        generate_llm_now = st.button("Generate LLM memo", disabled=not use_llm)
        if use_llm and api_key:
            if provider_label == "Gemini":
                os.environ["GEMINI_API_KEY"] = api_key
            else:
                os.environ["OPENAI_API_KEY"] = api_key

    demo_data = load_demo_data()
    constituents = (
        load_constituents(constituents_file)
        if constituents_file is not None
        else demo_data.constituents
    )
    factor_scores = (
        load_factor_scores(factor_scores_file)
        if factor_scores_file is not None
        else demo_data.factor_scores
    )
    backtest_metrics = (
        load_backtest_metrics(backtest_metrics_file)
        if backtest_metrics_file is not None
        else demo_data.backtest_metrics
    )

    summary = calculate_rebalance_summary(constituents, factor_scores, backtest_metrics)
    risk_flags = detect_risk_flags(summary)
    recommendation = generate_recommendation(summary, risk_flags)
    checklist = build_review_checklist(risk_flags)
    memo = generate_memo(
        summary,
        risk_flags,
        recommendation,
        use_llm=use_llm and generate_llm_now,
        provider=provider_label.lower(),
        model=model,
    )

    metric_cols = st.columns(4)
    backtest = summary["backtest_metrics"]
    metric_cols[0].metric("Names", f"{summary['number_of_names']:.0f}")
    metric_cols[1].metric("Backtest Turnover", f"{backtest['turnover']:.1%}")
    metric_cols[2].metric("Tracking Error", f"{backtest['tracking_error']:.1%}")
    metric_cols[3].metric("Excess Return", f"{backtest['annualized_excess_return'] * 10000:.0f} bps")

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
                st.warning(
                    f"{flag['severity'].title()}: {flag['category']} - {flag['message']}"
                )
        else:
            st.success("No starter-rule risk flags were triggered.")

        st.subheader("Recommendation")
        st.info(recommendation)

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
