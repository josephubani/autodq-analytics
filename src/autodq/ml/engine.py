import pandas as pd

from sklearn.model_selection import train_test_split

from autodq.ml.evaluator import ModelEvaluator
from autodq.ml.model_selector import ModelSelector
from autodq.ml.models import ModelReport
from autodq.ml.preprocessing import MLPreprocessor
from autodq.ml.trainer import ModelTrainer


class MLEngine:
    """
    End-to-end machine learning engine for AutoDQ.
    """

    def __init__(self):
        self.selector = ModelSelector()
        self.preprocessor = MLPreprocessor()
        self.trainer = ModelTrainer()
        self.evaluator = ModelEvaluator()

    def train(
        self,
        df: pd.DataFrame,
        target: str,
        algorithm: str | None = "auto",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> ModelReport:
        if target is None:
            raise ValueError("Target column must be set before modelling.")

        if target not in df.columns:
            raise ValueError(f"Target column not found: {target}")

        working_df = df.dropna(subset=[target]).copy()

        problem_type = self.selector.detect_problem_type(
            working_df,
            target,
        )

        selected_algorithm = self.selector.default_algorithm(
            problem_type=problem_type,
            algorithm=algorithm,
        )

        scale_numeric = selected_algorithm in [
            "linear_regression",
            "logistic_regression",
        ]

        X, y, preprocessor, numeric_features, categorical_features = (
            self.preprocessor.build(
                df=working_df,
                target=target,
                scale_numeric=scale_numeric,
            )
        )

        stratify = y if problem_type == "classification" and y.nunique() > 1 else None

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify,
        )

        pipeline, _ = self.trainer.build_model(
            problem_type=problem_type,
            algorithm=selected_algorithm,
            preprocessor=preprocessor,
        )

        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)

        if problem_type == "regression":
            metrics = self.evaluator.evaluate_regression(
                algorithm=selected_algorithm,
                y_test=y_test,
                y_pred=y_pred,
            )
        else:
            metrics = self.evaluator.evaluate_classification(
                algorithm=selected_algorithm,
                y_test=y_test,
                y_pred=y_pred,
            )

        predictions = self.evaluator.build_predictions(
            y_test=list(y_test),
            y_pred=list(y_pred),
            problem_type=problem_type,
        )

        feature_importance = self.evaluator.extract_feature_importance(
            pipeline=pipeline,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
        )

        recommendations = self._recommendations(
            problem_type=problem_type,
            metrics=metrics,
            feature_importance=feature_importance,
        )

        return ModelReport(
            target=target,
            problem_type=problem_type,
            algorithm=selected_algorithm,
            metrics=metrics,
            feature_importance=feature_importance,
            predictions=predictions,
            recommendations=recommendations,
            model_object=pipeline,
            preprocessing_object=preprocessor,
            feature_columns=list(X.columns),
        )

    def _recommendations(
        self,
        problem_type: str,
        metrics,
        feature_importance,
    ) -> list[str]:
        recommendations = []

        if problem_type == "regression":
            if metrics.r2 is not None and metrics.r2 >= 0.85:
                recommendations.append(
                    "Model performance is strong based on R². Review target leakage before trusting results."
                )
            elif metrics.r2 is not None and metrics.r2 >= 0.6:
                recommendations.append(
                    "Model performance is moderate. Feature engineering or more data may improve results."
                )
            else:
                recommendations.append(
                    "Model performance is weak. Review feature quality, target definition, and outliers."
                )

        if problem_type == "classification":
            if metrics.f1 is not None and metrics.f1 >= 0.85:
                recommendations.append(
                    "Classification performance is strong based on weighted F1 score."
                )
            elif metrics.f1 is not None and metrics.f1 >= 0.6:
                recommendations.append(
                    "Classification performance is moderate. Check class imbalance and feature quality."
                )
            else:
                recommendations.append(
                    "Classification performance is weak. Review target quality, class balance, and features."
                )

        if feature_importance:
            top_feature = feature_importance[0].feature
            recommendations.append(
                f"The most influential feature appears to be '{top_feature}'. Review whether it is valid or causes leakage."
            )

        return recommendations