import io
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd

from autodq import (
    ADQLCellParser,
    ADQLFileRunner,
    ADQLValidationError,
    AutoDQ,
)
from autodq.cli import (
    _dataframe_html,
    _recommendations_html,
    _value_html,
    main,
)
from autodq.vscode import extension_path, install_extension


class ADQLStandaloneFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.data = pd.DataFrame(
            {
                "Region": ["North", "South", "North", "West"],
                "Revenue": [100.0, 150.0, 75.0, 200.0],
                "Units": [2, 3, 1, 4],
            }
        )
        self.dataset = self.root / "sales.csv"
        self.data.to_csv(self.dataset, index=False)
        self.script = self.root / "analysis.adql"
        self.script.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Profile]
PROFILE;
# %% [Regional totals]
SELECT Region, SUM(Revenue) AS total_revenue
FROM CURRENT
GROUP BY Region
ORDER BY total_revenue DESC;
""",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_cell_parser_reads_shebang_and_named_cells(self):
        document = ADQLCellParser().read(self.script)

        self.assertEqual(document.cell_count, 3)
        self.assertEqual(
            [cell.title for cell in document.cells],
            ["Dataset", "Profile", "Regional totals"],
        )
        self.assertIn("DATASET", document.cell(1).source)
        self.assertIn("SELECT", document.cell(3).source)

    def test_markdown_cells_are_preserved_and_skipped_by_execution(self):
        markdown = self.root / "markdown.adql"
        markdown.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [markdown] Analysis notes
# Sales analysis

This cell is rendered as Markdown and is not ADQL code.
# %% [Rows]
HEAD 2;
""",
            encoding="utf-8",
        )
        document = ADQLCellParser().read(markdown)
        result = ADQLFileRunner().run(markdown)

        self.assertEqual(document.cell(2).kind, "markdown")
        self.assertEqual(document.cell(2).title, "Analysis notes")
        self.assertIn("This cell is rendered", document.cell(2).source)
        self.assertTrue(result.success)
        self.assertEqual(result.cell_runs[1].result.statement_count, 0)
        self.assertEqual(len(result.data), 2)

    def test_standalone_file_runs_all_cells_relative_to_its_location(self):
        result = ADQLFileRunner().run(self.script)

        self.assertTrue(result.success)
        self.assertEqual(result.completed_cell_count, 3)
        self.assertEqual(result.project.target, "Revenue")
        self.assertEqual(result.data.iloc[0]["Region"], "West")
        self.assertEqual(result.source_name, str(self.script.resolve()))

    def test_cell_only_and_through_cell_modes(self):
        runner = ADQLFileRunner()
        selected = runner.run(self.script, cell=3)
        cumulative = runner.run(self.script, through_cell=2)

        self.assertTrue(selected.success)
        self.assertEqual(len(selected.cell_runs), 1)
        self.assertEqual(selected.cell_runs[0].cell.number, 3)
        self.assertEqual(len(selected.data), 3)
        self.assertTrue(cumulative.success)
        self.assertEqual(len(cumulative.cell_runs), 2)
        self.assertIsNotNone(cumulative.project.state.profile_report)

    def test_project_run_adql_preserves_existing_project_and_cells(self):
        project = AutoDQ(str(self.dataset), target="Revenue")
        result = project.run_adql(
            self.script,
            through_cell=3,
            auto_display=False,
        )

        self.assertIs(result.project, project)
        self.assertEqual(len(result.cell_runs), 3)
        self.assertEqual(len(result.data), 3)

    def test_standalone_validation_requires_dataset_declaration_or_override(self):
        no_dataset = self.root / "no-dataset.adql"
        no_dataset.write_text("HEAD 2;", encoding="utf-8")
        runner = ADQLFileRunner()

        with self.assertRaisesRegex(ADQLValidationError, "DATASET"):
            runner.validate(no_dataset)

        document = runner.validate(no_dataset, dataset=self.dataset)
        self.assertEqual(document.cell_count, 1)

    def test_cli_runs_shorthand_lists_cells_and_writes_json(self):
        output = self.root / "result.json"
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                [str(self.script), "--through-cell", "3", "--json", str(output)]
            )
            cells_code = main(["cells", str(self.script)])
            validate_code = main(["validate", str(self.script)])

        self.assertEqual(exit_code, 0, stderr.getvalue())
        self.assertEqual(cells_code, 0)
        self.assertEqual(validate_code, 0)
        self.assertIn("ADQL completed", stdout.getvalue())
        self.assertIn("Regional totals", stdout.getvalue())
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(payload["success"])
        self.assertEqual(payload["cell_count"], 3)

    def test_notebook_json_returns_only_selected_cell_as_rich_html(self):
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run",
                    str(self.script),
                    "--through-cell",
                    "3",
                    "--notebook-json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["cell"]["number"], 3)
        self.assertEqual(payload["protocol"], "autodq-notebook-v1")
        self.assertEqual(
            [item["mime"] for item in payload["outputs"]],
            ["text/plain", "text/html"],
        )
        self.assertIn("total_revenue", payload["outputs"][1]["data"])
        self.assertIn("autodq-output-toggle", payload["outputs"][1]["data"])
        self.assertIn("Click to show or hide", payload["outputs"][1]["data"])
        self.assertIn("<details", payload["outputs"][1]["data"])
        self.assertNotIn("Profile completed", stdout.getvalue())

    def test_notebook_json_renders_visualization_as_png(self):
        visualization = self.root / "visualization.adql"
        visualization.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Chart]
