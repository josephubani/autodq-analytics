class ConsoleFeatureRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Feature Engineering Recommendations ===\n")

        if report is None or not report.recommendations:
            print("No feature recommendations available.")
            return

        print(f"Recommendations: {report.recommendation_count}")

        for index, recommendation in enumerate(report.recommendations, start=1):
            print(f"\n{index}. {recommendation.feature_name}")
            print(f"   Type: {recommendation.feature_type}")
            print(f"   Priority: {recommendation.priority}")
            print(f"   Source Columns: {', '.join(recommendation.source_columns)}")
            print(f"   Formula: {recommendation.formula}")
            print(f"   Executable: {recommendation.executable}")
            print(f"   Reason: {recommendation.reason}")
            print(f"   Confidence: {round(recommendation.confidence * 100, 2)}%")