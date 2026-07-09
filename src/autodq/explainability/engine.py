class ExplainabilityEngine:
    """
    Explainability engine placeholder.

    Current phase:
    - prepares structure for SHAP
    - falls back to global feature importance
    - filters identifier-like features from explanation output
    """

    def explain(
        self,
        model_report,
        prediction_report=None,
        max_rows: int = 20,
    ):
        from autodq.explainability.models import (
            ExplainabilityReport,
            FeatureContribution,
            RowExplanation,
        )

        if model_report is None:
            raise ValueError("No model report available. Run project.model() first.")

        global_features = []
        rank = 1

        for item in model_report.feature_importance:
            feature_lower = item.feature.lower()

            if self._is_identifier_like(feature_lower):
                continue

            direction = "positive" if item.importance >= 0 else "negative"

            global_features.append(
                FeatureContribution(
                    feature=item.feature,
                    contribution=round(float(item.importance), 6),
                    direction=direction,
                    rank=rank,
                )
            )

            rank += 1

            if len(global_features) == 10:
                break

        row_explanations = []

        if prediction_report is not None:
            for prediction in prediction_report.predictions[:max_rows]:
                row_explanations.append(
                    RowExplanation(
                        row_id=prediction.row_id,
                        prediction=prediction.predicted,
                        top_contributions=global_features[:3],
                        explanation=(
                            "Temporary explanation based on global feature importance. "
                            "SHAP row-level explanations will replace this."
                        ),
                    )
                )

        return ExplainabilityReport(
            algorithm=model_report.algorithm,
            method="global_feature_importance_fallback",
            row_explanations=row_explanations,
            global_features=global_features,
            warnings=[
                "SHAP is not active yet. Current explanations use global feature importance."
            ],
        )

    def _is_identifier_like(self, feature_name: str) -> bool:
        identifier_tokens = [
            "id",
            "uuid",
            "guid",
            "transaction",
            "customer_id",
            "order_id",
            "invoice",
            "receipt",
        ]

        return any(token in feature_name for token in identifier_tokens)