VISUALIZE bar X Region Y Revenue TITLE "Revenue by Region";
""",
            encoding="utf-8",
        )
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run",
                    str(visualization),
                    "--through-cell",
                    "2",
                    "--notebook-json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        image_output = next(
            item
            for item in payload["outputs"]
            if item["mime"] == "image/png"
        )
        image = base64.b64decode(image_output["data"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["cell"]["number"], 2)
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(
            image_output["metadata"]["title"],
            "Revenue by Region",
        )

    def test_notebook_json_renders_profile_and_diagnosis_reports(self):
        quality = self.root / "quality.adql"
        quality.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Quality]
PROFILE;
DIAGNOSE;
""",
            encoding="utf-8",
        )
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run",
                    str(quality),
                    "--through-cell",
                    "2",
                    "--notebook-json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        html_outputs = [
            item["data"]
            for item in payload["outputs"]
            if item["mime"] == "text/html"
        ]

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(html_outputs), 2)
        self.assertIn("Dataset Profile", html_outputs[0])
        self.assertIn("Semantic type", html_outputs[0])
        self.assertIn("Data Quality Diagnosis", html_outputs[1])
        self.assertIn("Quality score", html_outputs[1])

    def test_auto_runs_from_adql_and_renders_workflow_summary(self):
        automatic = self.root / "automatic.adql"
        automatic.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Automatic workflow]
AUTO MODE review VISUALIZE false REPORT "reports/auto.json";
""",
            encoding="utf-8",
        )
        result = ADQLFileRunner().run(automatic)
        auto_result = result.cell_runs[-1].result.latest.value
        report = self.root / "reports" / "auto.json"

        self.assertTrue(result.success)
        self.assertTrue(auto_result.success)
        self.assertEqual(auto_result.config.mode, "review")
        self.assertEqual(auto_result.config.report_output, str(report.resolve()))
        self.assertTrue(report.is_file())

        notebook = self.root / "automatic-notebook.adql"
        notebook.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Automatic workflow]
AUTO MODE review VISUALIZE false;
""",
            encoding="utf-8",
        )
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run",
                    str(notebook),
                    "--through-cell",
                    "2",
                    "--notebook-json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        auto_html = next(
            item["data"]
            for item in payload["outputs"]
            if item["mime"] == "text/html"
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("AutoDQ Automatic Workflow", auto_html)
        self.assertIn("Automatic Workflow", auto_html)
        self.assertIn("Click to show or hide", auto_html)

    def test_notebook_json_renders_other_structured_reports(self):
        reports = self.root / "reports.adql"
        reports.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Statistics]
