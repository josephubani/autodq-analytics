class ConsoleRecommendationRenderer:
    @staticmethod
    def render(recommendations: list) -> None:
        print("\n=== AutoDQ Cleaning Recommendations ===")

        if not recommendations:
            print("No cleaning recommendations generated.")
            return

        for index, recommendation in enumerate(recommendations, start=1):
            print(f"\n{index}. {recommendation.issue_type}")
            print(f"   Strategy: {recommendation.strategy}")
            print(f"   Priority: {recommendation.priority}")
            print(f"   Action: {recommendation.action}")
            print(f"   Reason: {recommendation.reason}")

            if recommendation.affected_columns:
                print(f"   Affected Columns: {', '.join(recommendation.affected_columns)}")

            if recommendation.risk:
                print(f"   Risk: {recommendation.risk}")

            if recommendation.confidence is not None:
                print(f"   Confidence: {round(recommendation.confidence * 100, 2)}%")