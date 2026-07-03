import pandas as pd

from sklearn.model_selection import train_test_split

from autodq.ml.evaluator import ModelEvaluator
from autodq.ml.model_selector import ModelSelector
from autodq.ml.models import ModelComparisonResult, ModelReport
from autodq.ml.preprocessing import MLPreprocessor
from autodq.ml.trainer import ModelTrainer


class MLEngine:
    """
    End-to-end machine learning engine for AutoDQ.
    Supports:
    - automatic problem detection
    - single-model training
    - auto model comparison
    - regression and classification
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

        if algorithm == "auto":
            candidate_algorithms = self.selector.candidate_algorithms(
                problem_type
            )
        else:
            candidate_algorithms = [
                self.selector.default_algorithm(
                    problem_type=problem_type,
                    algorithm=algorithm,
                )
            ]

        if not candidate_algorithms:
            raise ValueError(
                f"No supported algorithms available for problem type: {problem_type}"
            )

        trained_reports: list[ModelReport] = []

        for candidate_algorithm in candidate_algorithms:
            report = self._train_single_model(
                df=working_df,
                target=target,
                problem_type=problem_type,
                algorithm=candidate_algorithm,
                test_size=test_size,
                random_state=random_state,
            )

            trained_reports.append(report)

        comparison = self._build_model_comparison(
            reports=trained_reports,
            problem_type=problem_type,
        )

        best_algorithm = comparison[0].algorithm

        best_report = next(
            report
            for report in trained_reports
            if report.algorithm == best_algorithm
        )

        best_report.model_comparison = comparison
        best_report.recommendations.extend(
            self._comparison_recommendations(comparison)
        )

        return best_report

    def _train_single_model(
        self,
        df: pd.DataFrame,
        target: str,
        problem_type: str,
        algorithm: str,
        test_size: float,
        random_state: int,
    ) -> ModelReport:
        scale_numeric = algorithm in [
            "linear_regression",
            "logistic_regression",
        ]

        X, y, preprocessor, numeric_features, categorical_features = (
            self.preprocessor.build(
                df=df,
                target=target,
                scale_numeric=scale_numeric,
            )
        )

        stratify = None

        if problem_type == "classification" and y.nunique(dropna=True) > 1:
            class_counts = y.value_counts(dropna=True)
            if class_counts.min() >= 2:
                stratify = y

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify,
        )

        pipeline, _ = self.trainer.build_model(
            problem_type=problem_type,
            algorithm=algorithm,
            preprocessor=preprocessor,
        )

        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)

        if problem_type == "regression":
            metrics = self.evaluator.evaluate_regression(
                algorithm=algorithm,
                y_test=y_test,
                y_pred=y_pred,
            )
        else:
            metrics = self.evaluator.evaluate_classification(
                algorithm=algorithm,
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
            algorithm=algorithm,
            metrics=metrics,
            feature_importance=feature_importance,
            predictions=predictions,
            recommendations=recommendations,
            model_object=pipeline,
            preprocessing_object=preprocessor,
            feature_columns=list(X.columns),
        )

    def _build_model_comparison(
        self,
        reports: list[ModelReport],
        problem_type: str,
    ) -> list[ModelComparisonResult]:
        comparison: list[ModelComparisonResult] = []

        for report in reports:
            if problem_type == "regression":
                primary_metric = "r2"
                primary_score = (
                    report.metrics.r2
                    if report.metrics.r2 is not None
                    else -999
                )
            else:
                primary_metric = "f1"
                primary_score = (
                    report.metrics.f1
                    if report.metrics.f1 is not None
                    else -999
                )

            comparison.append(
                ModelComparisonResult(
                    algorithm=report.algorithm,
                    problem_type=problem_type,
                    primary_metric=primary_metric,
                    primary_score=primary_score,
                    metrics=report.metrics,
                )
            )

        comparison.sort(
            key=lambda item: item.primary_score,
            reverse=True,
        )

        for rank, item in enumerate(comparison, start=1):
            item.rank = rank

        return comparison

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

    def _comparison_recommendations(
        self,
        comparison: list[ModelComparisonResult],
    ) -> list[str]:
        if not comparison:
            return []

        winner = comparison[0]

        recommendations = [
            f"{winner.algorithm} was selected as the best model based on {winner.primary_metric}."
        ]

        if len(comparison) > 1:
            second = comparison[1]
            gap = round(winner.primary_score - second.primary_score, 4)

            if gap < 0.02:
                recommendations.append(
                    f"The top models performed similarly. Compare {winner.algorithm} and {second.algorithm} before final deployment."
                )
            else:
                recommendations.append(
                    f"{winner.algorithm} clearly outperformed the next-best model by {gap} {winner.primary_metric} points."
                )

        return recommendations