from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from autodq.io.loaders import load_dataset
from autodq.prediction.models import PredictionReport, PredictionResult
from autodq.uncertainty.engine import UncertaintyEngine


class PredictionEngine:
    """Generate predictions and calibrated uncertainty estimates."""

    def __init__(self):
        self.uncertainty_engine = UncertaintyEngine()

    def predict(
        self,
        model_report,
        data=None,
        target: str | None = None,
        strict_schema: bool = False,
        uncertainty: bool = True,
        confidence_level: float = 0.9,
        low_confidence_threshold: float = 0.6,
    ) -> tuple[pd.DataFrame, PredictionReport]:
        if model_report is None:
            raise ValueError(
                "No trained model available. Run project.model() first."
            )

        if data is None:
            raise ValueError("Prediction data is required.")

        self.uncertainty_engine.validate_confidence_level(
            confidence_level
        )
        self.uncertainty_engine.validate_low_confidence_threshold(
            low_confidence_threshold
        )

        if isinstance(data, (str, Path)):
            df = load_dataset(data)
        else:
            df = data.copy()

        pipeline = model_report.model_object

        if pipeline is None:
            raise ValueError("Model object is missing from the model report.")

        actual_values = None

        if target and target in df.columns:
            actual_values = df[target].copy()
            X = df.drop(columns=[target])
        else:
            X = df.copy()

        X, schema_warnings = self._align_schema(
            X=X,
            model_report=model_report,
            strict_schema=strict_schema,
        )
        predictions = np.asarray(pipeline.predict(X))
        output_df = df.copy()
        output_df["AutoDQ_Prediction"] = predictions
        calibration = getattr(
            model_report,
            "uncertainty_calibration",
            None,
        )
        uncertainty_values = self._empty_uncertainty()

        if uncertainty and model_report.problem_type == "regression":
            uncertainty_values = self._regression_uncertainty(
                output_df=output_df,
                predictions=predictions,
                actual_values=actual_values,
                calibration=calibration,
                confidence_level=float(confidence_level),
                warnings=schema_warnings,
            )
        elif uncertainty and model_report.problem_type == "classification":
            uncertainty_values = self._classification_uncertainty(
                output_df=output_df,
                pipeline=pipeline,
                X=X,
                calibration=calibration,
                low_confidence_threshold=float(
                    low_confidence_threshold
                ),
                warnings=schema_warnings,
            )

        top_features = self._top_features(model_report)
        results = self._build_results(
            predictions=predictions,
            actual_values=actual_values,
            problem_type=model_report.problem_type,
            uncertainty_values=uncertainty_values,
            confidence_level=float(confidence_level),
            low_confidence_threshold=float(low_confidence_threshold),
            top_features=top_features,
        )
        calibration_metrics = (
            dict(calibration.metrics)
            if calibration is not None
            else {}
        )
        report = PredictionReport(
            target=model_report.target,
            problem_type=model_report.problem_type,
            algorithm=model_report.algorithm,
            predictions=results[:100],
            total_predictions=len(predictions),
            warnings=schema_warnings,
            uncertainty_requested=uncertainty,
            uncertainty_available=uncertainty_values["available"],
            uncertainty_method=uncertainty_values["method"],
            confidence_level=(
                float(confidence_level)
                if model_report.problem_type == "regression"
                and uncertainty_values["available"]
                else None
            ),
            calibration_size=(
                calibration.calibration_size
                if calibration is not None
                else 0
            ),
            calibration_metrics=calibration_metrics,
            empirical_coverage=uncertainty_values["coverage"],
            mean_interval_width=uncertainty_values["mean_width"],
            mean_confidence=uncertainty_values["mean_confidence"],
            low_confidence_count=uncertainty_values[
                "low_confidence_count"
            ],
            low_confidence_threshold=(
                float(low_confidence_threshold)
                if model_report.problem_type == "classification"
                and uncertainty_values["available"]
                else None
            ),
        )
        return output_df, report

    def _regression_uncertainty(
        self,
        *,
        output_df: pd.DataFrame,
        predictions: np.ndarray,
        actual_values,
        calibration,
        confidence_level: float,
        warnings: list[str],
    ) -> dict:
        values = self._empty_uncertainty()

        if calibration is None or not calibration.available:
            warnings.append(
                "Regression intervals are unavailable because this model "
                "does not contain conformal calibration scores. Retrain "
                "the model with the current AutoDQ version."
            )
            return values

        lower, upper, radius = self.uncertainty_engine.regression_intervals(
            predictions=predictions,
            calibration=calibration,
            confidence_level=confidence_level,
        )
        widths = upper - lower
        output_df["AutoDQ_Prediction_Lower"] = lower
        output_df["AutoDQ_Prediction_Upper"] = upper
        output_df["AutoDQ_Interval_Width"] = widths
        output_df["AutoDQ_Confidence_Level"] = confidence_level
        coverage = None

        if actual_values is not None:
            actual = pd.to_numeric(actual_values, errors="coerce").to_numpy()
            valid = np.isfinite(actual)

            if np.any(valid):
                coverage = float(
                    np.mean(
                        (actual[valid] >= lower[valid])
                        & (actual[valid] <= upper[valid])
                    )
                )

        values.update(
            {
                "available": True,
                "method": calibration.method,
                "lower": lower,
                "upper": upper,
                "width": widths,
                "radius": radius,
                "coverage": coverage,
                "mean_width": float(np.mean(widths)),
            }
        )
        return values

    def _classification_uncertainty(
        self,
        *,
        output_df: pd.DataFrame,
        pipeline,
        X: pd.DataFrame,
        calibration,
        low_confidence_threshold: float,
        warnings: list[str],
    ) -> dict:
        values = self._empty_uncertainty()

        try:
            estimates = self.uncertainty_engine.classification_estimates(
                pipeline=pipeline,
                X=X,
            )
        except ValueError as error:
            warnings.append(str(error))
            return values

        probabilities = estimates["probabilities"]
        confidence = estimates["confidence"]
        uncertainty = estimates["uncertainty"]
        margin = estimates["margin"]
        entropy = estimates["entropy"]
        low_confidence = confidence < low_confidence_threshold
        output_df["AutoDQ_Confidence"] = confidence
        output_df["AutoDQ_Uncertainty"] = uncertainty
        output_df["AutoDQ_Prediction_Margin"] = margin
        output_df["AutoDQ_Entropy"] = entropy
        output_df["AutoDQ_Low_Confidence"] = low_confidence
        probability_columns = []

        for index, label in enumerate(estimates["class_labels"]):
            column = self._probability_column(label, probability_columns)
            probability_columns.append(column)
            output_df[column] = probabilities[:, index]

        if calibration is None:
            warnings.append(
                "Classification probabilities are available, but holdout "
                "calibration diagnostics are missing. Retrain the model "
                "with the current AutoDQ version."
            )
        elif calibration.metrics.get(
            "expected_calibration_error",
            0.0,
        ) > 0.1:
            warnings.append(
                "Classifier probabilities show elevated calibration error; "
                "interpret confidence with caution."
            )

        values.update(
            {
                "available": True,
                "method": "predict_proba",
                "probabilities": probabilities,
                "class_labels": estimates["class_labels"],
                "confidence": confidence,
                "uncertainty": uncertainty,
                "margin": margin,
                "entropy": entropy,
                "low_confidence": low_confidence,
                "mean_confidence": float(np.mean(confidence) * 100),
                "low_confidence_count": int(np.sum(low_confidence)),
            }
        )
        return values

    def _build_results(
        self,
        *,
        predictions: np.ndarray,
        actual_values,
        problem_type: str,
        uncertainty_values: dict,
        confidence_level: float,
        low_confidence_threshold: float,
        top_features: list[str],
    ) -> list[PredictionResult]:
        results = []

        for index, predicted in enumerate(predictions):
            actual = (
                actual_values.iloc[index]
                if actual_values is not None
                else None
            )
            residual = None
            absolute_error = None
            percent_error = None

            if actual is not None and problem_type == "regression":
                residual = round(float(actual - predicted), 4)
                absolute_error = round(abs(float(actual - predicted)), 4)

                if actual != 0:
                    percent_error = round(
                        (absolute_error / abs(float(actual))) * 100,
                        4,
                    )

            result_uncertainty = self._row_uncertainty(
                index=index,
                problem_type=problem_type,
                values=uncertainty_values,
                confidence_level=confidence_level,
                low_confidence_threshold=low_confidence_threshold,
            )
            explanation = self._build_explanation(
                predicted=predicted,
                problem_type=problem_type,
                top_features=top_features,
                uncertainty=result_uncertainty,
            )
            results.append(
                PredictionResult(
                    row_id=index,
                    actual=actual,
                    predicted=predicted,
                    residual=residual,
                    absolute_error=absolute_error,
                    percent_error=percent_error,
                    top_features=top_features,
                    explanation=explanation,
                    **result_uncertainty,
                )
            )

        return results

    def _row_uncertainty(
        self,
        *,
        index: int,
        problem_type: str,
        values: dict,
        confidence_level: float,
        low_confidence_threshold: float,
    ) -> dict:
        if not values["available"]:
            return {}

        if problem_type == "regression":
            lower = float(values["lower"][index])
            upper = float(values["upper"][index])
            return {
                "confidence": round(confidence_level * 100, 2),
                "uncertainty": round((1 - confidence_level) * 100, 2),
                "lower_bound": lower,
                "upper_bound": upper,
                "interval_width": float(values["width"][index]),
                "confidence_level": confidence_level,
                "uncertainty_method": values["method"],
            }

        probabilities = values["probabilities"][index]
        class_probabilities = {
            str(label): float(probability)
            for label, probability in zip(
                values["class_labels"],
                probabilities,
            )
        }
        confidence = float(values["confidence"][index])
        return {
            "confidence": round(confidence * 100, 2),
            "uncertainty": round(
                float(values["uncertainty"][index]) * 100,
                2,
            ),
            "class_probabilities": class_probabilities,
            "prediction_margin": float(values["margin"][index]),
            "entropy": float(values["entropy"][index]),
            "low_confidence": confidence < low_confidence_threshold,
            "uncertainty_method": values["method"],
        }

    def _align_schema(
        self,
        X: pd.DataFrame,
        model_report,
        strict_schema: bool,
    ) -> tuple[pd.DataFrame, list[str]]:
        expected_columns = list(
            getattr(model_report, "feature_columns", [])
        )

        if not expected_columns:
            return X, []

        missing_columns = [
            column
            for column in expected_columns
            if column not in X.columns
        ]

        if missing_columns:
            raise ValueError(
                "Prediction data is missing required model features: "
                f"{missing_columns}"
            )

        extra_columns = [
            column
            for column in X.columns
            if column not in expected_columns
        ]
        schema_warnings = []

        if extra_columns and strict_schema:
            raise ValueError(
                "Prediction data contains unexpected features: "
                f"{extra_columns}"
            )

        if extra_columns:
            schema_warnings.append(
                "Ignored unexpected prediction features: "
                f"{extra_columns}"
            )

        expected_dtypes = getattr(model_report, "feature_dtypes", {})
        dtype_changes = []

        for column in expected_columns:
            expected_dtype = expected_dtypes.get(column)
            actual_dtype = str(X[column].dtype)

            if expected_dtype and expected_dtype != actual_dtype:
                dtype_changes.append(
                    f"{column}: expected {expected_dtype}, "
                    f"received {actual_dtype}"
                )

        if dtype_changes:
            schema_warnings.append(
                "Prediction feature dtypes differ from training: "
                + "; ".join(dtype_changes)
            )

        return X[expected_columns].copy(), schema_warnings

    def _top_features(self, model_report, limit: int = 3) -> list[str]:
        if not model_report.feature_importance:
            return []

        clean_features = []

        for item in model_report.feature_importance:
            feature = item.feature.lower()

            if "id" in feature:
                continue

            clean_features.append(item.feature)

            if len(clean_features) == limit:
                break

        return clean_features

    def _build_explanation(
        self,
        *,
        predicted,
        problem_type: str,
        top_features: list[str],
        uncertainty: dict,
    ) -> str:
        feature_text = (
            ", ".join(top_features)
            if top_features
            else "the strongest model features"
        )

        if problem_type == "regression":
            interval_text = ""

            if uncertainty.get("lower_bound") is not None:
                interval_text = (
                    f" The {uncertainty['confidence_level']:.0%} conformal "
                    f"interval is [{uncertainty['lower_bound']:.4f}, "
                    f"{uncertainty['upper_bound']:.4f}]."
                )

            return (
                f"The model predicted {float(predicted):.4f}."
                f"{interval_text} The strongest global drivers include "
                f"{feature_text}."
            )

        confidence_text = ""

        if uncertainty.get("confidence") is not None:
            confidence_text = (
                f" Probability confidence is "
                f"{uncertainty['confidence']:.2f}%."
            )

        return (
            f"The model predicted class '{predicted}'.{confidence_text} "
            f"The strongest global drivers include {feature_text}."
        )

    @staticmethod
    def _probability_column(label, existing: list[str]) -> str:
        suffix = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            str(label),
        ).strip("_") or "class"
        candidate = f"AutoDQ_Probability_{suffix}"
        counter = 2

        while candidate in existing:
            candidate = f"AutoDQ_Probability_{suffix}_{counter}"
            counter += 1

        return candidate

    @staticmethod
    def _empty_uncertainty() -> dict:
        return {
            "available": False,
            "method": None,
            "lower": None,
            "upper": None,
            "width": None,
            "radius": None,
            "probabilities": None,
            "class_labels": [],
            "confidence": None,
            "uncertainty": None,
            "margin": None,
            "entropy": None,
            "low_confidence": None,
            "coverage": None,
            "mean_width": None,
            "mean_confidence": None,
            "low_confidence_count": 0,
        }
