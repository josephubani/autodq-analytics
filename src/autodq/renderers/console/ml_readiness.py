class ConsoleMLReadinessRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Machine Learning Readiness ===\n")

        if report is None:
            print("No ML readiness report available.")
            return

        print(f"Readiness Score: {report.score}/100")
        print(f"Target: {report.target}")
        print(f"Target Type: {report.target_type}")
        print(f"Recommended Task: {report.recommended_task}")

        print("\nRecommended Models:")
        for model in report.recommended_models:
            print(f"- {model}")

        if report.strengths:
            print("\nStrengths:")
            for strength in report.strengths:
                print(f"- {strength}")

        if report.issues:
            print("\nReadiness Issues:")
            for issue in report.issues:
                print(f"\n- [{issue.severity.upper()}] {issue.issue_type}")
                print(f"  Message: {issue.message}")
                print(f"  Recommendation: {issue.recommendation}")
                print(f"  Confidence: {round(issue.confidence * 100, 2)}%")