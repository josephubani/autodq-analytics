from abc import ABC, abstractmethod

import pandas as pd

from autodq.semantics.prediction import SemanticPrediction


class BaseSemanticDetector(ABC):
    name: str = "base_detector"

    @abstractmethod
    def detect(self, column_name: str, series: pd.Series, df: pd.DataFrame) -> SemanticPrediction | None:
        """
        Return a SemanticPrediction if the detector identifies a semantic type.
        Otherwise, return None.
        """
        pass