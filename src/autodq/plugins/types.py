from enum import Enum


class PluginType(str, Enum):
    SEMANTIC_DETECTOR = "semantic_detector"
    DIAGNOSIS_ANALYZER = "diagnosis_analyzer"
    CLEANING_STRATEGY = "cleaning_strategy"
    VISUALIZATION_RECOMMENDER = "visualization_recommender"
    MODEL_RECOMMENDER = "model_recommender"