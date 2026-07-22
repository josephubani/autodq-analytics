import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import AutoDQ
from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class CleaningReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rows = [
            [25, 100.0, 1.0, "North", "a@example.com"],
            [30, 110.0, 2.0, "South", "b@example.com"],
            [-5, 120.0, 3.0, "Unknown", "invalid-email"],
            [40, 130.0, np.nan, None, "d@example.com"],
            [200, 10000.0, 5.0, "West", "e@example.com"],
            [35, 140.0, 6.0, "North", "f@example.com"],
            [28, 150.0, 7.0, "South", "g@example.com"],
            [31, 160.0, 8.0, "West", "h@example.com"],
            [29, 170.0, 9.0, "North", "i@example.com"],
            [32, 180.0, 10.0, "South", "j@example.com"],
            [33, 190.0, 11.0, "West", "k@example.com"],
            [34, 200.0, 12.0, "North", "l@example.com"],
        ]
        rows.append(list(rows[0]))
        self.data = pd.DataFrame(
            rows,
            columns=["Age", "Revenue", "Quantity", "Region", "Email"],
        )
        self.dataset_path = self.root / "review.csv"
        self.data.to_csv(self.dataset_path, index=False)
        self.project = AutoDQ(str(self.dataset_path))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _review(self):
        return self.project.review_cleaning(
            use_knowledge=True,
            auto_display=False,
        )

    @staticmethod
    def _action(review, issue_type, column=None):
        for action in review.actions:
            if action.issue_type != issue_type:
                continue

            if column is None or column in action.affected_columns:
                return action

        raise AssertionError(
            f"Action not found: issue={issue_type}, column={column}"
        )

    def test_partial_approve_reject_and_approve_all_are_audited(self):
        review = self._review()
        first, second = review.actions[:2]
        self.project.approve(first.action_id)
        self.project.reject(
            second.action_id,
            reason="Business owner rejected this change.",
        )

        self.assertEqual(first.status, "approved")
        self.assertEqual(second.status, "rejected")
        events = [item.event_type for item in review.audit_trail]
        self.assertIn("action_approved", events)
        self.assertIn("action_rejected", events)
        rejected = next(
            item
            for item in review.audit_trail
            if item.event_type == "action_rejected"
        )
        self.assertEqual(
            rejected.reason,
            "Business owner rejected this change.",
        )

        self.project.approve_all()
        self.assertTrue(
            all(action.status == "approved" for action in review.actions)
        )

    def test_action_preview_is_rich_and_does_not_modify_data(self):
        review = self._review()
        action = self._action(review, "missing_values", "Quantity")
        before = review.working_data.copy(deep=True)
        preview = self.project.cleaning_preview(action.action_id)

        self.assertEqual(preview.action_id, action.action_id)
        self.assertGreater(preview.affected_row_count, 0)
        self.assertTrue(preview.before_sample)
        self.assertTrue(preview.after_sample)
        self.assertIn("Interactive Cleaning Preview", preview.to_html())
        pd.testing.assert_frame_equal(before, review.working_data)

        all_previews = review.preview()
        self.assertEqual(all_previews.action_count, review.action_count)
        self.assertIn("Cleaning Preview", all_previews.to_html())

    def test_manual_row_edits_flow_into_cleaned_data_and_audit(self):
        review = self._review()
        self.project.edit_row(
            2,
            {"Age": 5, "Region": "North"},
            reason="Confirmed from the source system.",
        )
        edits = [
            item
            for item in review.audit_trail
            if item.event_type == "manual_cell_edit"
        ]

        self.assertEqual(len(edits), 2)
        self.assertEqual({item.column for item in edits}, {"Age", "Region"})
        age_edit = next(item for item in edits if item.column == "Age")
        self.assertEqual(age_edit.old_value, -5)
        self.assertEqual(age_edit.new_value, 5)
        cleaned = self.project.apply_cleaning_review()
        self.assertEqual(cleaned.loc[2, "Age"], 5)
        self.assertEqual(cleaned.loc[2, "Region"], "North")

    def test_domain_rules_find_ranges_values_patterns_nulls_and_duplicates(self):
        review = self._review()
        self.project.add_domain_rule(
            "Region",
            allowed_values=["North", "South", "West"],
            nullable=False,
            description="Supported sales regions only.",
        )
        self.project.add_domain_rule(
            "Email",
            pattern=r"[^@\s]+@[^@\s]+\.[^@\s]+",
            unique=True,
        )
        self.project.add_domain_rule("Quantity", nullable=False)
        report = self.project.validate_domain()
        codes = {item.code for item in report.violations}

        self.assertIn("min_value", codes)
        self.assertIn("max_value", codes)
        self.assertIn("allowed_values", codes)
        self.assertIn("null", codes)
        self.assertIn("pattern", codes)
        self.assertIn("unique", codes)
        self.assertGreater(report.invalid_row_count, 0)
        self.assertFalse(report.is_valid)
        self.assertIn("Domain Validation", report.to_html())
        self.assertIs(self.project.state.domain_validation_report, report)
        self.assertEqual(len(review.domain_rules), report.rule_count)

    def test_outlier_review_and_clip_records_every_changed_cell(self):
        review = self._review()
        report = self.project.review_outliers("Revenue")
        outliers = report.for_column("Revenue")

        self.assertTrue(outliers)
        original_value = review.working_data.loc[4, "Revenue"]
        changed = self.project.treat_outliers(
            "Revenue",
            strategy="clip",
            reason="Cap data-entry extremes to reviewed IQR bounds.",
        )
        audit_changes = [
            item
            for item in review.audit_trail
            if item.event_type == "outlier_treatment"
            and item.column == "Revenue"
        ]

        self.assertEqual(changed, len(audit_changes))
        self.assertGreater(changed, 0)
        self.assertLess(review.working_data.loc[4, "Revenue"], original_value)
        self.assertLessEqual(
            review.working_data.loc[4, "Revenue"],
            outliers[0].upper_bound,
        )
        cleaned = self.project.clean()
        self.assertEqual(
            cleaned.loc[4, "Revenue"],
            review.working_data.loc[4, "Revenue"],
        )

    def test_outlier_row_removal_is_audited_per_row(self):
        review = self._review()
        rows_before = len(review.working_data)
        removed = review.treat_outliers(
            "Age",
            strategy="remove",
            lower_bound=0,
            upper_bound=120,
            reason="Impossible age values.",
        )
        removals = [
            item
            for item in review.audit_trail
            if item.event_type == "manual_row_removal"
        ]

        self.assertEqual(removed, 2)
        self.assertEqual(len(removals), removed)
        self.assertEqual(len(review.working_data), rows_before - removed)
        self.assertNotIn(2, review.working_data.index)
        self.assertNotIn(4, review.working_data.index)

    def test_fractional_clip_promotes_integer_column_safely(self):
        review = self._review()
        changed = review.treat_outliers(
            "Age",
            strategy="clip",
            lower_bound=0,
            upper_bound=120.5,
        )

        self.assertGreater(changed, 0)
        self.assertTrue(
            pd.api.types.is_float_dtype(review.working_data["Age"])
        )
        self.assertEqual(review.working_data.loc[4, "Age"], 120.5)

    def test_reviewed_cleaning_combines_automation_and_manual_changes(self):
        review = self._review()
        missing_action = self._action(
            review,
            "missing_values",
            "Quantity",
        )
        duplicate_action = self._action(review, "duplicate_rows")
        outlier_ids = [
            action.action_id
            for action in review.actions
            if action.issue_type == "outliers"
        ]
        review.approve([missing_action.action_id, duplicate_action.action_id])

        if outlier_ids:
            review.reject(outlier_ids, reason="Keep valid business extremes.")

        review.edit_row(2, {"Region": "West"}, reason="Verified region.")
        cleaned = self.project.clean()

        self.assertEqual(len(cleaned), len(self.data) - 1)
        self.assertFalse(cleaned["Quantity"].isna().any())
        self.assertEqual(cleaned.loc[2, "Region"], "West")
        successful_ids = {
            item.action_id
            for item in self.project.state.cleaning_report.actions
            if item.status == "success"
        }
        self.assertIn(missing_action.action_id, successful_ids)
        self.assertIn(duplicate_action.action_id, successful_ids)

    def test_audit_exports_json_csv_and_escapes_notebook_html(self):
        review = self._review()
        review.edit_row(
            1,
            {"Region": "West"},
            reason="<script>alert('unsafe')</script>",
        )
        json_path = review.export_audit(self.root / "audit.json")
        csv_path = self.project.export_cleaning_audit(
            str(self.root / "audit.csv")
        )
        payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertTrue(payload)
        self.assertTrue(csv_path.is_file())
        self.assertIn("manual_cell_edit", csv_path.read_text(encoding="utf-8"))
        markup = review.to_html()
        self.assertIn("Interactive Cleaning", markup)
        self.assertNotIn("<script>alert", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_invalid_review_changes_are_atomic(self):
        review = self._review()
        statuses = [action.status for action in review.actions]
        before = review.working_data.copy(deep=True)

        with self.assertRaises(KeyError):
            review.approve([review.actions[0].action_id, 9999])

        with self.assertRaisesRegex(ValueError, "unknown columns"):
            review.edit_row(0, {"MissingColumn": 1})

        with self.assertRaisesRegex(ValueError, "numeric columns"):
            review.review_outliers("Region")

        with self.assertRaisesRegex(ValueError, "at least one constraint"):
            review.add_domain_rule("Region")

        self.assertEqual(statuses, [action.status for action in review.actions])
        pd.testing.assert_frame_equal(before, review.working_data)

    def test_review_is_included_in_json_reports(self):
        review = self._review()
        review.edit_row(0, {"Region": "West"}, reason="Correction")
        domain_report = review.validate_domain()
        report = AutoDQReport(
            dataset=str(self.dataset_path),
            session=self.project.session,
            cleaning_review=review,
            domain_validation=domain_report,
        )
        output = self.root / "report.json"
        JSONExporter().export(report, output)
        payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["cleaning_review"]["audit_count"],
            review.audit_count,
        )
        self.assertEqual(
            payload["domain_validation"]["rule_count"],
            domain_report.rule_count,
        )
        markup = HTMLExporter()._build_html(report)
        self.assertIn("Interactive Cleaning Review", markup)
        self.assertIn("Recent Cleaning Audit Trail", markup)

    def test_workspace_save_persists_cleaning_audit(self):
        workspace_root = self.root / "workspaces"
        project = AutoDQ.create_workspace(
            name="Review Workspace",
            dataset_path=str(self.dataset_path),
            workspace_root=str(workspace_root),
        )
        project.review_cleaning(auto_display=False)
        project.edit_row(1, {"Region": "West"}, reason="Workspace edit")
        info = project.save_workspace(include_model=False)
        audit_path = Path(info["path"]) / "logs" / "cleaning_audit.json"

        self.assertTrue(audit_path.is_file())
        self.assertEqual(
            info["metadata"]["cleaning_audit"],
            "logs/cleaning_audit.json",
        )
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertTrue(
            any(item["event_type"] == "manual_cell_edit" for item in payload)
        )


if __name__ == "__main__":
    unittest.main()
