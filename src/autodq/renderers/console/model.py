from autodq.utils.ml_formatting import pretty_algorithm_name
class ConsoleModelRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Model Report ===\n")

        if report is None:
            print("No model report available.")
            return

        print(f"Target: {report.target}")
        print(f"Problem Type: {report.problem_type}")
        print(f"Algorithm: {pretty_algorithm_name(report.algorithm)}")
        print(f"Features Used: {report.feature_count}")
        print(f"Predictions Stored: {report.prediction_count}")

        print("\nMetrics:")

        if report.problem_type == "regression":
            print(f"  MAE: {report.metrics.mae}")
            print(f"  RMSE: {report.metrics.rmse}")
            print(f"  R²: {report.metrics.r2}")
        else:
            print(f"  Accuracy: {report.metrics.accuracy}")
            print(f"  Precision: {report.metrics.precision}")
            print(f"  Recall: {report.metrics.recall}")
            print(f"  F1: {report.metrics.f1}")
            
        if report.model_comparison:
            print("\nModel Comparison:")

            for item in report.model_comparison:
                print(
                    f"  {item.rank}. {item.algorithm} | "
                    f"{item.primary_metric}: {item.primary_score}"
                )

        if report.feature_importance:
            print("\nTop Feature Importance:")

            for item in report.feature_importance[:15]:
                print(f"  {item.rank}. {item.feature}: {item.importance}")

        if report.recommendations:
            print("\nRecommendations:")

            for recommendation in report.recommendations:
                print(f"- {recommendation}")

        if report.predictions:
            print("\nSample Predictions:")

            for prediction in report.predictions[:10]:
                if report.problem_type == "regression":
                    print(
                        f"  Actual: {prediction.actual} | "
                        f"Predicted: {round(prediction.predicted, 4)} | "
                        f"Residual: {prediction.residual}"
                    )
                else:
                    print(
                        f"  Actual: {prediction.actual} | "
                        f"Predicted: {prediction.predicted}"
                    )