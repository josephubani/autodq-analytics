"""AutoDQ Studio — a Streamlit interface for the AutoDQ analytics engine."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = APP_DIR.parent

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.autodq_web.presenters import (  # noqa: E402
    action_frame,
    column_catalog,
    dataset_metrics,
    frame_to_csv_bytes,
    frame_to_excel_bytes,
    humanize_identifier,
    issue_frame,
    recommendation_frame,
    to_serializable,
    validation_frame,
)
from app.autodq_web.styles import APP_CSS  # noqa: E402
from autodq import AutoDQ  # noqa: E402
from autodq.visualization.renderers.matplotlib_renderer import (  # noqa: E402
    MatplotlibVisualizationRenderer,
)


NAVIGATION = (
    "Overview",
    "Quality scan",
    "Cleaning lab",
    "Explore",
    "ADQL studio",
)

ADQL_TEMPLATES = {
    "Quick quality check": """PROFILE;
DIAGNOSE;
MISSING SUMMARY;
DUPLICATES SUMMARY;""",
    "Preview current data": """SELECT *
FROM CURRENT
LIMIT 25;""",
    "Numeric summary": """STATISTICS;
INTERPRET;""",
    "Readiness check": """CORRELATION MIN ABS 0.30;
READINESS;""",
}


def configure_page() -> None:
    st.set_page_config(
        page_title="AutoDQ Studio",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/josephubani/autodq-analytics",
            "Report a bug": "https://github.com/josephubani/autodq-analytics/issues",
            "About": "AutoDQ Studio — data quality and analytics without the boilerplate.",
        },
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)


def initialize_state() -> None:
    defaults = {
        "project": None,
        "dataset_name": None,
        "dataset_fingerprint": None,
        "upload_fingerprint": None,
        "workspace_dir": None,
        "page": "Overview",
        "adql_source": ADQL_TEMPLATES["Quick quality check"],
        "adql_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def project() -> AutoDQ | None:
    return st.session_state.project


def source_frame() -> pd.DataFrame | None:
    current = project()
    return current.state.data if current is not None else None


def stage_frame(stage: str) -> pd.DataFrame | None:
    current = project()
    if current is None:
        return None
    if stage == "cleaned":
        return current.state.cleaned_data
    if stage == "engineered":
        return current.state.engineered_data
    return current.state.data


def safe_uploaded_name(name: str) -> str:
    path = Path(name).name
    stem = "".join(char for char in Path(path).stem if char.isalnum() or char in "-_ ").strip()
    return f"{stem or 'dataset'}{Path(path).suffix.lower()}"


def load_project(path: Path, *, display_name: str, fingerprint: str) -> None:
    with st.spinner("Loading the dataset into AutoDQ…"):
        current = AutoDQ(str(path))
        current.load()
    st.session_state.project = current
    st.session_state.dataset_name = display_name
    st.session_state.dataset_fingerprint = fingerprint
    st.session_state.adql_result = None


def load_upload(uploaded_file) -> None:
    payload = uploaded_file.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    if digest == st.session_state.upload_fingerprint:
        return

    root = Path(tempfile.mkdtemp(prefix="autodq-studio-"))
    path = root / safe_uploaded_name(uploaded_file.name)
    path.write_bytes(payload)
    st.session_state.workspace_dir = str(root)
    st.session_state.upload_fingerprint = digest
    load_project(path, display_name=path.name, fingerprint=digest)
    st.toast("Dataset loaded", icon="✅")
    st.rerun()


def load_sample() -> None:
    path = REPOSITORY_ROOT / "datasets" / "sample" / "sales.csv"
    fingerprint = f"sample:{path.stat().st_mtime_ns}:{path.stat().st_size}"
    load_project(path, display_name="sales.csv · sample", fingerprint=fingerprint)
    st.toast("Sample sales dataset loaded", icon="✨")
    st.rerun()


def reset_session() -> None:
    workspace = st.session_state.get("workspace_dir")
    if workspace:
        shutil.rmtree(workspace, ignore_errors=True)
    for key in list(st.session_state):
        del st.session_state[key]
    st.rerun()


def render_brand() -> None:
    st.markdown(
        """
        <div class="dq-brand">
          <div class="dq-mark">DQ</div>
          <div><strong>AutoDQ Studio</strong><span>Quality intelligence workspace</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        render_brand()
        uploaded = st.file_uploader(
            "Upload a dataset",
            type=("csv", "xlsx", "xls"),
            help="Your file stays in this local Streamlit session.",
        )
        if uploaded is not None:
            load_upload(uploaded)

        sample_disabled = not (REPOSITORY_ROOT / "datasets" / "sample" / "sales.csv").exists()
        if st.button(
            "Use sample sales data",
            width="stretch",
            disabled=sample_disabled,
        ):
            load_sample()

        current = project()
        if current is not None and current.state.data is not None:
            st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
            st.markdown(
                '<span class="dq-status"><span class="dq-dot"></span>Dataset active</span>',
                unsafe_allow_html=True,
            )
            st.caption(st.session_state.dataset_name)

            columns = list(current.state.data.columns)
            options = ["No target"] + columns
            active_target = current.target if current.target in columns else "No target"
            selected = st.selectbox(
                "Prediction target",
                options,
                index=options.index(active_target),
                help="Optional. Needed for readiness, modeling, and SHAP workflows.",
            )
            target = None if selected == "No target" else selected
            if target != current.target:
                if target is None:
                    current.state.target = None
                    current._invalidate_target_pipeline()
                else:
                    current.set_target(target)

            st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
            page = st.radio(
                "Workspace",
                NAVIGATION,
                key="page",
                label_visibility="collapsed",
            )
            st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
            if st.button("Reset workspace", width="stretch"):
                reset_session()
            return page

        st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
        st.caption("Upload CSV or Excel, or begin with the bundled sales example.")
        return "Overview"


