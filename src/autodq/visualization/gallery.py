from __future__ import annotations


class VisualizationGallery:
    """
    Stores visualization specifications created during an AutoDQ session.

    Responsibilities:
    - append newly created charts
    - prevent accidental duplicates
    - remove charts
    - clear the gallery
    - expose all retained charts to reporting
    """

    def __init__(self):
        self._charts = []

    @property
    def charts(self) -> list:
        return list(self._charts)

    @property
    def chart_count(self) -> int:
        return len(self._charts)

    def add_report(
        self,
        visualization_report,
        allow_duplicates: bool = False,
    ) -> list:
        """
        Add every chart from a VisualizationReport.

        Returns only the charts that were newly added.
        """

        if visualization_report is None:
            return []

        incoming_charts = getattr(
            visualization_report,
            "charts",
            [],
        )

        added_charts = []

        for chart in incoming_charts:
            if (
                not allow_duplicates
                and self._contains_chart(chart)
            ):
                continue

            self._charts.append(chart)
            added_charts.append(chart)

        return added_charts

    def remove(self, chart_id: str):
        """
        Remove a chart by its chart ID.
        """

        for index, chart in enumerate(self._charts):
            if getattr(chart, "chart_id", None) == chart_id:
                return self._charts.pop(index)

        raise KeyError(
            f"Visualization was not found: {chart_id}"
        )

    def clear(self) -> None:
        self._charts.clear()

    def get(self, chart_id: str):
        for chart in self._charts:
            if getattr(chart, "chart_id", None) == chart_id:
                return chart

        raise KeyError(
            f"Visualization was not found: {chart_id}"
        )

    def _contains_chart(self, candidate) -> bool:
        candidate_signature = self._signature(candidate)

        return any(
            self._signature(existing) == candidate_signature
            for existing in self._charts
        )

    def _signature(self, chart) -> tuple:
        """
        Build a stable signature to prevent repeated identical charts.
        """

        return (
            getattr(chart, "chart_type", None),
            getattr(chart, "x", None),
            getattr(chart, "y", None),
            getattr(chart, "column", None),
            getattr(chart, "stage", None),
            getattr(chart, "title", None),
        )