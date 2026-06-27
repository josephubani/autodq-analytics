import pandas as pd

from autodq.diagnosis.engine import run_diagnosis
from autodq.models.validation import ValidationMetric, ValidationReport


class ValidationEngine:
    """
    Compares data quality before and after cleaning.
    """

    def validate(
        self,
        before_df: pd.DataFrame,
        after_df: pd.DataFrame,
    ) -> ValidationReport:
        before_diagnosis = run_diagnosis(before_df)
        after_diagnosis = run_diagnosis(after_df)

        return ValidationReport(
            missing_values=ValidationMetric(
                name="missing_values",
                before=int(before_df.isna().sum().sum()),
                after=int(after_df.isna().sum().sum()),
            ),
            duplicate_rows=ValidationMetric(
                name="duplicate_rows",
                before=int(before_df.duplicated().sum()),
                after=int(after_df.duplicated().sum()),
            ),
            rows=ValidationMetric(
                name="rows",
                before=int(len(before_df)),
                after=int(len(after_df)),
            ),
            columns=ValidationMetric(
                name="columns",
                before=int(len(before_df.columns)),
                after=int(len(after_df.columns)),
            ),
            quality_score_before=before_diagnosis.quality_score,
            quality_score_after=after_diagnosis.quality_score,
        )