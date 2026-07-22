from __future__ import annotations

import math
from typing import Any

import numpy as np

from autodq.uncertainty.models import UncertaintyCalibration


class UncertaintyEngine:
    """Calibrate and generate uncertainty estimates for AutoDQ models."""

    def calibrate(
        self,
        *,
        pipeline,
        X_calibration,
        y_calibration,
        predictions,
        problem_type: str,
    ) -> UncertaintyCalibration | None:
        if problem_type == "regression":
            actual = np.asarray(y_calibration, dtype=float)
            predicted = np.asarray(predictions, dtype=float)
            scores = np.abs(actual - predicted)
            scores = scores[np.isfinite(scores)]

            if scores.size == 0:
                return None

            return UncertaintyCalibration(
                problem_type="regression",
                method="holdout_conformal",
                calibration_size=int(scores.size),
                scores=sorted(float(value) for value in scores),
                metrics={
                    "median_absolute_residual": float(
                        np.median(scores)
                    ),
                    "mean_absolute_residual": float(np.mean(scores)),
                },
            )

        if problem_type != "classification" or not hasattr(
            pipeline,
            "predict_proba",
        ):
            return None

        probabilities = np.asarray(
            pipeline.predict_proba(X_calibration),
            dtype=float,
        )
        class_labels = self._class_labels(pipeline)

        if probabilities.ndim != 2 or not class_labels:
            return None

        metrics = self._classification_calibration_metrics(
            actual=np.asarray(y_calibration),
            predicted=np.asarray(predictions),
            probabilities=probabilities,
            class_labels=class_labels,
        )
        return UncertaintyCalibration(
            problem_type="classification",
            method="predict_proba",
            calibration_size=len(probabilities),
            class_labels=class_labels,
            metrics=metrics,
        )

    def regression_intervals(
        self,
        predictions,
        calibration: UncertaintyCalibration,
        confidence_level: float,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        self.validate_confidence_level(confidence_level)

        if (
            calibration is None
            or calibration.problem_type != "regression"
            or not calibration.scores
        ):
            raise ValueError(
                "Regression uncertainty calibration is unavailable."
            )

        scores = np.asarray(calibration.scores, dtype=float)
        sample_size = len(scores)
        quantile_level = math.ceil(
            (sample_size + 1) * confidence_level
        ) / sample_size
        quantile_level = min(1.0, quantile_level)
        radius = float(
            np.quantile(scores, quantile_level, method="higher")
        )
        predicted = np.asarray(predictions, dtype=float)
        return predicted - radius, predicted + radius, radius

    def classification_estimates(
        self,
        *,
        pipeline,
        X,
    ) -> dict[str, Any]:
        if not hasattr(pipeline, "predict_proba"):
            raise ValueError(
                "The trained classifier does not provide probabilities."
            )

        probabilities = np.asarray(
            pipeline.predict_proba(X),
            dtype=float,
        )
        class_labels = self._class_labels(pipeline)

        if probabilities.ndim != 2 or probabilities.shape[1] < 2:
            raise ValueError(
                "Classification probabilities have an invalid shape."
            )

        if probabilities.shape[1] != len(class_labels):
            raise ValueError(
                "Classifier classes do not match probability columns."
            )

        ordered = np.sort(probabilities, axis=1)
        confidence = ordered[:, -1]
        margin = ordered[:, -1] - ordered[:, -2]
        safe_probabilities = np.clip(probabilities, 1e-15, 1.0)
        entropy = -np.sum(
            safe_probabilities * np.log(safe_probabilities),
            axis=1,
        ) / np.log(probabilities.shape[1])
        return {
            "probabilities": probabilities,
            "class_labels": class_labels,
            "confidence": confidence,
            "uncertainty": 1 - confidence,
            "margin": margin,
            "entropy": entropy,
        }

    @staticmethod
    def validate_confidence_level(confidence_level: float) -> None:
        if not isinstance(confidence_level, (int, float)) or not (
            0.5 <= float(confidence_level) < 1.0
        ):
            raise ValueError(
                "confidence_level must be at least 0.5 and less than 1.0."
            )

    @staticmethod
    def validate_low_confidence_threshold(threshold: float) -> None:
        if not isinstance(threshold, (int, float)) or not (
            0.0 < float(threshold) < 1.0
        ):
            raise ValueError(
                "low_confidence_threshold must be between 0 and 1."
            )

    def _classification_calibration_metrics(
        self,
        *,
        actual: np.ndarray,
        predicted: np.ndarray,
        probabilities: np.ndarray,
        class_labels: list[Any],
    ) -> dict[str, float]:
        label_to_index = {
            self._label_key(label): index
            for index, label in enumerate(class_labels)
        }
        actual_indices = np.asarray(
            [label_to_index[self._label_key(value)] for value in actual],
            dtype=int,
        )
        confidence = probabilities.max(axis=1)
        correct = (predicted == actual).astype(float)
        expected_calibration_error = 0.0
        boundaries = np.linspace(0.0, 1.0, 11)

        for lower, upper in zip(boundaries[:-1], boundaries[1:]):
            if upper == 1.0:
                mask = (confidence >= lower) & (confidence <= upper)
            else:
                mask = (confidence >= lower) & (confidence < upper)

            if not np.any(mask):
                continue

            weight = float(np.mean(mask))
            expected_calibration_error += weight * abs(
                float(np.mean(correct[mask]))
                - float(np.mean(confidence[mask]))
            )

        selected_probabilities = probabilities[
            np.arange(len(actual_indices)),
            actual_indices,
        ]
        log_loss = -float(
            np.mean(np.log(np.clip(selected_probabilities, 1e-15, 1.0)))
        )
        one_hot = np.eye(len(class_labels))[actual_indices]
        brier_score = float(
            np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))
        )
        return {
            "expected_calibration_error": expected_calibration_error,
            "log_loss": log_loss,
            "brier_score": brier_score,
            "mean_confidence": float(np.mean(confidence)),
            "calibration_accuracy": float(np.mean(correct)),
        }

    @staticmethod
    def _class_labels(pipeline) -> list[Any]:
        labels = getattr(pipeline, "classes_", None)

        if labels is None and hasattr(pipeline, "named_steps"):
            labels = getattr(
                pipeline.named_steps.get("model"),
                "classes_",
                None,
            )

        if labels is None:
            return []

        return [
            label.item() if isinstance(label, np.generic) else label
            for label in labels
        ]

    @staticmethod
    def _label_key(value: Any) -> tuple[str, str]:
        if isinstance(value, np.generic):
            value = value.item()

        return type(value).__name__, str(value)
