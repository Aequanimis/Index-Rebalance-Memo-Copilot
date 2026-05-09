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


def _load_inputs(use_demo_data, constituents_file, factor_scores_file, backtest_metrics_file):
    """Load demo data by default, with uploaded CSVs overriding demo inputs."""
    demo_data = load_demo_data()

    constituents = (
        demo_data.constituents
        if use_demo_data or constituents_file is None
        else load_constituents(constituents_file)
    )
    factor_scores = (
        demo_data.factor_scores
        if use_demo_data or factor_scores_file is None
        else load_factor_scores(factor_scores_file)
    )
    backtest_metrics = (
        demo_data.backtest_metrics
        if use_demo_data or backtest_metrics_file is None
        else load_backtest_metrics(backtest_metrics_file)
    )
    return constituents, factor_scores, backtest_metrics


def _select_llm_provider(provider_choice: str) -> tuple[str, str]:
    """Choose provider/model without displaying or storing API keys."""
    if provider_choice == "Gemini":
        return "gemini", "gemini-2.5-flash"
    if provider_choice == "OpenAI":
        return "openai", "gpt-4o-mini"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini", "gemini-2.5-flash"
    return "openai", "gpt-4o-mini"


def _render_flag(flag: dict) -> None:
    """Render one risk flag with an easy-to-scan severity label."""
    severity = flag.get("severity", "medium").lower()
    label = f"[{severity.upper()}] {flag.get('category', 'Risk')}: {flag.get('message', '')}"
    if severity == "high":
        st.error(label)
    elif severity == "medium":
        st.warning(label)
    else:
        st.info(label)


def main() -> None:
    st.title("Index Rebalance Memo Copilot")
    st.write(
        "This tool helps an index research intern convert rebalance model outputs "
        "into a structured review memo with quantitative metrics, risk flags, and "
        "a human review checklist."
    )

    with st.sidebar:
        st.header("Inputs")
        use_demo_data = st.checkbox("Use demo data", value=True)
        constituents_file = st.file_uploader("Constituents CSV", type="csv")
        factor_scores_file = st.file_uploader("Factor scores CSV", type="csv")
        backtest_metrics_file = st.file_uploader("Backtest metrics CSV", type="csv")

        st.header("Generation")
        use_llm = st.toggle("Use LLM generation if API key is available", value=False)
        provider_choice = st.selectbox(
            "LLM provider",
            ["Auto", "Gemini", "OpenAI"],
            disabled=not use_llm,
        )
        st.caption("API keys are read from environment variables and are never shown.")
        generate_button = st.button("Generate Rebalance Memo", type="primary")

    try:
        constituents, factor_scores, backtest_metrics = _load_inputs(
            use_demo_data,
            constituents_file,
            factor_scores_file,
            backtest_metrics_file,
        )
        summary = calculate_rebalance_summary(constituents, factor_scores, backtest_metrics)
        flags = detect_risk_flags(summary)
        recommendation = generate_recommendation(summary, flags)
        checklist = build_review_checklist(flags)
    except ValueError as exc:
        st.error(f"Input error: {exc}")
        return
    except Exception as exc:
        st.error(f"Unexpected error while processing inputs: {exc}")
        return

    st.header("Input Data Preview")
    data_tabs = st.tabs(["Constituents", "Factor Scores", "Backtest Metrics"])
    with data_tabs[0]:
        st.dataframe(constituents, width="stretch")
    with data_tabs[1]:
        st.dataframe(factor_scores, width="stretch")
    with data_tabs[2]:
        st.dataframe(backtest_metrics, width="stretch")

    st.header("Quantitative Summary")
    backtest = summary["backtest_metrics"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Names", f"{summary['number_of_names']}")
    metric_cols[1].metric("Tracking Error", f"{backtest['tracking_error']:.1%}")
    metric_cols[2].metric("Turnover", f"{backtest['turnover']:.1%}")
    metric_cols[3].metric(
        "Excess Return",
        f"{backtest['annualized_excess_return'] * 10000:.0f} bps",
    )

    summary_cols = st.columns(4)
    summary_cols[0].metric("Overweights", f"{summary['number_of_overweights']}")
    summary_cols[1].metric("Underweights", f"{summary['number_of_underweights']}")
    summary_cols[2].metric("Missing Factors", f"{summary['missing_factor_count']}")
    summary_cols[3].metric("Suspended Names", f"{summary['suspended_count']}")

    st.header("Risk Flags")
    if flags:
        for flag in flags:
            _render_flag(flag)
    else:
        st.success("No rule-based risk flags were triggered.")

    st.info(f"Recommendation: {recommendation}")

    st.header("Generated Memo")
    if generate_button:
        provider, model = _select_llm_provider(provider_choice)
        try:
            memo = generate_memo(
                summary,
                flags,
                recommendation,
                use_llm=use_llm,
                provider=provider,
                model=model,
            )
            st.session_state["generated_memo"] = memo
        except Exception as exc:
            st.error(f"Memo generation failed: {exc}")

    memo = st.session_state.get("generated_memo")
    if memo:
        st.text_area("Memo draft", memo, height=520)
        st.download_button(
            "Download memo as .txt",
            data=memo,
            file_name="rebalance_review_memo.txt",
            mime="text/plain",
        )
    else:
        st.info("Click Generate Rebalance Memo in the sidebar to create the memo draft.")

    st.header("Human Review Reminder")
    st.write(
        "This copilot drafts a review memo from structured inputs. A human analyst "
        "must validate the data, methodology constraints, trading feasibility, and "
        "final recommendation before any index action is approved."
    )
    for item in checklist:
        st.checkbox(item, value=False)


if __name__ == "__main__":
    main()
