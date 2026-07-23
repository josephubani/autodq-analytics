import pandas as pd

from autodq.semantics.base import BaseSemanticDetector
from autodq.semantics.prediction import SemanticPrediction
from autodq.utils.helpers import is_text_or_categorical_dtype


class CategoricalDetector(BaseSemanticDetector):
    name = "categorical_detector"

    def detect(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> SemanticPrediction | None:
        if not is_text_or_categorical_dtype(series.dtype):
            return None

        total_rows = len(df)

        if total_rows == 0:
            return None

        unique_count = series.nunique(dropna=True)
        unique_ratio = unique_count / total_rows

        if unique_ratio <= 0.8:
            return SemanticPrediction(
                semantic_type="categorical",
                confidence=0.82,
                detector=self.name,
                evidence=[
                    "Column is text/category dtype",
                    f"Unique ratio is {round(unique_ratio, 2)}",
                ],
            )

        return SemanticPrediction(
            semantic_type="text",
            confidence=0.7,
            detector=self.name,
            evidence=[
                "Column is text dtype",
                f"High unique ratio: {round(unique_ratio, 2)}",
            ],
        )
