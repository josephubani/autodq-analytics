class ConsoleInventoryRenderer:
    @staticmethod
    def render(value) -> None:
        report = getattr(value, "report", value)
        section = getattr(value, "section", "overview")
        print(f"\n=== AutoDQ Inventory {section.replace('_', ' ').title()} ===\n")
        if report is None:
            print("No inventory analytics report available.")
            return

        if section == "overview":
            detection = report.detection
            print(f"Dataset Type: {detection.dataset_type.replace('_', ' ').title()}")
            print(f"Inventory Confidence: {detection.confidence * 100:.1f}%")
            print(f"Network Nodes: {report.node_count:,}")
            for item in report.kpis:
                print(f"- {item.name}: {item.value} {item.unit} [{item.status.upper()}]")
            if detection.warnings:
                print("Inventory Notes:")
                for warning in detection.warnings:
                    print(f"- {warning}")
            return

        if section == "network":
            if not report.echelons:
                print("No inventory network could be calculated.")
            for item in report.echelons:
                print(
                    f"- {item.echelon}: {item.node_count:,} nodes, "
                    f"{item.shortage_units:g} shortage units, "
                    f"{item.excess_units:g} excess units"
                )
            return

        if section == "rebalancing":
            if not report.recommendations:
                print("No transfer or replenishment action is currently required.")
            for item in report.recommendations:
                source = item.source_location or "external supply"
                print(
                    f"- [{item.priority.upper()}] {item.action.title()} "
                    f"{item.quantity:g} {item.item}: {source} -> "
                    f"{item.target_location}"
                )
