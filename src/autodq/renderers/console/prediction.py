class ConsolePredictionRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Prediction Report ===\n")

        if report is None:
            print("No prediction report available.")
            return

        print(f"Target: {report.target}")
        print(f"Problem Type: {report.problem_type}")
        print(f"Algorithm: {report.algorithm}")
        print(f"Predictions Stored: {report.prediction_count}")

        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"- {warning}")

        if report.predictions:
            print("\nSample Predictions:")

            for prediction in report.predictions[:15]:
                if report.problem_type == "regression":
                    print(
                        f"  Row {prediction.row_id} | "
                        f"Actual: {prediction.actual} | "
                        f"Predicted: {round(prediction.predicted, 4)} | "
                        f"Residual: {prediction.residual} | "
                        f"Abs Error: {prediction.absolute_error}"
                    )
                else:
                    print(
                        f"  Row {prediction.row_id} | "
                        f"Actual: {prediction.actual} | "
                        f"Predicted: {prediction.predicted}"
                    )