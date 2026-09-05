import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from autodq import (
    ADQLParser,
    ADQLValidationError,
    ADQLValidator,
    AutoDQ,
    MultiEchelonInventoryEngine,
)


class MultiEchelonInventoryTests(unittest.TestCase):
    @staticmethod
    def _dataset() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "SKU": ["A", "A", "A", "B", "B"],
                "Location": ["DC1", "Store1", "Store2", "DC1", "Store1"],
                "Echelon": ["DC", "Store", "Store", "DC", "Store"],
                "Parent_Location": [None, "DC1", "DC1", None, "DC1"],
                "Snapshot_Date": ["2026-09-01"] * 5,
                "On_Hand": [500, 5, 50, 20, 2],
                "On_Order": [0, 0, 0, 0, 0],
                "Backorders": [0, 0, 0, 0, 3],
                "Daily_Demand": [5, 10, 2, 1, 4],
                "Lead_Time_Days": [7, 2, 2, 7, 3],
                "Safety_Stock": [20, 10, 5, 5, 5],
                "Unit_Cost": [4, 4, 4, 8, 8],
                "Storage_Capacity": [1000, 300, 300, 500, 200],
            }
        )

    def test_engine_recognizes_network_and_calculates_inventory_position(self):
        report = MultiEchelonInventoryEngine().analyze(
            self._dataset(),
            dataset_name="stock",
            horizon_days=14,
            service_level=95,
        )

        self.assertTrue(report.detection.is_inventory)
        self.assertTrue(report.detection.is_multi_echelon)
        self.assertEqual(report.detection.dataset_type, "multi_echelon_inventory")
        self.assertEqual(report.service_level, 0.95)
        self.assertEqual(report.node_count, 5)
        self.assertEqual({item.echelon for item in report.echelons}, {"DC", "Store"})

        store_b = next(
            item for item in report.nodes
            if item.item == "B" and item.location == "Store1"
        )
        self.assertEqual(store_b.inventory_position, -1)
        self.assertEqual(store_b.status, "critical")
        self.assertGreater(store_b.shortage_units, 0)

    def test_rebalancing_never_mixes_items_or_exceeds_donor_excess(self):
        report = MultiEchelonInventoryEngine().analyze(
            self._dataset(),
            horizon_days=14,
            top=20,
        )
        transfers = [
            item for item in report.recommendations if item.action == "transfer"
        ]
        replenishments = [
            item for item in report.recommendations if item.action == "replenish"
        ]

        self.assertTrue(
            any(
                item.item == "A"
                and item.source_location == "DC1"
                and item.target_location == "Store1"
                for item in transfers
            )
        )
        self.assertTrue(
            any(item.item == "B" and item.target_location == "Store1" for item in replenishments)
        )
        for transfer in transfers:
            donor = next(
                item for item in report.nodes
                if item.item == transfer.item
                and item.location == transfer.source_location
            )
            self.assertLessEqual(transfer.quantity, donor.excess_units)

    def test_latest_snapshot_is_used_per_item_location_node(self):
        data = self._dataset()
        old = data.iloc[[0]].copy()
        old["Snapshot_Date"] = "2026-08-01"
        old["On_Hand"] = 9999
        report = MultiEchelonInventoryEngine().analyze(
            pd.concat([old, data], ignore_index=True),
            horizon_days=14,
        )

        dc_a = next(
            item for item in report.nodes
            if item.item == "A" and item.location == "DC1"
        )
        self.assertEqual(dc_a.on_hand, 500)
        self.assertEqual(report.snapshot_rows, 5)
        self.assertTrue(report.snapshot_at.startswith("2026-09-01"))

    def test_missing_required_roles_returns_diagnostic_without_fake_nodes(self):
        report = MultiEchelonInventoryEngine().analyze(
            pd.DataFrame({"SKU": ["A"], "Warehouse": ["DC1"]})
        )
        self.assertFalse(report.detection.is_inventory)
        self.assertEqual(report.node_count, 0)
        self.assertTrue(
            any("ON_HAND" in item and "DEMAND" in item for item in report.detection.warnings)
        )

    def test_adql_inventory_commands_support_named_data_and_mixed_case(self):
        source = """
        iNvEnToRy DaTaSeT stock ITEM SKU LOCATION Location ECHELON Echelon
            PARENT Parent_Location ON_HAND On_Hand ON_ORDER On_Order
            BACKORDER Backorders DEMAND Daily_Demand LEAD_TIME Lead_Time_Days
            SAFETY_STOCK Safety_Stock UNIT_COST Unit_Cost
            SERVICE_LEVEL 95 HORIZON 14 TOP 20;
        InVeNtOrY DaTaSeT stock NeTwOrK HORIZON 14;
        INVENTORY DATASET stock REBALANCE HORIZON 14 TOP 20;
        """
        script = ADQLParser().parse(source)
        ADQLValidator().validate(script)
        self.assertEqual([item.kind for item in script.statements], ["INVENTORY"] * 3)
        self.assertEqual(script.statements[1].parameters["action"], "network")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stock.csv"
            self._dataset().to_csv(path, index=False)
            project = AutoDQ(path)
            project.add_dataset("stock", dataset_path=path)
            run = project.query(source, auto_display=False)

            self.assertTrue(run.success)
            self.assertIs(project.state.inventory_report, run.results[-1].value.report)
            self.assertEqual(run.results[0].value.section, "overview")
            self.assertEqual(run.results[1].value.section, "network")
            self.assertEqual(run.results[2].value.section, "rebalancing")

    def test_inventory_validation_rejects_invalid_policy_options(self):
        for source in (
            "INVENTORY SERVICE_LEVEL 0;",
            "INVENTORY SERVICE_LEVEL 101;",
            "INVENTORY HORIZON 0;",
            "INVENTORY TOP 101;",
        ):
            with self.subTest(source=source):
                with self.assertRaises(ADQLValidationError):
                    ADQLValidator().validate(ADQLParser().parse(source))

    def test_inventory_is_in_reports_and_dashboards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "stock.csv"
            self._dataset().to_csv(path, index=False)
            project = AutoDQ(path)
            project.load()
            report = project.inventory(horizon_days=14, top=20)
            dashboard = project.dashboard(
                include_charts=False,
                include_data_preview=False,
                auto_display=False,
            )
            complete = project.reporting_engine.build_report(
                state=project.state,
                session=project.session,
                output_dir=root / "assets",
            )
            json_path = root / "report.json"
            project.reporting_engine.export(complete, str(json_path))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            html = dashboard.to_html()

        self.assertEqual(payload["inventory"]["node_count"], report.node_count)
        self.assertIsNotNone(dashboard.inventory)
        self.assertIn("Multi-echelon inventory", html)
        self.assertIn("Priority inventory actions", html)


if __name__ == "__main__":
    unittest.main()
