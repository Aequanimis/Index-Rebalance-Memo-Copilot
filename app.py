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


def _apply_page_styles() -> None:
    """Apply lightweight Streamlit styling for a more polished business UI."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(120, 130, 150, 0.18);
        }
        .hero-panel {
            border: 1px solid rgba(120, 130, 150, 0.20);
            border-radius: 8px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1.1rem;
            background: linear-gradient(180deg, rgba(40, 70, 100, 0.15), rgba(40, 70, 100, 0.05));
        }
        .hero-title {
            font-size: 2.1rem;
            font-weight: 750;
            line-height: 1.15;
            margin-bottom: 0.35rem;
        }
        .hero-subtitle {
            color: rgba(230, 235, 245, 0.78);
            font-size: 1.02rem;
            max-width: 900px;
        }
        .section-kicker {
            color: rgba(230, 235, 245, 0.62);
            text-transform: uppercase;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.25rem;
        }
        .status-card {
            border: 1px solid rgba(120, 130, 150, 0.20);
            border-radius: 8px;
            padding: 0.9rem 1rem;
            min-height: 104px;
            background: rgba(255, 255, 255, 0.035);
        }
        .status-label {
            color: rgba(230, 235, 245, 0.65);
            font-size: 0.78rem;
            margin-bottom: 0.35rem;
        }
        .status-value {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .status-note {
            color: rgba(230, 235, 245, 0.64);
            font-size: 0.82rem;
        }
        .risk-high {
            border-left: 4px solid #ff5a5f;
        }
        .risk-medium {
            border-left: 4px solid #f4b942;
        }
        .risk-low {
            border-left: 4px solid #6fbf73;
        }
        </style>
        """,
        unsafe_allow_html=True,
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


