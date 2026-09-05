class ConsoleOperationsRenderer:
    @staticmethod
    def render(value) -> None:
        report = getattr(value, "report", value)
        section = getattr(value, "section", "overview")
        print(f"\n=== AutoDQ {section.replace('_', ' ').title()} ===\n")
        if report is None:
            print("No operational analytics report available.")
            return

        if section == "overview":
            detection = report.detection
            print(f"Dataset Type: {detection.dataset_type.replace('_', ' ').title()}")
            print(f"Operational Confidence: {detection.confidence * 100:.1f}%")
            print(f"Rows Analyzed: {report.rows_analyzed:,}")
            print("Recognized Columns:")
            for role, column in detection.columns.to_dict().items():
                if column not in (None, [], "units"):
                    print(f"- {role.replace('_', ' ').title()}: {column}")
            if detection.warnings:
                print("Inference Notes:")
                for warning in detection.warnings:
                    print(f"- {warning}")
            return

        if section == "kpis":
            for item in report.kpis:
                print(f"- {item.name}: {item.value} {item.unit} [{item.status.upper()}]")
            return

        if section == "process":
            if not report.process_segments:
                print("No process stages or statuses were available.")
            for item in report.process_segments:
                print(
                    f"- {item.dimension}={item.segment}: {item.records:,} records "
                    f"({item.share_percent:.1f}%), average duration "
                    f"{item.average_duration}"
                )
            print(f"Time Trend Periods: {len(report.trends)}")
            return

        if section == "bottlenecks":
            if not report.bottlenecks:
                print("No material bottlenecks detected.")
            for item in report.bottlenecks:
                print(
                    f"- [{item.severity.upper()}] {item.dimension}={item.segment} "
                    f"(score {item.score}): {item.evidence}"
                )
            return

        if section == "root_causes":
            print("These signals are associations, not proof of causation.")
            if not report.root_causes:
                print("No sufficiently strong operational drivers detected.")
            for item in report.root_causes:
                print(f"- {item.feature}: {item.evidence}")
