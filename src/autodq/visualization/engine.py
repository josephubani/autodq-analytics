import pandas as pd

from autodq.visualization.models import VisualizationReport, VisualizationSpec


class VisualizationEngine:
    """
    Builds visualization specifications for AutoDQ.

    Supports:
    - automatic recommended charts
    - user-selected charts
    - before/after comparison visuals
    """

    def visualize(
        self,
        df: pd.DataFrame,
        chart: str | None = None,
        x: str | None = None,
        y: str | None = None,
        column: str | None = None,
        stage: str = "current",
        cleaned_df: pd.DataFrame | None = None,
        diagnosis_report=None,
        cleaning_report=None,
        validation_report=None,
    ) -> VisualizationReport:
        report = VisualizationReport()

        if chart is None or chart == "auto":
            report.charts.extend(
                self._auto_charts(
                    df=df,
                    cleaned_df=cleaned_df,
                    diagnosis_report=diagnosis_report,
                    cleaning_report=cleaning_report,
                    validation_report=validation_report,
                )
            )
            return report

        if chart == "quality_score":
            spec = self._quality_score_chart(validation_report)
            if spec:
                report.charts.append(spec)

        elif chart == "missing_values":
            report.charts.append(self._missing_values_chart(df, stage=stage))

        elif chart == "issue_breakdown":
            spec = self._issue_breakdown_chart(diagnosis_report)
            if spec:
                report.charts.append(spec)

        elif chart == "cleaning_status":
            spec = self._cleaning_status_chart(cleaning_report)
            if spec:
                report.charts.append(spec)

        elif chart == "comparison":
            specs = self._comparison_charts(validation_report)
            report.charts.extend(specs)

        elif chart == "distribution":
            if column is None:
                raise ValueError("column is required for distribution chart.")
            report.charts.append(self._distribution_chart(df, column, stage=stage))

        elif chart == "bar":
            if x is None or y is None:
                raise ValueError("x and y are required for bar chart.")
            report.charts.append(self._bar_chart(df, x=x, y=y, stage=stage))

        elif chart == "scatter":
            if x is None or y is None:
                raise ValueError("x and y are required for scatter chart.")
            report.charts.append(self._scatter_chart(df, x=x, y=y, stage=stage))

        else:
            raise ValueError(
                f"Unsupported chart: {chart}. "
                "Supported: auto, quality_score, missing_values, issue_breakdown, "
                "cleaning_status, comparison, distribution, bar, scatter"
            )

        return report

    def _auto_charts(
        self,
        df: pd.DataFrame,
        cleaned_df: pd.DataFrame | None = None,
        diagnosis_report=None,
        cleaning_report=None,
        validation_report=None,
    ) -> list[VisualizationSpec]:
        charts = []

        quality_chart = self._quality_score_chart(validation_report)
        if quality_chart:
            quality_chart.recommended = True
            charts.append(quality_chart)

        charts.append(self._missing_values_chart(df, stage="before"))

        if cleaned_df is not None:
            charts.append(self._missing_values_chart(cleaned_df, stage="after"))

        issue_chart = self._issue_breakdown_chart(diagnosis_report)
        if issue_chart:
            issue_chart.recommended = True
            charts.append(issue_chart)

        cleaning_chart = self._cleaning_status_chart(cleaning_report)
        if cleaning_chart:
            cleaning_chart.recommended = True
            charts.append(cleaning_chart)

        charts.extend(self._comparison_charts(validation_report))

        return charts

    def _quality_score_chart(self, validation_report) -> VisualizationSpec | None:
        if validation_report is None:
            return None

        return VisualizationSpec(
            chart_id="quality_score_comparison",
            chart_type="bar",
            title="Quality Score Before vs After",
            description="Compares the dataset quality score before and after approved cleaning actions.",
            x="stage",
            y="score",
            stage="comparison",
            recommended=True,
            data=[
                {
                    "stage": "before",
                    "score": validation_report.quality_score_before,
                },
                {
                    "stage": "after",
                    "score": validation_report.quality_score_after,
                },
            ],
        )

    def _missing_values_chart(
        self,
        df: pd.DataFrame,
        stage: str = "current",
    ) -> VisualizationSpec:
        missing = (
            df.isna()
            .sum()
            .reset_index()
            .rename(columns={"index": "column", 0: "missing_values"})
        )

        missing = missing[missing["missing_values"] > 0]

        data = missing.to_dict(orient="records")

        return VisualizationSpec(
            chart_id=f"missing_values_{stage}",
            chart_type="bar",
            title=f"Missing Values by Column ({stage})",
            description="Shows missing value counts by column.",
            x="column",
            y="missing_values",
            stage=stage,
            recommended=True,
            data=data,
        )

    def _issue_breakdown_chart(self, diagnosis_report) -> VisualizationSpec | None:
        if diagnosis_report is None:
            return None

        data = []

        for issue in diagnosis_report.issues:
            data.append(
                {
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "confidence": round(issue.confidence * 100, 2),
                }
            )

        return VisualizationSpec(
            chart_id="issue_breakdown",
            chart_type="bar",
            title="Data Quality Issue Breakdown",
            description="Shows detected data quality issues and confidence levels.",
            x="issue_type",
            y="confidence",
            stage="before",
            recommended=True,
            data=data,
        )

    def _cleaning_status_chart(self, cleaning_report) -> VisualizationSpec | None:
        if cleaning_report is None:
            return None

        counts = {}

        for action in cleaning_report.actions:
            counts[action.status] = counts.get(action.status, 0) + 1

        data = [
            {"status": status, "count": count}
            for status, count in counts.items()
        ]

        return VisualizationSpec(
            chart_id="cleaning_action_status",
            chart_type="bar",
            title="Cleaning Action Status",
            description="Shows how many approved actions succeeded or were skipped.",
            x="status",
            y="count",
            stage="after",
            recommended=True,
            data=data,
        )

    def _comparison_charts(self, validation_report) -> list[VisualizationSpec]:
        if validation_report is None:
            return []

        metrics = [
            validation_report.missing_values,
            validation_report.duplicate_rows,
            validation_report.rows,
            validation_report.columns,
        ]

        charts = []

        for metric in metrics:
            charts.append(
                VisualizationSpec(
                    chart_id=f"{metric.name}_comparison",
                    chart_type="bar",
                    title=f"{metric.name.replace('_', ' ').title()} Before vs After",
                    description=f"Compares {metric.name.replace('_', ' ')} before and after cleaning.",
                    x="stage",
                    y="value",
                    stage="comparison",
                    recommended=True,
                    data=[
                        {"stage": "before", "value": metric.before},
                        {"stage": "after", "value": metric.after},
                    ],
                )
            )

        return charts

    def _distribution_chart(
        self,
        df: pd.DataFrame,
        column: str,
        stage: str = "current",
    ) -> VisualizationSpec:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

        series = pd.to_numeric(df[column], errors="coerce").dropna()

        if series.empty:
            data = []
        else:
            counts = pd.cut(series, bins=10).value_counts().sort_index()
            data = [
                {
                    "bin": str(interval),
                    "count": int(count),
                }
                for interval, count in counts.items()
            ]

        return VisualizationSpec(
            chart_id=f"distribution_{column}_{stage}",
            chart_type="bar",
            title=f"Distribution of {column} ({stage})",
            description=f"Shows the approximate distribution of {column}.",
            x="bin",
            y="count",
            stage=stage,
            recommended=False,
            data=data,
        )

    def _bar_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        stage: str = "current",
    ) -> VisualizationSpec:
        if x not in df.columns:
            raise ValueError(f"Column not found: {x}")

        if y not in df.columns:
            raise ValueError(f"Column not found: {y}")

        grouped = (
            df.groupby(x, dropna=False)[y]
            .sum(numeric_only=True)
            .reset_index()
            .sort_values(y, ascending=False)
            .head(20)
        )

        data = grouped.to_dict(orient="records")

        return VisualizationSpec(
            chart_id=f"bar_{x}_by_{y}_{stage}",
            chart_type="bar",
            title=f"{y} by {x}",
            description=f"Compares total {y} across {x}.",
            x=x,
            y=y,
            stage=stage,
            recommended=False,
            data=data,
        )

    def _scatter_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        stage: str = "current",
    ) -> VisualizationSpec:
        if x not in df.columns:
            raise ValueError(f"Column not found: {x}")

        if y not in df.columns:
            raise ValueError(f"Column not found: {y}")

        data = df[[x, y]].dropna().head(500).to_dict(orient="records")

        return VisualizationSpec(
            chart_id=f"scatter_{x}_vs_{y}_{stage}",
            chart_type="scatter",
            title=f"{x} vs {y}",
            description=f"Shows the relationship between {x} and {y}.",
            x=x,
            y=y,
            stage=stage,
            recommended=False,
            data=data,
        )