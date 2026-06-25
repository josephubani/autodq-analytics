class ConsolePreviewRenderer:
    @staticmethod
    def render(previews: list[dict]) -> None:
        print("\n=== AutoDQ Cleaning Preview ===")

        if not previews:
            print("No previews available.")
            return

        for preview in previews:
            print(f"\nAction {preview['action_id']}: {preview['issue_type']}")
            print(f"Strategy: {preview['strategy']}")
            print("Preview:")

            details = preview["preview"]

            if preview["issue_type"] == "duplicate_rows":
                ConsolePreviewRenderer._render_duplicates(details)

            elif preview["issue_type"] == "missing_values":
                ConsolePreviewRenderer._render_missing(details)

            elif preview["issue_type"] == "outliers":
                ConsolePreviewRenderer._render_outliers(details)

            else:
                print(details)

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