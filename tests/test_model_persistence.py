import json
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import AutoDQ


class ModelPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rng = np.random.default_rng(42)
        row_count = 80

        self.regression_data = pd.DataFrame(
            {
                "units": rng.integers(1, 30, row_count),
                "price": rng.uniform(5, 100, row_count),
                "discount": rng.uniform(0, 0.3, row_count),
                "region": rng.choice(
                    ["North", "South", "West"],
                    row_count,
                ),
            }
        )
        self.regression_data["revenue"] = (
            self.regression_data["units"]
            * self.regression_data["price"]
            * (1 - self.regression_data["discount"])
            + rng.normal(0, 10, row_count)
        )
        self.regression_path = self.root / "regression.csv"
        self.regression_data.to_csv(
            self.regression_path,
            index=False,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _trained_regression_project(self) -> AutoDQ:
        project = AutoDQ(
            str(self.regression_path),
            target="revenue",
        )
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )
        return project

    def _load_model(self, project, bundle_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return project.load_model(str(bundle_path))

    def test_regression_round_trip_preserves_predictions_and_shap(self):
        project = self._trained_regression_project()
        predictions_before = project.predict()[
            "AutoDQ_Prediction"
        ].to_numpy()
        bundle_path = self.root / "models" / "revenue_model"
        bundle = project.save_model(str(bundle_path))
        self.assertIs(project.state.model_bundle, bundle)

        self.assertTrue(
            (bundle.path / "model.joblib").is_file()
        )
        self.assertTrue(
            (bundle.path / "manifest.json").is_file()
        )
        self.assertEqual(bundle.manifest.format_version, 1)
        self.assertEqual(
            bundle.manifest.feature_columns,
            ["units", "price", "discount", "region"],
        )
        self.assertEqual(
            bundle.manifest.model_report["predictions"],
            [],
        )

        restored = AutoDQ(str(self.regression_path))
        report = self._load_model(restored, bundle_path)
        self.assertIsNotNone(restored.state.model_bundle)
        predictions_after = restored.predict()[
            "AutoDQ_Prediction"
        ].to_numpy()

        np.testing.assert_allclose(
            predictions_before,
            predictions_after,
        )
        self.assertEqual(report.target, "revenue")
        self.assertEqual(
            report.feature_dtypes,
            bundle.manifest.feature_dtypes,
        )

        explanation = restored.explain(
            max_rows=10,
            use_engineered=False,
        )
        self.assertTrue(explanation.has_shap_artifacts)

    def test_classification_round_trip_preserves_predictions(self):
        data = self.regression_data.drop(columns=["revenue"]).copy()
        data["churned"] = (
            (data["price"] < 45) | (data["units"] < 5)
        ).astype(int)
        dataset_path = self.root / "classification.csv"
        data.to_csv(dataset_path, index=False)

        project = AutoDQ(
            str(dataset_path),
            target="churned",
        )
        project.model(
            algorithm="decision_tree_classifier",
            use_engineered=False,
        )
        predictions_before = project.predict()[
            "AutoDQ_Prediction"
        ].to_numpy()
        bundle_path = self.root / "classification_model"
        project.save_model(str(bundle_path))

        restored = AutoDQ(str(dataset_path))
        self._load_model(restored, bundle_path)
        predictions_after = restored.predict()[
            "AutoDQ_Prediction"
        ].to_numpy()

        np.testing.assert_array_equal(
            predictions_before,
            predictions_after,
        )

    def test_overwrite_is_explicit(self):
        project = self._trained_regression_project()
        bundle_path = self.root / "revenue_model"
        project.save_model(str(bundle_path))

        with self.assertRaises(FileExistsError):
            project.save_model(str(bundle_path))

        replacement = project.save_model(
            str(bundle_path),
            overwrite=True,
        )
        self.assertTrue(
            (replacement.path / "manifest.json").is_file()
        )

    def test_checksum_detects_modified_model_file(self):
        project = self._trained_regression_project()
        bundle_path = self.root / "revenue_model"
        project.save_model(str(bundle_path))

        with (bundle_path / "model.joblib").open("ab") as stream:
            stream.write(b"modified")

        restored = AutoDQ(str(self.regression_path))

        with self.assertRaisesRegex(
            ValueError,
            "checksum verification failed",
        ):
            self._load_model(restored, bundle_path)

    def test_prediction_schema_validation(self):
        project = self._trained_regression_project()
        bundle_path = self.root / "revenue_model"
        project.save_model(str(bundle_path))
        restored = AutoDQ(str(self.regression_path))
        self._load_model(restored, bundle_path)

        missing = self.regression_data.drop(
            columns=["revenue", "price"]
        )

        with self.assertRaisesRegex(
            ValueError,
            "missing required model features",
        ):
            restored.predict(missing)

        extra = self.regression_data.drop(
            columns=["revenue"]
        ).copy()
        extra["unused"] = 1
        restored.predict(extra)
        self.assertIn(
            "Ignored unexpected prediction features",
            restored.state.prediction_report.warnings[0],
        )

        with self.assertRaisesRegex(
            ValueError,
            "unexpected features",
        ):
            restored.predict(extra, strict_schema=True)

    def test_unsupported_manifest_version_is_rejected(self):
        project = self._trained_regression_project()
        bundle_path = self.root / "revenue_model"
        project.save_model(str(bundle_path))
        manifest_path = bundle_path / "manifest.json"

        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)

        manifest["format_version"] = 999

        with manifest_path.open("w", encoding="utf-8") as stream:
            json.dump(manifest, stream)

        restored = AutoDQ(str(self.regression_path))

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported model bundle format version",
        ):
            self._load_model(restored, bundle_path)


if __name__ == "__main__":
    unittest.main()
