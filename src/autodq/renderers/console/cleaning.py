class ConsoleCleaningRenderer:

    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Cleaning Report ===\n")

        print(f"Actions processed: {report.action_count}")
        print(f"Successful actions: {report.successful_actions}")

        for action in report.actions:
            print(f"\nAction {action.action_id}: {action.issue_type}")
            print(f"  Strategy: {action.strategy}")
            print(f"  Status: {action.status}")
            print(f"  Message: {action.message}")

            if action.affected_columns:
                print(f"  Affected Columns: {', '.join(action.affected_columns)}")

            if action.rows_before is not None and action.rows_after is not None:
                print(f"  Rows before: {action.rows_before}")
                print(f"  Rows after: {action.rows_after}")