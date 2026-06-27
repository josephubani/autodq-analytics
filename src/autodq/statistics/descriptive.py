import numpy as np
import pandas as pd

from autodq.semantics.inference import infer_semantic_types
from autodq.statistics.models import ColumnStatistics


class DescriptiveStatisticsEngine:
    """
    Computes descriptive statistics for numeric analytical columns.
    Identifier-like numeric columns are skipped.
    """

    def analyze(
        self,
        df: pd.DataFrame,
    ) -> dict[str, ColumnStatistics]:

        results = {}
        semantic_types = infer_semantic_types(df)

        numeric_columns = df.select_dtypes(include="number").columns

        for column in numeric_columns:
            if semantic_types.get(column) == "identifier":
                continue

            series = df[column]

            count = int(series.count())
            missing = int(series.isna().sum())

            missing_percent = round(
                missing / len(df) * 100,
                2,
            )

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            mode = None
            modes = series.mode()

            if not modes.empty:
                mode = modes.iloc[0]

            mean = series.mean()
            std = series.std()

            cv = None

            if mean not in (0, None) and not pd.isna(mean):
                cv = std / mean

            results[column] = ColumnStatistics(
                column=column,
                count=count,
                missing=missing,
                missing_percent=missing_percent,
                mean=mean,
                median=series.median(),
                mode=mode,
                minimum=series.min(),
                maximum=series.max(),
                variance=series.var(),
                std=std,
                value_range=series.max() - series.min(),
                iqr=iqr,
                mad=np.median(
                    np.abs(series.dropna() - series.median())
                ),
                coefficient_variation=cv,
                skewness=series.skew(),
                kurtosis=series.kurt(),
            )

        return results