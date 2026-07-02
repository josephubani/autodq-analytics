import numpy as np

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

from autodq.ml.models import (
    FeatureImportance,
    ModelMetrics,
    ModelPrediction,
)


class ModelEvaluator:
    """
    Evaluates trained ML models and extracts predictions/feature importance.
    """

    def evaluate_regression(
        self,
        algorithm: str,
        y_test,
        y_pred,
    ) -> ModelMetrics:
        return ModelMetrics(
            problem_type="regression",
            algorithm=algorithm,
            mae=round(mean_absolute_error(y_test, y_pred), 4),
            rmse=round(np.sqrt(mean_squared_error(y_test, y_pred)), 4),
            r2=round(r2_score(y_test, y_pred), 4),
        )

    def evaluate_classification(
        self,
        algorithm: str,
        y_test,
        y_pred,
    ) -> ModelMetrics:
        return ModelMetrics(
            problem_type="classification",
            algorithm=algorithm,
            accuracy=round(accuracy_score(y_test, y_pred), 4),
            precision=round(
                precision_score(y_test, y_pred, average="weighted", zero_division=0),
                4,
            ),
            recall=round(
                recall_score(y_test, y_pred, average="weighted", zero_division=0),
                4,
            ),
            f1=round(
                f1_score(y_test, y_pred, average="weighted", zero_division=0),
                4,
            ),
        )

    def build_predictions(
        self,
        y_test,
        y_pred,
        problem_type: str,
        limit: int = 25,
    ) -> list[ModelPrediction]:
        predictions = []

        for actual, predicted in list(zip(y_test, y_pred))[:limit]:
            residual = None

            if problem_type == "regression":
                residual = round(float(actual - predicted), 4)

            predictions.append(
                ModelPrediction(
                    actual=actual,
                    predicted=predicted,
                    residual=residual,
                )
            )

        return predictions

    def extract_feature_importance(
        self,
        pipeline,
        numeric_features: list[str],
        categorical_features: list[str],
    ) -> list[FeatureImportance]:
        model = pipeline.named_steps["model"]
        preprocessor = pipeline.named_steps["preprocessor"]

        feature_names = list(numeric_features)

        if categorical_features:
            encoder = (
                preprocessor
                .named_transformers_["cat"]
                .named_steps["encoder"]
            )

            encoded_names = list(
                encoder.get_feature_names_out(categorical_features)
            )

            feature_names.extend(encoded_names)

        importances = None

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_

        elif hasattr(model, "coef_"):
            coef = model.coef_

            if len(coef.shape) > 1:
                importances = np.mean(np.abs(coef), axis=0)
            else:
                importances = np.abs(coef)

        if importances is None:
            return []

        feature_importance = []

        for feature, importance in zip(feature_names, importances):
            feature_importance.append(
                FeatureImportance(
                    feature=feature,
                    importance=round(float(importance), 6),
                    rank=0,
                )
            )

        feature_importance.sort(
            key=lambda item: item.importance,
            reverse=True,
        )

        for index, item in enumerate(feature_importance, start=1):
            item.rank = index

        return feature_importance[:25]