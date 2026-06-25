import pandas as pd

from autodq.semantics.base import BaseSemanticDetector
from autodq.semantics.prediction import SemanticPrediction


class IdentifierDetector(BaseSemanticDetector):
    name = "identifier_detector"

    ID_KEYWORDS = ["id", "identifier", "key"]

    def detect(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> SemanticPrediction | None:
        column_lower = column_name.lower()
        total_rows = len(df)

        if total_rows == 0:
            return None

        unique_ratio = series.nunique(dropna=True) / total_rows
        name_suggests_id = any(keyword in column_lower for keyword in self.ID_KEYWORDS)

        if name_suggests_id and unique_ratio >= 0.85:
            return SemanticPrediction(
                semantic_type="identifier",
                confidence=0.95,
                detector=self.name,
                evidence=[
                    "Column name suggests identifier",
                    f"Unique ratio is {round(unique_ratio, 2)}",
                ],
            )

        return None