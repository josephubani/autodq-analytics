from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from autodq.explainability.models import ExplainabilityReport


class SHAPVisualizer:
    """
    Generates SHAP visualizations from cached SHAP artifacts.

    This class NEVER recomputes SHAP values.
    """

    SUPPORTED_CHARTS = (
        "summary",
        "bar",
        "beeswarm",
        "waterfall",
        "dependence",
    )

    def __init__(self, report: ExplainabilityReport):
        self.report = report

        if report.shap_artifacts is None:
            raise ValueError(
                "No SHAP artifacts available.\n"
                "Run project.explain() before visualizing SHAP."
            )

        self.artifacts = report.shap_artifacts
        self.shap = self._load_shap()
        self._validate_artifacts()

    def plot(
        self,
        chart: str = "summary",
        row: int = 0,
        feature: str | None = None,
        save: str | Path | None = None,
        show: bool = True,
    ):
        chart_normalized = chart.lower().strip()

        if chart_normalized == "summary":
            return self.summary(save=save, show=show)

        if chart_normalized == "bar":
            return self.bar(save=save, show=show)

        if chart_normalized == "beeswarm":
            return self.beeswarm(save=save, show=show)

        if chart_normalized == "waterfall":
            return self.waterfall(
                row=row,
                save=save,
                show=show,
            )

        if chart_normalized == "dependence":
            if feature is None:
                raise ValueError(
                    "A feature name is required for a SHAP "
                    "dependence plot."
                )

            return self.dependence(
                feature=feature,
                save=save,
                show=show,
            )

        raise ValueError(
            f"Unsupported SHAP chart: {chart}. "
            f"Supported charts: {', '.join(self.SUPPORTED_CHARTS)}"
        )

    def summary(
        self,
        save: str | Path | None = None,
        show: bool = True,
    ):
        self._start_plot()
        self.shap.summary_plot(
            self.artifacts.shap_values,
            self.artifacts.transformed_data,
            feature_names=self.artifacts.feature_names,
            show=False,
        )

        return self._finish(save, show)

    def bar(
        self,
        save: str | Path | None = None,
        show: bool = True,
    ):
        self._start_plot()
        self.shap.summary_plot(
            self.artifacts.shap_values,
            self.artifacts.transformed_data,
            feature_names=self.artifacts.feature_names,
            plot_type="bar",
            show=False,
        )

        return self._finish(save, show)

    def beeswarm(
        self,
        save: str | Path | None = None,
        show: bool = True,
    ):
        self._start_plot()
        self.shap.plots.beeswarm(
            self.artifacts.explanation,
            show=False,
        )

        return self._finish(save, show)

    def waterfall(
        self,
        row: int = 0,
        save: str | Path | None = None,
        show: bool = True,
    ):
        row_count = len(self.artifacts.explanation)

        if not isinstance(row, int):
            raise TypeError("Waterfall row must be an integer position.")

        if row < 0 or row >= row_count:
            raise IndexError(
                f"Waterfall row {row} is out of range. "
                f"Choose a row from 0 to {row_count - 1}."
            )

        self._start_plot()
        self.shap.plots.waterfall(
            self.artifacts.explanation[row],
            show=False,
        )

        return self._finish(save, show)

    def dependence(
        self,
        feature: str,
        save: str | Path | None = None,
        show: bool = True,
    ):
        if feature not in self.artifacts.feature_names:
            available = ", ".join(self.artifacts.feature_names[:10])
            suffix = (
                " ..."
                if len(self.artifacts.feature_names) > 10
                else ""
            )
            raise ValueError(
                f"Unknown SHAP feature: {feature}. "
                f"Available features: {available}{suffix}"
            )

        self._start_plot()
        self.shap.dependence_plot(
            feature,
            self.artifacts.shap_values,
            self.artifacts.transformed_data,
            feature_names=self.artifacts.feature_names,
            show=False,
        )

        return self._finish(save, show)

    @staticmethod
    def _load_shap():
        try:
            import shap
        except ImportError as error:
            raise ImportError(
                "SHAP plotting requires the optional 'shap' dependency. "
                "Install it with 'pip install shap'."
            ) from error

        return shap

    def _validate_artifacts(self) -> None:
        missing = []

        if self.artifacts.shap_values is None:
            missing.append("shap_values")

        if self.artifacts.explanation is None:
            missing.append("explanation")

        if self.artifacts.transformed_data is None:
            missing.append("transformed_data")

        if not self.artifacts.feature_names:
            missing.append("feature_names")

        if missing:
            raise ValueError(
                "Incomplete SHAP artifacts: "
                f"{', '.join(missing)}. Run project.explain() again."
            )

    @staticmethod
    def _start_plot() -> None:
        plt.figure()

    @staticmethod
    def _finish(
        save: str | Path | None,
        show: bool,
    ):
        figure = plt.gcf()
        figure.tight_layout()

        if save is not None:
            output_path = Path(save).expanduser()

            if not output_path.suffix:
                output_path = output_path.with_suffix(".png")

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            figure.savefig(
                output_path,
                dpi=300,
                bbox_inches="tight",
            )

        if show:
            plt.show()

        return figure
