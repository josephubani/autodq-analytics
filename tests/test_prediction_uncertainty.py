import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import AutoDQ


class PredictionUncertaintyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary_directory.name)
        rng = np.random.default_rng(73)
        row_count = 180

        cls.regression_data = pd.DataFrame(
            {
                "units": rng.integers(1, 50, row_count),
                "price": rng.uniform(8, 130, row_count),
                "discount": rng.uniform(0, 0.35, row_count),
                "region": rng.choice(
                    ["North", "South", "West"],
                    row_count,
                ),
            }
        )
        region_effect = cls.regression_data["region"].map(
            {"North": 25.0, "South": -10.0, "West": 12.0}
        )
        cls.regression_data["revenue"] = (
            cls.regression_data["units"]
            * cls.regression_data["price"]
            * (1 - cls.regression_data["discount"])
            + region_effect
            + rng.normal(0, 35, row_count)
        )
        cls.regression_path = cls.root / "regression.csv"
        cls.regression_data.to_csv(cls.regression_path, index=False)
        cls.regression_project = AutoDQ(
            str(cls.regression_path),
            target="revenue",
        )
        cls.regression_project.model(
            algorithm="linear_regression",
            use_engineered=False,
        )

        cls.classification_data = cls.regression_data.drop(
            columns=["revenue"]
        ).copy()
        buying_score = (
            cls.classification_data["units"]
            + cls.classification_data["price"] / 6
            - cls.classification_data["discount"] * 35
            + rng.normal(0, 5, row_count)
        )
        cls.classification_data["segment"] = np.where(
            buying_score >= np.median(buying_score),
            "high_value",
            "standard",
        )
        cls.classification_path = cls.root / "classification.csv"
        cls.classification_data.to_csv(
            cls.classification_path,
            index=False,
        )
        cls.classification_project = AutoDQ(
            str(cls.classification_path),
            target="segment",
        )
        cls.classification_project.model(
            algorithm="random_forest_classifier",
            use_engineered=False,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def test_regression_predictions_include_conformal_intervals(self):
        output = self.regression_project.predict(
            confidence_level=0.9
        )
        report = self.regression_project.state.prediction_report

        for column in (
            "AutoDQ_Prediction_Lower",
            "AutoDQ_Prediction_Upper",
            "AutoDQ_Interval_Width",
            "AutoDQ_Confidence_Level",
        ):
            self.assertIn(column, output.columns)

        self.assertTrue(
            np.all(
                output["AutoDQ_Prediction_Lower"]
                <= output["AutoDQ_Prediction"]
            )
        )
        self.assertTrue(
            np.all(
                output["AutoDQ_Prediction"]
                <= output["AutoDQ_Prediction_Upper"]
            )
        )
        self.assertTrue(
            np.all(output["AutoDQ_Interval_Width"] > 0)
        )
        self.assertTrue(report.uncertainty_available)
        self.assertEqual(report.uncertainty_method, "holdout_conformal")
        self.assertEqual(report.confidence_level, 0.9)
        self.assertGreater(report.calibration_size, 0)
        self.assertGreater(report.mean_interval_width, 0)
        self.assertGreaterEqual(report.empirical_coverage, 0)
        self.assertLessEqual(report.empirical_coverage, 1)

    def test_higher_confidence_has_no_narrower_interval(self):
        interval_80 = self.regression_project.predict(
            confidence_level=0.8
        )["AutoDQ_Interval_Width"]
        interval_95 = self.regression_project.predict(
            confidence_level=0.95
        )["AutoDQ_Interval_Width"]

        self.assertTrue(np.all(interval_95 >= interval_80))

    def test_targetless_regression_data_has_intervals_without_coverage(self):
        features = self.regression_data.drop(columns=["revenue"])
        output = self.regression_project.predict(features)
        report = self.regression_project.state.prediction_report

        self.assertIn("AutoDQ_Prediction_Lower", output.columns)
        self.assertNotIn("revenue", output.columns)
        self.assertIsNone(report.empirical_coverage)
        self.assertIsNone(report.predictions[0].actual)

    def test_classification_predictions_include_probability_diagnostics(self):
        output = self.classification_project.predict(
            low_confidence_threshold=0.7
        )
        report = self.classification_project.state.prediction_report
        probability_columns = [
            column
            for column in output.columns
            if column.startswith("AutoDQ_Probability_")
        ]

        self.assertEqual(len(probability_columns), 2)
        np.testing.assert_allclose(
            output[probability_columns].sum(axis=1),
            np.ones(len(output)),
        )
        np.testing.assert_allclose(
            output["AutoDQ_Confidence"],
            output[probability_columns].max(axis=1),
        )
        self.assertTrue(
            output["AutoDQ_Prediction_Margin"].between(0, 1).all()
        )
        self.assertTrue(output["AutoDQ_Entropy"].between(0, 1).all())
        self.assertEqual(output["AutoDQ_Low_Confidence"].dtype, bool)
        self.assertEqual(report.uncertainty_method, "predict_proba")
        self.assertTrue(report.uncertainty_available)
        self.assertEqual(
            report.low_confidence_count,
            int(output["AutoDQ_Low_Confidence"].sum()),
        )
        self.assertIn(
            "expected_calibration_error",
            report.calibration_metrics,
        )
        self.assertIn("log_loss", report.calibration_metrics)
        self.assertIn("brier_score", report.calibration_metrics)
        self.assertEqual(
            set(report.predictions[0].class_probabilities),
            {"high_value", "standard"},
        )

    def test_uncertainty_can_be_disabled(self):
        output = self.regression_project.predict(uncertainty=False)
        report = self.regression_project.state.prediction_report
        generated_columns = [
            column
            for column in output.columns
            if column.startswith("AutoDQ_")
        ]

        self.assertEqual(generated_columns, ["AutoDQ_Prediction"])
        self.assertFalse(report.uncertainty_requested)
        self.assertFalse(report.uncertainty_available)
        self.assertIsNone(report.predictions[0].confidence)

    def test_persistence_preserves_interval_calibration(self):
        expected = self.regression_project.predict(
            confidence_level=0.9
        )
        bundle_path = self.root / "uncertainty_model"
        self.regression_project.save_model(
            str(bundle_path),
            overwrite=True,
        )
        restored = AutoDQ(str(self.regression_path))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            report = restored.load_model(str(bundle_path))

        actual = restored.predict(confidence_level=0.9)

        self.assertIsNotNone(report.uncertainty_calibration)
        self.assertEqual(
            report.uncertainty_calibration.method,
            "holdout_conformal",
        )
        np.testing.assert_allclose(
            expected[
                [
                    "AutoDQ_Prediction_Lower",
                    "AutoDQ_Prediction_Upper",
                ]
            ],
            actual[
                [
                    "AutoDQ_Prediction_Lower",
                    "AutoDQ_Prediction_Upper",
                ]
            ],
        )

    def test_legacy_model_warns_when_calibration_is_missing(self):
        model_report = self.regression_project.state.model_report
        calibration = model_report.uncertainty_calibration

        try:
            model_report.uncertainty_calibration = None
            output = self.regression_project.predict()
            report = self.regression_project.state.prediction_report
        finally:
            model_report.uncertainty_calibration = calibration

        self.assertNotIn("AutoDQ_Prediction_Lower", output.columns)
        self.assertFalse(report.uncertainty_available)
        self.assertTrue(
            any("Retrain" in warning for warning in report.warnings)
        )

    def test_invalid_uncertainty_controls_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "confidence_level"):
            self.regression_project.predict(confidence_level=1.0)

        with self.assertRaisesRegex(
            ValueError,
            "low_confidence_threshold",
        ):
            self.classification_project.predict(
                low_confidence_threshold=0
            )


if __name__ == "__main__":
    unittest.main()
