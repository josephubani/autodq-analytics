import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import ADQLParser, AutoDQ, MLReadinessEngine
from autodq.interpretation.models import (
    InterpretationReport,
    StatisticalInterpretation,
)
from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class MLReadinessTests(unittest.TestCase):
    def _dataset(self, rows: int = 1_200, seed: int = 42) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        return pd.DataFrame(
            {
                "feature_a": rng.normal(0, 1, rows),
                "feature_b": rng.normal(5, 2, rows),
                "segment": rng.choice(["A", "B", "C"], rows),
                "target": rng.normal(100, 15, rows),
            }
        )

    def test_score_is_the_normalized_sum_of_visible_components(self):
        data = self._dataset()
        report = MLReadinessEngine().analyze(data, target="target")

        self.assertEqual(sum(item.max_score for item in report.components), 100)
        self.assertEqual(report.component_count, 7)
        self.assertEqual(report.assessed_points, 90)
        self.assertEqual(report.assessment_coverage, 90)
        self.assertAlmostEqual(
            report.score,
            round(report.earned_points / report.assessed_points * 100, 2),
        )
        stability = next(
            item for item in report.components if item.key == "feature_stability"
        )
        self.assertFalse(stability.assessed)
        self.assertEqual(stability.status, "not_assessed")
        self.assertIn("components", report.to_dict())
        self.assertIn("Calculation:", report.to_notebook_html())

    def test_data_quality_deductions_are_explicit(self):
        data = self._dataset()
        data.loc[:119, "feature_a"] = np.nan
        data = pd.concat([data, data.iloc[:24]], ignore_index=True)
        report = MLReadinessEngine().analyze(data, target="target")
        quality = next(
            item for item in report.components if item.key == "data_quality"
        )

        self.assertLess(quality.score, quality.max_score)
        self.assertGreater(quality.metrics["missing_cells"], 0)
        self.assertGreater(quality.metrics["duplicate_rows"], 0)
        self.assertTrue(any("missing" in item for item in quality.deductions))
        self.assertTrue(any("duplicate" in item for item in quality.deductions))

    def test_distribution_interpretations_affect_feature_readiness(self):
        data = self._dataset()
        interpretation = InterpretationReport(
            interpretations={
                "feature_a": [
                    StatisticalInterpretation(
                        column="feature_a",
                        insight_type="skewness",
                        severity="high",
                        message="Highly skewed.",
                    ),
                    StatisticalInterpretation(
                        column="feature_a",
                        insight_type="heavy_tail",
                        severity="high",
                        message="Heavy tailed.",
                    ),
                ]
            }
        )
        report = MLReadinessEngine().analyze(
            data,
            target="target",
            interpretation_report=interpretation,
        )
        feature = next(
            item for item in report.components if item.key == "feature_readiness"
        )

        self.assertEqual(feature.score, 13)
        self.assertEqual(feature.metrics["high_skew_features"], 1)
        self.assertEqual(feature.metrics["heavy_tailed_features"], 1)

    def test_reference_dataset_adds_psi_feature_stability(self):
        baseline = self._dataset(seed=7)
        stable_current = baseline.copy()
        stable = MLReadinessEngine().analyze(
            stable_current,
            target="target",
            reference_df=baseline,
            reference_name="baseline",
        )
        stable_component = next(
            item for item in stable.components if item.key == "feature_stability"
        )

        self.assertTrue(stable_component.assessed)
        self.assertEqual(stable_component.score, 10)
        self.assertEqual(stable.assessment_coverage, 100)

        shifted_current = baseline.copy()
        shifted_current["feature_a"] = shifted_current["feature_a"] + 8
        shifted = MLReadinessEngine().analyze(
            shifted_current,
            target="target",
            reference_df=baseline,
            reference_name="baseline",
        )
        shifted_component = next(
            item for item in shifted.components if item.key == "feature_stability"
        )

        self.assertLess(shifted_component.score, stable_component.score)
        self.assertGreater(shifted_component.metrics["shifted_features"], 0)
        self.assertTrue(
            any(issue.issue_type == "feature_instability" for issue in shifted.issues)
        )

    def test_target_leakage_is_not_double_counted_as_multicollinearity(self):
        data = self._dataset()
        data["target_copy"] = data["target"]
        report = MLReadinessEngine().analyze(data, target="target")
        leakage = next(
            item for item in report.components if item.key == "leakage_safety"
        )
        multicollinearity = next(
            item for item in report.components if item.key == "multicollinearity"
        )

        self.assertEqual(leakage.metrics["flagged_features"], {"target_copy": 1.0})
        self.assertEqual(multicollinearity.metrics["flagged_pairs"], [])

    def test_project_reports_include_readiness_breakdown(self):
        data = self._dataset()
        readiness = MLReadinessEngine().analyze(data, target="target")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "readiness.json"
            report = AutoDQReport(
                dataset="in-memory",
                session=None,
                ml_readiness=readiness,
            )
            JSONExporter().export(report, output)
            payload = json.loads(output.read_text(encoding="utf-8"))
            markup = HTMLExporter()._build_html(report)

        self.assertEqual(
            len(payload["ml_readiness"]["components"]),
            7,
        )
        self.assertIn("Machine Learning Readiness", markup)
        self.assertIn("Assessment coverage", markup)
        self.assertIn("Feature stability", markup)

    def test_adql_readiness_accepts_current_and_named_reference_datasets(self):
        parsed = ADQLParser().parse(
            "READINESS REFERENCE baseline; "
            "READINESS DATASET current_copy REFERENCE baseline;"
        )
        self.assertEqual(
            parsed.statements[0].parameters,
            {"reference_dataset": "baseline"},
        )
        self.assertEqual(
            parsed.statements[1].parameters,
            {
                "dataset_name": "current_copy",
                "reference_dataset": "baseline",
            },
        )
        mixed = ADQLParser().parse(
            "rEaDiNeSs dAtAsEt CurrentCopy rEfErEnCe BaselineData;"
        ).statements[0]
        self.assertEqual(mixed.parameters["dataset_name"], "CurrentCopy")
        self.assertEqual(
            mixed.parameters["reference_dataset"],
            "BaselineData",
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current_path = root / "current.csv"
            baseline_path = root / "baseline.csv"
            current = self._dataset()
            baseline = current.copy()
            current.to_csv(current_path, index=False)
            baseline.to_csv(baseline_path, index=False)
            project = AutoDQ(current_path, target="target")
            project.add_dataset("baseline", dataset_path=baseline_path)
            run = project.query(
                "READINESS REFERENCE baseline;",
                auto_display=False,
            )

        self.assertTrue(run.success)
        self.assertEqual(run.value.reference_name, "baseline")
        self.assertEqual(run.value.assessment_coverage, 100)
        self.assertIn("assessed 100.0%", run.latest.message)


if __name__ == "__main__":
    unittest.main()
