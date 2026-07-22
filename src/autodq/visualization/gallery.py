from __future__ import annotations

from pathlib import Path

from autodq.visualization.models import (
    VisualizationReport,
    VisualizationSpec,
)


class VisualizationGallery:
    """Searchable collection of reusable AutoDQ charts."""

    def __init__(self):
        self._charts: list[VisualizationSpec] = []

    @property
    def charts(self) -> list[VisualizationSpec]:
        return list(self._charts)

    @property
    def chart_count(self) -> int:
        return len(self._charts)

    def add_report(
        self,
        visualization_report,
        allow_duplicates: bool = False,
        replace_existing: bool = False,
    ) -> list[VisualizationSpec]:
        """Add report charts and return charts added or replaced."""
        if visualization_report is None:
            return []

        incoming_charts = getattr(visualization_report, "charts", [])
        changed = []

        for chart in incoming_charts:
            existing_index = self._find_index(chart)

            if existing_index is not None and not allow_duplicates:
                if replace_existing:
                    self._charts[existing_index] = chart
                    changed.append(chart)

                continue

            self._charts.append(chart)
            changed.append(chart)

        return changed

    def get(self, chart_id: str) -> VisualizationSpec:
        for chart in self._charts:
            if chart.chart_id == chart_id:
                return chart

        raise KeyError(f"Visualization was not found: {chart_id}")

    def remove(self, chart_id: str) -> VisualizationSpec:
        for index, chart in enumerate(self._charts):
            if chart.chart_id == chart_id:
                return self._charts.pop(index)

        raise KeyError(f"Visualization was not found: {chart_id}")

    def filter(
        self,
        *,
        chart_type: str | None = None,
        stage: str | None = None,
        recommended: bool | None = None,
    ) -> list[VisualizationSpec]:
        charts = self._charts

        if chart_type is not None:
            charts = [
                chart
                for chart in charts
                if chart.chart_type == chart_type
            ]

        if stage is not None:
            charts = [chart for chart in charts if chart.stage == stage]

        if recommended is not None:
            charts = [
                chart
                for chart in charts
                if chart.recommended is recommended
            ]

        return list(charts)

    def customize(self, chart_id: str, **options) -> VisualizationSpec:
        return self.get(chart_id).customize(**options)

    def to_report(self) -> VisualizationReport:
        return VisualizationReport(charts=self.charts)

    def show(self) -> VisualizationReport:
        report = self.to_report()
        report.show()
        return report

    def save(
        self,
        output_dir: str | Path,
        *,
        format: str = "png",
    ) -> list[Path]:
        return self.to_report().save(output_dir, format=format)

    def clear(self) -> None:
        self._charts.clear()

    def _find_index(self, candidate) -> int | None:
        signature = self._signature(candidate)

        for index, existing in enumerate(self._charts):
            if self._signature(existing) == signature:
                return index

        return None

    @staticmethod
    def _signature(chart) -> tuple:
        return (
            getattr(chart, "chart_id", None),
            getattr(chart, "chart_type", None),
            getattr(chart, "stage", None),
        )
