from pathlib import Path

from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class ReportingEngine:
    """
    Builds and exports complete AutoDQ reports.
    """

    def build_report(
        self,
        state,
        session,
        output_dir: str | Path = "reports",
    ):
        output_dir = Path(output_dir)
        chart_dir = output_dir / "charts"

        from autodq.visualization.renderers.matplotlib_renderer import (
            MatplotlibVisualizationRenderer,
        )

        rendered_visualizations = MatplotlibVisualizationRenderer().render_report(
            visualization_report=state.visualization_report,
            output_dir=chart_dir,
        )

        return AutoDQReport(
            dataset=str(state.dataset_path),
            session=session,
            profile=state.profile_report,
            statistics=state.statistics_report,
            interpretations=state.interpretation_report,
            diagnosis=state.diagnosis_report,
            recommendations=state.recommendations,
            decision_plan=state.decision_plan,
            preview=state.preview_report,
            cleaning=state.cleaning_report,
            cleaning_review=state.cleaning_review,
            domain_validation=state.domain_validation_report,
            automation=state.auto_run_report,
            dashboard=state.dashboard_report,
            adql_history=list(state.adql_history),
            validation=state.validation_report,
            visualizations=state.visualization_report,
            rendered_visualizations=rendered_visualizations,
            model=state.model_report,
            prediction=state.prediction_report,
            explainability=state.explainability_report,
            blue=state.blue_report,
        )

    def export(
        self,
        report,
        output: str,
        style: str = "executive",
    ):
        output = Path(output)
        suffix = output.suffix.lower()

        if suffix == ".json":
            JSONExporter().export(report, output)

        elif suffix == ".html":
            HTMLExporter().export(
                report,
                output,
                style=style,
            )

        else:
            raise ValueError(
                f"Unsupported report format: {suffix}"
            )
