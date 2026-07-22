import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from autodq import AutoDQ
from autodq.explainability.engine import ExplainabilityEngine
from autodq.explainability.shap_visualizer import SHAPVisualizer
from autodq.ml.engine import MLEngine


class SHAPPlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(42)
        row_count = 80

        cls.regression_data = pd.DataFrame(
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
        cls.regression_data["revenue"] = (
            cls.regression_data["units"]
            * cls.regression_data["price"]
            * (1 - cls.regression_data["discount"])
            + rng.normal(0, 10, row_count)
        )

        cls.classification_data = pd.DataFrame(
            {
                "age": rng.integers(18, 75, row_count),
                "balance": rng.normal(5000, 1500, row_count),
                "tenure": rng.integers(0, 15, row_count),
                "segment": rng.choice(
                    ["consumer", "business"],
                    row_count,
                ),
            }
        )
        cls.classification_data["churned"] = (
            (
                cls.classification_data["balance"] < 4500
            )
            | (
                cls.classification_data["tenure"] < 3
            )
        ).astype(int)

        regression_model = MLEngine().train(
            df=cls.regression_data,
            target="revenue",
            algorithm="decision_tree_regressor",
            test_size=0.25,
            random_state=42,
        )
        classification_model = MLEngine().train(
            df=cls.classification_data,
            target="churned",
            algorithm="decision_tree_classifier",
            test_size=0.25,
            random_state=42,
        )
        linear_regression_model = MLEngine().train(
            df=cls.regression_data,
            target="revenue",
            algorithm="linear_regression",
            test_size=0.25,
            random_state=42,
        )
        logistic_model = MLEngine().train(
            df=cls.classification_data,
            target="churned",
            algorithm="logistic_regression",
            test_size=0.25,
            random_state=42,
        )

        engine = ExplainabilityEngine()
        cls.regression_report = engine.explain(
            model_report=regression_model,
            data=cls.regression_data,
            max_rows=20,
        )
        cls.classification_report = engine.explain(
            model_report=classification_model,
            data=cls.classification_data,
            max_rows=20,
        )
        cls.linear_regression_report = engine.explain(
            model_report=linear_regression_model,
            data=cls.regression_data,
            max_rows=20,
        )
        cls.logistic_report = engine.explain(
            model_report=logistic_model,
            data=cls.classification_data,
            max_rows=20,
        )

    def tearDown(self):
        plt.close("all")

    def test_regression_explanation_retains_plot_artifacts(self):
        report = self.regression_report

        self.assertEqual(report.method, "shap_tree_explainer")
        self.assertTrue(report.has_shap_artifacts)
        self.assertEqual(
            report.shap_artifacts.shap_values.shape[0],
            20,
        )
        self.assertNotIn("shap_artifacts", report.to_dict())

    def test_classification_selects_a_single_output(self):
        report = self.classification_report
        artifacts = report.shap_artifacts

        self.assertEqual(report.method, "shap_tree_explainer")
        self.assertTrue(report.has_shap_artifacts)
        self.assertEqual(artifacts.shap_values.ndim, 2)
        self.assertEqual(artifacts.output_index, 1)
        self.assertEqual(artifacts.output_name, 1)

    def test_linear_models_retain_plot_artifacts(self):
        for report in (
            self.linear_regression_report,
            self.logistic_report,
        ):
            with self.subTest(algorithm=report.algorithm):
                self.assertEqual(
                    report.method,
                    "shap_linear_explainer",
                )
                self.assertTrue(report.has_shap_artifacts)
                self.assertEqual(
                    report.shap_artifacts.shap_values.ndim,
                    2,
                )

    def test_all_regression_plots_export(self):
        visualizer = SHAPVisualizer(self.regression_report)
        feature = visualizer.artifacts.feature_names[0]

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            outputs = {
                "summary": output_dir / "summary.png",
                "bar": output_dir / "bar.svg",
                "beeswarm": output_dir / "beeswarm.png",
                "waterfall": output_dir / "waterfall.png",
                "dependence": output_dir / "dependence.png",
            }

            figures = [
                visualizer.summary(
                    save=outputs["summary"],
                    show=False,
                ),
                visualizer.bar(
                    save=outputs["bar"],
                    show=False,
                ),
                visualizer.beeswarm(
                    save=outputs["beeswarm"],
                    show=False,
                ),
                visualizer.waterfall(
                    row=0,
                    save=outputs["waterfall"],
                    show=False,
                ),
                visualizer.dependence(
                    feature=feature,
                    save=outputs["dependence"],
                    show=False,
                ),
            ]

            for figure in figures:
                self.assertIsNotNone(figure)

            self.assertEqual(
                len({id(figure) for figure in figures}),
                len(figures),
            )

            for output in outputs.values():
                self.assertTrue(output.exists(), output)
                self.assertGreater(output.stat().st_size, 0)

    def test_classification_plots_export(self):
        visualizer = SHAPVisualizer(self.classification_report)

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            bar_output = output_dir / "classification_bar.png"
            waterfall_output = (
                output_dir / "classification_waterfall.png"
            )

            visualizer.bar(save=bar_output, show=False)
            visualizer.waterfall(
                row=1,
                save=waterfall_output,
                show=False,
            )

            self.assertGreater(bar_output.stat().st_size, 0)
            self.assertGreater(waterfall_output.stat().st_size, 0)

    def test_invalid_waterfall_row_has_clear_error(self):
        visualizer = SHAPVisualizer(self.regression_report)

        with self.assertRaisesRegex(IndexError, "out of range"):
            visualizer.waterfall(row=1000, show=False)

    def test_invalid_dependence_feature_has_clear_error(self):
        visualizer = SHAPVisualizer(self.regression_report)

        with self.assertRaisesRegex(ValueError, "Unknown SHAP feature"):
            visualizer.dependence(
                feature="not_a_feature",
                show=False,
            )

    def test_project_runs_shap_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            dataset_path = directory_path / "regression.csv"
            output_path = directory_path / "project_summary.png"
            self.regression_data.to_csv(dataset_path, index=False)

            project = AutoDQ(
                str(dataset_path),
                target="revenue",
            )
            model_report = project.model(
                algorithm="decision_tree_regressor",
                use_engineered=False,
            )
            project.predict()
            explanation_report = project.explain(
                max_rows=20,
                use_engineered=False,
            )

            figure = project.visualize_shap(
                chart="summary",
                save=str(output_path),
                display=False,
            )

            self.assertEqual(
                model_report.algorithm,
                "decision_tree_regressor",
            )
            self.assertEqual(
                explanation_report.method,
                "shap_tree_explainer",
            )
            self.assertTrue(
                explanation_report.has_shap_artifacts
            )
            self.assertIsNotNone(figure)
            self.assertGreater(output_path.stat().st_size, 0)
            self.assertEqual(
                project.session.events[-1].step,
                "visualize_shap",
            )


if __name__ == "__main__":
    unittest.main()
