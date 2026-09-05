import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import (
    ADQLParser,
    ADQLSyntaxError,
    ADQLValidationError,
    ADQLValidator,
    AutoDQ,
    OperationalAnalyticsEngine,
)
from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class OperationalAnalyticsTests(unittest.TestCase):
    @staticmethod
    def _dataset(rows: int = 120) -> pd.DataFrame:
        created = pd.date_range("2026-01-01", periods=rows, freq="h")
        team = np.where(np.arange(rows) < 80, "Team A", "Team B")
        duration = np.where(
            team == "Team A",
            2 + np.arange(rows) % 3,
            12 + np.arange(rows) % 9,
        )
        failed = (team == "Team B") & (np.arange(rows) % 2 == 0)
        return pd.DataFrame(
            {
                "Order_ID": [f"ORD-{index:04d}" for index in range(rows)],
                "Created_At": created,
                "Completed_At": created + pd.to_timedelta(duration, unit="h"),
                "Status": np.where(failed, "failed", "completed"),
                "Stage": np.where(np.arange(rows) % 2, "shipping", "packing"),
                "Team": team,
                "Region": np.where(np.arange(rows) % 2, "East", "West"),
                "Revenue": 100 + np.arange(rows) * 2.0,
                "Cost": 60 + np.arange(rows) * 1.1,
                "Units": 1 + np.arange(rows) % 5,
                "Capacity": np.full(rows, 10),
            }
        )

    def test_engine_recognizes_operations_and_derives_elapsed_hours(self):
        report = OperationalAnalyticsEngine().analyze(
            self._dataset(),
            dataset_name="orders",
            sla_target=8,
            period="day",
        )

        self.assertTrue(report.detection.is_operational)
        self.assertGreaterEqual(report.detection.confidence, 0.8)
        self.assertEqual(report.detection.columns.start, "Created_At")
        self.assertEqual(report.detection.columns.end, "Completed_At")
        self.assertEqual(report.detection.columns.duration_unit, "hours")
        self.assertEqual(report.dataset_name, "orders")
        self.assertGreater(len(report.trends), 0)
        self.assertGreater(len(report.process_segments), 0)

        kpis = {item.key: item for item in report.kpis}
        self.assertIn("throughput_per_day", kpis)
        self.assertIn("average_cycle_time", kpis)
        self.assertIn("sla_breach_rate", kpis)
        self.assertIn("failure_rate", kpis)
        self.assertIn("capacity_utilization", kpis)

    def test_bottlenecks_and_root_causes_surface_slow_team(self):
        report = OperationalAnalyticsEngine().analyze(
            self._dataset(),
            group_by=["Team", "Region"],
            start_column="Created_At",
            end_column="Completed_At",
            status_column="Status",
            sla_target=8,
            top=10,
        )

        self.assertTrue(
            any(
                item.dimension == "Team" and item.segment == "Team B"
                for item in report.bottlenecks
            )
        )
        self.assertTrue(
            any(
                item.feature == "Team" and item.segment == "Team B"
                for item in report.root_causes
            )
        )
        self.assertIn("associations", report.view("root_causes").to_dict()["association_warning"])
        self.assertIn("Operational Bottlenecks", report.view("bottlenecks").to_notebook_html())

    def test_explicit_roles_are_case_insensitive_and_unknown_columns_fail(self):
        data = self._dataset()
        report = OperationalAnalyticsEngine().analyze(
            data,
            entity_column="order_id",
            start_column="created_at",
            end_column="completed_at",
            group_by="team",
        )
        self.assertEqual(report.detection.columns.entity, "Order_ID")
        self.assertEqual(report.detection.columns.group_by, ["Team"])

        with self.assertRaisesRegex(ValueError, "does not exist"):
            OperationalAnalyticsEngine().analyze(
                data,
                duration_column="Unknown_Duration",
            )

    def test_adql_operational_commands_support_named_datasets_and_mixed_case(self):
        parser = ADQLParser()
        source = """
        oPeRaTiOnS DaTaSeT operations SLA 8 PERIOD day TOP 5;
        kPi DaTaSeT operations SLA 8;
        pRoCeSs DaTaSeT operations START Created_At END Completed_At
            STATUS Status STAGE Stage PERIOD day;
        bOtTlEnEcKs DaTaSeT operations GROUP Team SLA 8 TOP 5;
        rOoT cAuSe DaTaSeT operations GROUP_BY Team,Region TOP 5;
        """
        script = parser.parse(source)
        ADQLValidator().validate(script)
        self.assertEqual(
            [item.kind for item in script.statements],
            ["OPERATIONS", "KPI", "PROCESS", "BOTTLENECKS", "ROOT"],
        )
        self.assertEqual(script.statements[-1].parameters["group_by"], ["Team", "Region"])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operations.csv"
            self._dataset().to_csv(path, index=False)
            project = AutoDQ(path)
            project.add_dataset("operations", dataset_path=path)
            run = project.query(source, auto_display=False)

        self.assertTrue(run.success)
        self.assertEqual(project.dataset_manager.primary().name, "operations")
        self.assertIn("Recognized", run.results[0].message)
        self.assertIn("operational KPI", run.results[1].message)
        self.assertEqual(run.results[-1].value.section, "root_causes")

    def test_operational_validation_rejects_unsafe_options(self):
        invalid = (
            "OPERATIONS PERIOD quarter;",
            "KPI SLA 0;",
            "BOTTLENECKS TOP 0;",
            "PROCESS START Opened_At;",
            "ROOT;",
        )
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises((ADQLValidationError, ADQLSyntaxError)) as caught:
                    script = ADQLParser().parse(source)
                    ADQLValidator().validate(script)
                self.assertTrue(str(caught.exception))

    def test_operational_results_are_in_json_and_html_reports(self):
        operations = OperationalAnalyticsEngine().analyze(
            self._dataset(),
            dataset_name="orders",
            sla_target=8,
        )
        report = AutoDQReport(
            dataset="orders.csv",
            session=None,
            operations=operations,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "report.json"
            JSONExporter().export(report, json_path)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markup = HTMLExporter()._build_html(report)

        self.assertEqual(payload["operations"]["dataset_name"], "orders")
        self.assertGreater(payload["operations"]["kpi_count"], 0)
        self.assertIn("Operational Analytics", markup)
        self.assertIn("Operational Root-Cause Signals", markup)

    def test_dashboard_reuses_operational_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.csv"
            self._dataset().to_csv(path, index=False)
            project = AutoDQ(path)
            project.load()
            project.operations(sla_target=8)
            dashboard = project.dashboard(
                include_charts=False,
                include_data_preview=False,
                auto_display=False,
            )
            markup = dashboard.to_html()

        self.assertIsNotNone(dashboard.operations)
        self.assertIn("Operational analytics", markup)
        self.assertIn("Bottlenecks", markup)
        self.assertIn("confidence", markup)


if __name__ == "__main__":
    unittest.main()
