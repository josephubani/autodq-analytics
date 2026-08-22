import tempfile
import unittest
from pathlib import Path

import pandas as pd

from autodq import AutoDQ


class StageConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.main_path = self.root / "main.csv"
        self.replacement_path = self.root / "replacement.csv"

        main = pd.DataFrame(
            {
                "ID": range(1, 61),
                "Date": [
                    f"2026-07-{1 + index % 28:02d}"
                    for index in range(60)
                ],
                "Region": ["North", "South", "West"] * 20,
                "Units": [1 + index % 8 for index in range(60)],
                "Revenue": [float(40 + index * 3) for index in range(60)],
                "Profit": [float(8 + index * 1.2) for index in range(60)],
            }
        )
        replacement = main.iloc[:12].copy()
        replacement["Region"] = "Replacement"
        main.to_csv(self.main_path, index=False)
        replacement.to_csv(self.replacement_path, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _project(self) -> AutoDQ:
        project = AutoDQ(str(self.main_path), target="Revenue")
        project.load()
        return project

    def test_named_consumers_use_live_active_data_after_type_change(self):
        project = self._project()
        project.set_type("Date", "datetime")

        contract = project.create_schema_contract(
            "live_schema",
            dataset="main",
            overwrite=True,
        )
        baseline = project.create_drift_baseline(
            "live_baseline",
            dataset="main",
            overwrite=True,
        )
        project.add_dataset(
            "lookup",
            data=pd.DataFrame({"ID": range(1, 61), "Flag": 1}),
        )
        merged = project.merge_datasets(
            "main",
            "lookup",
            output_name="joined",
            on="ID",
        )

        self.assertEqual(contract.columns["Date"].dtype, "datetime")
        self.assertEqual(baseline.columns["Date"].kind, "datetime")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(merged["Date"]))

    def test_dataset_switch_and_active_overwrite_clear_stale_outputs(self):
        project = self._project()
        project.visualize(
            chart="bar",
            x="Region",
            y="Revenue",
            display=False,
        )
        project.add_dataset(
            "replacement",
            dataset_path=str(self.replacement_path),
        )
        project.use_dataset("replacement")

        self.assertEqual(project.visualization_gallery.chart_count, 0)
        self.assertIsNone(project.state.visualization_report)

        run = project.query(
            f'ADD DATASET replacement FROM "{self.main_path}" OVERWRITE; '
            "PROFILE;",
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertEqual(project.dataset_manager.primary().name, "replacement")
        self.assertEqual(project.state.profile_report["rows"], 60)

    def test_clean_feature_and_target_changes_invalidate_downstream_models(self):
        project = self._project()
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )
        project.predict(uncertainty=False)
        project.clean()

        self.assertIsNone(project.state.model_report)
        self.assertIsNone(project.state.prediction_report)

        project.features()
        project.apply_features()
        project.model(algorithm="decision_tree_regressor")
        project.predict(uncertainty=False)
        project.create_feature(
            "RevenueSquared",
            method="square",
            column="Revenue",
        )

        self.assertIsNone(project.state.model_report)
        self.assertIsNone(project.state.prediction_report)
        self.assertIn("RevenueSquared", project.state.engineered_data.columns)

        project.model(algorithm="decision_tree_regressor")
        project.set_target("Profit")

        self.assertIsNone(project.state.engineered_data)
        self.assertIsNone(project.state.model_report)
        self.assertIsNone(project.state.correlation_report)
        self.assertIsNone(project.state.ml_readiness_report)

    def test_adql_visualization_explains_unavailable_named_stage(self):
        project = self._project()
        project.query(
            "LET engineered_snapshot = CURRENT; PROFILE engineered_snapshot;",
            auto_display=False,
        )
        result = project.query(
            "VISUALIZE DATASET engineered_snapshot scatter "
            "X Revenue Y Profit STAGE engineered;",
            auto_display=False,
        ).latest

        self.assertIn("engineered stage is unavailable", result.message)
        self.assertIn("use STAGE current", result.message)

        with self.assertRaisesRegex(ValueError, "Unsupported visualization stage"):
            project.visualize(chart="auto", stage="unknown", display=False)


if __name__ == "__main__":
    unittest.main()