STATISTICS;
""",
            encoding="utf-8",
        )
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                ["run", str(reports), "--through-cell", "2", "--notebook-json"]
            )

        payload = json.loads(stdout.getvalue())
        markup = next(
            item["data"]
            for item in payload["outputs"]
            if item["mime"] == "text/html"
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("Statistics", markup)
        self.assertIn("Descriptive", markup)

    def test_notebook_dataframe_preview_limits_rows_and_columns(self):
        frame = pd.DataFrame(
            {
                f"column_{column}": range(40)
                for column in range(25)
            }
        )

        markup = _dataframe_html(frame, limit=5, column_limit=3)

        self.assertIn("Showing 5 of 40 rows", markup)
        self.assertIn("showing 3 of 25 columns", markup)
        self.assertIn("Output truncated", markup)
        self.assertIn("column_2", markup)
        self.assertNotIn("column_3", markup)
        self.assertEqual(markup.count("<tr"), 6)

    def test_notebook_structured_preview_replaces_oversized_rich_html(self):
        class OversizedReport:
            def to_html(self):
                return "<div>" + ("unbounded-output " * 2_000) + "</div>"

            def to_dict(self):
                return {
                    "summary": "available",
                    "records": [
                        {"row": index, "details": "x" * 1_000}
                        for index in range(100)
                    ],
                }

        markup = _value_html(
            "review",
            OversizedReport(),
            item_limit=5,
            character_limit=2_000,
        )

        self.assertIn("Review", markup)
        self.assertIn("Summary", markup)
        self.assertIn("Output truncated", markup)
        self.assertIn("additional item(s) omitted", markup)
        self.assertNotIn("unbounded-output", markup)
        self.assertNotIn("<pre", markup)
        self.assertIn("autodq-structured-table", markup)
        self.assertLess(len(markup), 20_000)

    def test_notebook_nested_analytics_render_as_tables_not_json(self):
        markup = _value_html(
            "statistics",
            {
                "descriptive": {
                    "Customer_Age": {
                        "column": "Customer_Age",
                        "count": 4_908,
                        "missing": 127,
                        "missing_percent": 2.52,
                        "mean": 35.9423,
                        "median": 36.0,
                        "minimum": 0.0,
                        "maximum": 120.0,
                        "std": 11.2465,
                    }
                },
                "distributions": {
                    "Customer_Age": {
                        "column": "Customer_Age",
                        "distribution_type": "approximately_normal",
                        "skewness_level": "approximately_symmetric",
                        "tail_risk": "low_tail_risk",
                        "confidence": 0.75,
                        "explanation": "The distribution is approximately normal.",
                    }
                },
            },
        )

        self.assertIn("Descriptive", markup)
        self.assertIn("Customer_Age", markup)
        self.assertIn("4,908", markup)
        self.assertIn("35.9423", markup)
        self.assertIn("75.0%", markup)
        self.assertIn("autodq-structured-table", markup)
        self.assertNotIn("<pre", markup)
        self.assertNotIn('&quot;Customer_Age&quot;', markup)

    def test_notebook_validation_sections_render_as_readable_metrics(self):
        markup = _value_html(
            "validate",
            {
                "quality_score_before": 87.92,
                "quality_score_after": 97.88,
                "quality_score_change": 9.96,
                "missing_values": {
                    "name": "missing_values",
                    "before": 382,
                    "after": 60,
                    "change": -322,
                },
                "duplicate_rows": {
                    "name": "duplicate_rows",
                    "before": 33,
                    "after": 0,
                    "change": -33,
                },
            },
        )

        self.assertIn("Quality Score Before", markup)
        self.assertIn("97.88", markup)
        self.assertIn("Missing Values", markup)
        self.assertIn("Duplicate Rows", markup)
        self.assertIn("-322", markup)
        self.assertNotIn("<pre", markup)
        self.assertNotIn('&quot;before&quot;', markup)

    def test_notebook_correlations_render_as_matrix_and_relationship_table(self):
        markup = _value_html(
            "correlation",
            {
                "matrix": {
                    "Revenue": {"Revenue": 1.0, "Profit": 0.83},
                    "Profit": {"Revenue": 0.83, "Profit": 1.0},
                },
                "relationships": [
                    {
                        "feature_a": "Revenue",
                        "feature_b": "Profit",
                        "correlation": 0.83,
                        "strength": "strong",
                        "direction": "positive",
                    }
                ],
            },
        )

        self.assertIn("autodq-matrix-table", markup)
        self.assertIn("Relationships", markup)
        self.assertIn("0.83", markup)
        self.assertIn("Strong", markup)
        self.assertIn("Positive", markup)
        self.assertNotIn("<pre", markup)

    def test_notebook_model_explain_and_blue_outputs_use_structured_views(self):
        reports = {
            "model": {
                "algorithm": "random_forest_regressor",
                "problem_type": "regression",
                "metrics": {"r2": 0.91, "mae": 18.2},
                "feature_importance": [
                    {"feature": "Profit", "importance": 0.72}
                ],
            },
            "explain": {
                "method": "shap_tree_explainer",
                "explanation_count": 20,
                "row_explanations": [
                    {
                        "row_id": 0,
                        "feature": "Profit",
                        "importance": 0.72,
                        "direction": "positive",
                    }
                ],
            },
            "blue": [
                {
                    "title": "Residuals vs Fitted Values",
                    "status": "failed",
                    "severity": "high",
                    "confidence": 0.9,
                    "interpretation": "Residual variance is not constant.",
                    "recommendation": "Use robust standard errors.",
                }
            ],
        }

        for title, report in reports.items():
            with self.subTest(title=title):
                markup = _value_html(title, report)

                self.assertIn("autodq-structured-table", markup)
                self.assertNotIn("<pre", markup)
                self.assertNotIn('&quot;status&quot;', markup)

        self.assertIn("Feature Importance", _value_html("model", reports["model"]))
        self.assertIn("Row Explanations", _value_html("explain", reports["explain"]))
        self.assertIn("Residuals vs Fitted Values", _value_html("blue", reports["blue"]))
        self.assertIn("90.0%", _value_html("blue", reports["blue"]))

    def test_notebook_recommendations_render_as_cards_instead_of_json(self):
        markup = _recommendations_html(
            [
                {
                    "issue_type": "missing_values",
                    "strategy": "median",
                    "reason": "Median is robust for this age distribution.",
                    "affected_columns": ["Customer_Age"],
                    "action": "Apply median strategy to Customer_Age.",
                    "priority": "low",
                    "risk": "Imputation can alter the distribution.",
                    "confidence": 0.88,
                }
            ]
        )

        self.assertIn("Cleaning Recommendations", markup)
        self.assertIn("autodq-recommendation", markup)
        self.assertIn("Apply median strategy to Customer_Age.", markup)
        self.assertIn("88% confidence", markup)
        self.assertIn("Why this is recommended", markup)
        self.assertIn("Customer_Age", markup)
        self.assertNotIn('&quot;issue_type&quot;', markup)

    def test_vscode_extension_is_bundled_and_installable(self):
        source = extension_path()
        package = json.loads(
            (source / "package.json").read_text(encoding="utf-8")
        )
        extension = (source / "extension.js").read_text(encoding="utf-8")
        destination = self.root / "vscode-extension"
        installed = install_extension(destination)

        self.assertEqual(package["contributes"]["languages"][0]["id"], "adql")
        self.assertEqual(
            package["contributes"]["notebooks"][0]["type"],
            "autodq-adql-notebook",
        )
        self.assertIn("ADQLNotebookSerializer", extension)
        self.assertIn("ADQLKernelSession", extension)
        self.assertIn("['kernel', notebook.uri.fsPath]", extension)
        self.assertIn("NotebookCellKind.Markup", extension)
        self.assertIn("new vscode.NotebookCellOutputItem", extension)
        self.assertNotIn("NotebookCellOutputItem.png", extension)
        self.assertIn("notebook.maxOutputRows", extension)
        self.assertIn("notebook.maxOutputCharacters", extension)
        self.assertEqual(package["version"], "0.2.2")
        language_icon = package["contributes"]["languages"][0]["icon"]
        self.assertEqual(language_icon["light"], "./icons/adql-light.svg")
        self.assertEqual(language_icon["dark"], "./icons/adql-dark.svg")
        self.assertTrue((source / "icons" / "adql-light.svg").is_file())
        self.assertTrue((source / "icons" / "adql-dark.svg").is_file())
        self.assertEqual(
            package["contributes"]["configuration"]["properties"]
            ["autodq.notebook.maxOutputRows"]["default"],
            25,
        )
        self.assertTrue((installed / "package.json").is_file())
        self.assertTrue((installed / "icons" / "adql-light.svg").is_file())
        self.assertTrue((installed / "icons" / "adql-dark.svg").is_file())

    def test_persistent_kernel_bootstraps_once_and_retains_project(self):
        process = subprocess.Popen(
            [sys.executable, "-m", "autodq", "kernel", str(self.script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            process.stdin.write(json.dumps({"id": 1, "cell": 2}) + "\n")
            process.stdin.flush()
            first = json.loads(process.stdout.readline())
            process.stdin.write(json.dumps({"id": 2, "cell": 3}) + "\n")
            process.stdin.flush()
            second = json.loads(process.stdout.readline())
        finally:
            if process.stdin:
                process.stdin.write(json.dumps({"action": "shutdown"}) + "\n")
                process.stdin.flush()
            process.wait(timeout=15)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()

        self.assertTrue(first["success"])
        self.assertEqual(first["session"]["executed_cells"], [1, 2])
        self.assertTrue(second["success"])
        self.assertEqual(second["session"]["executed_cells"], [1, 2, 3])
        self.assertEqual(second["cell"]["number"], 3)

    def test_cli_import_does_not_eagerly_load_matplotlib(self):
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import autodq.cli; "
                    "print('matplotlib.pyplot' in sys.modules); "
                    "print('statsmodels.api' in sys.modules)"
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(process.stdout.strip().splitlines(), ["False", "False"])


if __name__ == "__main__":
    unittest.main()
