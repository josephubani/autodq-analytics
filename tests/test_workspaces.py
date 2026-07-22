import json
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import AutoDQ


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workspace_root = self.root / "workspaces"
        rng = np.random.default_rng(17)
        row_count = 90
        self.sales = pd.DataFrame(
            {
                "units": rng.integers(1, 40, row_count),
                "price": rng.uniform(5, 120, row_count),
                "discount": rng.uniform(0, 0.25, row_count),
                "region": rng.choice(
                    ["North", "South", "West"],
                    row_count,
                ),
            }
        )
        self.sales["revenue"] = (
            self.sales["units"]
            * self.sales["price"]
            * (1 - self.sales["discount"])
            + rng.normal(0, 8, row_count)
        )
        self.sales_path = self.root / "sales.csv"
        self.sales.to_csv(self.sales_path, index=False)

        self.support = self.sales.copy()
        self.support["units"] = self.support["units"] + 100
        self.support_path = self.root / "support.csv"
        self.support.to_csv(self.support_path, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _create(self, name="Sales Analysis", dataset_path=None):
        return AutoDQ.create_workspace(
            name=name,
            dataset_path=str(dataset_path or self.sales_path),
            target="revenue",
            workspace_root=str(self.workspace_root),
        )

    def test_workspaces_are_isolated_and_listed(self):
        sales_project = self._create("Sales Analysis")
        support_project = self._create(
            "Support Analysis",
            self.support_path,
        )

        self.assertEqual(sales_project.workspace_name, "Sales Analysis")
        self.assertNotEqual(
            sales_project.workspace.path,
            support_project.workspace.path,
        )
        support_manifest_before = (
            support_project.workspace.manifest_path.read_text(
                encoding="utf-8"
            )
        )
        sales_project.load()
        sales_project.state.data.loc[0, "units"] = 999
        sales_project.save_workspace(include_model=False)

        self.assertEqual(
            support_manifest_before,
            support_project.workspace.manifest_path.read_text(
                encoding="utf-8"
            ),
        )
        restored_support = AutoDQ.open_workspace(
            "support-analysis",
            workspace_root=str(self.workspace_root),
        )
        self.assertEqual(
            restored_support.data.loc[0, "units"],
            self.support.loc[0, "units"],
        )
        summaries = AutoDQ.list_workspaces(
            workspace_root=str(self.workspace_root)
        )
        self.assertEqual(
            [summary.workspace_id for summary in summaries],
            ["sales-analysis", "support-analysis"],
        )
        self.assertTrue(
            all(summary.dataset_count == 1 for summary in summaries)
        )

        with self.assertRaises(FileExistsError):
            self._create("Sales Analysis")

    def test_save_and_open_restores_datasets_session_and_model(self):
        project = self._create("Revenue Model")
        review_data = self.sales.copy()
        review_data["region"] = "Review"
        project.add_dataset("manual review", data=review_data)
        project.use_dataset("manual review")
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )
        predictions_before = project.predict()[
            "AutoDQ_Prediction"
        ].to_numpy()
        info = project.save_workspace()
        event_count_before_open = project.session.event_count
        workspace_path = Path(info["path"])
        model_path = workspace_path / info["active_model"]

        self.assertTrue((model_path / "manifest.json").is_file())
        self.assertTrue((model_path / "model.joblib").is_file())
        self.assertTrue(model_path.is_relative_to(workspace_path / "models"))
        self.assertEqual(info["active_dataset"], "manual review")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            restored = AutoDQ.open_workspace(
                "revenue-model",
                workspace_root=str(self.workspace_root),
            )

        self.assertEqual(
            restored.dataset_manager.names(),
            ["main", "manual review"],
        )
        self.assertEqual(
            restored.dataset_manager.primary().name,
            "manual review",
        )
        self.assertEqual(restored.dataset_path.name, "manual_review.csv")
        self.assertEqual(restored.target, "revenue")
        self.assertIsNotNone(restored.state.model_report)
        self.assertIsNotNone(restored.state.model_bundle)
        self.assertGreater(
            restored.session.event_count,
            event_count_before_open,
        )
        self.assertIn(
            "create_workspace",
            restored.session.steps_completed,
        )
        self.assertIn("save_workspace", restored.session.steps_completed)
        predictions_after = restored.predict()[
            "AutoDQ_Prediction"
        ].to_numpy()
        np.testing.assert_allclose(
            predictions_before,
            predictions_after,
        )

        for entry in restored.dataset_manager.entries():
            self.assertTrue(
                Path(entry.path).is_relative_to(workspace_path / "datasets")
            )

    def test_retraining_invalidates_previous_model_bundle(self):
        project = self._create("Retraining")
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )
        project.save_workspace()
        original_bundle = project.state.model_bundle
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
            random_state=99,
        )

        self.assertIsNone(project.state.model_bundle)
        project.save_workspace()
        self.assertIsNotNone(project.state.model_bundle)
        self.assertIsNot(project.state.model_bundle, original_bundle)

    def test_unsafe_manifest_path_is_rejected(self):
        project = self._create("Unsafe Paths")
        manifest_path = project.workspace.manifest_path
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["datasets"][0]["file"] = "../../outside.csv"
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "unsafe path"):
            AutoDQ.open_workspace(
                "unsafe-paths",
                workspace_root=str(self.workspace_root),
            )

    def test_plain_project_cannot_be_saved_as_workspace(self):
        project = AutoDQ(str(self.sales_path), target="revenue")

        with self.assertRaisesRegex(RuntimeError, "not attached"):
            project.save_workspace()

    def test_workspace_restores_saved_dtypes(self):
        project = self._create("Typed Data")
        project.load()
        project.set_type("region", "category")
        project.save_workspace(include_model=False)
        restored = AutoDQ.open_workspace(
            "typed-data",
            workspace_root=str(self.workspace_root),
        )

        self.assertEqual(str(restored.data["region"].dtype), "category")

    def test_workspace_rejects_unsafe_model_name(self):
        project = self._create("Safe Models")
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )

        with self.assertRaisesRegex(ValueError, "model_name"):
            project.save_workspace(model_name="../../outside")


if __name__ == "__main__":
    unittest.main()
