from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from autodq.dashboard.models import (
    Dashboard,
    DashboardMetric,
    serializable_value,
)


class DashboardEngine:
    """Build dashboards from the current AutoDQ project state."""

    SUPPORTED_STAGES = {
        "current": "current",
        "raw": "current",
        "before": "current",
        "cleaned": "cleaned",
        "after": "cleaned",
        "engineered": "engineered",
        "features": "engineered",
        "best": "best",
    }

    @classmethod
    def validate_options(
        cls,
        *,
        theme: str,
        stage: str,
        max_charts: int | None,
        max_preview_rows: int,
    ) -> None:
        normalized_theme = str(theme).lower().strip()

        if normalized_theme not in Dashboard.SUPPORTED_THEMES:
            supported = ", ".join(Dashboard.SUPPORTED_THEMES)
            raise ValueError(
                f"Unsupported dashboard theme: {theme}. "
                f"Supported themes: {supported}."
            )

        normalized_stage = str(stage).lower().strip()

        if normalized_stage not in cls.SUPPORTED_STAGES:
            supported = ", ".join(sorted(cls.SUPPORTED_STAGES))
            raise ValueError(
                f"Unsupported dashboard stage: {stage}. "
                f"Supported stages: {supported}."
            )

        cls._validate_limits(max_charts, max_preview_rows)

    def build(
        self,
        state,
        session,
        *,
        title: str = "AutoDQ Analytics Dashboard",
        subtitle: str | None = None,
        theme: str = "light",
        stage: str = "best",
        chart_ids: list[str] | tuple[str, ...] | None = None,
        max_charts: int | None = 12,
        max_preview_rows: int = 20,
        include_data_preview: bool = True,
        auto_display: bool = True,
    ) -> Dashboard:
        self.validate_options(
            theme=theme,
            stage=stage,
            max_charts=max_charts,
            max_preview_rows=max_preview_rows,
        )
        stage_name, frame = self._select_frame(state, stage)
        charts = self._select_charts(
            state.visualization_report,
            chart_ids=chart_ids,
            max_charts=max_charts,
        )
        profile = state.profile_report or {}
        diagnosis = state.diagnosis_report
        validation = state.validation_report
        missing_cells = int(frame.isna().sum().sum())
        duplicate_rows = int(frame.duplicated().sum())
        quality_score = self._quality_score(
            stage=stage_name,
            diagnosis=diagnosis,
            validation=validation,
        )
        issues = (
            [item.to_dict() for item in diagnosis.issues]
            if diagnosis is not None
            else []
        )
        dataset_label = Path(state.dataset_path).name
        resolved_subtitle = subtitle

        if resolved_subtitle is None:
            resolved_subtitle = (
                f"{dataset_label} · {stage_name.title()} data · "
                f"Generated from the active project state"
            )

        dashboard = Dashboard(
            title=title,
            subtitle=resolved_subtitle,
            dataset=str(state.dataset_path),
            stage=stage_name,
            theme=theme,
            metrics=self._metrics(
                frame=frame,
                missing_cells=missing_cells,
                duplicate_rows=duplicate_rows,
                quality_score=quality_score,
            ),
            issues=issues,
            recommendations=self._recommendations(state.recommendations),
            cleaning=self._cleaning_summary(state.cleaning_report),
            review=self._review_summary(state.cleaning_review),
            domain=self._domain_summary(state.domain_validation_report),
            automation=self._automation_summary(state.auto_run_report),
            model=self._model_summary(state.model_report),
            prediction=self._prediction_summary(state.prediction_report),
            columns=self._column_summary(frame, profile),
            preview=(
                self._data_preview(frame, max_preview_rows)
                if include_data_preview
                else []
            ),
            charts=charts,
            auto_display=auto_display,
        )
        return dashboard

    def _select_frame(self, state, stage: str) -> tuple[str, pd.DataFrame]:
        normalized = str(stage).lower().strip()

        if normalized not in self.SUPPORTED_STAGES:
            supported = ", ".join(sorted(self.SUPPORTED_STAGES))
            raise ValueError(
                f"Unsupported dashboard stage: {stage}. "
                f"Supported stages: {supported}."
            )

        normalized = self.SUPPORTED_STAGES[normalized]

        if normalized == "best":
            if state.engineered_data is not None:
                return "engineered", state.engineered_data

            if state.cleaned_data is not None:
                return "cleaned", state.cleaned_data

            normalized = "current"

        if normalized == "cleaned":
            if state.cleaned_data is None:
                raise ValueError(
                    "No cleaned data is available. Run project.clean() or "
                    "use stage='current'."
                )

            return normalized, state.cleaned_data

        if normalized == "engineered":
            if state.engineered_data is None:
                raise ValueError(
                    "No engineered data is available. Run "
                    "project.apply_features() or use stage='best'."
                )

            return normalized, state.engineered_data

        if state.data is None:
            raise ValueError("Project data must be loaded before dashboarding.")

        return "current", state.data

    @staticmethod
    def _validate_limits(
        max_charts: int | None,
        max_preview_rows: int,
    ) -> None:
        if max_charts is not None and (
            isinstance(max_charts, bool)
            or not isinstance(max_charts, int)
            or max_charts < 0
        ):
            raise ValueError("max_charts must be zero, a positive integer, or None.")

        if (
            isinstance(max_preview_rows, bool)
            or not isinstance(max_preview_rows, int)
            or max_preview_rows < 0
        ):
            raise ValueError("max_preview_rows must be zero or a positive integer.")

    @staticmethod
    def _select_charts(
        report,
        *,
        chart_ids: list[str] | tuple[str, ...] | None,
        max_charts: int | None,
    ) -> list[Any]:
        if report is None or max_charts == 0:
            if chart_ids:
                raise KeyError("No visualizations are available in the gallery.")

            return []

        charts = list(report.charts)

        if chart_ids is not None:
            if not isinstance(chart_ids, (list, tuple)) or any(
                not isinstance(chart_id, str) or not chart_id.strip()
                for chart_id in chart_ids
            ):
                raise ValueError(
                    "chart_ids must be a list or tuple of chart ID strings."
                )

            requested = list(chart_ids)

            if len(requested) != len(set(requested)):
                raise ValueError("chart_ids cannot contain duplicates.")

            available = {chart.chart_id: chart for chart in charts}
            missing = [chart_id for chart_id in requested if chart_id not in available]

            if missing:
                raise KeyError(
                    "Dashboard visualization was not found: "
                    + ", ".join(missing)
                )

            charts = [available[chart_id] for chart_id in requested]

        if max_charts is not None:
            charts = charts[:max_charts]

        return charts

    @staticmethod
    def _quality_score(stage: str, diagnosis, validation) -> float | None:
        if stage in {"cleaned", "engineered"} and validation is not None:
            if validation.quality_score_after is not None:
                return float(validation.quality_score_after)

        if diagnosis is not None and diagnosis.quality_score is not None:
            return float(diagnosis.quality_score)

        return None

    @staticmethod
    def _metrics(
        *,
        frame: pd.DataFrame,
        missing_cells: int,
        duplicate_rows: int,
        quality_score: float | None,
    ) -> list[DashboardMetric]:
        quality_display = (
            f"{quality_score:.1f}/100"
            if quality_score is not None
            else "Not scored"
        )
        quality_status = "neutral"

        if quality_score is not None:
            if quality_score >= 90:
                quality_status = "good"
            elif quality_score >= 70:
                quality_status = "warning"
            else:
                quality_status = "bad"

        return [
            DashboardMetric(
                key="rows",
                label="Rows",
                value=int(len(frame)),
                display=f"{len(frame):,}",
                description="Rows in the selected dashboard stage",
            ),
            DashboardMetric(
                key="columns",
                label="Columns",
                value=int(len(frame.columns)),
                display=f"{len(frame.columns):,}",
                description="Columns in the selected dashboard stage",
            ),
            DashboardMetric(
                key="quality_score",
                label="Quality score",
                value=quality_score,
                display=quality_display,
                description="Latest available AutoDQ data-quality score",
                status=quality_status,
            ),
            DashboardMetric(
                key="missing_cells",
                label="Missing cells",
                value=missing_cells,
                display=f"{missing_cells:,}",
                description="Empty values in the selected dashboard stage",
                status="good" if missing_cells == 0 else "warning",
            ),
            DashboardMetric(
                key="duplicate_rows",
                label="Duplicate rows",
                value=duplicate_rows,
                display=f"{duplicate_rows:,}",
                description="Repeated rows in the selected dashboard stage",
                status="good" if duplicate_rows == 0 else "warning",
            ),
        ]

    @staticmethod
    def _recommendations(items) -> list[dict[str, Any]]:
        if not items:
            return []

        return [serializable_value(item.to_dict()) for item in items]

    @staticmethod
    def _cleaning_summary(report) -> dict[str, Any] | None:
        if report is None:
            return None

        return serializable_value(report.to_dict())

    @staticmethod
    def _review_summary(review) -> dict[str, Any] | None:
        if review is None:
            return None

        outliers = review.outlier_report
        return {
            "action_count": review.action_count,
            "pending_count": review.pending_count,
            "approved_count": review.approved_count,
            "rejected_count": review.rejected_count,
            "audit_count": review.audit_count,
            "changed": review.changed,
            "outlier_count": (
                outliers.outlier_count if outliers is not None else 0
            ),
        }

    @staticmethod
    def _domain_summary(report) -> dict[str, Any] | None:
        if report is None:
            return None

        return {
            "rule_count": report.rule_count,
            "violation_count": report.violation_count,
            "invalid_row_count": report.invalid_row_count,
            "checked_rows": report.checked_rows,
            "is_valid": report.is_valid,
            "violations": [
                item.to_dict() for item in report.violations[:50]
            ],
        }

    @staticmethod
    def _automation_summary(report) -> dict[str, Any] | None:
        if report is None:
            return None

        data = report.to_dict()
        return {
            "mode": data["config"]["mode"],
            "success": data["success"],
            "completed_count": data["completed_count"],
            "reused_count": data["reused_count"],
            "skipped_count": data["skipped_count"],
            "failed_count": data["failed_count"],
            "duration_seconds": data["duration_seconds"],
            "next_actions": data["next_actions"],
            "stages": data["stages"],
        }

    @staticmethod
    def _model_summary(report) -> dict[str, Any] | None:
        if report is None:
            return None

        return {
            "target": report.target,
            "problem_type": report.problem_type,
            "algorithm": report.algorithm,
            "metrics": serializable_value(report.metrics.to_dict()),
            "feature_count": report.feature_count,
            "feature_importance": [
                item.to_dict() for item in report.feature_importance[:10]
            ],
            "recommendations": list(report.recommendations),
        }

    @staticmethod
    def _prediction_summary(report) -> dict[str, Any] | None:
        if report is None:
            return None

        return {
            "target": report.target,
            "problem_type": report.problem_type,
            "algorithm": report.algorithm,
            "prediction_count": report.prediction_count,
            "uncertainty_requested": report.uncertainty_requested,
            "uncertainty_available": report.uncertainty_available,
            "uncertainty_method": report.uncertainty_method,
            "confidence_level": report.confidence_level,
            "empirical_coverage": report.empirical_coverage,
            "mean_interval_width": report.mean_interval_width,
            "mean_confidence": report.mean_confidence,
            "low_confidence_count": report.low_confidence_count,
            "warnings": list(report.warnings),
            "sample": [
                item.to_dict() for item in report.predictions[:20]
            ],
        }

    @staticmethod
    def _column_summary(
        frame: pd.DataFrame,
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        semantic_types = profile.get("semantic_types", {})
        return [
            {
                "column": str(column),
                "dtype": str(frame[column].dtype),
                "semantic_type": semantic_types.get(column),
                "missing": int(frame[column].isna().sum()),
                "unique": int(frame[column].nunique(dropna=True)),
            }
            for column in frame.columns
        ]

    @staticmethod
    def _data_preview(
        frame: pd.DataFrame,
        max_rows: int,
    ) -> list[dict[str, Any]]:
        if max_rows == 0:
            return []

        preview = frame.head(max_rows).copy()
        preview.insert(0, "_row", preview.index)
        return serializable_value(preview.to_dict(orient="records"))
