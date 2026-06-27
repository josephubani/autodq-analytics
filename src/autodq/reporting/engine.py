from pathlib import Path

from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter
from autodq.visualization.renderers.matplotlib_renderer import (
    MatplotlibVisualizationRenderer,
)


class ReportingEngine:
    def __init__(self):
        self.visual_renderer = MatplotlibVisualizationRenderer()

    def build_report(self, state, session, output_dir: str | Path = "reports"):
        output_dir = Path(output_dir)
        chart_dir = output_dir / "charts"

        rendered_visualizations = self.visual_renderer.render_report(
            visualization_report=state.visualization_report,
            output_dir=chart_dir,
        )

        return AutoDQReport(
            dataset=str(state.dataset_path),
            profile=state.profile_report,
            statistics=state.statistics_report,
            interpretations=state.interpretation_report,
            diagnosis=state.diagnosis_report,
            recommendations=state.recommendations,
            decision_plan=state.decision_plan,
            preview=state.preview_report,
            cleaning=state.cleaning_report,
            validation=state.validation_report,
            visualizations=state.visualization_report,
            rendered_visualizations=rendered_visualizations,
            session=session,
        )

    def export(self, report, output: str, style: str = "executive"):
        output = Path(output)
        suffix = output.suffix.lower()

        if suffix == ".json":
            JSONExporter().export(report, output)

        elif suffix == ".html":
            HTMLExporter().export(report, output, style=style)

        else:
            raise ValueError(f"Unsupported report format: {suffix}")