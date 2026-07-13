from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(slots=True)
class BLUEDiagnosticChart:
    """
    Visualization specification compatible with AutoDQ's
    visualization gallery and Matplotlib renderer.
    """

    chart_id: str
    chart_type: str
    title: str
    description: str
    stage: str
    data: list[dict[str, Any]]
    x: str | None = None
    y: str | None = None
    column: str | None = None


@dataclass(slots=True)
class BLUEVisualizationReport:
    charts: list[BLUEDiagnosticChart]

    @property
    def chart_count(self) -> int:
        return len(self.charts)


class BLUEVisualizer:
    """
    Builds diagnostic visualization specifications for BLUE analysis.

    Charts:
    - residuals vs fitted
    - Q-Q plot
    - Cook's distance
    - VIF bar chart
    """

    def build(
        self,
        df: pd.DataFrame,
        target: str,
        blue_report,
    ) -> BLUEVisualizationReport:
        if blue_report is None:
            raise ValueError(
                "No BLUE report available. Run project.blue() first."
            )

        if target not in df.columns:
            raise ValueError(
                f"Target column not found: {target}"
            )

        features = list(
            getattr(
                blue_report,
                "features_used",
                [],
            )
        )

        if not features:
            raise ValueError(
                "BLUE report does not contain features_used."
            )

        available_features = [
            feature
            for feature in features
            if feature in df.columns
        ]

        if not available_features:
            raise ValueError(
                "None of the BLUE features are available in the dataset."
            )

        model_df = (
            df[available_features + [target]]
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
            .copy()
        )

        if len(model_df) < 3:
            raise ValueError(
                "Not enough complete observations for BLUE visualizations."
            )

        X = model_df[available_features].astype(float)
        y = model_df[target].astype(float)

        X_constant = sm.add_constant(
            X,
            has_constant="add",
        )

        fitted_model = sm.OLS(
            y,
            X_constant,
        ).fit()

        residuals = np.asarray(
            fitted_model.resid,
            dtype=float,
        )

        fitted_values = np.asarray(
            fitted_model.fittedvalues,
            dtype=float,
        )

        influence = fitted_model.get_influence()

        cooks_distance = np.asarray(
            influence.cooks_distance[0],
            dtype=float,
        )

        charts = [
            self._residuals_vs_fitted_chart(
                fitted_values=fitted_values,
                residuals=residuals,
            ),
            self._qq_chart(
                residuals=residuals,
            ),
            self._cooks_distance_chart(
                cooks_distance=cooks_distance,
            ),
            self._vif_chart(
                blue_report=blue_report,
            ),
        ]

        return BLUEVisualizationReport(
            charts=charts,
        )

    def _residuals_vs_fitted_chart(
        self,
        fitted_values: np.ndarray,
        residuals: np.ndarray,
    ) -> BLUEDiagnosticChart:
        data = [
            {
                "fitted_value": float(fitted),
                "residual": float(residual),
            }
            for fitted, residual in zip(
                fitted_values,
                residuals,
            )
        ]

        return BLUEDiagnosticChart(
            chart_id="blue_residuals_vs_fitted",
            chart_type="blue_residuals_vs_fitted",
            title="Residuals vs Fitted Values",
            description=(
                "Assesses linearity and constant residual variance. "
                "A random horizontal pattern around zero is preferred."
            ),
            stage="blue",
            data=data,
            x="fitted_value",
            y="residual",
        )

    def _qq_chart(
        self,
        residuals: np.ndarray,
    ) -> BLUEDiagnosticChart:
        theoretical_quantiles, ordered_values = (
            sm.ProbPlot(
                residuals,
                fit=True,
            ).theoretical_quantiles,
            np.sort(residuals),
        )

        usable_length = min(
            len(theoretical_quantiles),
            len(ordered_values),
        )

        data = [
            {
                "theoretical_quantile": float(
                    theoretical_quantiles[index]
                ),
                "observed_residual": float(
                    ordered_values[index]
                ),
            }
            for index in range(usable_length)
        ]

        return BLUEDiagnosticChart(
            chart_id="blue_qq_plot",
            chart_type="blue_qq_plot",
            title="Residual Q–Q Plot",
            description=(
                "Compares observed residual quantiles with a normal "
                "distribution. Points close to a straight line support "
                "residual normality."
            ),
            stage="blue",
            data=data,
            x="theoretical_quantile",
            y="observed_residual",
        )

    def _cooks_distance_chart(
        self,
        cooks_distance: np.ndarray,
    ) -> BLUEDiagnosticChart:
        threshold = (
            4 / len(cooks_distance)
            if len(cooks_distance) > 0
            else 0
        )

        data = [
            {
                "observation": int(index),
                "cooks_distance": float(value),
                "threshold": float(threshold),
            }
            for index, value in enumerate(
                cooks_distance
            )
        ]

        return BLUEDiagnosticChart(
            chart_id="blue_cooks_distance",
            chart_type="blue_cooks_distance",
            title="Cook’s Distance",
            description=(
                "Identifies observations that exert unusual influence "
                "on fitted regression coefficients."
            ),
            stage="blue",
            data=data,
            x="observation",
            y="cooks_distance",
        )

    def _vif_chart(
        self,
        blue_report,
    ) -> BLUEDiagnosticChart:
        data = [
            {
                "feature": result.feature,
                "vif": float(result.vif),
            }
            for result in blue_report.vif_results[:15]
        ]

        return BLUEDiagnosticChart(
            chart_id="blue_vif_chart",
            chart_type="blue_vif_chart",
            title="Variance Inflation Factors",
            description=(
                "Higher VIF values indicate stronger multicollinearity. "
                "Values above 5 require review; values above 10 are severe."
            ),
            stage="blue",
            data=data,
            x="feature",
            y="vif",
        )