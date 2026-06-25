class ConsoleProfileRenderer:
    @staticmethod
    def render(report: dict) -> None:
        print("\n=== AutoDQ Dataset Profile ===")
        print(f"Dataset: {report['dataset_path']}")
        print(f"Rows: {report['rows']}")
        print(f"Columns: {report['columns']}")
        print(f"Duplicate rows: {report['duplicate_rows']}")

        print("\nColumn Groups:")
        print(f"Numeric: {report['numeric_columns']}")
        print(f"Categorical: {report['categorical_columns']}")
        print(f"Datetime: {report['datetime_columns']}")

        print("\nColumns:")
        for col in report["column_names"]:
            dtype = report["data_types"][col]
            semantic = report["semantic_types"].get(col, "unknown")
            missing = report["missing_values"][col]
            missing_pct = report["missing_percentages"][col]

            print(
                f"- {col} | type: {dtype} | semantic: {semantic} | "
                f"missing: {missing} ({missing_pct}%)"
            )