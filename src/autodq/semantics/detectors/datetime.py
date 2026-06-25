import pandas as pd

from autodq.semantics.base import BaseSemanticDetector
from autodq.semantics.prediction import SemanticPrediction


class DateTimeDetector(BaseSemanticDetector):
    name = "datetime_detector"

    DATE_KEYWORDS = ["date", "time", "timestamp", "month", "year"]

    def detect(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> SemanticPrediction | None:
        column_lower = column_name.lower()
        evidence = []

        if pd.api.types.is_datetime64_any_dtype(series):
            return SemanticPrediction(
                semantic_type="datetime",
                confidence=0.98,
                detector=self.name,
                evidence=["Column already has datetime dtype"],
            )

        if not pd.api.types.is_object_dtype(series):
            return None

        parsed = pd.to_datetime(series.dropna(), errors="coerce")
        success_rate = parsed.notna().mean() if len(parsed) > 0 else 0

        if success_rate >= 0.8:
            evidence.append(f"Datetime parsing success rate is {round(success_rate, 2)}")

            if any(keyword in column_lower for keyword in self.DATE_KEYWORDS):
                evidence.append("Column name suggests date/time")
                confidence = 0.97
            else:
                confidence = 0.88

            return SemanticPrediction(
                semantic_type="datetime",
                confidence=confidence,
                detector=self.name,
                evidence=evidence,
            )

        return None