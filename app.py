import os
from io import StringIO
import csv

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
        .workflow-stepper {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 1rem;
            color: rgba(235, 240, 248, 0.84);
            font-size: 0.9rem;
            font-weight: 600;
        }
        .step-pill {
            border: 1px solid rgba(102, 152, 210, 0.30);
            border-radius: 999px;
            padding: 0.34rem 0.62rem;
            background: rgba(35, 78, 122, 0.20);
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
        .metric-card {
            border: 1px solid rgba(120, 130, 150, 0.20);
            border-radius: 8px;
            padding: 0.85rem 0.95rem;
            min-height: 112px;
            background: rgba(255, 255, 255, 0.03);
        }
        .metric-label {
            color: rgba(230, 235, 245, 0.66);
            font-size: 0.78rem;
            margin-bottom: 0.25rem;
        }
        .metric-value {
            font-size: 1.42rem;
            font-weight: 760;
            margin-bottom: 0.25rem;
        }
        .metric-caption {
            color: rgba(230, 235, 245, 0.62);
            font-size: 0.78rem;
            line-height: 1.25;
        }
        .memo-preview {
            border: 1px solid rgba(120, 130, 150, 0.20);
            border-radius: 8px;
            padding: 1.1rem 1.2rem;
            background: rgba(255, 255, 255, 0.035);
        }
        div.stButton > button[kind="primary"] {
            background: #1f5f9f;
            border-color: #1f5f9f;
            color: #ffffff;
        }
        div.stButton > button[kind="primary"]:hover {
            background: #194f85;
            border-color: #194f85;
            color: #ffffff;
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


def _metric_card(label: str, value: str, caption: str) -> None:
    """Render one consistent dashboard metric card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def _risk_flags_csv(flags: list[dict]) -> str:
    """Convert risk flags to CSV text for download."""
    output = StringIO()
    fieldnames = ["severity", "category", "message", "human_review_required"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for flag in flags:
        writer.writerow({field: flag.get(field, "") for field in fieldnames})
    return output.getvalue()


def _control_checklist(dynamic_checklist: list[str]) -> list[str]:
    """Create the formal human control checklist shown in the app."""
    required_items = [
        "Confirm proposed weights match approved rebalance model output.",
        "Validate index methodology constraints and eligibility screens.",
        "Review corporate actions, data quality exceptions, and stale pricing.",
        "Review tracking error drivers and active risk budget usage.",
        "Confirm trading feasibility for suspended, limit-up, and limit-down names.",
        "Approve or revise the final recommendation.",
    ]
    for item in dynamic_checklist:
        if item not in required_items:
            required_items.append(item)
    return required_items


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
            <div class="workflow-stepper">
                <span class="step-pill">1 Load Data</span>
                <span class="step-pill">2 Run Checks</span>
                <span class="step-pill">3 Review Risks</span>
                <span class="step-pill">4 Generate Memo</span>
                <span class="step-pill">5 Human Approval</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Workflow Summary")
        st.caption("Load data, review deterministic checks, then generate the memo.")
        st.divider()

        st.header("Data Source")
        use_demo_data = st.checkbox("Use demo data", value=True)
        constituents_file = st.file_uploader("Constituents CSV", type="csv")
        factor_scores_file = st.file_uploader("Factor scores CSV", type="csv")
        backtest_metrics_file = st.file_uploader("Backtest metrics CSV", type="csv")
        if use_demo_data:
            st.caption("Demo data is active. Uploaded files are ignored until demo data is turned off.")
        else:
            st.caption("Upload any subset of files. Missing files fall back to the demo data.")

        st.divider()
        st.header("Memo Generation")
        use_llm = st.toggle("Generate with LLM", value=False)
        provider_choice = st.selectbox(
            "LLM provider",
            ["Auto", "Gemini", "OpenAI"],
            disabled=not use_llm,
        )
        default_provider, default_model = _select_llm_provider(provider_choice)
        model = st.text_input("Model", value=default_model, disabled=not use_llm)
        api_key = st.text_input(
            "API key",
            type="password",
            disabled=not use_llm,
            help="Optional. You can paste a key for this session, or set it as an environment variable before launching the app.",
        )
        st.caption("API keys are used only for this session and never written to project files.")

        st.divider()
        st.header("Actions")
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
    control_checklist = _control_checklist(checklist)

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
        provider, selected_default_model = _select_llm_provider(provider_choice)
        selected_model = model or selected_default_model
        _status_card("Memo mode", active_mode, f"Provider: {provider}, model: {selected_model}")

    st.divider()

    st.markdown("## Quantitative Dashboard")
    metric_cols = st.columns(4)
    with metric_cols[0]:
        _metric_card("Names", f"{summary['number_of_names']}", "Constituents in the review universe")
    with metric_cols[1]:
        _metric_card("Excess Return", f"{backtest['annualized_excess_return'] * 10000:.0f} bps", "Annualized active return target")
    with metric_cols[2]:
        _metric_card("Tracking Error", f"{backtest['tracking_error']:.1%}", "Active risk versus benchmark")
    with metric_cols[3]:
        _metric_card("Turnover", f"{backtest['turnover']:.1%}", "Estimated trading intensity")

    metric_cols_2 = st.columns(3)
    with metric_cols_2[0]:
        _metric_card("One-way Cost", f"{backtest['one_way_cost']:.2%}", "Transaction cost assumption")
    with metric_cols_2[1]:
        _metric_card("Missing Factors", f"{summary['missing_factor_count']}", "Data quality gaps in factor inputs")
    with metric_cols_2[2]:
        trading_constraints = summary["suspended_count"] + summary["limit_up_count"] + summary["limit_down_count"]
        _metric_card("Trading Constraints", f"{trading_constraints}", "Suspended plus price-limited names")

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
            risk_table = [
                {
                    "Severity": flag.get("severity", "").title(),
                    "Category": flag.get("category", ""),
                    "Message": flag.get("message", ""),
                    "Human Review Required": "Yes" if flag.get("human_review_required") else "No",
                }
                for flag in flags
            ]
            st.dataframe(risk_table, width="stretch", hide_index=True)
        else:
            st.success("No rule-based risk flags were triggered.")
    with risk_right:
        st.markdown("#### Severity Summary")
        st.metric("High severity", severity_counts["high"])
        st.metric("Medium severity", severity_counts["medium"])
        st.metric("Human review items", len(control_checklist))

    st.info(f"Recommendation: {recommendation}")

    with st.expander("View input data tables", expanded=False):
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
        provider, selected_default_model = _select_llm_provider(provider_choice)
        selected_model = model or selected_default_model
        try:
            memo = generate_memo(
                summary,
                flags,
                recommendation,
                use_llm=use_llm,
                provider=provider,
                model=selected_model,
            )
            st.session_state["generated_memo"] = memo
        except Exception as exc:
            st.error(f"Memo generation failed: {exc}")

    memo = st.session_state.get("generated_memo")
    if memo:
        memo_col, action_col = st.columns([3, 1])
        with memo_col:
            with st.container(border=True):
                st.markdown(memo)
            with st.expander("View raw memo text for copying", expanded=False):
                st.text_area("Raw memo text", memo, height=360)
        with action_col:
            st.markdown("#### Memo Actions")
            st.download_button(
                "Download memo as .txt",
                data=memo,
                file_name="rebalance_review_memo.txt",
                mime="text/plain",
                width="stretch",
            )
            if flags:
                st.download_button(
                    "Download risk flags as .csv",
                    data=_risk_flags_csv(flags),
                    file_name="risk_flags.csv",
                    mime="text/csv",
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
    for index, item in enumerate(control_checklist):
        with review_cols[index % 2]:
            st.checkbox(item, value=False)

    st.markdown("## Methodology Note")
    method_cols = st.columns(4)
    methodology = [
        ("Python calculates", "Metrics are computed before memo generation."),
        ("Rules detect risks", "Transparent thresholds create risk flags."),
        ("GenAI drafts", "The model converts structured inputs into prose."),
        ("Human decides", "Analysts approve, revise, or reject the output."),
    ]
    for index, (label, note) in enumerate(methodology):
        with method_cols[index]:
            _status_card(f"Step {index + 1}", label, note)


if __name__ == "__main__":
    main()
