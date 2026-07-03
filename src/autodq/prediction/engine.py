from pathlib import Path

import pandas as pd

from autodq.io.loaders import load_dataset
from autodq.prediction.models import PredictionReport, PredictionResult


class PredictionEngine:
    """
    Generates predictions from a trained AutoDQ model report.
    """

    def predict(
        self,
        model_report,
        data=None,
        target: str | None = None,
    ) -> tuple[pd.DataFrame, PredictionReport]:
        if model_report is None:
            raise ValueError("No trained model available. Run project.model() first.")

        if data is None:
            raise ValueError("Prediction data is required.")

        if isinstance(data, (str, Path)):
            df = load_dataset(data)
        else:
            df = data.copy()

        pipeline = model_report.model_object

        if pipeline is None:
            raise ValueError("Model object is missing from the model report.")

        actual_values = None

        if target and target in df.columns:
            actual_values = df[target].copy()
            X = df.drop(columns=[target])
        else:
            X = df.copy()

        predictions = pipeline.predict(X)

        output_df = df.copy()
        output_df["AutoDQ_Prediction"] = predictions

        results: list[PredictionResult] = []

        for index, predicted in enumerate(predictions):
            actual = None
            residual = None
            absolute_error = None
            percent_error = None

            if actual_values is not None:
                actual = actual_values.iloc[index]

                if model_report.problem_type == "regression":
                    residual = round(float(actual - predicted), 4)
                    absolute_error = round(abs(float(actual - predicted)), 4)

                    if actual != 0:
                        percent_error = round((absolute_error / abs(float(actual))) * 100, 4)

            results.append(
                PredictionResult(
                    row_id=index,
                    actual=actual,
                    predicted=predicted,
                    residual=residual,
                    absolute_error=absolute_error,
                    percent_error=percent_error,
                )
            )

        report = PredictionReport(
            target=model_report.target,
            problem_type=model_report.problem_type,
            algorithm=model_report.algorithm,
            predictions=results[:100],
            warnings=[],
        )

        return output_df, report