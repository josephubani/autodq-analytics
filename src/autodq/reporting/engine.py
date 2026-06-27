from pathlib import Path

from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class ReportingEngine:
    def build_report(self, state, session):
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