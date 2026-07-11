from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from autodq.explainability.models import (
    ExplainabilityReport,
    FeatureContribution,
    RowExplanation,
)


class ExplainabilityEngine:
    """
    Generates global and row-level machine learning explanations.

    Supported behavior:
    - SHAP TreeExplainer for fitted tree estimators
    - SHAP LinearExplainer for fitted linear estimators
    - general SHAP Explainer fallback
    - global feature importance fallback if SHAP fails
    """

    TREE_ALGORITHM_TOKENS = (
        "random_forest",
        "decision_tree",
        "gradient_boosting",
        "xgboost",
        "lightgbm",
        "catboost",
        "extra_trees",
    )

    LINEAR_ALGORITHM_TOKENS = (
        "linear_regression",
        "logistic_regression",
        "ridge",
        "lasso",
        "elastic_net",
    )

    def explain(
        self,
        model_report,
        data: pd.DataFrame | None = None,
        prediction_report=None,
        max_rows: int = 20,
        max_global_features: int = 10,
        max_row_features: int = 5,
    ) -> ExplainabilityReport:
        if model_report is None:
            raise ValueError(
                "No model report available. Run project.model() first."
            )

        if data is None or data.empty:
            return self._global_importance_fallback(
                model_report=model_report,
                prediction_report=prediction_report,
                max_rows=max_rows,
                max_global_features=max_global_features,
                warning=(
                    "Prediction data was not supplied. "
                    "Global feature importance fallback was used."
                ),
            )

        pipeline = getattr(model_report, "model_object", None)

        if pipeline is None:
            return self._global_importance_fallback(
                model_report=model_report,
                prediction_report=prediction_report,
                max_rows=max_rows,
                max_global_features=max_global_features,
                warning=(
                    "The fitted model pipeline is unavailable. "
                    "Global feature importance fallback was used."
                ),
            )

        try:
            import shap
        except ImportError:
            return self._global_importance_fallback(
                model_report=model_report,
                prediction_report=prediction_report,
                max_rows=max_rows,
                max_global_features=max_global_features,
                warning=(
                    "SHAP is not installed. Run 'pip install shap'. "
                    "Global feature importance fallback was used."
                ),
            )

        working_df = data.copy()

        target = getattr(model_report, "target", None)

        if target and target in working_df.columns:
            feature_df = working_df.drop(columns=[target])
        else:
            feature_df = working_df

        feature_df = self._align_input_columns(
            df=feature_df,
            model_report=model_report,
        )

        if feature_df.empty:
            return self._global_importance_fallback(
                model_report=model_report,
                prediction_report=prediction_report,
                max_rows=max_rows,
                max_global_features=max_global_features,
                warning=(
                    "No valid feature columns remained after schema alignment. "
                    "Global feature importance fallback was used."
                ),
            )

        explain_df = feature_df.head(max_rows).copy()

        try:
            estimator = self._get_estimator(pipeline)
            transformer = self._get_transformer(pipeline)

            transformed_data = self._transform_data(
                transformer=transformer,
                data=explain_df,
            )

            feature_names = self._get_feature_names(
                transformer=transformer,
                original_columns=list(explain_df.columns),
                transformed_width=transformed_data.shape[1],
            )

            transformed_frame = pd.DataFrame(
                transformed_data,
                columns=feature_names,
                index=explain_df.index,
            )

            method, shap_values, base_values = self._calculate_shap_values(
                shap_module=shap,
                estimator=estimator,
                transformed_data=transformed_frame,
                algorithm=model_report.algorithm,
                problem_type=model_report.problem_type,
            )

            normalized_values = self._normalize_shap_values(
                shap_values=shap_values,
                problem_type=model_report.problem_type,
            )

            normalized_base_values = self._normalize_base_values(
                base_values=base_values,
                row_count=len(transformed_frame),
                problem_type=model_report.problem_type,
            )

            global_features = self._build_global_features(
                shap_values=normalized_values,
                feature_names=feature_names,
                max_features=max_global_features,
            )

            row_explanations = self._build_row_explanations(
                shap_values=normalized_values,
                transformed_frame=transformed_frame,
                feature_names=feature_names,
                base_values=normalized_base_values,
                prediction_report=prediction_report,
                model_report=model_report,
                max_features=max_row_features,
            )

            warnings: list[str] = []

            if any(
                self._is_identifier_like(feature)
                for feature in feature_names
            ):
                warnings.append(
                    "Identifier-like transformed features were excluded "
                    "from the displayed explanations."
                )

            return ExplainabilityReport(
                algorithm=model_report.algorithm,
                method=method,
                row_explanations=row_explanations,
                global_features=global_features,
                warnings=warnings,
                feature_names=feature_names,
            )

        except Exception as error:
            return self._global_importance_fallback(
                model_report=model_report,
                prediction_report=prediction_report,
                max_rows=max_rows,
                max_global_features=max_global_features,
                warning=(
                    "SHAP explanation failed and AutoDQ used global feature "
                    f"importance instead. Error: {type(error).__name__}: {error}"
                ),
            )

    def _get_estimator(self, pipeline):
        if hasattr(pipeline, "steps") and pipeline.steps:
            return pipeline.steps[-1][1]

        return pipeline

    def _get_transformer(self, pipeline):
        if hasattr(pipeline, "steps") and len(pipeline.steps) > 1:
            return pipeline[:-1]

        return None

    def _transform_data(
        self,
        transformer,
        data: pd.DataFrame,
    ) -> np.ndarray:
        if transformer is None:
            transformed = data.to_numpy()
        else:
            transformed = transformer.transform(data)

        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()

        return np.asarray(transformed)

    def _get_feature_names(
        self,
        transformer,
        original_columns: list[str],
        transformed_width: int,
    ) -> list[str]:
        feature_names: list[str] = []

        if transformer is not None and hasattr(
            transformer,
            "get_feature_names_out",
        ):
            try:
                feature_names = list(
                    transformer.get_feature_names_out()
                )
            except Exception:
                feature_names = []

        if not feature_names and len(original_columns) == transformed_width:
            feature_names = list(original_columns)

        if len(feature_names) != transformed_width:
            feature_names = [
                f"feature_{index}"
                for index in range(transformed_width)
            ]

        return [
            self._clean_feature_name(feature)
            for feature in feature_names
        ]

    def _clean_feature_name(self, feature: str) -> str:
        feature = str(feature)

        prefixes = (
            "numeric__",
            "categorical__",
            "num__",
            "cat__",
            "remainder__",
        )

        for prefix in prefixes:
            if feature.startswith(prefix):
                return feature[len(prefix):]

        return feature

    def _calculate_shap_values(
        self,
        shap_module,
        estimator,
        transformed_data: pd.DataFrame,
        algorithm: str,
        problem_type: str,
    ) -> tuple[str, Any, Any]:
        algorithm_lower = (algorithm or "").lower()

        if any(
            token in algorithm_lower
            for token in self.TREE_ALGORITHM_TOKENS
        ):
            explainer = shap_module.TreeExplainer(estimator)
            explanation = explainer(transformed_data)

            return (
                "shap_tree_explainer",
                explanation.values,
                explanation.base_values,
            )

        if any(
            token in algorithm_lower
            for token in self.LINEAR_ALGORITHM_TOKENS
        ):
            explainer = shap_module.LinearExplainer(
                estimator,
                transformed_data,
            )
            explanation = explainer(transformed_data)

            return (
                "shap_linear_explainer",
                explanation.values,
                explanation.base_values,
            )

        explainer = shap_module.Explainer(
            estimator,
            transformed_data,
        )
        explanation = explainer(transformed_data)

        return (
            "shap_general_explainer",
            explanation.values,
            explanation.base_values,
        )

    def _normalize_shap_values(
        self,
        shap_values,
        problem_type: str,
    ) -> np.ndarray:
        values = np.asarray(shap_values)

        if values.ndim == 2:
            return values

        if values.ndim == 3:
            if problem_type == "classification":
                class_index = 1 if values.shape[2] > 1 else 0
                return values[:, :, class_index]

            return values[:, :, 0]

        raise ValueError(
            f"Unsupported SHAP value dimensions: {values.shape}"
        )

    def _normalize_base_values(
        self,
        base_values,
        row_count: int,
        problem_type: str,
    ) -> np.ndarray:
        values = np.asarray(base_values)

        if values.ndim == 0:
            return np.repeat(float(values), row_count)

        if values.ndim == 1:
            if len(values) == row_count:
                return values.astype(float)

            selected = values[1] if len(values) > 1 else values[0]
            return np.repeat(float(selected), row_count)

        if values.ndim == 2:
            class_index = (
                1
                if problem_type == "classification"
                and values.shape[1] > 1
                else 0
            )
            return values[:, class_index].astype(float)

        return np.repeat(np.nan, row_count)

    def _build_global_features(
        self,
        shap_values: np.ndarray,
        feature_names: list[str],
        max_features: int,
    ) -> list[FeatureContribution]:
        mean_absolute_values = np.mean(
            np.abs(shap_values),
            axis=0,
        )

        total = float(mean_absolute_values.sum())

        ranked_indices = np.argsort(
            mean_absolute_values
        )[::-1]

        results: list[FeatureContribution] = []

        for index in ranked_indices:
            feature = feature_names[index]

            if self._is_identifier_like(feature):
                continue

            contribution = float(mean_absolute_values[index])

            contribution_percent = (
                contribution / total * 100
                if total > 0
                else 0.0
            )

            results.append(
                FeatureContribution(
                    feature=feature,
                    feature_value=None,
                    contribution=round(contribution, 6),
                    contribution_percent=round(
                        contribution_percent,
                        2,
                    ),
                    direction="absolute",
                    rank=len(results) + 1,
                )
            )

            if len(results) >= max_features:
                break

        return results

    def _build_row_explanations(
        self,
        shap_values: np.ndarray,
        transformed_frame: pd.DataFrame,
        feature_names: list[str],
        base_values: np.ndarray,
        prediction_report,
        model_report,
        max_features: int,
    ) -> list[RowExplanation]:
        row_results: list[RowExplanation] = []

        stored_predictions = (
            prediction_report.predictions
            if prediction_report is not None
            else []
        )

        for row_position in range(len(transformed_frame)):
            row_shap = shap_values[row_position]
            row_values = transformed_frame.iloc[row_position]

            ranked_indices = np.argsort(
                np.abs(row_shap)
            )[::-1]

            contributions: list[FeatureContribution] = []

            total_absolute = float(
                np.abs(row_shap).sum()
            )

            for feature_index in ranked_indices:
                feature = feature_names[feature_index]

                if self._is_identifier_like(feature):
                    continue

                contribution = float(
                    row_shap[feature_index]
                )

                contribution_percent = (
                    abs(contribution)
                    / total_absolute
                    * 100
                    if total_absolute > 0
                    else 0.0
                )

                contributions.append(
                    FeatureContribution(
                        feature=feature,
                        feature_value=self._safe_value(
                            row_values.iloc[feature_index]
                        ),
                        contribution=round(
                            contribution,
                            6,
                        ),
                        contribution_percent=round(
                            contribution_percent,
                            2,
                        ),
                        direction=(
                            "positive"
                            if contribution >= 0
                            else "negative"
                        ),
                        rank=len(contributions) + 1,
                    )
                )

                if len(contributions) >= max_features:
                    break

            positive = [
                item
                for item in contributions
                if item.direction == "positive"
            ]

            negative = [
                item
                for item in contributions
                if item.direction == "negative"
            ]

            prediction = self._resolve_prediction(
                row_position=row_position,
                stored_predictions=stored_predictions,
                model_report=model_report,
                transformed_frame=transformed_frame,
            )

            explanation_text = self._build_explanation_text(
                prediction=prediction,
                positive=positive,
                negative=negative,
            )

            row_results.append(
                RowExplanation(
                    row_id=int(
                        transformed_frame.index[row_position]
                    ),
                    prediction=self._safe_value(prediction),
                    base_value=round(
                        float(base_values[row_position]),
                        6,
                    ),
                    top_contributions=contributions,
                    positive_contributions=positive,
                    negative_contributions=negative,
                    explanation=explanation_text,
                )
            )

        return row_results

    def _resolve_prediction(
        self,
        row_position: int,
        stored_predictions,
        model_report,
        transformed_frame: pd.DataFrame,
    ):
        if row_position < len(stored_predictions):
            return stored_predictions[row_position].predicted

        estimator = self._get_estimator(
            model_report.model_object
        )

        return estimator.predict(
            transformed_frame.iloc[
                [row_position]
            ]
        )[0]

    def _build_explanation_text(
        self,
        prediction,
        positive: list[FeatureContribution],
        negative: list[FeatureContribution],
    ) -> str:
        parts = [
            f"The model predicted {self._safe_value(prediction)}."
        ]

        if positive:
            positive_names = ", ".join(
                item.feature
                for item in positive[:3]
            )
            parts.append(
                f"The strongest increasing influences were "
                f"{positive_names}."
            )

        if negative:
            negative_names = ", ".join(
                item.feature
                for item in negative[:3]
            )
            parts.append(
                f"The strongest decreasing influences were "
                f"{negative_names}."
            )

        if not positive and not negative:
            parts.append(
                "No material row-level contributions were available."
            )

        return " ".join(parts)

    def _align_input_columns(
        self,
        df: pd.DataFrame,
        model_report,
    ) -> pd.DataFrame:
        expected_columns = getattr(
            model_report,
            "feature_columns",
            None,
        )

        if not expected_columns:
            return df

        missing_columns = [
            column
            for column in expected_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                "The explanation dataset is missing required model "
                f"features: {missing_columns}"
            )

        return df[expected_columns].copy()

    def _global_importance_fallback(
        self,
        model_report,
        prediction_report,
        max_rows: int,
        max_global_features: int,
        warning: str,
    ) -> ExplainabilityReport:
        global_features: list[FeatureContribution] = []

        for item in getattr(
            model_report,
            "feature_importance",
            [],
        ):
            if self._is_identifier_like(item.feature):
                continue

            contribution = float(item.importance)

            global_features.append(
                FeatureContribution(
                    feature=item.feature,
                    feature_value=None,
                    contribution=round(
                        contribution,
                        6,
                    ),
                    contribution_percent=round(
                        abs(contribution) * 100,
                        2,
                    ),
                    direction="absolute",
                    rank=len(global_features) + 1,
                )
            )

            if len(global_features) >= max_global_features:
                break

        row_explanations: list[RowExplanation] = []

        if prediction_report is not None:
            for prediction in prediction_report.predictions[:max_rows]:
                row_explanations.append(
                    RowExplanation(
                        row_id=prediction.row_id,
                        prediction=prediction.predicted,
                        base_value=None,
                        top_contributions=global_features[:3],
                        positive_contributions=[],
                        negative_contributions=[],
                        explanation=(
                            "This explanation uses global feature "
                            "importance because SHAP was unavailable."
                        ),
                    )
                )

        return ExplainabilityReport(
            algorithm=model_report.algorithm,
            method="global_feature_importance_fallback",
            row_explanations=row_explanations,
            global_features=global_features,
            warnings=[warning],
            feature_names=[
                item.feature
                for item in global_features
            ],
        )

    def _is_identifier_like(self, feature_name: str) -> bool:
        feature_lower = str(feature_name).lower()

        identifier_tokens = (
            "customer_id",
            "transaction_id",
            "order_id",
            "invoice_id",
            "receipt_id",
            "uuid",
            "guid",
        )

        if any(
            token in feature_lower
            for token in identifier_tokens
        ):
            return True

        if feature_lower.endswith("_id"):
            return True

        return False

    def _safe_value(self, value):
        if isinstance(value, np.generic):
            return value.item()

        if pd.isna(value):
            return None

        if isinstance(value, float):
            return round(value, 6)

        return value