from pathlib import Path

from autodq.models.report import AutoDQReport
from autodq.reporting.json_exporter import JSONExporter
from autodq.reporting.html_exporter import HTMLExporter


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
            session=session,
        )

    def export(self, report, output: str):

        output = Path(output)

        suffix = output.suffix.lower()

        if suffix == ".json":
            JSONExporter().export(report, output)

        elif suffix == ".html":
            HTMLExporter().export(report, output)

        else:
            raise ValueError(
                f"Unsupported report format: {suffix}"
            )