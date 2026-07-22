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
        print(f"Predictions Generated: {report.prediction_count}")

        if report.uncertainty_available:
            method = report.uncertainty_method.replace("_", " ").title()
            print(f"Uncertainty Method: {method}")
            print(f"Calibration Rows: {report.calibration_size}")

            if report.problem_type == "regression":
                print(
                    "Interval Confidence: "
                    f"{report.confidence_level:.0%}"
                )

                if report.mean_interval_width is not None:
                    print(
                        "Mean Interval Width: "
                        f"{report.mean_interval_width:.4f}"
                    )

                if report.empirical_coverage is not None:
                    print(
                        "Observed Coverage: "
                        f"{report.empirical_coverage:.2%}"
                    )
            else:
                if report.mean_confidence is not None:
                    print(
                        "Mean Probability Confidence: "
                        f"{report.mean_confidence:.2f}%"
                    )

                print(
                    "Low-Confidence Predictions: "
                    f"{report.low_confidence_count} "
                    f"(< {report.low_confidence_threshold:.0%})"
                )

                calibration_error = report.calibration_metrics.get(
                    "expected_calibration_error"
                )

                if calibration_error is not None:
                    print(
                        "Holdout Calibration Error (ECE): "
                        f"{calibration_error:.4f}"
                    )
        elif report.uncertainty_requested:
            print("Uncertainty: Unavailable for this model")
        else:
            print("Uncertainty: Disabled")

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

                    print(f"Prediction #{prediction.row_id}")
                    print(f"  Actual        : {actual}")
                    print(f"  Predicted     : {predicted}")
                    print(f"  Residual      : {residual}")
                    print(f"  Absolute Error: {abs_error}")
                    print(f"  Percent Error : {percent_error}")

                    if prediction.lower_bound is not None:
                        print(
                            "  Prediction Interval: "
                            f"[{prediction.lower_bound:.4f}, "
                            f"{prediction.upper_bound:.4f}]"
                        )
                        print(
                            "  Interval Width: "
                            f"{prediction.interval_width:.4f}"
                        )

                    if prediction.top_features:
                        print(
                            f"  Most Important Features   : {', '.join(prediction.top_features)}"
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

                    if prediction.uncertainty is not None:
                        print(
                            "  Uncertainty : "
                            f"{prediction.uncertainty}%"
                        )

                    if prediction.prediction_margin is not None:
                        print(
                            "  Probability Margin: "
                            f"{prediction.prediction_margin:.4f}"
                        )

                    if prediction.entropy is not None:
                        print(
                            f"  Entropy     : {prediction.entropy:.4f}"
                        )

                    if prediction.low_confidence is not None:
                        print(
                            "  Low Confidence: "
                            f"{prediction.low_confidence}"
                        )

                    if prediction.class_probabilities:
                        probabilities = ", ".join(
                            f"{label}={value:.2%}"
                            for label, value in (
                                prediction.class_probabilities.items()
                            )
                        )
                        print(f"  Class Probabilities: {probabilities}")

                    if prediction.top_features:
                        print(
                            f"  Top Drivers : {', '.join(prediction.top_features)}"
                        )

                    if prediction.explanation:
                        print(f"  Explanation : {prediction.explanation}")

                    print("-" * 80)
