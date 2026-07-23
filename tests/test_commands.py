import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from autodq import (
    ADQLExecutionError,
    ADQLParser,
    ADQLSyntaxError,
    ADQLValidationError,
    AutoDQ,
)


class ADQLTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rng = np.random.default_rng(404)
        row_count = 84
        self.data = pd.DataFrame(
            {
                "Region": rng.choice(
                    ["North", "South", "West"],
                    row_count,
                ),
                "Units": rng.integers(1, 45, row_count).astype(float),
                "Price": rng.uniform(8, 120, row_count),
                "Discount": rng.uniform(0, 0.25, row_count),
                "Active": rng.choice([True, False], row_count),
            }
        )
        self.data["Revenue"] = (
            self.data["Units"]
            * self.data["Price"]
            * (1 - self.data["Discount"])
            + rng.normal(0, 15, row_count)
        )
        self.data.loc[3, "Units"] = np.nan
        self.data.loc[6, "Region"] = None
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

    def test_parser_supports_scripts_comments_quotes_and_workflow_options(self):
        parser = ADQLParser()
        script = parser.parse(
            """
            -- analysis preparation
            PROFILE;
            # semicolons inside strings do not split statements
            SELECT Region, SUM(Revenue) AS total
            FROM CURRENT
            WHERE Region = "North;Enterprise"
            GROUP BY Region
            ORDER BY total DESC
            LIMIT 5;
            DASHBOARD TITLE "Sales; Quality" THEME executive
                MAX_ROWS 12 DISPLAY false;
            """
        )

        self.assertEqual(script.statement_count, 3)
        self.assertEqual(
            [item.kind for item in script.statements],
            ["PROFILE", "SELECT", "DASHBOARD"],
        )
        select = script.statements[1].parameters
        self.assertEqual(select["where"][0]["value"], "North;Enterprise")
        self.assertEqual(select["order_by"][0]["column"], "total")
        dashboard = script.statements[2].parameters
        self.assertEqual(dashboard["title"], "Sales; Quality")
        self.assertEqual(dashboard["max_preview_rows"], 12)
        self.assertFalse(dashboard["auto_display"])

    def test_grouped_select_matches_pandas_and_does_not_mutate_data(self):
        project = self._project()
        original = project.load().copy(deep=True)
        run = project.query(
            """
            SELECT Region, SUM(Revenue) AS total_revenue,
                   AVG(Price) AS average_price, COUNT(*) AS transactions
            FROM CURRENT
            WHERE Revenue > 100 AND Region IS NOT NULL
            GROUP BY Region
            ORDER BY total_revenue DESC
            LIMIT 3;
            """,
            auto_display=False,
        )
        expected = (
            original.loc[
                (original["Revenue"] > 100) & original["Region"].notna()
            ]
            .groupby("Region", as_index=False, sort=False)
            .agg(
                total_revenue=("Revenue", "sum"),
                average_price=("Price", "mean"),
                transactions=("Revenue", "size"),
            )
            .sort_values("total_revenue", ascending=False, kind="mergesort")
            .head(3)
            .reset_index(drop=True)
        )

        assert_frame_equal(run.data, expected)
        assert_frame_equal(project.data, original)
        self.assertTrue(run.success)
        self.assertEqual(run.latest.total_rows, 3)
        self.assertIs(project.adql_history[-1], run)
        self.assertIn("adql", project.session.steps_completed)

    def test_filters_distinct_aliases_nulls_and_aggregates(self):
        project = self._project()
        regions = project.query(
            """
            SELECT DISTINCT Region AS area
            FROM CURRENT
            WHERE Region IN ("North", "South")
              AND Region CONTAINS "o"
            ORDER BY area ASC;
            """,
            auto_display=False,
        ).data

        self.assertEqual(regions["area"].tolist(), ["North", "South"])

        missing = project.query(
            "SELECT COUNT(*) AS missing_rows FROM CURRENT "
            "WHERE Units IS NULL;",
            auto_display=False,
        ).data
        self.assertEqual(int(missing.loc[0, "missing_rows"]), 1)

        summary = project.query(
            "SELECT COUNT(*) AS rows, COUNT(Region) AS known_regions, "
            "NUNIQUE(Region) AS region_count FROM CURRENT;",
            auto_display=False,
        ).data
        self.assertEqual(int(summary.loc[0, "rows"]), len(self.data))
        self.assertEqual(
            int(summary.loc[0, "known_regions"]),
            int(self.data["Region"].count()),
        )
        self.assertEqual(int(summary.loc[0, "region_count"]), 3)

    def test_select_supports_cleaned_engineered_and_prediction_sources(self):
        project = self._project(target="Revenue")
        project.load()
        project.state.cleaned_data = project.data.drop_duplicates().copy()
        project.state.engineered_data = project.state.cleaned_data.assign(
            Net_Price=lambda frame: frame["Price"] * (1 - frame["Discount"])
        )

        cleaned = project.query(
            "SELECT COUNT(*) AS rows FROM CLEANED;",
            auto_display=False,
        )
        engineered = project.query(
            "SELECT Region, Net_Price FROM ENGINEERED LIMIT 4;",
            auto_display=False,
        )

        self.assertEqual(
            int(cleaned.data.loc[0, "rows"]),
            len(project.state.cleaned_data),
        )
        self.assertEqual(len(engineered.data), 4)
        self.assertIn("Net_Price", engineered.data.columns)

        project.model(
            algorithm="decision_tree_regressor",
            use_engineered=False,
        )
        project.predict(confidence_level=0.9)
        predictions = project.query(
            "SELECT AutoDQ_Prediction, AutoDQ_Prediction_Lower, "
            "AutoDQ_Prediction_Upper FROM PREDICTIONS LIMIT 5;",
            auto_display=False,
        )
        self.assertEqual(len(predictions.data), 5)
        self.assertTrue(
            (
                predictions.data["AutoDQ_Prediction_Lower"]
                <= predictions.data["AutoDQ_Prediction"]
            ).all()
        )

    def test_workflow_commands_are_wired_to_project_and_dashboard(self):
        project = self._project()
        dashboard_path = self.root / "adql dashboard.html"
        run = project.query(
            f"""
            PROFILE;
            DIAGNOSE;
            VISUALIZE bar X Region Y Revenue
                TITLE "Revenue by Region" THEME dark;
            DASHBOARD TITLE "ADQL Sales Dashboard" THEME executive
                SAVE "{dashboard_path}" OVERWRITE DISPLAY false;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertEqual(run.statement_count, 4)
        self.assertIsNotNone(project.state.profile_report)
        self.assertIsNotNone(project.state.diagnosis_report)
        self.assertEqual(
            project.state.visualization_report.latest.title,
            "Revenue by Region",
        )
        self.assertEqual(
            project.state.visualization_report.latest.style.theme,
            "dark",
        )
        self.assertTrue(dashboard_path.is_file())
        self.assertEqual(
            project.state.dashboard_report.title,
            "ADQL Sales Dashboard",
        )

    def test_model_and_predict_commands_include_uncertainty(self):
        project = self._project()
        run = project.adql(
            """
            MODEL TARGET Revenue USING decision_tree_regressor
                USE_ENGINEERED false TEST_SIZE 0.2 RANDOM_STATE 12;
            PREDICT CONFIDENCE 0.9 UNCERTAINTY true;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertEqual(project.target, "Revenue")
        self.assertIsNotNone(project.state.model_report)
        self.assertIsNotNone(project.state.prediction_report)
        self.assertTrue(project.state.prediction_report.uncertainty_available)
        self.assertEqual(
            project.state.prediction_report.confidence_level,
            0.9,
        )
        self.assertIn("AutoDQ_Prediction", run.data.columns)

    def test_extended_adql_manages_datasets_features_and_gallery(self):
        project = self._project(target="Revenue")
        costs_path = self.root / "costs.csv"
        pd.DataFrame(
            {
                "Region": ["North", "South", "West"],
                "RegionalCost": [10.0, 20.0, 30.0],
            }
        ).to_csv(costs_path, index=False)
        chart_dir = self.root / "charts"

        run = project.query(
            f"""
            ADD DATASET costs FROM "{costs_path}";
            MERGE main WITH costs AS joined ON Region HOW left;
            FEATURE CREATE PriceSquared METHOD square COLUMN Price;
            VISUALIZE bar X Region Y Revenue TITLE "Revenue by Region";
            GALLERY CUSTOMIZE bar_Region_by_Revenue_current SUBTITLE "ADQL managed" THEME dark;
            GALLERY SAVE TO "{chart_dir}" FORMAT png;
            LIST DATASETS;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertIn("PriceSquared", project.state.engineered_data.columns)
        self.assertEqual(
            project.get_visualization("bar_Region_by_Revenue_current").style.subtitle,
            "ADQL managed",
        )
        self.assertTrue(any(chart_dir.glob("*.png")))
        self.assertIn("joined", set(run.data["name"]))

    def test_extended_adql_cleaning_review_and_audit(self):
        project = self._project()
        audit_path = self.root / "audit.json"
        run = project.query(
            f"""
            KNOWLEDGE;
            REVIEW;
            EDIT ROW 3 CHANGES '{{"Units": 10}}' REASON "Verified value";
            DOMAIN ADD Revenue MIN 0 DESCRIPTION "Revenue cannot be negative";
            DOMAIN VALIDATE;
            OUTLIERS REVIEW COLUMNS Revenue IQR 1.5;
            CLEANING PREVIEW MAX_ROWS 2;
            AUDIT EXPORT TO "{audit_path}";
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertEqual(
            project.state.cleaning_review.working_data.loc[3, "Units"],
            10,
        )
        self.assertTrue(audit_path.is_file())
        self.assertGreater(project.state.cleaning_review.audit_count, 0)

    def test_extended_adql_model_persistence_workspace_and_intelligence(self):
        project = self._project(target="Revenue")
        model_path = self.root / "saved-model"
        workspace_root = self.root / "workspaces"
        run = project.query(
            f"""
            WORKSPACE CREATE sales_review ROOT "{workspace_root}";
            CORRELATION MIN_ABS 0.2;
            READINESS;
            FEATURES;
            BLUE MAX_FEATURES 4;
            BLUE VISUALIZE APPEND true;
            BLUE INTERPRET;
            BLUE PRESCRIBE;
            MODEL USING decision_tree_regressor USE_ENGINEERED false;
            MODEL SAVE TO "{model_path}";
            MODEL LOAD FROM "{model_path}";
            WORKSPACE SAVE INCLUDE_MODEL true;
            WORKSPACE INFO;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertTrue((model_path / "manifest.json").is_file())
        self.assertEqual(run.value["name"], "sales_review")
        self.assertEqual(project.workspace_name, "sales_review")
        self.assertIsNotNone(project.state.model_report)
        self.assertIsNotNone(project.state.blue_report)
        self.assertTrue(project.state.blue_report.prescriptions)

    def test_extended_adql_explain_and_shap_plot(self):
        project = self._project(target="Revenue")
        run = project.query(
            """
            MODEL USING decision_tree_regressor USE_ENGINEERED false;
            PREDICT CONFIDENCE 0.9;
            EXPLAIN MAX_ROWS 5 USE_ENGINEERED false;
            SHAP CHART bar;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertIsNotNone(project.state.explainability_report)
        self.assertEqual(
            project.state.explainability_report.explanation_count,
            5,
        )
        self.assertTrue(hasattr(run.value, "savefig"))

    def test_auto_review_and_partial_approval_commands(self):
        project = self._project()
        auto = project.query(
            "AUTO MODE review VISUALIZE false;",
            auto_display=False,
        )
        review = project.state.cleaning_review
        first = review.actions[0]
        approval = project.query(
            f"APPROVE {first.action_id};",
            auto_display=False,
        )

        self.assertTrue(auto.success)
        self.assertEqual(auto.value.config.mode, "review")
        self.assertEqual(first.status, "approved")
        self.assertTrue(approval.success)

        pending = next(
            action for action in review.actions if action.status == "pending"
        )
        project.query(
            f'REJECT {pending.action_id} REASON "Not valid for this domain";',
            auto_display=False,
        )
        self.assertEqual(pending.status, "rejected")

    def test_auto_statement_maps_every_public_workflow_option(self):
        statement = ADQLParser().parse(
            """
            AUTO MODE full
                VISUALIZE false
                APPROVE_ALL true
                APPLY_CLEANING true
                APPLY_FEATURES true
                TRAIN_MODEL true
                PREDICT true
                EXPLAIN true
                ALGORITHM decision_tree_regressor
                TEST_SIZE 0.25
                RANDOM_STATE 7
                REPORT "reports/auto.json"
                REPORT_STYLE journal
                SAVE_WORKSPACE false
                REFRESH true
                CONTINUE_ON_ERROR true
                RAISE_ON_ERROR false;
            """
        ).statements[0]

        self.assertEqual(
            statement.parameters,
            {
                "mode": "full",
                "visualize": False,
                "approve_all": True,
                "apply_cleaning": True,
                "apply_features": True,
                "train_model": True,
                "generate_predictions": True,
                "explain_model": True,
                "algorithm": "decision_tree_regressor",
                "test_size": 0.25,
                "random_state": 7,
                "report_output": "reports/auto.json",
                "report_style": "journal",
                "save_workspace": False,
                "refresh": True,
                "continue_on_error": True,
                "raise_on_error": False,
            },
        )

    def test_adql_file_execution_help_and_history(self):
        project = self._project()
        script_path = self.root / "analysis.adql"
        script_path.write_text(
            "PROFILE; SELECT Region, Revenue FROM CURRENT LIMIT 3;",
            encoding="utf-8",
        )
        run = project.run_adql(script_path, auto_display=False)

        self.assertTrue(run.success)
        self.assertEqual(run.source_name, str(script_path.resolve()))
        self.assertEqual(len(run.data), 3)

        help_result = project.query("HELP MODEL;", auto_display=False)
        self.assertIn("MODEL", help_result.data.iloc[0]["command"])
        history = project.query("HISTORY LIMIT 2;", auto_display=False)
        self.assertEqual(len(history.data), 2)
        self.assertIn("status", history.data.columns)

        with self.assertRaisesRegex(ValueError, ".adql"):
            project.run_adql(self.root / "analysis.txt")

        with self.assertRaises(FileNotFoundError):
            project.run_adql(self.root / "missing.adql")

    def test_runtime_failure_is_recorded_and_continue_on_error_resumes(self):
        project = self._project()

        with self.assertRaises(ADQLExecutionError) as context:
            project.query(
                "SELECT MissingColumn FROM CURRENT;",
                auto_display=False,
            )

        failed = context.exception.result
        self.assertFalse(failed.success)
        self.assertEqual(failed.failed_count, 1)
        self.assertIs(project.adql_history[-1], failed)

        continued = project.query(
            "PROFILE; SELECT MissingColumn FROM CURRENT; HEAD 2;",
            continue_on_error=True,
            auto_display=False,
        )
        self.assertFalse(continued.success)
        self.assertEqual(continued.completed_count, 2)
        self.assertEqual(continued.failed_count, 1)
        self.assertEqual(len(continued.data), 2)

    def test_syntax_validation_and_injection_attempts_fail_before_execution(self):
        project = self._project()

        with self.assertRaises(ADQLSyntaxError):
            project.query("PYTHON import os;", auto_display=False)

        with self.assertRaisesRegex(ADQLSyntaxError, "OR"):
            project.query(
                'SELECT * FROM CURRENT WHERE Region = "North" '
                'OR Region = "South";',
                auto_display=False,
            )

        with self.assertRaisesRegex(ADQLValidationError, "LIMIT"):
            project.query(
                "SELECT * FROM CURRENT LIMIT 10001;",
                auto_display=False,
            )

        with self.assertRaisesRegex(ADQLValidationError, "GROUP BY"):
            project.query(
                "SELECT Region, SUM(Revenue) AS total FROM CURRENT;",
                auto_display=False,
            )

        with self.assertRaisesRegex(ADQLValidationError, "AUTO TEST_SIZE"):
            project.query(
                "AUTO MODE review TEST_SIZE 1.5;",
                auto_display=False,
            )

        with self.assertRaisesRegex(ADQLValidationError, "AUTO REPORT"):
            project.query(
                'AUTO MODE review REPORT "unsafe.txt";',
                auto_display=False,
            )

        self.assertIsNone(project.state.data)
        self.assertEqual(project.adql_history, [])

    def test_exports_require_explicit_overwrite(self):
        project = self._project()
        output = self.root / "current.csv"
        output.write_text("do not replace", encoding="utf-8")

        with self.assertRaisesRegex(ADQLExecutionError, "OVERWRITE"):
            project.query(
                f'EXPORT CURRENT TO "{output}";',
                auto_display=False,
            )

        self.assertEqual(output.read_text(encoding="utf-8"), "do not replace")
        exported = project.query(
            f'EXPORT CURRENT TO "{output}" OVERWRITE;',
            auto_display=False,
        )
        self.assertTrue(exported.success)
        self.assertGreater(output.stat().st_size, len("do not replace"))

    def test_query_history_is_in_json_and_html_reports(self):
        project = self._project()
        project.query("HEAD 2;", auto_display=False)
        report = project.reporting_engine.build_report(
            project.state,
            project.session,
            output_dir=self.root / "report-assets",
        )
        json_path = self.root / "report.json"
        html_path = self.root / "report.html"
        project.reporting_engine.export(report, str(json_path))
        project.reporting_engine.export(report, str(html_path))
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        markup = html_path.read_text(encoding="utf-8")

        self.assertEqual(len(payload["adql_history"]), 1)
        self.assertEqual(
            payload["adql_history"][0]["results"][0]["statement"]["kind"],
            "HEAD",
        )
        self.assertIn("ADQL Query History", markup)

    def test_notebook_html_escapes_queries_and_errors(self):
        project = self._project()

        with self.assertRaises(ADQLExecutionError) as context:
            project.query(
                "SELECT `<script>alert(1)</script>` FROM CURRENT;",
                auto_display=False,
            )

        markup = context.exception.result.to_html()
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<script>alert(1)</script>", markup)


if __name__ == "__main__":
    unittest.main()
