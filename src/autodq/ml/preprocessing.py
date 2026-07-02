import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class MLPreprocessor:
    """
    Builds preprocessing pipelines for numeric and categorical features.
    """

    def build(
        self,
        df: pd.DataFrame,
        target: str,
        scale_numeric: bool = False,
    ):
        if target not in df.columns:
            raise ValueError(f"Target column not found: {target}")

        X = df.drop(columns=[target])
        y = df[target]

        numeric_features = list(X.select_dtypes(include="number").columns)
        categorical_features = list(
            X.select_dtypes(include=["object", "category", "string"]).columns
        )

        numeric_steps = [
            ("imputer", SimpleImputer(strategy="median")),
        ]

        if scale_numeric:
            numeric_steps.append(("scaler", StandardScaler()))

        numeric_pipeline = Pipeline(steps=numeric_steps)

        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "encoder",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_pipeline, numeric_features),
                ("cat", categorical_pipeline, categorical_features),
            ],
            remainder="drop",
        )

        return X, y, preprocessor, numeric_features, categorical_features