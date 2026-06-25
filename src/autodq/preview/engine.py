import pandas as pd

from autodq.decision.engine import DecisionPlan
from autodq.models.preview import PreviewAction, PreviewReport


class PreviewEngine:
    """
    Generates safe previews of proposed cleaning actions without modifying data.
    """

    def preview(self, df: pd.DataFrame, decision_plan: DecisionPlan) -> PreviewReport:
        actions = []

        for action in decision_plan.actions:
            if action.issue_type == "duplicate_rows":
                actions.append(self._preview_duplicates(df, action))

            elif action.issue_type == "missing_values":
                actions.append(self._preview_missing_values(df, action))

            elif action.issue_type == "outliers":
                actions.append(self._preview_outliers(df, action))

        return PreviewReport(actions=actions)

    def _preview_duplicates(self, df: pd.DataFrame, action) -> PreviewAction:
        duplicate_count = int(df.duplicated().sum())

        return PreviewAction(
            action_id=action.action_id,
            issue_type=action.issue_type,
            strategy=action.strategy,
            details={
                "rows_before": int(len(df)),
                "rows_after": int(len(df) - duplicate_count),
                "rows_removed": duplicate_count,
            },
        )

    def _preview_missing_values(self, df: pd.DataFrame, action) -> PreviewAction:
        column_previews = {}

        for column in action.affected_columns:
            if column not in df.columns:
                continue

            column_previews[column] = {
                "missing_before": int(df[column].isna().sum()),
                "suggested_action": "Column-specific imputation or removal",
                "sample_values": df[column].head(5).astype(str).tolist(),
            }

        return PreviewAction(
            action_id=action.action_id,
            issue_type=action.issue_type,
            strategy=action.strategy,
            details=column_previews,
        )

    def _preview_outliers(self, df: pd.DataFrame, action) -> PreviewAction:
        column_previews = {}

        for column in action.affected_columns:
            if column not in df.columns:
                continue

            series = df[column].dropna()

            if not pd.api.types.is_numeric_dtype(series):
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower = q1 - (1.5 * iqr)
            upper = q3 + (1.5 * iqr)
            outlier_values = series[(series < lower) | (series > upper)]

            column_previews[column] = {
                "outlier_count": int(len(outlier_values)),
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
                "sample_outliers": outlier_values.head(5).tolist(),
                "suggested_action": "Review, clip, winsorize, transform, or validate with domain knowledge",
            }

        return PreviewAction(
            action_id=action.action_id,
            issue_type=action.issue_type,
            strategy=action.strategy,
            details=column_previews,
        )