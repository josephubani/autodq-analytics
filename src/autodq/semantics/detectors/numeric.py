import pandas as pd

from autodq.semantics.base import BaseSemanticDetector
from autodq.semantics.prediction import SemanticPrediction


class ContinuousNumericDetector(BaseSemanticDetector):
    name = "continuous_numeric_detector"

    def detect(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> SemanticPrediction | None:
        if not pd.api.types.is_numeric_dtype(series):
            return None

        non_null = series.dropna()

        if non_null.empty:
            return None

        unique_count = non_null.nunique()

        if pd.api.types.is_float_dtype(non_null) or unique_count > 20:
            return SemanticPrediction(
                semantic_type="continuous_numeric",
                confidence=0.85,
                detector=self.name,
                evidence=[
                    "Column is numeric",
                    f"Unique numeric values: {unique_count}",
                ],
            )

        return None


class DiscreteNumericDetector(BaseSemanticDetector):
    name = "discrete_numeric_detector"

    def detect(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> SemanticPrediction | None:
        if not pd.api.types.is_numeric_dtype(series):
            return None

        non_null = series.dropna()

        if non_null.empty:
            return None

        unique_count = non_null.nunique()

        if pd.api.types.is_integer_dtype(non_null) and unique_count <= 20:
            return SemanticPrediction(
                semantic_type="discrete_numeric",
                confidence=0.82,
                detector=self.name,
                evidence=[
                    "Column is integer numeric",
                    f"Unique count is {unique_count}, suggesting discrete values",
                ],
            )

        return None