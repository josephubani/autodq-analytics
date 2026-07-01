class ConsoleCorrelationRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Correlation Intelligence ===\n")

        if report is None:
            print("No correlation report available.")
            return

        print(f"Relationships found: {report.relationship_count}")
        print(f"Target relationships found: {report.target_relationship_count}")

        if report.target_relationships:
            print("\nTarget Relationships:")

            for relationship in report.target_relationships[:15]:
                print(f"\n- {relationship.feature} → {relationship.target}")
                print(f"  Correlation: {relationship.correlation}")
                print(f"  Strength: {relationship.strength}")
                print(f"  Direction: {relationship.direction}")
                print(f"  Interpretation: {relationship.interpretation}")
                print(f"  Recommendation: {relationship.recommendation}")
                print(f"  Confidence: {round(relationship.confidence * 100, 2)}%")

        if report.relationships:
            print("\nTop Feature Relationships:")

            for relationship in report.relationships[:15]:
                print(f"\n- {relationship.feature_a} ↔ {relationship.feature_b}")
                print(f"  Correlation: {relationship.correlation}")
                print(f"  Strength: {relationship.strength}")
                print(f"  Direction: {relationship.direction}")
                print(f"  Severity: {relationship.severity}")
                print(f"  Interpretation: {relationship.interpretation}")
                print(f"  Recommendation: {relationship.recommendation}")
                print(f"  Confidence: {round(relationship.confidence * 100, 2)}%")