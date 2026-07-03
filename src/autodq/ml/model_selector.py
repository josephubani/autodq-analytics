import pandas as pd


class ModelSelector:
    """
    Selects ML problem type and model family from target column.
    """

    def detect_problem_type(
        self,
        df: pd.DataFrame,
        target: str,
    ) -> str:
        if target not in df.columns:
            raise ValueError(f"Target column not found: {target}")

        series = df[target].dropna()

        if series.empty:
            return "unknown"

        if pd.api.types.is_numeric_dtype(series):
            unique_count = series.nunique()

            if unique_count <= 10:
                return "classification"

            return "regression"

        return "classification"

    def default_algorithm(
        self,
        problem_type: str,
        algorithm: str | None = None,
    ) -> str:
        if algorithm and algorithm != "auto":
            return algorithm

        if problem_type == "regression":
            return "random_forest_regressor"

        if problem_type == "classification":
            return "random_forest_classifier"

        return "unsupported"
    def candidate_algorithms(self, problem_type: str) -> list[str]:
        if problem_type == "regression":
            return [
                "random_forest_regressor",
                "decision_tree_regressor",
                "linear_regression",
            ]

        if problem_type == "classification":
            return [
                "random_forest_classifier",
                "decision_tree_classifier",
                "logistic_regression",
            ]

        return []