class ConsoleDiagnosisRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Data Quality Diagnosis ===")
        print(f"Quality Score: {report.quality_score}/100")
        print(f"Issues found: {report.issue_count}")

        if report.summary:
            print(f"Summary: {report.summary}")

        if not report.has_issues():
            return

        print("\nDetected Issues:")

        for issue in report.issues:
            print(f"\n- [{issue.severity.upper()}] {issue.issue_type}")
            print(f"  Message: {issue.message}")

            if issue.affected_columns:
                print(f"  Affected Columns: {', '.join(issue.affected_columns)}")

            if issue.recommendation:
                print(f"  Recommendation: {issue.recommendation}")

            if issue.confidence is not None:
                print(f"  Confidence: {round(issue.confidence * 100, 2)}%")