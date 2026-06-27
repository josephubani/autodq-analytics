class ConsoleVisualizationRenderer:
    @staticmethod
    def render(report) -> None:
        print("\n=== AutoDQ Visualizations ===\n")

        if report.chart_count == 0:
            print("No visualizations generated.")
            return

        print(f"Charts generated: {report.chart_count}")

        for chart in report.charts:
            print(f"\n- {chart.title}")
            print(f"  ID: {chart.chart_id}")
            print(f"  Type: {chart.chart_type}")
            print(f"  Stage: {chart.stage}")
            print(f"  X: {chart.x}")
            print(f"  Y: {chart.y}")
            print(f"  Recommended: {chart.recommended}")
            print(f"  Data points: {len(chart.data)}")
            print(f"  Description: {chart.description}")