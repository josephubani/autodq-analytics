import unittest

import numpy as np
import pandas as pd

from app.autodq_web.presenters import (
    action_frame,
    column_catalog,
    dataset_metrics,
    frame_to_csv_bytes,
    frame_to_excel_bytes,
    humanize_identifier,
    issue_frame,
    recommendation_frame,
    validation_frame,
)
from autodq.decision.engine import DecisionAction, DecisionPlan
from autodq.models.issues import DataIssue
from autodq.models.recommendations import CleaningRecommendation
from autodq.models.reports import DiagnosisReport
from autodq.models.validation import ValidationMetric, ValidationReport
from autodq.review.models import CleaningReview


class StreamlitPresenterTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "Customer_Age": [24.0, np.nan, 41.0, 24.0],
                "Region": ["East", "West", "East", "East"],
            }
        )

    def test_humanizes_identifiers_without_mutating_columns(self):
        self.assertEqual(humanize_identifier("Customer_Age"), "Customer Age")
        catalog = column_catalog(self.frame)
        self.assertEqual(catalog.iloc[0]["Column"], "Customer Age")
        self.assertEqual(catalog.iloc[0]["Source name"], "Customer_Age")
        self.assertEqual(list(self.frame.columns), ["Customer_Age", "Region"])

    def test_dataset_metrics_are_stable(self):
        metrics = dataset_metrics(self.frame)
        self.assertEqual(metrics["rows"], 4)
        self.assertEqual(metrics["columns"], 2)
        self.assertEqual(metrics["missing"], 1)
        self.assertEqual(metrics["duplicates"], 1)
        self.assertEqual(metrics["completeness"], 87.5)

    def test_issue_and_recommendation_frames(self):
        report = DiagnosisReport(
            issues=[
                DataIssue(
                    issue_type="missing_values",
                    severity="warning",
                    message="One value is missing.",
                    affected_columns=["Customer_Age"],
                    confidence=0.9,
                )
            ],
            quality_score=91.0,
        )
        issues = issue_frame(report)
        self.assertEqual(issues.iloc[0]["Issue"], "missing values")
        self.assertEqual(issues.iloc[0]["Columns"], "Customer Age")
        self.assertEqual(issues.iloc[0]["Confidence"], 90.0)

        recommendations = recommendation_frame(
            [
                CleaningRecommendation(
                    issue_type="missing_values",
                    strategy="median",
                    reason="Numeric field.",
                    affected_columns=["Customer_Age"],
                    action="Fill the missing value.",
                )
            ]
        )
        self.assertEqual(recommendations.iloc[0]["Columns"], "Customer Age")

    def test_action_and_validation_frames(self):
        plan = DecisionPlan(
            actions=[
                DecisionAction(
                    action_id=1,
                    issue_type="missing_values",
                    strategy="median",
                    affected_columns=["Customer_Age"],
                    action="Fill values.",
                    reason="Missing data.",
                    priority="medium",
                )
            ]
        )
        review = CleaningReview(
            original_data=self.frame,
            working_data=self.frame.copy(),
            decision_plan=plan,
        )
        actions = action_frame(review)
        self.assertEqual(actions.iloc[0]["ID"], 1)
        self.assertEqual(actions.iloc[0]["Columns"], "Customer Age")

        validation = ValidationReport(
            missing_values=ValidationMetric("missing_values", 1, 0),
            duplicate_rows=ValidationMetric("duplicate_rows", 1, 0),
            rows=ValidationMetric("rows", 4, 3),
            columns=ValidationMetric("columns", 2, 2),
            quality_score_before=80.0,
            quality_score_after=100.0,
        )
        table = validation_frame(validation)
        self.assertEqual(table.iloc[0]["Metric"], "missing values")
        self.assertEqual(table.iloc[0]["Change"], -1)

    def test_download_payloads_are_valid(self):
        self.assertTrue(frame_to_csv_bytes(self.frame).startswith(b"Customer_Age"))
        self.assertTrue(frame_to_excel_bytes(self.frame).startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
