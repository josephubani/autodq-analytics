import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import (
    ADQLParser,
    ADQLValidationError,
    ADQLValidator,
    AutoDQ,
    MultiEchelonInventoryEngine,
    OperationalAnalyticsEngine,
    PrescriptiveAnalyticsEngine,
)


class PrescriptiveAnalyticsTests(unittest.TestCase):
    @staticmethod
    def _operations(rows: int = 120) -> pd.DataFrame:
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
                "Revenue": 100 + np.arange(rows) * 2.0,
                "Cost": 60 + np.arange(rows) * 1.1,
            }
        )

    @staticmethod
    def _inventory() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "SKU": ["A", "A", "A", "B", "B"],
                "Location": ["DC1", "Store1", "Store2", "DC1", "Store1"],
                "Echelon": ["DC", "Store", "Store", "DC", "Store"],
                "Parent_Location": [None, "DC1", "DC1", None, "DC1"],
                "On_Hand": [500, 5, 50, 20, 2],
                "On_Order": [0, 0, 0, 0, 0],
                "Backorders": [0, 0, 0, 0, 3],
                "Daily_Demand": [5, 10, 2, 1, 4],
                "Lead_Time_Days": [7, 2, 2, 7, 3],
                "Safety_Stock": [20, 10, 5, 5, 5],
                "Unit_Cost": [4, 4, 4, 8, 8],
            }
        )

    def test_engine_generates_traceable_actions_and_optimizes_constraints(self):
        operations = OperationalAnalyticsEngine().analyze(
            self._operations(),
            dataset_name="orders",
            group_by="Team",
            start_column="Created_At",
            end_column="Completed_At",
            status_column="Status",
            sla_target=8,
        )
        engine = PrescriptiveAnalyticsEngine()
        plan = engine.generate(
            dataset_name="orders",
            operations_report=operations,
            objective="reduce_delay",
            max_actions=2,
            min_confidence=0.1,
        )

        self.assertGreater(len(plan.actions), 0)
        self.assertLessEqual(len(plan.selected_actions), 2)
        self.assertEqual(plan.objective, "reduce_delay")
        self.assertIn("operations", plan.source_reports)
        self.assertTrue(all(item.action_id.startswith("A") for item in plan.actions))
        self.assertTrue(all(item.rationale for item in plan.actions))
        self.assertTrue(all(item.cost_basis for item in plan.actions))
        self.assertIn(plan.optimization.method, {"scipy_milp", "deterministic_greedy"})
        self.assertIn("Prescriptive Analytics Plan", plan.to_notebook_html())

    def test_inventory_recommendations_become_costed_prescriptions(self):
        inventory = MultiEchelonInventoryEngine().analyze(
            self._inventory(),
            dataset_name="stock",
            horizon_days=14,
            top=20,
        )
        plan = PrescriptiveAnalyticsEngine().generate(
            dataset_name="stock",
            inventory_report=inventory,
            objective="minimize_shortage",
            max_actions=5,
            min_confidence=0.1,
        )

        self.assertIn("inventory", plan.source_reports)
        self.assertTrue(
            any(item.action_type == "inventory_transfer" for item in plan.actions)
        )
        self.assertTrue(
            any(item.action_type == "inventory_replenishment" for item in plan.actions)
        )
        self.assertTrue(
            all(item.expected_impact >= 0 for item in plan.actions)
        )

    def test_what_if_scenario_preserves_baseline_and_projects_kpis(self):
        operations = OperationalAnalyticsEngine().analyze(
            self._operations(),
            dataset_name="orders",
            start_column="Created_At",
            end_column="Completed_At",
            status_column="Status",
            group_by="Team",
        )
        engine = PrescriptiveAnalyticsEngine()
        plan = engine.generate(
            dataset_name="orders",
            operations_report=operations,
            min_confidence=0.1,
        )
        scenario = engine.scenario(
            plan,
            name="Faster service",
            operations_report=operations,
            duration_change=-20,
            failure_change=-10,
            cost_change=5,
        )

        self.assertEqual(scenario.scenario_id, "S001")
        self.assertLess(
            scenario.projected_metrics["average_cycle_time"],
            scenario.baseline_metrics["average_cycle_time"],
        )
        self.assertLess(
            scenario.projected_metrics["failure_rate"],
            scenario.baseline_metrics["failure_rate"],
        )
        self.assertEqual(len(plan.scenarios), 1)

    def test_approval_execution_and_rejection_are_governed_and_audited(self):
        operations = OperationalAnalyticsEngine().analyze(
            self._operations(), dataset_name="orders", group_by="Team"
        )
        engine = PrescriptiveAnalyticsEngine()
        plan = engine.generate(
            dataset_name="orders",
            operations_report=operations,
            min_confidence=0.1,
        )
        selected = plan.selected_actions[0]
        engine.approve(plan, selected.action_id, actor="analyst")
        executed = engine.execute(plan, selected.action_id, actor="manager")

        self.assertEqual(executed.status, "executed")
        self.assertEqual(executed.metadata["execution_mode"], "record_only")
        self.assertFalse(executed.metadata["external_side_effects"])
        self.assertTrue(any(item.event == "approve" for item in plan.audit_trail))
        self.assertTrue(any(item.event == "execute" for item in plan.audit_trail))
        with self.assertRaisesRegex(ValueError, "Cannot execute"):
            proposed = next(
                item for item in plan.actions if item.status == "proposed"
            )
            engine.execute(plan, proposed.action_id)

    def test_adql_prescriptive_workflow_is_case_insensitive_and_rich(self):
        source = """
        oPeRaTiOnS GROUP Team START Created_At END Completed_At
            STATUS Status SLA 8;
        pReScRiBe OBJECTIVE reduce_delay SOURCE operations
            MAX_ACTIONS 2 MIN_CONFIDENCE 0.1 MAX_RISK medium;
        sCeNaRiO NAME "Faster service" DURATION_CHANGE -20
            FAILURE_CHANGE -10 COST_CHANGE 5;
        oPtImIzE OBJECTIVE reduce_delay MAX_ACTIONS 1
            MIN_CONFIDENCE 0.1;
        aCtIoN LIST STATUS selected;
        """
        script = ADQLParser().parse(source)
        ADQLValidator().validate(script)
        self.assertEqual(
            [item.kind for item in script.statements],
            ["OPERATIONS", "PRESCRIBE", "SCENARIO", "OPTIMIZE", "ACTION"],
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.csv"
            self._operations().to_csv(path, index=False)
            project = AutoDQ(path)
            run = project.query(source, auto_display=False)
            selected_id = project.state.prescriptive_report.selected_actions[0].action_id
            governance = project.query(
                f"ACTION APPROVE {selected_id} ACTOR analyst; "
                f"ACTION EXECUTE {selected_id} ACTOR manager; ACTION AUDIT;",
                auto_display=False,
            )

        self.assertTrue(run.success)
        self.assertTrue(governance.success)
        self.assertEqual(
            project.state.prescriptive_report.get_action(selected_id).status,
            "executed",
        )
        self.assertIn("no external system", governance.results[1].message)
        self.assertGreaterEqual(len(governance.results[-1].data), 3)

    def test_adql_validation_rejects_unsafe_prescriptive_options(self):
        invalid = (
            "PRESCRIBE OBJECTIVE unknown;",
            "PRESCRIBE BUDGET -1;",
            "OPTIMIZE MAX_ACTIONS 0;",
            "PRESCRIBE MIN_CONFIDENCE 2;",
            "PRESCRIBE MAX_RISK extreme;",
            'SCENARIO NAME "No change" DURATION_CHANGE 0;',
            'SCENARIO NAME "Impossible" CAPACITY_CHANGE -100;',
            "ACTION LIST STATUS unknown;",
            'ACTION AUDIT TO "audit.txt";',
        )
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(ADQLValidationError):
                    ADQLValidator().validate(ADQLParser().parse(source))

    def test_prescriptive_results_flow_to_reports_and_dashboards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "orders.csv"
            self._operations().to_csv(path, index=False)
            project = AutoDQ(path)
            project.load()
            project.operations(group_by="Team")
            project.prescribe(source="operations", min_confidence=0.1)
            project.what_if("Faster", duration_change=-10)
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
            dashboard_html = dashboard.to_html()

        self.assertGreater(payload["prescriptive"]["action_count"], 0)
        self.assertIsNotNone(dashboard.prescriptive)
        self.assertIn("Prescriptive analytics", dashboard_html)
        self.assertIn("What-if scenarios", dashboard_html)


if __name__ == "__main__":
    unittest.main()
