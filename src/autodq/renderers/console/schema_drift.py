class ConsoleSchemaRenderer:
    @staticmethod
    def render_contract(contract) -> None:
        if contract is None:
            print("\nNo schema contract available.")
            return
        print(f"\n=== Schema Contract: {contract.name} ===")
        print(f"Version: {contract.contract_version}")
        print(f"Source dataset: {contract.dataset}")
        print(f"Columns: {contract.column_count} | Rules: {contract.rule_count}")
        print(f"Unexpected columns: {contract.extra_columns}")
        print(contract.to_frame().to_string(index=False))

    @staticmethod
    def render_validation(report) -> None:
        if report is None:
            print("\nNo schema validation report available.")
            return
        print("\n=== Schema Contract Validation ===")
        print(f"Contract: {report.contract_name} {report.contract_version}")
        print(f"Dataset: {report.dataset}")
        print(
            f"Status: {'PASSED' if report.success else 'FAILED'} | "
            f"Passed: {report.passed_count}/{report.test_count} | "
            f"Blocking failures: {report.blocking_failure_count}"
        )
        print(report.to_frame().to_string(index=False))


class ConsoleDriftRenderer:
    @staticmethod
    def render_baseline(baseline) -> None:
        if baseline is None:
            print("\nNo drift baseline available.")
            return
        print(f"\n=== Drift Baseline: {baseline.name} ===")
        print(f"Dataset: {baseline.dataset}")
        print(f"Rows: {baseline.row_count:,} | Columns: {baseline.column_count:,}")
        print(f"Duplicate rate: {baseline.duplicate_percent:.2f}%")
        print(baseline.to_frame().to_string(index=False))

    @staticmethod
    def render(report) -> None:
        if report is None:
            print("\nNo drift report available.")
            return
        print("\n=== AutoDQ Schema and Data Drift ===")
        print(f"Dataset: {report.dataset}")
        print(
            f"Reference: {report.baseline_name} ({report.baseline_dataset})"
        )
        print(f"Stability score: {report.stability_score:.2f}/100")
        print(
            f"Stable: {report.stable_count} | Moderate: {report.moderate_count} | "
            f"Major: {report.major_count} | "
            f"Blocking: {report.blocking_failure_count}"
        )
        print(report.to_frame().to_string(index=False))
