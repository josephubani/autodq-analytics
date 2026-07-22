import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from autodq import AutoDQ, VisualizationReport, VisualizationSpec
from autodq.visualization.notebook_renderer import (
    NotebookVisualizationRenderer,
)
from autodq.visualization.renderers.matplotlib_renderer import (
    MatplotlibVisualizationRenderer,
)


class RichVisualizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rng = np.random.default_rng(24)
        row_count = 60
        self.data = pd.DataFrame(
            {
                "region": rng.choice(
                    ["North", "South", "East", "West"],
                    row_count,
                ),
                "units": rng.integers(1, 25, row_count),
                "price": rng.uniform(5, 80, row_count),
            }
        )
        self.data["revenue"] = (
            self.data["units"] * self.data["price"]
        )
        self.dataset_path = self.root / "sales.csv"
        self.data.to_csv(self.dataset_path, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()
        plt.close("all")

    def _project(self):
        return AutoDQ(str(self.dataset_path), target="revenue")

    def _bar_chart(self) -> VisualizationSpec:
        return VisualizationSpec(
            chart_id="revenue_by_region",
            chart_type="bar",
            title="Revenue by Region",
            description="Regional revenue comparison.",
            data=[
                {"region": "North", "revenue": 1200},
                {"region": "South", "revenue": 900},
            ],
            x="region",
            y="revenue",
        )

    def test_project_visualize_wires_all_customization_options(self):
        project = self._project()
        report = project.visualize(
            chart="bar",
            x="region",
            y="revenue",
            display=False,
            title="Regional Performance",
            subtitle="Fiscal year overview",
            x_label="Sales region",
            y_label="Revenue (CAD)",
            theme="dark",
            color="#38bdf8",
            palette="colorblind",
            figsize=(11, 6),
            dpi=220,
            grid=False,
            legend=True,
            legend_position="upper right",
            transparent=True,
            save=str(self.root / "regional_performance.svg"),
        )
        chart = report.latest

        self.assertIs(
            project.get_visualization(chart.chart_id),
            chart,
        )
        self.assertEqual(chart.title, "Regional Performance")
        self.assertEqual(chart.style.subtitle, "Fiscal year overview")
        self.assertEqual(chart.style.x_label, "Sales region")
        self.assertEqual(chart.style.y_label, "Revenue (CAD)")
        self.assertEqual(chart.style.theme, "dark")
        self.assertEqual(chart.style.color, "#38bdf8")
        self.assertEqual(chart.style.palette, "colorblind")
        self.assertEqual(chart.style.figsize, (11.0, 6.0))
        self.assertEqual(chart.style.dpi, 220)
        self.assertFalse(chart.style.grid)
        self.assertTrue(chart.style.legend)
        self.assertTrue(chart.style.transparent)
        self.assertFalse(report.auto_display)
        self.assertTrue((self.root / "regional_performance.svg").is_file())

        renderer = MatplotlibVisualizationRenderer()
        figure, _ = renderer.build_figure(chart)

        try:
            axis = figure.axes[0]
            self.assertEqual(axis.get_xlabel(), "Sales region")
            self.assertEqual(axis.get_ylabel(), "Revenue (CAD)")
        finally:
            plt.close(figure)

    def test_reusable_chart_saves_png_svg_and_uses_template(self):
        chart = self._bar_chart().customize(
            template="publication",
            subtitle="Prepared for publication",
        )
        png_path = chart.save(self.root / "publication.png")
        svg_path = chart.save(self.root / "publication.svg")

        self.assertEqual(png_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertIn("<svg", svg_path.read_text(encoding="utf-8")[:500])

        renderer = MatplotlibVisualizationRenderer()
        figure, resolved = renderer.build_figure(chart)

        try:
            self.assertEqual(resolved["theme"], "journal")
            self.assertEqual(resolved["dpi"], 300)
            self.assertEqual(tuple(figure.get_size_inches()), (7.0, 4.5))
        finally:
            plt.close(figure)

    def test_chart_clone_show_and_style_reset_are_reusable(self):
        chart = self._bar_chart().customize(theme="dark", dpi=200)
        clone = chart.clone("revenue_for_slides").customize(
            template="presentation"
        )

        self.assertNotEqual(chart.chart_id, clone.chart_id)
        self.assertEqual(chart.style.theme, "dark")
        self.assertEqual(clone.style.template, "presentation")

        with patch.object(
            NotebookVisualizationRenderer,
            "show_chart",
        ) as show_chart:
            self.assertIs(clone.show(), clone)
            show_chart.assert_called_once_with(clone)

        clone.reset_style()
        self.assertIsNone(clone.style.theme)
        self.assertIsNone(clone.style.template)

    def test_rich_html_is_embedded_and_escapes_user_content(self):
        chart = self._bar_chart()
        chart.title = "Revenue <script>alert('x')</script>"
        report = VisualizationReport(charts=[chart])
        markup = report._repr_html_()

        self.assertIn("data:image/png;base64,", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<script>alert", markup)
        self.assertIn("autodq-gallery", markup)
        self.assertIn("autodq-card", markup)

    def test_notebook_renderer_automatically_displays_html_gallery(self):
        report = VisualizationReport(charts=[self._bar_chart()])
        renderer = NotebookVisualizationRenderer()

        with patch.object(renderer, "is_notebook", return_value=True), patch.object(
            renderer,
            "_display_html",
        ) as display_html:
            rendered = renderer.render(report)

        self.assertEqual(rendered[0]["chart_id"], "revenue_by_region")
        self.assertIsNone(rendered[0]["image_path"])
        display_html.assert_called_once()
        self.assertIn(
            "data:image/png;base64,",
            display_html.call_args.args[0],
        )

    def test_gallery_replaces_filters_customizes_and_exports(self):
        project = self._project()
        first = project.visualize(
            chart="bar",
            x="region",
            y="revenue",
            display=False,
            title="Initial title",
        )
        chart_id = first.latest.chart_id
        project.visualize(
            chart="bar",
            x="region",
            y="revenue",
            display=False,
            title="Updated title",
        )

        self.assertEqual(project.visualization_gallery.chart_count, 1)
        self.assertEqual(
            project.get_visualization(chart_id).title,
            "Updated title",
        )
        project.customize_visualization(
            chart_id,
            theme="journal",
            grid=False,
        )
        filtered = project.filter_visualizations(
            chart_type="bar",
            stage="current",
        )
        self.assertEqual([chart.chart_id for chart in filtered], [chart_id])

        exported = project.save_visualizations(
            str(self.root / "gallery"),
            format="svg",
        )
        self.assertEqual(len(exported), 1)
        self.assertEqual(exported[0].suffix, ".svg")
        self.assertTrue(exported[0].is_file())

    def test_workspace_gallery_exports_to_workspace_by_default(self):
        project = AutoDQ.create_workspace(
            "Notebook Workspace",
            str(self.dataset_path),
            target="revenue",
            workspace_root=str(self.root / "workspaces"),
        )
        project.visualize(
            chart="scatter",
            x="units",
            y="revenue",
            display=False,
            template="presentation",
        )
        exported = project.save_visualizations(format="png")

        self.assertEqual(len(exported), 1)
        self.assertTrue(exported[0].is_file())
        self.assertTrue(
            exported[0].is_relative_to(project.workspace.visualizations_dir)
        )

    def test_invalid_customization_and_export_are_clear(self):
        chart = self._bar_chart()

        with self.assertRaisesRegex(ValueError, "theme"):
            chart.customize(theme="neon")

        with self.assertRaisesRegex(ValueError, "figsize"):
            chart.customize(figsize=(0, 4))

        with self.assertRaisesRegex(ValueError, "format"):
            chart.save(self.root / "chart.bmp")


if __name__ == "__main__":
    unittest.main()
