import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from autodq import AutoDQ, AutoRunConfig, AutoRunError


class ProjectAutoTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rng = np.random.default_rng(91)
        row_count = 80
        self.data = pd.DataFrame(
            {
                "Units": rng.integers(1, 45, row_count),
                "Price": rng.uniform(10, 120, row_count),
                "Discount": rng.uniform(0, 0.25, row_count),
                "Region": rng.choice(
                    ["North", "South", "West"],
                    row_count,
                ),
            }
        )
        self.data["Revenue"] = (
            self.data["Units"]
            * self.data["Price"]
            * (1 - self.data["Discount"])
            + rng.normal(0, 20, row_count)
        )
        self.data.loc[3, "Units"] = np.nan
        self.data.loc[5, "Region"] = None
        self.data.loc[7, "Revenue"] = 25000
        self.data = pd.concat(
            [self.data, self.data.iloc[[0]]],
            ignore_index=True,
        )
        self.dataset_path = self.root / "auto.csv"
        self.data.to_csv(self.dataset_path, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _project(self, target=None):
        return AutoDQ(str(self.dataset_path), target=target)

    def test_auto_config_presets_and_validation(self):
        review = AutoRunConfig.from_options(mode="review")
        clean = AutoRunConfig.from_options(mode="clean")
        full = AutoRunConfig.from_options(mode="full")

        self.assertFalse(review.apply_cleaning)
        self.assertFalse(review.train_model)
        self.assertTrue(clean.approve_all)
        self.assertTrue(clean.apply_cleaning)
        self.assertTrue(full.train_model)
        self.assertTrue(full.generate_predictions)
        self.assertTrue(full.explain_model)

        override = AutoRunConfig.from_options(
            mode="full",
            approve_all=False,
            explain_model=False,
        )
        self.assertFalse(override.approve_all)
        self.assertFalse(override.explain_model)

        with self.assertRaisesRegex(ValueError, "mode"):
            AutoRunConfig.from_options(mode="unsafe")

        with self.assertRaisesRegex(ValueError, "test_size"):
            AutoRunConfig.from_options(test_size=1)

        with self.assertRaisesRegex(ValueError, "report_output"):
            AutoRunConfig.from_options(report_output="report.txt")

    def test_default_auto_prepares_review_without_mutating_data(self):
        project = self._project()
        result = project.auto(
            visualize=False,
            auto_display=False,
        )

        self.assertTrue(result.success)
        self.assertIs(project.state.auto_run_report, result)
        self.assertIs(result.review, project.state.cleaning_review)
        self.assertIsNone(project.state.cleaned_data)
        self.assertIsNone(project.state.model_report)
        self.assertEqual(result.stage("clean").status, "skipped")
        self.assertEqual(result.stage("model").status, "skipped")
        self.assertEqual(result.stage("review").status, "completed")
        self.assertGreater(result.review.action_count, 0)
        self.assertGreater(result.review.pending_count, 0)
        self.assertTrue(
            any("pending cleaning" in item for item in result.next_actions)
        )
        self.assertIn("auto", project.session.steps_completed)
        self.assertIn("Automatic Workflow", result.to_html())

    def test_clean_mode_approves_applies_and_validates(self):
        project = self._project()
        result = project.auto(
            mode="clean",
            visualize=False,
            auto_display=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.stage("approve_all").status, "completed")
        self.assertEqual(result.stage("clean").status, "completed")
        self.assertEqual(
            result.stage("validate_cleaning").status,
            "completed",
        )
        self.assertIsNotNone(project.state.cleaned_data)
        self.assertIsNotNone(project.state.validation_report)
        self.assertFalse(project.state.cleaned_data["Units"].isna().any())
        self.assertFalse(project.state.cleaned_data["Region"].isna().any())
        self.assertEqual(
            len(project.state.cleaned_data),
            len(self.data) - 1,
        )
        self.assertTrue(
            all(
                action.status == "approved"
                for action in result.review.actions
            )
        )

    def test_full_mode_trains_and_predicts_when_target_is_set(self):
        project = self._project(target="Revenue")
        result = project.auto(
            mode="full",
            algorithm="decision_tree_regressor",
            visualize=False,
            auto_display=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.stage("model").status, "completed")
        self.assertEqual(result.stage("predict").status, "completed")
        self.assertEqual(result.stage("explain").status, "completed")
        self.assertIsNotNone(project.state.model_report)
        self.assertIsNotNone(project.state.prediction_report)
        self.assertIsNotNone(project.state.explainability_report)
        self.assertIn(
            "AutoDQ_Prediction",
            project.state.prediction_data.columns,
        )
        self.assertTrue(
            project.state.prediction_report.uncertainty_available
        )

    def test_repeat_auto_reuses_outputs_and_preserves_review_changes(self):
        project = self._project()
        first = project.auto(visualize=False, auto_display=False)
        review = first.review
        review.edit_row(
            5,
            {"Region": "North"},
            reason="Verified correction.",
        )
        first_action = review.actions[0]
        review.approve(first_action.action_id)
        second = project.auto(visualize=False, auto_display=False)

        self.assertIs(second.review, review)
        self.assertEqual(second.stage("load").status, "reused")
        self.assertEqual(second.stage("review").status, "reused")
        self.assertEqual(review.working_data.loc[5, "Region"], "North")
        self.assertEqual(first_action.status, "approved")

        refreshed = project.auto(
            visualize=False,
            refresh=True,
            auto_display=False,
        )
        self.assertIsNot(refreshed.review, review)
        self.assertTrue(pd.isna(refreshed.review.working_data.loc[5, "Region"]))

    def test_existing_partial_approvals_can_be_applied_without_approve_all(self):
        project = self._project()
        review_result = project.auto(
            visualize=False,
            auto_display=False,
        )
        review = review_result.review
        missing_units = next(
            action
            for action in review.actions
            if action.issue_type == "missing_values"
            and "Units" in action.affected_columns
        )
        review.approve(missing_units.action_id)
        clean_result = project.auto(
            apply_cleaning=True,
            approve_all=False,
            visualize=False,
            auto_display=False,
        )

        self.assertEqual(clean_result.stage("review").status, "reused")
        self.assertEqual(clean_result.stage("clean").status, "completed")
        self.assertFalse(project.state.cleaned_data["Units"].isna().any())
        self.assertTrue(project.state.cleaned_data["Region"].isna().any())

    def test_auto_failure_can_return_stop_continue_or_raise(self):
        stopped_project = self._project()

        with patch.object(
            stopped_project,
            "profile",
            side_effect=RuntimeError("profile <script> failed"),
        ):
            stopped = stopped_project.auto(
                visualize=False,
                auto_display=False,
            )

        self.assertFalse(stopped.success)
        self.assertTrue(stopped.halted)
        self.assertEqual(stopped.stage("profile").status, "failed")
        self.assertNotIn("<script>", stopped.to_html())

        continued_project = self._project()

        with patch.object(
            continued_project,
            "profile",
            side_effect=RuntimeError("profile failed"),
        ):
            continued = continued_project.auto(
                visualize=False,
                continue_on_error=True,
                auto_display=False,
            )

        self.assertFalse(continued.success)
        self.assertFalse(continued.halted)
        self.assertEqual(
            continued.stage("statistics").status,
            "completed",
        )

        raised_project = self._project()

        with patch.object(
            raised_project,
            "profile",
            side_effect=RuntimeError("profile failed"),
        ), self.assertRaises(AutoRunError) as context:
            raised_project.auto(
                visualize=False,
                raise_on_error=True,
                auto_display=False,
            )

        self.assertEqual(context.exception.stage, "profile")
        self.assertEqual(
            context.exception.result.stage("profile").status,
            "failed",
        )

    def test_auto_report_is_exported_to_json(self):
        project = self._project()
        output = self.root / "auto_report.json"
        result = project.auto(
            visualize=True,
            report_output=str(output),
            auto_display=False,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result.success)
        self.assertTrue(output.is_file())
        self.assertIsNotNone(payload["automation"])
        self.assertEqual(
            payload["automation"]["config"]["mode"],
            "review",
        )
        self.assertTrue(payload["automation"]["stages"])

    def test_auto_can_save_an_attached_workspace(self):
        workspace_root = self.root / "workspaces"
        project = AutoDQ.create_workspace(
            name="Automatic Workflow",
            dataset_path=str(self.dataset_path),
            workspace_root=str(workspace_root),
        )
        result = project.auto(
            visualize=False,
            save_workspace=True,
            auto_display=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.stage("save_workspace").status,
            "completed",
        )
        self.assertTrue(project.workspace.session_path.is_file())
        self.assertTrue(
            (project.workspace.logs_dir / "cleaning_audit.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
