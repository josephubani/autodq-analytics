from pathlib import Path

import pandas as pd

from autodq.io.loaders import load_dataset
from autodq.prediction.models import PredictionReport, PredictionResult


class PredictionEngine:
    """
    Generates predictions from a trained AutoDQ model report.
    """

    def predict(
        self,
        model_report,
        data=None,
        target: str | None = None,
        strict_schema: bool = False,
    ) -> tuple[pd.DataFrame, PredictionReport]:
        if model_report is None:
            raise ValueError("No trained model available. Run project.model() first.")

        if data is None:
            raise ValueError("Prediction data is required.")

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
        predictions = pipeline.predict(X)

        output_df = df.copy()
        output_df["AutoDQ_Prediction"] = predictions

        results: list[PredictionResult] = []

        for index, predicted in enumerate(predictions):
            actual = None
            residual = None
            absolute_error = None
            percent_error = None

            if actual_values is not None:
                actual = actual_values.iloc[index]

                if model_report.problem_type == "regression":
                    residual = round(float(actual - predicted), 4)
                    absolute_error = round(abs(float(actual - predicted)), 4)

                    if actual != 0:
                        percent_error = round((absolute_error / abs(float(actual))) * 100, 4)
            confidence = self._estimate_confidence(
                model_report=model_report,
                absolute_error=absolute_error,
                actual=actual,
            )

            top_features = self._top_features(model_report)

            explanation = self._build_explanation(
                predicted=predicted,
                actual=actual,
                confidence=confidence,
                top_features=top_features,
                problem_type=model_report.problem_type,
            )         

            results.append(
                PredictionResult(
                    row_id=index,
                    actual=actual,
                    predicted=predicted,
                    residual=residual,
                    absolute_error=absolute_error,
                    percent_error=percent_error,
                    confidence=confidence,
                    top_features=top_features,
                    explanation=explanation,
                )
            )

        report = PredictionReport(
            target=model_report.target,
            problem_type=model_report.problem_type,
            algorithm=model_report.algorithm,
            predictions=results[:100],
            warnings=schema_warnings,
        )

        return output_df, report

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

        expected_dtypes = getattr(
            model_report,
            "feature_dtypes",
            {},
        )
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

    def _estimate_confidence(
        self,
        model_report,
        absolute_error,
        actual,
    ) -> float:
        if model_report.problem_type != "regression":
            return 80.0

        if absolute_error is None or actual is None:
            return 80.0

        if actual == 0:
            return 75.0

        error_ratio = abs(float(absolute_error)) / max(abs(float(actual)), 1)

        confidence = 100 - min(60, error_ratio * 100)

        return round(max(40, min(99, confidence)), 2)

    def _build_explanation(
        self,
        predicted,
        actual,
        confidence,
        top_features,
        problem_type,
    ) -> str:
        if problem_type == "regression":
            feature_text = ", ".join(top_features) if top_features else "the strongest model features"

            if actual is not None:
                return (
                    f"The model predicted {round(float(predicted), 4)}. "
                    f"This prediction is mainly influenced by {feature_text}. "
                    f"Estimated confidence is {confidence}%."
                )

            return (
                f"The model predicted {round(float(predicted), 4)}. "
                f"This prediction is mainly influenced by {feature_text}. "
                f"Estimated confidence is {confidence}%."
            )

        return (
            f"The model predicted class '{predicted}'. "
            f"The prediction is mainly influenced by {', '.join(top_features) if top_features else 'the strongest model features'}."
        )
