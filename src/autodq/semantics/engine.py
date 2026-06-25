import pandas as pd

from autodq.semantics.prediction import SemanticPrediction
from autodq.semantics.registry import get_default_detectors


class SemanticEngine:
    """
    Coordinates semantic type inference across all registered detectors.
    """

    def __init__(self, detectors=None):
        self.detectors = detectors or get_default_detectors()

    def infer_column(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> dict:
        predictions: list[SemanticPrediction] = []

        for detector in self.detectors:
            prediction = detector.detect(column_name, series, df)

            if prediction is not None:
                predictions.append(prediction)

        if not predictions:
            return {
                "primary_type": "unknown",
                "confidence": 0.0,
                "predictions": [],
            }

        predictions = sorted(predictions, key=lambda p: p.confidence, reverse=True)
        primary = predictions[0]

        return {
            "primary_type": primary.semantic_type,
            "confidence": primary.confidence,
            "predictions": [prediction.to_dict() for prediction in predictions],
        }

    def infer(self, df: pd.DataFrame) -> dict:
        semantic_report = {}

        for column in df.columns:
            semantic_report[column] = self.infer_column(column, df[column], df)

        return semantic_report


def infer_semantic_types(df: pd.DataFrame) -> dict:
    """
    Return simple mapping:
    column_name -> primary semantic type
    """

    engine = SemanticEngine()
    report = engine.infer(df)

    return {
        column: details["primary_type"]
        for column, details in report.items()
    }


def infer_semantic_report(df: pd.DataFrame) -> dict:
    """
    Return full semantic inference details.
    """

    engine = SemanticEngine()
    return engine.infer(df)