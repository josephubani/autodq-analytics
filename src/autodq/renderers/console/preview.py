class ConsolePreviewRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Cleaning Preview ===")

        if report.action_count == 0:
            print("No previews available.")
            return

        for action in report.actions:
            print(f"\nAction {action.action_id}: {action.issue_type}")
            print(f"Strategy: {action.strategy}")
            print("Preview:")

            if action.issue_type == "duplicate_rows":
                ConsolePreviewRenderer._render_duplicates(action.details)

            elif action.issue_type == "missing_values":
                ConsolePreviewRenderer._render_missing(action.details)

            elif action.issue_type == "outliers":
                ConsolePreviewRenderer._render_outliers(action.details)

            else:
                print(action.details)

    @staticmethod
    def _render_duplicates(details: dict) -> None:
        print(f"  Rows before: {details['rows_before']}")
        print(f"  Rows after: {details['rows_after']}")
        print(f"  Rows removed: {details['rows_removed']}")

    @staticmethod
    def _render_missing(details: dict) -> None:
        for column, info in details.items():
            print(f"  {column}:")
            print(f"    Missing before: {info['missing_before']}")
            print(f"    Suggested action: {info['suggested_action']}")
            print(f"    Sample values: {info['sample_values']}")

    @staticmethod
    def _render_outliers(details: dict) -> None:
        for column, info in details.items():
            print(f"  {column}:")
            print(f"    Outlier count: {info['outlier_count']}")
            print(f"    Lower bound: {info['lower_bound']}")
            print(f"    Upper bound: {info['upper_bound']}")
            print(f"    Sample outliers: {info['sample_outliers']}")
            print(f"    Suggested action: {info['suggested_action']}")