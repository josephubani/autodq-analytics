class ConsoleMLReadinessRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Machine Learning Readiness ===\n")

        if report is None:
            print("No ML readiness report available.")
            return

        print(f"Readiness Score: {report.score}/100")
        print(f"Readiness Level: {report.readiness_level.replace('_', ' ').title()}")
        print(
            "Score Calculation: "
            f"{report.earned_points:.2f} / {report.assessed_points:.2f} "
            f"assessed points x 100"
        )
        print(f"Assessment Coverage: {report.assessment_coverage:.2f}%")
        print(f"Target: {report.target}")
        print(f"Target Type: {report.target_type}")
        print(f"Recommended Task: {report.recommended_task}")

        print("\nComponent Breakdown:")
        for component in report.components:
            points = (
                f"{component.score:.2f}/{component.max_score:.0f}"
                if component.assessed
                else f"not assessed/{component.max_score:.0f}"
            )
            print(
                f"- {component.name}: {points} "
                f"[{component.status.replace('_', ' ').upper()}]"
            )
            print(f"  Calculation: {component.summary}")
            for deduction in component.deductions:
                print(f"  Deduction: {deduction}")
            if component.recommendation:
                print(f"  Recommendation: {component.recommendation}")

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
