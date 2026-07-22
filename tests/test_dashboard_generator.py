import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import AutoDQ, Dashboard, DashboardMetric
from autodq.visualization import VisualizationReport, VisualizationSpec


class DashboardGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rng = np.random.default_rng(111)
        row_count = 72
        self.data = pd.DataFrame(
            {
                "region": rng.choice(
                    ["North", "South", "West"],
                    row_count,
                ),
                "units": rng.integers(1, 40, row_count).astype(float),
                "price": rng.uniform(8, 110, row_count),
                "discount": rng.uniform(0, 0.25, row_count),
            }
        )
        self.data["revenue"] = (
            self.data["units"]
            * self.data["price"]
            * (1 - self.data["discount"])
            + rng.normal(0, 12, row_count)
        )
        self.data.loc[3, "units"] = np.nan
        self.data.loc[5, "region"] = None
        self.data = pd.concat(
            [self.data, self.data.iloc[[0]]],
            ignore_index=True,
        )
        self.dataset_path = self.root / "sales.csv"
        self.data.to_csv(self.dataset_path, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _project(self, target=None):
        return AutoDQ(str(self.dataset_path), target=target)

    def _charts(self):
        return [
            VisualizationSpec(
                chart_id="revenue_by_region",
                chart_type="bar",
                title="Revenue by Region",
                description="Regional revenue comparison.",
                data=[
                    {"region": "North", "revenue": 1200.0},
                    {"region": "South", "revenue": 900.0},
                ],
                x="region",
                y="revenue",
                stage="current",
            ),
            VisualizationSpec(
                chart_id="units_vs_revenue",
                chart_type="scatter",
                title="Units vs Revenue",
                description="Sales relationship.",
                data=[
                    {"units": 4, "revenue": 320.0},
                    {"units": 10, "revenue": 860.0},
                ],
                x="units",
                y="revenue",
                stage="current",
            ),
        ]

    def test_project_dashboard_prepares_analysis_and_core_metrics(self):
        project = self._project()
        dashboard = project.dashboard(
            include_charts=False,
            auto_display=False,
        )

        self.assertIsInstance(dashboard, Dashboard)
        self.assertIs(project.state.dashboard_report, dashboard)
        self.assertIsNotNone(project.state.profile_report)
        self.assertIsNotNone(project.state.diagnosis_report)
        self.assertEqual(dashboard.stage, "current")
        self.assertEqual(dashboard.get_metric("rows").value, len(self.data))
        self.assertEqual(
            dashboard.get_metric("columns").value,
            len(self.data.columns),
        )
        self.assertEqual(dashboard.get_metric("missing_cells").value, 2)
        self.assertEqual(dashboard.get_metric("duplicate_rows").value, 1)
        self.assertEqual(dashboard.preview_row_count, 20)
        self.assertIn("dashboard", project.session.steps_completed)
        self.assertIsNone(dashboard._repr_html_())

    def test_default_dashboard_generates_and_embeds_automatic_charts(self):
        project = self._project()
        dashboard = project.dashboard(auto_display=False)

        self.assertIsNotNone(project.state.visualization_report)
        self.assertGreaterEqual(dashboard.chart_count, 1)
        self.assertTrue(any(chart.recommended for chart in dashboard.charts))
        self.assertIn("data:image/png;base64,", dashboard.to_html())

    def test_standalone_html_embeds_charts_controls_and_escapes_content(self):
        project = self._project()
        project.load()
        charts = self._charts()
        charts[0].title = "Revenue <script>alert('bad')</script>"
        project.state.visualization_report = VisualizationReport(charts=charts)
        dashboard = project.dashboard(
            title="Board <script>alert('title')</script>",
            theme="dark",
            auto_display=False,
        )
        markup = dashboard.to_html()

        self.assertIn("data:image/png;base64,", markup)
        self.assertIn('data-theme="dark"', markup)
        self.assertIn('id="chart-search"', markup)
        self.assertIn('id="chart-type"', markup)
        self.assertIn('id="theme-toggle"', markup)
        self.assertIn('id="download-preview"', markup)
        self.assertIn("&lt;script&gt;alert", markup)
        self.assertNotIn("<script>alert('bad')</script>", markup)
        self.assertNotIn("<script>alert('title')</script>", markup)
        self.assertNotIn('src="http', markup)
        self.assertNotIn('href="http', markup)

        dashboard.auto_display = True
        notebook_markup = dashboard._repr_html_()
        self.assertIn("<iframe", notebook_markup)
        self.assertIn("srcdoc=", notebook_markup)
        self.assertIn("allow-scripts", notebook_markup)

        with self.assertRaisesRegex(ValueError, "height"):
            dashboard.to_notebook_html(height=100)

    def test_dashboard_save_requires_html_and_explicit_overwrite(self):
        project = self._project()
        dashboard = project.dashboard(
            include_charts=False,
            auto_display=False,
        )
        output = self.root / "dashboard.html"
        saved = dashboard.save(output)

        self.assertEqual(saved, output.resolve())
        self.assertEqual(dashboard.path, output.resolve())
        self.assertTrue(output.read_text(encoding="utf-8").startswith("<!doctype html>"))

        with self.assertRaises(FileExistsError):
            dashboard.save(output)

        self.assertEqual(dashboard.save(output, overwrite=True), output.resolve())

        with self.assertRaisesRegex(ValueError, "html"):
            dashboard.save(self.root / "dashboard.pdf")

    def test_dashboard_selects_charts_by_id_and_handles_render_failure(self):
        project = self._project()
        project.load()
        charts = self._charts()
        project.state.visualization_report = VisualizationReport(charts=charts)
        dashboard = project.dashboard(
            chart_ids=["units_vs_revenue", "revenue_by_region"],
            max_charts=1,
            auto_display=False,
        )

        self.assertEqual(dashboard.chart_count, 1)
        self.assertEqual(dashboard.charts[0].chart_id, "units_vs_revenue")

        with self.assertRaisesRegex(KeyError, "not found"):
            project.dashboard(
                chart_ids=["missing_chart"],
                auto_display=False,
            )

        broken = VisualizationSpec(
            chart_id="broken",
            chart_type="not-a-chart",
            title="Broken chart",
            description="Exercises graceful dashboard degradation.",
            data=[],
        )
        project.state.visualization_report = VisualizationReport(
            charts=[broken]
        )
        degraded = project.dashboard(auto_display=False)
        markup = degraded.to_html()

        self.assertIn("Chart could not be rendered", markup)
        self.assertEqual(len(degraded.warnings), 1)

    def test_best_stage_uses_cleaned_then_engineered_data(self):
        project = self._project()
        project.load()
        project.state.cleaned_data = project.data.drop_duplicates().copy()
        project.state.cleaned_data["units"] = (
            project.state.cleaned_data["units"].fillna(0)
        )
        cleaned = project.dashboard(
            stage="best",
            include_charts=False,
            auto_display=False,
        )

        self.assertEqual(cleaned.stage, "cleaned")
        self.assertEqual(
            cleaned.get_metric("rows").value,
            len(project.state.cleaned_data),
        )
        self.assertEqual(cleaned.get_metric("missing_cells").value, 1)

        project.state.engineered_data = project.state.cleaned_data.assign(
            net_price=lambda frame: frame["price"] * (1 - frame["discount"])
        )
        engineered = project.dashboard(
            stage="best",
            include_charts=False,
            auto_display=False,
        )

        self.assertEqual(engineered.stage, "engineered")
        self.assertEqual(
            engineered.get_metric("columns").value,
            len(self.data.columns) + 1,
        )

    def test_model_prediction_and_uncertainty_are_reused(self):
        project = self._project(target="revenue")
        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )
        project.predict(confidence_level=0.9)
        dashboard = project.dashboard(
            include_charts=False,
            auto_display=False,
        )

        self.assertEqual(dashboard.model["target"], "revenue")
        self.assertEqual(
            dashboard.model["algorithm"],
            project.state.model_report.algorithm,
        )
        self.assertEqual(
            dashboard.prediction["prediction_count"],
            len(self.data),
        )
        self.assertTrue(dashboard.prediction["uncertainty_available"])
        self.assertEqual(
            dashboard.prediction["confidence_level"],
            0.9,
        )
        self.assertIn("Model & predictions", dashboard.to_html())

    def test_workspace_relative_output_is_saved_under_reports(self):
        project = AutoDQ.create_workspace(
            "Dashboard Workspace",
            str(self.dataset_path),
            workspace_root=str(self.root / "workspaces"),
        )
        dashboard = project.dashboard(
            output="sales-dashboard.html",
            include_charts=False,
            auto_display=False,
        )

        expected = project.workspace.reports_dir / "sales-dashboard.html"
        self.assertEqual(dashboard.path, expected.resolve())
        self.assertTrue(expected.is_file())

    def test_dashboard_is_in_json_and_html_project_reports(self):
        project = self._project()
        dashboard = project.dashboard(
            include_charts=False,
            auto_display=False,
        )
        report = project.reporting_engine.build_report(
            project.state,
            project.session,
            output_dir=self.root / "report-assets",
        )
        json_output = self.root / "report.json"
        html_output = self.root / "report.html"
        project.reporting_engine.export(report, str(json_output))
        project.reporting_engine.export(report, str(html_output))
        payload = json.loads(json_output.read_text(encoding="utf-8"))
        markup = html_output.read_text(encoding="utf-8")

        self.assertEqual(payload["dashboard"]["title"], dashboard.title)
        self.assertEqual(
            payload["dashboard"]["metric_count"],
            dashboard.metric_count,
        )
        self.assertIn("Generated Dashboard", markup)
        self.assertIn(dashboard.title, markup)

    def test_invalid_dashboard_options_fail_clearly(self):
        project = self._project()

        with self.assertRaisesRegex(ValueError, "theme"):
            project.dashboard(
                theme="neon",
                include_charts=False,
                auto_display=False,
            )

        with self.assertRaisesRegex(ValueError, "stage"):
            project.dashboard(
                stage="future",
                include_charts=False,
                auto_display=False,
            )

        with self.assertRaisesRegex(ValueError, "max_preview_rows"):
            project.dashboard(
                max_preview_rows=-1,
                include_charts=False,
                auto_display=False,
            )

        with self.assertRaisesRegex(ValueError, "chart_ids"):
            project.dashboard(
                chart_ids=["chart"],
                include_charts=False,
                auto_display=False,
            )

        with self.assertRaisesRegex(ValueError, "html"):
            project.dashboard(
                output=str(self.root / "dashboard.json"),
                include_charts=False,
                auto_display=False,
            )

        with self.assertRaisesRegex(ValueError, "status"):
            DashboardMetric(
                key="invalid",
                label="Invalid",
                value=0,
                display="0",
                status="unknown",
            )


if __name__ == "__main__":
    unittest.main()
