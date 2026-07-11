class ConsoleDatasetRenderer:
    @staticmethod
    def render_datasets(entries) -> None:
        print("\n=== AutoDQ Dataset Registry ===\n")

        if not entries:
            print("No datasets registered.")
            return

        for entry in entries:
            primary = "Yes" if entry.is_primary else "No"

            print(f"Dataset: {entry.name}")
            print(f"  Path: {entry.path or 'In-memory DataFrame'}")
            print(f"  Rows: {entry.rows}")
            print(f"  Columns: {entry.columns}")
            print(f"  Primary: {primary}")
            print()

    @staticmethod
    def render_merge(report) -> None:
        print("\n=== AutoDQ Merge Report ===\n")

        print(f"Left Dataset: {report.left_dataset}")
        print(f"Right Dataset: {report.right_dataset}")
        print(f"Join Type: {report.how}")
        print(f"Join Columns: {', '.join(report.join_columns)}")
        print(f"Detected Relationship: {report.relationship}")

        print("\nRows:")
        print(f"  Left: {report.left_rows}")
        print(f"  Right: {report.right_rows}")
        print(f"  Output: {report.output_rows}")
        print(f"  Change: {report.row_change:+}")
        print(f"  Expanded Rows: {report.expanded_rows}")

        print("\nMatching:")
        print(f"  Matched Left Rows: {report.matched_left_rows}")
        print(f"  Unmatched Left Rows: {report.unmatched_left_rows}")

        print("\nDuplicate Keys:")
        print(f"  Left: {report.duplicate_left_keys}")
        print(f"  Right: {report.duplicate_right_keys}")

        if report.warnings:
            print("\nWarnings:")

            for warning in report.warnings:
                print(f"- {warning}")

    @staticmethod
    def render_concat(report) -> None:
        print("\n=== AutoDQ Concatenation Report ===\n")

        print(f"Datasets: {', '.join(report.datasets)}")
        print(f"Axis: {report.axis}")
        print(f"Input Rows: {report.input_rows}")
        print(f"Output Rows: {report.output_rows}")
        print(f"Input Columns: {report.input_columns}")
        print(f"Output Columns: {report.output_columns}")

        if report.warnings:
            print("\nWarnings:")

            for warning in report.warnings:
                print(f"- {warning}")