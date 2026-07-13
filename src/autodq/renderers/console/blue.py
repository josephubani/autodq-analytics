class ConsoleBLUERenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ BLUE Diagnostics ===\n")

        if report is None:
            print("No BLUE report available.")
            return

        print(f"Target: {report.target}")
        print(f"Rows Analyzed: {report.rows_analyzed}")
        print(f"Features Analyzed: {report.features_analyzed}")
        if report.features_used:
            print(
                "Features Used: "
                + ", ".join(report.features_used)
            )

        if report.excluded_features:
            print(
                "Excluded Features: "
                + ", ".join(report.excluded_features)
            )
        print(f"Suitability Score: {report.suitability_score}/100")
        print(f"Overall Status: {report.overall_status}")

        print("\nAssumption Results:")

        for result in report.assumptions:
            print(
                f"\n- {result.assumption}"
            )
            print(
                f"  Status: {result.status}"
            )

            if result.statistic is not None:
                print(
                    f"  Statistic: {result.statistic}"
                )

            if result.p_value is not None:
                print(
                    f"  P-value: {result.p_value}"
                )

            print(
                f"  Interpretation: {result.interpretation}"
            )
            print(
                f"  Recommendation: {result.recommendation}"
            )
            print(
                f"  Confidence: {round(result.confidence * 100, 2)}%"
            )

        if report.vif_results:
            print("\nVariance Inflation Factors:")

            for result in report.vif_results[:15]:
                print(
                    f"  {result.feature}: "
                    f"{result.vif} "
                    f"[{result.severity.upper()}]"
                )

        if report.recommendations:
            print("\nRecommendations:")

            for recommendation in report.recommendations:
                print(
                    f"- {recommendation}"
                )

        if report.warnings:
            print("\nWarnings:")

            for warning in report.warnings:
                print(
                    f"- {warning}"
                )