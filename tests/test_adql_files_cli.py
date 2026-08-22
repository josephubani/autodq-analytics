import io
import base64
import json
import re
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
    _profile_html,
    _recommendations_html,
    _session_html,
    _value_html,
    main,
)
from autodq.commands.grammar import (
    AGGREGATE_FUNCTIONS,
    AUTO_OPTIONS,
    BLUE_OPTIONS,
    DASHBOARD_OPTIONS,
    EXPLAIN_OPTIONS,
    GALLERY_STYLE_OPTIONS,
    MODEL_OPTIONS,
    PREDICT_OPTIONS,
    SHAP_OPTIONS,
    SET_TYPE_OPTIONS,
    SUPPORTED_COMMANDS,
    VISUALIZE_OPTIONS,
)
from autodq.dashboard.models import Dashboard
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

    def test_saved_notebook_output_cache_is_ignored_by_adql_runtime(self):
        cache = base64.b64encode(
            json.dumps(
                {
                    "version": 1,
                    "cells": [
                        {
                            "index": 2,
                            "fingerprint": "test",
                            "outputs": [],
                        }
                    ],
                }
            ).encode("utf-8")
        ).decode("ascii")
        self.script.write_text(
            self.script.read_text(encoding="utf-8")
            + "\n# <autodq-output-cache version=\"1\">\n"
            + f"# {cache}\n"
            + "# </autodq-output-cache>\n",
            encoding="utf-8",
        )

        document = ADQLCellParser().read(self.script)
        result = ADQLFileRunner().run(self.script)

        self.assertEqual(document.cell_count, 3)
        self.assertNotIn("autodq-output-cache", document.cell(3).source)
        self.assertTrue(result.success)
        self.assertEqual(result.completed_cell_count, 3)

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

    def test_session_summary_uses_rich_notebook_output(self):
        project = AutoDQ(str(self.dataset), target="Revenue")
        project.load()
        summary = project.session_info()
        markup = _session_html(summary)

        self.assertIn("AutoDQ Session", markup)
        self.assertIn("Active dataset", markup)
        self.assertIn("Registered datasets", markup)
        self.assertIn("Workflow state", markup)
        self.assertIn("main", markup)

        session_script = self.root / "session.adql"
        session_script.write_text(
            "# %% [Dataset]\n"
            "DATASET \"sales.csv\" TARGET Revenue;\n"
            "# %% [Session]\n"
            "SESSION;\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run",
                    str(session_script),
                    "--through-cell",
                    "2",
                    "--notebook-json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [item["mime"] for item in payload["outputs"]],
            ["text/plain", "text/html"],
        )
        self.assertIn("AutoDQ Session", payload["outputs"][1]["data"])
        self.assertIn("Active dataset", payload["outputs"][1]["data"])

    def test_let_assignment_uses_compact_notebook_confirmation(self):
        let_script = self.root / "let-assignment.adql"
        let_script.write_text(
            "# %% [Dataset]\n"
            "DATASET \"sales.csv\" TARGET Revenue;\n"
            "# %% [Reusable result]\n"
            "LET regional_sales = SELECT Region, SUM(Revenue) AS total_revenue "
            "FROM CURRENT GROUP BY Region ORDER BY total_revenue DESC;\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run",
                    str(let_script),
                    "--through-cell",
                    "2",
                    "--notebook-json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [item["mime"] for item in payload["outputs"]],
            ["text/plain", "text/html"],
        )
        self.assertIn("dataset regional_sales", payload["outputs"][0]["data"])
        confirmation = payload["outputs"][1]["data"]
        self.assertIn("Let output", confirmation)
        self.assertIn("regional_sales", confirmation)
        self.assertIn("SELECT result", confirmation)
        self.assertIn("Rows", confirmation)
        self.assertIn("Columns", confirmation)
        self.assertNotIn("autodq-dataframe-wrap", confirmation)
        self.assertNotIn("total_revenue</th>", confirmation)
        self.assertIn("autodq-output-toggle", payload["outputs"][1]["data"])

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
        preview = markup.split(
            '<details class="autodq-full-output-toggle">',
            1,
        )[0]

        self.assertIn("Showing 5 of 40 rows", markup)
        self.assertIn("showing 3 of 25 columns", markup)
        self.assertIn("Output truncated", markup)
        self.assertIn("View full output", markup)
        self.assertIn("Hide full output", markup)
        self.assertIn("column_2", preview)
        self.assertNotIn("column_3", preview)
        self.assertIn("column_24", markup)
        self.assertIn("<td>39</td>", markup)
        self.assertEqual(preview.count("<tr"), 6)

    def test_notebook_structured_preview_defers_oversized_rich_html(self):
        class OversizedReport:
            def to_html(self):
                return "<div>" + ("unbounded-output " * 2_000) + "</div>"

            def to_dict(self):
                return {
                    "summary": "available",
                    "records": [
                        {
                            "row": index,
                            "details": f"complete-record-{index}-" + "x" * 950,
                        }
                        for index in range(100)
                    ],
                }

        markup = _value_html(
            "review",
            OversizedReport(),
            item_limit=5,
            character_limit=2_000,
        )
        preview = markup.split(
            '<details class="autodq-full-output-toggle">',
            1,
        )[0]

        self.assertIn("Review", markup)
        self.assertIn("Summary", markup)
        self.assertIn("Output truncated", markup)
        self.assertIn("View full output", markup)
        self.assertIn("Hide full output", markup)
        self.assertIn("additional item(s) omitted", markup)
        self.assertNotIn("unbounded-output", preview)
        self.assertNotIn("unbounded-output", markup)
        self.assertIn("complete-record-99", markup)
        self.assertNotIn("<pre", preview)
        self.assertIn("autodq-structured-table", preview)
        self.assertLess(len(preview), 20_000)

    def test_notebook_rejects_standalone_html_that_can_leak_theme_css(self):
        class StandaloneReport:
            def to_html(self):
                return """<!doctype html>
<html><head><style>
:root { color-scheme: light; }
body { background: white; color: black; }
</style></head><body>Standalone report</body></html>"""

            def to_dict(self):
                return {
                    "summary": "Theme-safe structured report",
                    "records": [{"row": 1, "status": "complete"}],
                }

        markup = _value_html(
            "report",
            StandaloneReport(),
            character_limit=200_000,
        )

        self.assertNotIn("<!doctype", markup.lower())
        self.assertNotIn("<html", markup.lower())
        self.assertNotIn("<body", markup.lower())
        self.assertNotIn(":root", markup.lower())
        self.assertIn("Theme-safe structured report", markup)
        self.assertIn("View full output", markup)

    def test_notebook_dashboard_uses_its_isolated_iframe(self):
        dashboard = Dashboard(
            title="Sales dashboard",
            subtitle="Theme isolation check",
            dataset="sales.csv",
            stage="engineered",
            theme="light",
        )
        markup = _value_html(
            "dashboard",
            dashboard,
            character_limit=2_000,
        )

        self.assertIn("<iframe", markup)
        self.assertIn("sandbox=", markup)
        self.assertNotIn("<html", markup.lower())
        self.assertNotIn("<body", markup.lower())
        self.assertIn("View full output", markup)

    def test_notebook_structured_full_output_contains_omitted_records(self):
        markup = _value_html(
            "predictions",
            {
                "records": [
                    {
                        "row_id": index,
                        "prediction": index * 10,
                        "label": f"complete-row-{index}",
                    }
                    for index in range(10)
                ]
            },
            item_limit=2,
            character_limit=2_000,
        )
        preview = markup.split(
            '<details class="autodq-full-output-toggle">',
            1,
        )[0]

        self.assertIn("<td>1</td>", preview)
        self.assertNotIn("complete-row-1", preview)
        self.assertNotIn("complete-row-9", preview)
        self.assertIn("complete-row-9", markup)
        self.assertIn("View full output", markup)

    def test_notebook_profile_full_output_contains_omitted_columns(self):
        columns = ["Customer_Age", "Region", "Revenue"]
        markup = _profile_html(
            {
                "column_names": columns,
                "data_types": {column: "float64" for column in columns},
                "semantic_types": {
                    column: "continuous_numeric"
                    for column in columns
                },
                "missing_values": {column: 0 for column in columns},
                "missing_percentages": {column: 0.0 for column in columns},
                "numeric_columns": [],
                "categorical_columns": [],
                "datetime_columns": [],
                "rows": 100,
                "columns": 3,
                "duplicate_rows": 0,
            },
            limit=1,
        )
        preview = markup.split(
            '<details class="autodq-full-output-toggle">',
            1,
        )[0]

        self.assertIn("Customer_Age", preview)
        self.assertNotIn("Revenue", preview)
        self.assertIn("Revenue", markup)
        self.assertIn("View full output", markup)

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

    def test_notebook_large_correlation_matrix_has_complete_expandable_view(self):
        features = [f"feature_{index}" for index in range(8)]
        matrix = {
            row: {
                column: 1.0 if row == column else 0.5
                for column in features
            }
            for row in features
        }
        markup = _value_html(
            "correlation",
            {"matrix": matrix},
            item_limit=3,
            character_limit=2_000,
        )
        preview = markup.split(
            '<details class="autodq-full-output-toggle">',
            1,
        )[0]

        self.assertIn("autodq-matrix-table", preview)
        self.assertIn("feature_2", preview)
        self.assertNotIn("feature_7", preview)
        self.assertIn("feature_7", markup)
        self.assertIn("View full output", markup)

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
                },
                {
                    "issue_type": "outliers",
                    "strategy": "review",
                    "reason": "A domain expert should inspect this value.",
                    "affected_columns": ["Revenue"],
                    "action": "Inspect the complete recommendation.",
                    "priority": "medium",
                    "risk": "Removing valid extremes can bias results.",
                    "confidence": 0.81,
                },
            ],
            limit=1,
        )
        preview = markup.split(
            '<details class="autodq-full-output-toggle">',
            1,
        )[0]

        self.assertIn("Cleaning Recommendations", markup)
        self.assertIn("autodq-recommendation", markup)
        self.assertIn("Apply median strategy to Customer_Age.", markup)
        self.assertIn("88% confidence", markup)
        self.assertIn("Why this is recommended", markup)
        self.assertIn("Customer_Age", markup)
        self.assertNotIn('&quot;issue_type&quot;', markup)
        self.assertNotIn("Inspect the complete recommendation.", preview)
        self.assertIn("Inspect the complete recommendation.", markup)
        self.assertIn("View full output", markup)

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
        self.assertIn("extractOutputCache", extension)
        self.assertIn("encodeCellOutputs", extension)
        self.assertIn("transientOutputs: false", extension)
        self.assertNotIn("transientOutputs: true", extension)
        self.assertIn("notebook.maxOutputRows", extension)
        self.assertIn("notebook.maxOutputCharacters", extension)
        self.assertEqual(package["version"], "0.3.13")
        renderer = package["contributes"]["notebookRenderer"][0]
        self.assertEqual(renderer["id"], "autodq-adql-review-renderer")
        self.assertEqual(renderer["requiresMessaging"], "always")
        self.assertIn(
            "application/vnd.autodq.review+json",
            renderer["mimeTypes"],
        )
        language_icon = package["contributes"]["languages"][0]["icon"]
        self.assertEqual(language_icon["light"], "./icons/adql-light.svg")
        self.assertEqual(language_icon["dark"], "./icons/adql-dark.svg")
        self.assertTrue((source / "icons" / "adql-light.svg").is_file())
        self.assertTrue((source / "icons" / "adql-dark.svg").is_file())
        self.assertTrue((source / "notebook-persistence.js").is_file())
        self.assertTrue((source / "review-protocol.js").is_file())
        self.assertTrue((source / "review-renderer.mjs").is_file())
        self.assertEqual(
            package["contributes"]["configuration"]["properties"]
            ["autodq.notebook.maxOutputRows"]["default"],
            25,
        )
        self.assertTrue((installed / "package.json").is_file())
        self.assertTrue((installed / "icons" / "adql-light.svg").is_file())
        self.assertTrue((installed / "icons" / "adql-dark.svg").is_file())
        self.assertTrue((installed / "notebook-persistence.js").is_file())
        self.assertTrue((installed / "review-protocol.js").is_file())
        self.assertTrue((installed / "review-renderer.mjs").is_file())

    def test_vscode_grammar_colors_complete_adql_vocabulary(self):
        source = extension_path()
        grammar = json.loads(
            (source / "syntaxes" / "adql.tmLanguage.json").read_text(
                encoding="utf-8"
            )
        )
        repository = grammar["repository"]

        self.assertEqual(grammar["scopeName"], "source.adql")
        self.assertEqual(
            grammar["patterns"][-1]["include"],
            "#identifiers",
        )
        self.assertLess(
            [item["include"] for item in grammar["patterns"]].index(
                "#booleanOptions"
            ),
            [item["include"] for item in grammar["patterns"]].index(
                "#numbers"
            ),
        )

        command_pattern = re.compile(repository["commands"]["match"])
        option_pattern = re.compile(repository["options"]["match"])
        function_pattern = re.compile(
            repository["aggregateFunctions"]["match"]
        )
        quality_metric_pattern = re.compile(
            repository["qualityMetrics"]["match"]
        )
        quality_predicate_pattern = re.compile(
            repository["qualityPredicates"]["match"]
        )
        constant_pattern = re.compile(repository["constants"]["match"])
        boolean_option_pattern = re.compile(
            repository["booleanOptions"]["match"]
        )
        enum_pattern = re.compile(repository["enumValues"]["match"])
        identifier_pattern = re.compile(repository["identifiers"]["match"])

        for command in sorted(SUPPORTED_COMMANDS):
            self.assertIsNotNone(
                command_pattern.fullmatch(command),
                f"Missing command highlighting for {command}",
            )

        option_groups = (
            VISUALIZE_OPTIONS,
            AUTO_OPTIONS,
            MODEL_OPTIONS,
            PREDICT_OPTIONS,
            EXPLAIN_OPTIONS,
            SHAP_OPTIONS,
            BLUE_OPTIONS,
            GALLERY_STYLE_OPTIONS,
            DASHBOARD_OPTIONS,
            SET_TYPE_OPTIONS,
        )
        parser_options = {
            "ACTIONS",
            "ALLOWED",
            "ALLOW_DUPLICATES",
            "AXIS",
            "BINS",
            "CHANGES",
            "COLUMNS",
            "DESCRIPTION",
            "EXPRESSION",
            "FAIL_ON",
            "HOW",
            "IGNORE_INDEX",
            "INCLUDE_MODEL",
            "IQR",
            "JOIN",
            "KEEP",
            "LABELS",
            "LEFT_ON",
            "LOAD_MODEL",
            "LOWER",
            "MAKE_ACTIVE",
            "METHOD",
            "MIN_PERCENT",
            "MIN_ABS",
            "MODEL_NAME",
            "NAME",
            "NAMES",
            "NULLABLE",
            "PATTERN",
            "REASON",
            "RECOMMENDED",
            "REFERENCE",
            "RIGHT_ON",
            "ROOT",
            "SEVERITY",
            "STRATEGY",
            "STYLE",
            "SUFFIXES",
            "UNIQUE",
            "UPPER",
            "VALUE",
        }
        vocabulary_rules = [
            re.compile(repository[name]["match"])
            for name in (
                "commands",
                "clauses",
                "actions",
                "options",
                "entities",
                "dataSources",
                "constants",
                "enumValues",
                "identifiers",
            )
        ]
        option_vocabulary = parser_options.union(
            *(set(group) for group in option_groups)
        )

        for option in sorted(parser_options):
            self.assertIsNotNone(
                option_pattern.fullmatch(option),
                f"Expected {option} to use the ADQL option scope",
            )

        for option in sorted(option_vocabulary):
            self.assertTrue(
                any(pattern.fullmatch(option) for pattern in vocabulary_rules),
                f"Missing syntax scope for {option}",
            )

        for option in (
            "ALLOWED",
            "COLUMNS",
            "DESCRIPTION",
            "IQR",
            "NULLABLE",
        ):
            self.assertIsNotNone(
                option_pattern.fullmatch(option),
                f"Expected {option} to use the ADQL option scope",
            )

        for function in (
            "AVG",
            "COUNT",
            "MAX",
            "MEAN",
            "MEDIAN",
            "MIN",
            "NUNIQUE",
            "SUM",
        ):
            self.assertIsNotNone(
                function_pattern.match(f"{function}("),
                f"Missing aggregate-function highlighting for {function}",
            )

        for metric in (
            "COLUMN_COUNT",
            "DISTINCT_COUNT",
            "DUPLICATE_PERCENT",
            "DUPLICATE_ROWS",
            "MISSING_COUNT",
            "MISSING_PERCENT",
            "QUALITY_SCORE",
            "ROW_COUNT",
        ):
            self.assertIsNotNone(
                quality_metric_pattern.fullmatch(metric),
                f"Missing quality-metric highlighting for {metric}",
            )

        for predicate in ("BETWEEN", "EXISTS", "MATCHES", "NOT NULL"):
            self.assertIsNotNone(
                quality_predicate_pattern.fullmatch(predicate),
                f"Missing quality-predicate highlighting for {predicate}",
            )

        for constant in ("TRUE", "false", "YeS", "nO", "On", "oFf"):
            self.assertIsNotNone(
                constant_pattern.fullmatch(constant),
                f"Missing constant highlighting for {constant}",
            )

        for expression in (
            "UNCERTAINTY ON",
            "DISPLAY off",
            "OVERWRITE YeS",
            "USE_ENGINEERED nO",
        ):
            self.assertIsNotNone(
                boolean_option_pattern.fullmatch(expression),
                f"Missing contextual boolean highlighting for {expression}",
            )

        for enum_value in (
            "BeEsWaRm",
            "dEpEnDeNcE",
            "str",
            "BOXPLOT",
            "cleaning_status",
            "comparison",
            "correlation_heatmap",
            "distribution",
            "issue_breakdown",
            "missing_values",
            "quality_score",
        ):
            self.assertIsNotNone(
                enum_pattern.fullmatch(enum_value),
                f"Missing enum highlighting for {enum_value}",
            )

        for identifier in (
            "Customer_Age",
            "Revenue",
            "average_profit",
            "total_revenue",
        ):
            self.assertIsNotNone(identifier_pattern.fullmatch(identifier))

        expected_scopes = {
            "commands": "keyword.control.adql",
            "aggregateFunctions": "support.function.aggregate.adql",
            "qualityPredicates": "keyword.control.quality.adql",
            "options": "storage.modifier.option.adql",
            "dataSources": "constant.language.data-source.adql",
            "identifiers": "variable.other.readwrite.adql",
        }
        for name, scope in expected_scopes.items():
            self.assertEqual(repository[name]["name"], scope)

        grammar_source = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "adql"
            / "grammar.ebnf"
        ).read_text(encoding="utf-8")
        terminals = {
            value.upper()
            for value in re.findall(
                r'"([A-Za-z_][A-Za-z0-9_]*)"',
                grammar_source,
            )
            if len(value) > 1 or value.upper() in {"X", "Y"}
        }
        contextual_phrase_parts = {
            "BY",
            "ENDS",
            "GROUP",
            "IS",
            "NOT",
            "ORDER",
            "STARTS",
        }
        specialized_rules = [
            re.compile(repository[name]["match"])
            for name in (
                "commands",
                "aggregateFunctions",
                "qualityMetrics",
                "qualityPredicates",
                "operators",
                "clauses",
                "actions",
                "options",
                "entities",
                "dataSources",
                "constants",
                "enumValues",
            )
        ]
        missing = set()

        for terminal in terminals - contextual_phrase_parts:
            if terminal in AGGREGATE_FUNCTIONS:
                matched = function_pattern.match(f"{terminal}(") is not None
            else:
                matched = any(
                    pattern.fullmatch(terminal)
                    for pattern in specialized_rules
                )

            if not matched:
                missing.add(terminal)

        self.assertSetEqual(
            missing,
            set(),
            "Normative ADQL words missing a semantic TextMate scope.",
        )

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