def page_title(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="dq-page-title">
          <small>{kicker}</small>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="dq-card">
          <div class="eyebrow">{eyebrow}</div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
        <section class="dq-hero">
          <div class="dq-kicker">AutoDQ · Web v1</div>
          <h1>From raw data to trusted decisions.</h1>
          <p>Profile quality, review evidence-backed cleaning actions, explore patterns, and run ADQL in one focused workspace.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    left, middle, right = st.columns(3)
    with left:
        feature_card("01 · Inspect", "Know the dataset", "Immediate structure, completeness, duplicate, and semantic-type signals.")
    with middle:
        feature_card("02 · Improve", "Clean with evidence", "Review recommendations before applying traceable changes to your data.")
    with right:
        feature_card("03 · Analyze", "Move beyond cleaning", "Create visuals and execute ADQL against the same in-memory project.")

    st.write("")
    action, note = st.columns([1, 2])
    with action:
        if st.button("Explore with sample data", type="primary", width="stretch"):
            load_sample()
    with note:
        st.markdown(
            '<p class="dq-note">No account or database required for v1. Uploaded files are processed inside the running Streamlit session.</p>',
            unsafe_allow_html=True,
        )


def metric_row(frame: pd.DataFrame, *, quality_score: float | None = None) -> None:
    metrics = dataset_metrics(frame)
    columns = st.columns(5)
    columns[0].metric("Rows", f"{metrics['rows']:,}")
    columns[1].metric("Columns", f"{metrics['columns']:,}")
    columns[2].metric("Missing cells", f"{metrics['missing']:,}", f"{metrics['missing_percent']:.2f}%")
    columns[3].metric("Duplicate rows", f"{metrics['duplicates']:,}", f"{metrics['duplicate_percent']:.2f}%")
    score = quality_score if quality_score is not None else metrics["completeness"]
    columns[4].metric("Quality score" if quality_score is not None else "Completeness", f"{score:.2f}")


def run_quality_scan() -> None:
    current = project()
    if current is None:
        return
    with st.spinner("AutoDQ is profiling, diagnosing, and building recommendations…"):
        current.profile()
        current.diagnose()
        current.recommend()
        current.decide()
        current.preview()
    st.toast("Quality scan completed", icon="✅")
    st.rerun()


def render_overview() -> None:
    current = project()
    frame = current.state.data
    page_title(
        "Workspace overview",
        st.session_state.dataset_name,
        "A live view of the active dataset and every artifact created during this session.",
    )
    quality_score = (
        current.state.diagnosis_report.quality_score
        if current.state.diagnosis_report is not None
        else None
    )
    metric_row(frame, quality_score=quality_score)

    st.write("")
    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Data preview")
        st.dataframe(frame.head(50), width="stretch", hide_index=True)
    with right:
        st.subheader("Workflow progress")
        stages = [
            ("Profile", current.state.profile_report is not None),
            ("Diagnosis", current.state.diagnosis_report is not None),
            ("Cleaning plan", current.state.decision_plan is not None),
            ("Cleaned data", current.state.cleaned_data is not None),
            ("Validation", current.state.validation_report is not None),
            ("ADQL run", bool(current.adql_history)),
        ]
        for label, complete in stages:
            icon = "✓" if complete else "○"
            color = "#66e5bd" if complete else "#78918b"
            st.markdown(f"<div style='padding:.47rem 0;color:{color};font-weight:650'>{icon}&nbsp;&nbsp;{label}</div>", unsafe_allow_html=True)
        st.write("")
        if st.button("Run quick quality scan", type="primary", width="stretch"):
            run_quality_scan()

    st.subheader("Column catalogue")
    st.dataframe(column_catalog(frame), width="stretch", hide_index=True)


def render_quality() -> None:
    current = project()
    page_title(
        "Quality intelligence",
        "Quality scan",
        "Surface missingness, duplication, outliers, datatype signals, and evidence-backed recommendations.",
    )
    if current.state.diagnosis_report is None:
        st.info("Run the scan to create a profile, diagnosis, statistical evidence, recommendations, and a cleaning plan.")
        if st.button("Run full quality scan", type="primary"):
            run_quality_scan()
        return

    report = current.state.diagnosis_report
    metric_row(current.state.data, quality_score=report.quality_score)
    st.write("")
    summary, action = st.columns([3, 1])
    with summary:
        st.markdown(f"**AutoDQ summary:** {report.summary or 'Quality analysis completed.'}")
    with action:
        if st.button("Refresh scan", width="stretch"):
            run_quality_scan()

    issues = issue_frame(report)
    tab_issues, tab_missing, tab_duplicates, tab_recommend = st.tabs(
        ("Issues", "Missing values", "Duplicate rows", "Recommendations")
    )
    with tab_issues:
        if issues.empty:
            st.success("No data-quality issues were detected.")
        else:
            st.dataframe(issues, width="stretch", hide_index=True)
    with tab_missing:
        missing = current.missing_summary()
        st.dataframe(missing, width="stretch", hide_index=True)
        chart_data = missing.loc[missing["missing"] > 0, ["column", "missing"]]
        if not chart_data.empty:
            st.bar_chart(chart_data.set_index("column"), color="#2dd4a3")
    with tab_duplicates:
        duplicates = current.duplicate_summary()
        if duplicates.empty:
            st.success("No exact duplicate rows were found.")
        else:
            st.caption(f"Showing {min(len(duplicates), 100):,} of {len(duplicates):,} duplicate-row occurrences.")
            st.dataframe(duplicates.head(100), width="stretch", hide_index=True)
    with tab_recommend:
        recommendations = recommendation_frame(current.state.recommendations)
        if recommendations.empty:
            st.success("No cleaning recommendations are required.")
        else:
            st.dataframe(recommendations, width="stretch", hide_index=True)


def prepare_review() -> None:
    current = project()
    if current.state.decision_plan is None:
        current.profile()
        current.diagnose()
        current.recommend()
        current.decide()
        current.preview()
    with st.spinner("Preparing the interactive cleaning review…"):
        current.review_cleaning(auto_display=False)
    st.toast("Cleaning review is ready", icon="🧹")
    st.rerun()


def render_cleaning() -> None:
    current = project()
    page_title(
        "Governed cleaning",
        "Cleaning lab",
        "Approve automatic actions, handle missing values and duplicates manually, then validate every change.",
    )
    if current.state.cleaning_review is None:
        st.info("Prepare a review to inspect every proposed cleaning action before data is changed.")
        if st.button("Prepare cleaning review", type="primary"):
            prepare_review()
        return

    review = current.state.cleaning_review
    counts = st.columns(4)
    counts[0].metric("Actions", review.action_count)
    counts[1].metric("Pending", review.pending_count)
    counts[2].metric("Approved", review.approved_count)
    counts[3].metric("Rejected", review.rejected_count)

    actions = action_frame(review)
    if actions.empty:
        st.success("No automatic cleaning actions are required. Manual tools remain available below.")
    else:
        st.dataframe(actions, width="stretch", hide_index=True)
        options = actions["ID"].tolist()
        selected = st.multiselect(
            "Select action IDs",
            options,
            format_func=lambda value: f"#{value} · {actions.loc[actions['ID'] == value, 'Issue'].iloc[0]}",
        )
        approve, reject, apply_all = st.columns([1, 1, 1.35])
        with approve:
            if st.button("Approve selected", disabled=not selected, width="stretch"):
                current.approve(selected)
                st.rerun()
        with reject:
            if st.button("Reject selected", disabled=not selected, width="stretch"):
                current.reject(selected, reason="Rejected in AutoDQ Studio")
                st.rerun()
        with apply_all:
            if st.button("Approve all and clean", type="primary", width="stretch"):
                with st.spinner("Applying approved actions and validating the result…"):
                    current.approve_all()
                    current.clean()
                    current.validate_cleaning()
                st.toast("Cleaned dataset created", icon="✅")
                st.rerun()

    tab_missing, tab_duplicates, tab_outliers, tab_result = st.tabs(
        ("Missing values", "Duplicates", "Outliers", "Cleaned result")
    )
    with tab_missing:
        summary = current.missing_summary()
        st.dataframe(summary, width="stretch", hide_index=True)
        affected = summary.loc[summary["missing"] > 0, "column"].tolist()
        if affected:
            selected_columns = st.multiselect(
                "Columns to fill",
                summary["column"].tolist(),
                default=affected,
                key="missing_columns",
            )
            strategy = st.selectbox(
                "Strategy",
                ("auto", "median", "mean", "mode", "zero", "ffill", "bfill", "interpolate", "constant"),
            )
            constant = st.text_input("Constant value", disabled=strategy != "constant")
            if st.button("Stage missing-value treatment", disabled=not selected_columns):
                value = constant if strategy == "constant" else None
                current.fill_missing(selected_columns, strategy=strategy, value=value, reason="Staged in AutoDQ Studio")
                st.toast("Missing-value treatment staged", icon="✅")
                st.rerun()
        else:
            st.success("No missing values remain in the review data.")
    with tab_duplicates:
        duplicates = current.duplicate_summary()
        if duplicates.empty:
            st.success("No exact duplicate rows remain.")
        else:
            st.dataframe(duplicates.head(100), width="stretch", hide_index=True)
            if st.button("Stage duplicate removal", key="drop_duplicates"):
                current.drop_duplicates(keep="first", reason="Staged in AutoDQ Studio")
                st.toast("Duplicate removal staged", icon="✅")
                st.rerun()
    with tab_outliers:
        if st.button("Review numeric outliers"):
            current.review_outliers()
            st.rerun()
        outlier_report = review.outlier_report
        if outlier_report is not None:
            st.metric("Outlier observations", outlier_report.outlier_count)
            records = pd.DataFrame([item.to_dict() for item in outlier_report.records])
            if records.empty:
                st.success("No IQR outliers were detected.")
            else:
                st.dataframe(records.head(200), width="stretch", hide_index=True)
    with tab_result:
        cleaned = current.state.cleaned_data
        if cleaned is None:
            st.caption("Apply the reviewed cleaning plan to create a validated cleaned dataset.")
        else:
            validation = current.state.validation_report
            if validation is not None:
                before, after, delta = st.columns(3)
                before.metric("Quality before", f"{validation.quality_score_before:.2f}")
                after.metric("Quality after", f"{validation.quality_score_after:.2f}")
                delta.metric("Quality change", f"{validation.quality_score_change:+.2f}")
                st.dataframe(validation_frame(validation), width="stretch", hide_index=True)
            st.dataframe(cleaned.head(100), width="stretch", hide_index=True)
            download_exports(cleaned, prefix="autodq-cleaned")


def available_stages() -> dict[str, str]:
    current = project()
    stages = {"Current data": "current"}
    if current.state.cleaned_data is not None:
        stages["Cleaned data"] = "cleaned"
    if current.state.engineered_data is not None:
        stages["Engineered data"] = "engineered"
    return stages


def render_chart_report(report) -> None:
    if report is None or not report.charts:
        st.warning("No visualization was generated for this selection.")
        return
    renderer = MatplotlibVisualizationRenderer()
    for chart in report.charts:
        st.markdown(f"#### {chart.title}")
        st.caption(chart.description)
        figure, _ = renderer.build_figure(chart)
        st.pyplot(figure, width="stretch")
        plt.close(figure)


def render_explore() -> None:
    current = project()
    page_title(
        "Visual analytics",
        "Explore",
        "Build reusable AutoDQ charts against the current, cleaned, or engineered stage.",
    )
    stage_options = available_stages()
    stage_label = st.selectbox("Dataset stage", tuple(stage_options))
    stage = stage_options[stage_label]
    frame = stage_frame(stage)
    numeric = list(frame.select_dtypes(include="number").columns)
    all_columns = list(frame.columns)
    chart_types = ["auto", "missing_values", "distribution"]
    if numeric:
        chart_types.extend(("histogram", "boxplot", "bar"))
    if len(numeric) >= 2:
        chart_types.extend(("scatter", "correlation_heatmap"))

    controls = st.columns([1, 1, 1])
    with controls[0]:
        chart = st.selectbox(
            "Chart type",
            chart_types,
            format_func=lambda value: humanize_identifier(value).title(),
        )
    x = y = column = None
    with controls[1]:
        if chart in {"distribution", "histogram", "boxplot"}:
            candidates = numeric if chart in {"histogram", "boxplot"} else all_columns
            column = st.selectbox("Column", candidates or all_columns)
        elif chart in {"bar", "scatter"}:
            x_candidates = numeric if chart == "scatter" else all_columns
            x = st.selectbox("X axis", x_candidates)
    with controls[2]:
        if chart in {"bar", "scatter"}:
            y = st.selectbox("Y axis", numeric)

    title = st.text_input("Optional chart title")
    if st.button("Generate visualization", type="primary"):
        try:
            with st.spinner("Rendering with AutoDQ…"):
                report = current.visualize(
                    chart=chart,
                    x=x,
                    y=y,
                    column=column,
                    stage=stage,
                    append=False,
                    display=False,
                    title=title or None,
                    theme="dark",
                    grid=True,
                )
            st.session_state.visualization_result = report
        except Exception as error:
            st.error(f"Visualization failed: {error}")

    report = st.session_state.get("visualization_result")
    if report is not None:
        render_chart_report(report)

    with st.expander("Preview selected stage"):
        st.dataframe(frame.head(100), width="stretch", hide_index=True)


def render_adql_result(run) -> None:
    summary = st.columns(4)
    summary[0].metric("Statements", run.statement_count)
    summary[1].metric("Completed", run.completed_count)
    summary[2].metric("Failed", run.failed_count)
    summary[3].metric("Runtime", f"{run.duration_seconds:.3f}s")

    for index, result in enumerate(run.results, start=1):
        icon = "✅" if result.success else "❌"
        with st.expander(f"{icon} Statement {index} · {result.statement.kind}", expanded=True):
            st.code(result.statement.raw, language="sql")
            if result.success:
                st.success(result.message)
            else:
                st.error(result.error_message or result.message)
            if result.data is not None and result.display_data:
                st.dataframe(result.data, width="stretch", hide_index=True)
            elif result.value is not None:
                st.json(to_serializable(result.value), expanded=False)


def render_adql() -> None:
    current = project()
    page_title(
        "Native analytics language",
        "ADQL studio",
        "Run ADQL directly against the same in-memory project. Commands can inspect, clean, analyze, and register reusable datasets.",
    )
    template, action = st.columns([2, 1])
    with template:
        selected_template = st.selectbox("Starter", tuple(ADQL_TEMPLATES))
    with action:
        st.write("")
        if st.button("Load starter", width="stretch"):
            st.session_state.adql_source = ADQL_TEMPLATES[selected_template]
            st.rerun()

    source = st.text_area(
        "ADQL",
        key="adql_source",
        height=260,
        help="Statements end with semicolons. Commands are case-insensitive.",
    )
    run_column, clear_column, help_column = st.columns([1, 1, 2])
    with run_column:
        run_clicked = st.button("Run ADQL", type="primary", width="stretch")
    with clear_column:
        if st.button("Clear output", width="stretch"):
            st.session_state.adql_result = None
            st.rerun()
    with help_column:
        st.caption("Tip: use double quotes for readable identifiers and single quotes for text or paths.")

    if run_clicked:
        try:
            with st.spinner("Executing ADQL…"):
                st.session_state.adql_result = current.query(
                    source,
                    auto_display=False,
                    source_name="streamlit",
                    base_path=REPOSITORY_ROOT,
                )
            st.toast("ADQL completed", icon="✅")
        except Exception as error:
            st.session_state.adql_result = None
            st.error(f"ADQL execution failed: {error}")

    if st.session_state.adql_result is not None:
        render_adql_result(st.session_state.adql_result)


def download_exports(frame: pd.DataFrame, *, prefix: str) -> None:
    csv_column, excel_column = st.columns(2)
    with csv_column:
        st.download_button(
            "Download CSV",
            frame_to_csv_bytes(frame),
            file_name=f"{prefix}.csv",
            mime="text/csv",
            width="stretch",
        )
    with excel_column:
        st.download_button(
            "Download Excel",
            frame_to_excel_bytes(frame),
            file_name=f"{prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def main() -> None:
    configure_page()
    initialize_state()
    page = render_sidebar()
    if project() is None:
        render_empty_state()
        return

    renderers = {
        "Overview": render_overview,
        "Quality scan": render_quality,
        "Cleaning lab": render_cleaning,
        "Explore": render_explore,
        "ADQL studio": render_adql,
    }
    renderers[page]()


if __name__ == "__main__":
    main()
