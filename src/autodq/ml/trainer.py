from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


class ModelTrainer:
    """
    Builds sklearn model pipelines.
    """

    def build_model(
        self,
        problem_type: str,
        algorithm: str,
        preprocessor,
    ):
        scale_numeric = False

        if algorithm == "linear_regression":
            model = LinearRegression()
            scale_numeric = True

        elif algorithm == "logistic_regression":
            model = LogisticRegression(max_iter=1000)
            scale_numeric = True

        elif algorithm == "decision_tree_regressor":
            model = DecisionTreeRegressor(random_state=42)

        elif algorithm == "decision_tree_classifier":
            model = DecisionTreeClassifier(random_state=42)

        elif algorithm == "random_forest_regressor":
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,
            )

        elif algorithm == "random_forest_classifier":
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,
            )

        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", model),
            ]
        )

        return pipeline, scale_numeric