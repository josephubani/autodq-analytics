class ConsoleInterpretationRenderer:

    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Statistical Interpretations ===\n")

        if report.insight_count == 0:
            print("No major statistical interpretations generated.")
            return

        for column, insights in report.interpretations.items():
            print(column)

            for insight in insights:
                print(f"  Insight: {insight.insight_type}")
                print(f"  Severity: {insight.severity}")
                print(f"  Message: {insight.message}")

                if insight.evidence:
                    print("  Evidence:")
                    for item in insight.evidence:
                        print(f"    - {item}")

                if insight.downstream_implications:
                    print("  Downstream Implications:")
                    for item in insight.downstream_implications:
                        print(f"    - {item}")

                print(f"  Confidence: {round(insight.confidence * 100, 2)}%")
                print()