def _severity_counts(flags: list[dict]) -> dict[str, int]:
    """Count risk flags by severity."""
    counts = {"high": 0, "medium": 0, "low": 0}
    for flag in flags:
        severity = flag.get("severity", "medium").lower()
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _status_card(label: str, value: str, note: str, class_name: str = "") -> None:
    """Render a compact status card."""
    st.markdown(
        f"""
        <div class="status-card {class_name}">
            <div class="status-label">{label}</div>
            <div class="status-value">{value}</div>
            <div class="status-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    _apply_page_styles()

    st.markdown(
        """
        <div class="hero-panel">
            <div class="section-kicker">Course final project</div>
            <div class="hero-title">Index Rebalance Memo Copilot</div>
            <div class="hero-subtitle">
                This tool helps an index research intern convert rebalance model outputs
                into a structured review memo with quantitative metrics, risk flags, and
                a human review checklist.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("Workflow")
        st.caption("Load data, review deterministic checks, then generate the memo.")
        st.divider()

        st.header("Inputs")
        use_demo_data = st.checkbox("Use demo data", value=True)
        constituents_file = st.file_uploader("Constituents CSV", type="csv")
        factor_scores_file = st.file_uploader("Factor scores CSV", type="csv")
        backtest_metrics_file = st.file_uploader("Backtest metrics CSV", type="csv")
        if use_demo_data:
            st.caption("Demo data is active. Uploaded files are ignored until demo data is turned off.")
        else:
            st.caption("Upload any subset of files. Missing files fall back to the demo data.")

        st.divider()
        st.header("Generation")
        use_llm = st.toggle("Use LLM generation if API key is available", value=False)
        provider_choice = st.selectbox(
            "LLM provider",
            ["Auto", "Gemini", "OpenAI"],
            disabled=not use_llm,
        )
        api_key = st.text_input(
            "API key",
            type="password",
            disabled=not use_llm,
            help="Optional. You can paste a key for this session, or set it as an environment variable before launching the app.",
        )
        st.caption("API keys are masked, used only for this session, and never written to project files.")
        generate_button = st.button("Generate Rebalance Memo", type="primary")

        if use_llm and api_key:
            if provider_choice == "OpenAI":
                os.environ["OPENAI_API_KEY"] = api_key
            else:
                os.environ["GEMINI_API_KEY"] = api_key

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

    backtest = summary["backtest_metrics"]
    severity_counts = _severity_counts(flags)
    active_mode = "LLM requested" if use_llm else "Mock memo"
    input_mode = "Demo data" if use_demo_data else "Uploaded files with demo fallback"

    status_cols = st.columns(4)
    with status_cols[0]:
        _status_card("Input mode", input_mode, f"{summary['number_of_names']} constituents loaded")
    with status_cols[1]:
        _status_card("Recommendation", recommendation, "Generated from deterministic risk flags")
    with status_cols[2]:
        risk_note = f"{severity_counts['high']} high / {severity_counts['medium']} medium"
        risk_class = "risk-high" if severity_counts["high"] else "risk-medium" if flags else "risk-low"
        _status_card("Risk profile", f"{len(flags)} flags", risk_note, risk_class)
    with status_cols[3]:
        provider, model = _select_llm_provider(provider_choice)
        _status_card("Memo mode", active_mode, f"Provider: {provider}, model: {model}")

    st.divider()

    st.markdown("## Quantitative Dashboard")
    metric_cols = st.columns(5)
    metric_cols[0].metric("Names", f"{summary['number_of_names']}")
    metric_cols[1].metric("Excess Return", f"{backtest['annualized_excess_return'] * 10000:.0f} bps")
    metric_cols[2].metric("Tracking Error", f"{backtest['tracking_error']:.1%}")
    metric_cols[3].metric("Turnover", f"{backtest['turnover']:.1%}")
    metric_cols[4].metric("One-way Cost", f"{backtest['one_way_cost']:.2%}")

    summary_cols = st.columns(4)
    summary_cols[0].metric("Overweights", f"{summary['number_of_overweights']}")
    summary_cols[1].metric("Underweights", f"{summary['number_of_underweights']}")
    summary_cols[2].metric("Missing Factors", f"{summary['missing_factor_count']}")
    summary_cols[3].metric(
        "Trading Constraints",
        f"{summary['suspended_count'] + summary['limit_up_count'] + summary['limit_down_count']}",
        help="Suspended plus limit-up and limit-down names",
    )

    diagnostics = {
        "current_weight_sum": summary["current_weight_sum"],
        "target_weight_sum": summary["target_weight_sum"],
        "benchmark_weight_sum": summary["benchmark_weight_sum"],
        "absolute_turnover_estimate": summary["absolute_turnover_estimate"],
        "max_active_weight": backtest["max_active_weight"],
        "top10_active_share": backtest["top10_active_share"],
    }
    with st.expander("Portfolio diagnostics", expanded=False):
        st.dataframe(
            [{"metric": key, "value": value} for key, value in diagnostics.items()],
            width="stretch",
            hide_index=True,
        )

    st.markdown("## Risk Flags")
    risk_left, risk_right = st.columns([2, 1])
    with risk_left:
        if flags:
            for flag in flags:
                _render_flag(flag)
        else:
            st.success("No rule-based risk flags were triggered.")
    with risk_right:
        st.markdown("#### Severity Summary")
        st.metric("High severity", severity_counts["high"])
        st.metric("Medium severity", severity_counts["medium"])
        st.metric("Human review items", len(checklist))

    st.info(f"Recommendation: {recommendation}")

    st.markdown("## Input Data Preview")
    data_tabs = st.tabs(["Constituents", "Factor Scores", "Backtest Metrics", "Top Active Names"])
    with data_tabs[0]:
        st.dataframe(constituents, width="stretch", height=360)
    with data_tabs[1]:
        st.dataframe(factor_scores, width="stretch", height=360)
    with data_tabs[2]:
        st.dataframe(backtest_metrics, width="stretch")
    with data_tabs[3]:
        active_cols = st.columns(2)
        with active_cols[0]:
            st.markdown("#### Top Overweights")
            st.dataframe(summary["top_overweight_names"], width="stretch", hide_index=True)
        with active_cols[1]:
            st.markdown("#### Top Underweights")
            st.dataframe(summary["top_underweight_names"], width="stretch", hide_index=True)

    st.markdown("## Generated Memo")
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
        memo_col, action_col = st.columns([3, 1])
        with memo_col:
            st.text_area("Memo draft", memo, height=520)
        with action_col:
            st.markdown("#### Memo Actions")
            st.download_button(
                "Download memo as .txt",
                data=memo,
                file_name="rebalance_review_memo.txt",
                mime="text/plain",
                width="stretch",
            )
            st.caption("The memo is a draft. Final approval remains with the analyst.")
    else:
        st.info("Click Generate Rebalance Memo in the sidebar to create the memo draft.")

    st.markdown("## Human Review Reminder")
    st.write(
        "This copilot drafts a review memo from structured inputs. A human analyst "
        "must validate the data, methodology constraints, trading feasibility, and "
        "final recommendation before any index action is approved."
    )
    review_cols = st.columns(2)
    for index, item in enumerate(checklist):
        with review_cols[index % 2]:
            st.checkbox(item, value=False)


if __name__ == "__main__":
    main()
