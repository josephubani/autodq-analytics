from autodq.utils.ml_formatting import pretty_algorithm_name
class ConsolePredictionRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Prediction Report ===\n")

        if report is None:
            print("No prediction report available.")
            return

        print(f"Target: {report.target}")
        print(f"Problem Type: {report.problem_type}")
        print(f"Algorithm: {pretty_algorithm_name(report.algorithm)}")
        print(f"Predictions Stored: {report.prediction_count}")

        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"- {warning}")

        if report.predictions:
            print("\nSample Predictions:\n")

            for prediction in report.predictions[:15]:

                if report.problem_type == "regression":

                    predicted = (
                        round(float(prediction.predicted), 4)
                        if prediction.predicted is not None
                        else "N/A"
                    )

                    actual = (
                        round(float(prediction.actual), 4)
                        if prediction.actual is not None
                        else "N/A"
                    )

                    residual = (
                        round(float(prediction.residual), 4)
                        if prediction.residual is not None
                        else "N/A"
                    )

                    abs_error = (
                        round(float(prediction.absolute_error), 4)
                        if prediction.absolute_error is not None
                        else "N/A"
                    )

                    percent_error = (
                        f"{round(float(prediction.percent_error), 2)}%"
                        if prediction.percent_error is not None
                        else "N/A"
                    )

                    confidence = (
                        f"{prediction.confidence}%"
                        if prediction.confidence is not None
                        else "N/A"
                    )

                    print(f"Prediction #{prediction.row_id}")
                    print(f"  Actual        : {actual}")
                    print(f"  Predicted     : {predicted}")
                    print(f"  Residual      : {residual}")
                    print(f"  Absolute Error: {abs_error}")
                    print(f"  Percent Error : {percent_error}")
                    print(f"  Confidence    : {confidence}")

                    if prediction.top_features:
                        print(
                            f"  Top Drivers   : {', '.join(prediction.top_features)}"
                        )

                    if prediction.explanation:
                        print(f"  Explanation   : {prediction.explanation}")

                    print("-" * 80)

                else:

                    confidence = (
                        f"{prediction.confidence}%"
                        if prediction.confidence is not None
                        else "N/A"
                    )

                    print(f"Prediction #{prediction.row_id}")
                    print(f"  Actual      : {prediction.actual}")
                    print(f"  Predicted   : {prediction.predicted}")
                    print(f"  Confidence  : {confidence}")

                    if prediction.top_features:
                        print(
                            f"  Top Drivers : {', '.join(prediction.top_features)}"
                        )

                    if prediction.explanation:
                        print(f"  Explanation : {prediction.explanation}")

                    print("-" * 80)