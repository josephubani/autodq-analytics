class ConsoleValidationRenderer:

    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Post-Cleaning Validation ===\n")

        print("Data Quality Impact:")
        print(f"  Quality Score Before: {report.quality_score_before}/100")
        print(f"  Quality Score After: {report.quality_score_after}/100")
        print(f"  Quality Score Change: {report.quality_score_change}")

        print("\nMetric Changes:")

        for metric in [
            report.missing_values,
            report.duplicate_rows,
            report.rows,
            report.columns,
        ]:
            print(f"\n{metric.name}")
            print(f"  Before: {metric.before}")
            print(f"  After: {metric.after}")
            print(f"  Change: {metric.change}")