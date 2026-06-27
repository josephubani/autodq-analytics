import pandas as pd

from autodq.decision.engine import DecisionPlan
from autodq.models.cleaning import CleaningActionResult, CleaningReport


class CleaningEngine:
    """
    Executes approved cleaning actions.

    Safety rule:
    Only actions with status='approved' are executed.
    """

    def clean(
        self,
        df: pd.DataFrame,
        decision_plan: DecisionPlan,
    ) -> tuple[pd.DataFrame, CleaningReport]:

        cleaned_df = df.copy()
        report = CleaningReport()

        for action in decision_plan.actions:
            if action.status != "approved":
                report.actions.append(
                    CleaningActionResult(
                        action_id=action.action_id,
                        issue_type=action.issue_type,
                        strategy=action.strategy,
                        affected_columns=action.affected_columns,
                        status="skipped",
                        message="Action was not approved.",
                        rows_before=len(cleaned_df),
                        rows_after=len(cleaned_df),
                    )
                )
                continue

            if action.issue_type == "duplicate_rows":
                result = self._remove_duplicates(cleaned_df, action)
                cleaned_df = result[0]
                report.actions.append(result[1])

            elif action.issue_type == "missing_values":
                result = self._handle_missing_values(cleaned_df, action)
                cleaned_df = result[0]
                report.actions.append(result[1])

            else:
                report.actions.append(
                    CleaningActionResult(
                        action_id=action.action_id,
                        issue_type=action.issue_type,
                        strategy=action.strategy,
                        affected_columns=action.affected_columns,
                        status="skipped",
                        message="Strategy is not executable yet. Manual review required.",
                        rows_before=len(cleaned_df),
                        rows_after=len(cleaned_df),
                    )
                )

        return cleaned_df, report

    def _remove_duplicates(self, df: pd.DataFrame, action):
        rows_before = len(df)
        cleaned_df = df.drop_duplicates()
        rows_after = len(cleaned_df)

        return cleaned_df, CleaningActionResult(
            action_id=action.action_id,
            issue_type=action.issue_type,
            strategy=action.strategy,
            affected_columns=action.affected_columns,
            status="success",
            message=f"Removed {rows_before - rows_after} duplicate row(s).",
            rows_before=rows_before,
            rows_after=rows_after,
        )

    def _handle_missing_values(self, df: pd.DataFrame, action):
        cleaned_df = df.copy()
        rows_before = len(cleaned_df)

        for column in action.affected_columns:
            if column not in cleaned_df.columns:
                continue

            if action.strategy == "median":
                cleaned_df[column] = cleaned_df[column].fillna(
                    cleaned_df[column].median()
                )

            elif action.strategy == "mean":
                cleaned_df[column] = cleaned_df[column].fillna(
                    cleaned_df[column].mean()
                )

            elif action.strategy == "mode":
                mode_values = cleaned_df[column].mode(dropna=True)

                if not mode_values.empty:
                    cleaned_df[column] = cleaned_df[column].fillna(
                        mode_values.iloc[0]
                    )

        return cleaned_df, CleaningActionResult(
            action_id=action.action_id,
            issue_type=action.issue_type,
            strategy=action.strategy,
            affected_columns=action.affected_columns,
            status="success",
            message=f"Applied {action.strategy} missing-value handling.",
            rows_before=rows_before,
            rows_after=len(cleaned_df),
        )