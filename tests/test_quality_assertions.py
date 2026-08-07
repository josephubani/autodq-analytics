import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

from autodq import (
    ADQLExecutionError,
    ADQLParser,
    ADQLSyntaxError,
    ADQLValidationError,
    ADQLValidator,
    AutoDQ,
    QualityAssertion,
)
from autodq.cli import main
from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class QualityAssertionTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.dataset = self.root / "quality.csv"
        pd.DataFrame(
            {
                "ID": [1, 2, 2, 4],
                "Revenue": [10.0, 20.0, -5.0, None],
                "Region": ["North", "South", None, "West"],
                "Email": [
                    "a@example.com",
                    "b@example.com",
                    "invalid",
                    None,
                ],
            }
        ).to_csv(self.dataset, index=False)
        self.project = AutoDQ(str(self.dataset))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_parser_accepts_column_metric_and_suite_forms(self):
        source = """
        ASSERT Revenue NOT NULL;
        ASSERT Revenue TYPE numeric;
        ASSERT Revenue BETWEEN 0 AND 1000 SEVERITY warning NAME "Revenue range";
        ASSERT Region ALLOWED North,South,East,West;
        ASSERT Email MATCHES "[^@]+@[^@]+";
        ASSERT ROW_COUNT BETWEEN 1 AND 10;
        ASSERT MISSING_PERCENT Region <= 25;
        ASSERT DISTINCT_COUNT Region >= 3;
        ASSERT SUITE ADD release_gate ID UNIQUE NAME "IDs are unique";
        ASSERT SUITE RUN release_gate FAIL_ON warning;
        ASSERT SUITE SHOW release_gate;
        ASSERT SUITE LIST;
        ASSERT SUITE EXPORT release_gate TO "gate.json" OVERWRITE;
        ASSERT SUITE LOAD restored FROM "gate.json" OVERWRITE;
        ASSERT SUITE DROP restored;
        """
        script = ADQLParser().parse(source)
        ADQLValidator().validate(script)

        self.assertEqual(script.statement_count, 15)
        self.assertEqual(script.statements[2].parameters["assertion"]["name"], "Revenue range")
        self.assertEqual(
            script.statements[6].parameters["assertion"]["column"],
            "Region",
        )
        self.assertEqual(
            script.statements[8].parameters["action"],
            "suite_add",
        )

    def test_invalid_assertions_fail_before_execution(self):
        parser = ADQLParser()
        invalid_syntax = [
            "ASSERT;",
            "ASSERT Revenue BETWEEN 10 20;",
            "ASSERT ROW_COUNT 10;",
            "ASSERT SUITE RUN;",
            "ASSERT SUITE UNKNOWN name;",
        ]
        for source in invalid_syntax:
            with self.subTest(source=source):
                with self.assertRaises(ADQLSyntaxError):
                    parser.parse(source)

        invalid_validation = [
            "ASSERT Revenue TYPE mystery;",
            "ASSERT ROW_COUNT >= many;",
            "ASSERT Revenue MIN high;",
            "ASSERT Revenue NOT NULL SEVERITY urgent;",
            "ASSERT ROW_COUNT >= 1 FAIL_ON sometimes;",
            "ASSERT SUITE EXPORT gate TO gate.csv;",
        ]
        for source in invalid_validation:
            with self.subTest(source=source):
                with self.assertRaises(ADQLValidationError):
                    ADQLValidator().validate(parser.parse(source))

    def test_direct_assertions_return_structured_results(self):
        passed = self.project.query(
            "ASSERT ROW_COUNT = 4;",
            auto_display=False,
        )
        self.assertTrue(passed.success)
        self.assertEqual(passed.latest.data.loc[0, "status"], "passed")
        self.assertEqual(passed.latest.value.passed_count, 1)

        with self.assertRaises(ADQLExecutionError) as raised:
            self.project.query(
                "ASSERT Revenue MIN 0;",
                auto_display=False,
            )

        result = raised.exception.result.latest
        self.assertFalse(result.success)
        self.assertEqual(result.data.loc[0, "status"], "failed")
        self.assertEqual(result.data.loc[0, "failed_count"], 1)
        self.assertEqual(result.error_type, "ADQLAssertionError")

    def test_severity_and_fail_on_control_blocking(self):
        warning = self.project.query(
            "ASSERT Revenue NOT NULL SEVERITY warning;",
            auto_display=False,
        )
        self.assertTrue(warning.success)
        self.assertEqual(warning.latest.data.loc[0, "status"], "failed")
        self.assertEqual(warning.latest.value.blocking_failure_count, 0)

        with self.assertRaises(ADQLExecutionError):
            self.project.query(
                "ASSERT Revenue NOT NULL SEVERITY warning FAIL_ON warning;",
                auto_display=False,
            )

        never = self.project.query(
            "ASSERT Revenue NOT NULL FAIL_ON never;",
            auto_display=False,
        )
        self.assertTrue(never.success)
        self.assertEqual(never.latest.value.failed_count, 1)

    def test_column_assertion_vocabulary(self):
        run = self.project.query(
            """
            ASSERT Revenue EXISTS;
            ASSERT Revenue TYPE numeric;
            ASSERT Revenue MAX 20;
            ASSERT Region ALLOWED North,South,West;
            ASSERT Email MATCHES "[^@]+@[^@]+" SEVERITY warning;
            """,
            continue_on_error=True,
            auto_display=False,
        )

        self.assertEqual(run.statement_count, 5)
        self.assertEqual(run.failed_count, 0)
        self.assertEqual(run.results[0].data.loc[0, "status"], "passed")
        self.assertEqual(run.results[1].data.loc[0, "status"], "passed")
        self.assertEqual(run.results[2].data.loc[0, "status"], "passed")
        self.assertEqual(run.results[3].data.loc[0, "status"], "passed")
        self.assertEqual(run.results[4].data.loc[0, "status"], "failed")

    def test_metric_assertion_vocabulary(self):
        run = self.project.query(
            """
            ASSERT ROW_COUNT = 4;
            ASSERT COLUMN_COUNT >= 4;
            ASSERT MISSING_COUNT = 3;
            ASSERT MISSING_PERCENT Revenue = 25;
            ASSERT DUPLICATE_ROWS = 0;
            ASSERT DUPLICATE_PERCENT <= 1;
            ASSERT DISTINCT_COUNT Region = 3;
            ASSERT QUALITY_SCORE BETWEEN 0 AND 100;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertEqual(run.completed_count, 8)
        self.assertIsNotNone(self.project.state.diagnosis_report)

    def test_suite_definition_run_and_inspection(self):
        defined = self.project.query(
            """
            ASSERT SUITE ADD release_gate ID UNIQUE
                NAME "Identifiers are unique";
            ASSERT SUITE ADD release_gate Revenue MIN 0
                NAME "Revenue is non-negative";
            ASSERT SUITE ADD release_gate MISSING_PERCENT Region <= 10
                SEVERITY warning NAME "Region completeness";
            ASSERT SUITE SHOW release_gate;
            ASSERT SUITE LIST;
            """,
            auto_display=False,
        )

        self.assertTrue(defined.success)
        self.assertEqual(
            self.project.quality_suite("release_gate").test_count,
            3,
        )
        self.assertEqual(defined.results[-2].row_count, 3)
        self.assertEqual(defined.latest.data.loc[0, "name"], "release_gate")

        with self.assertRaises(ADQLExecutionError) as raised:
            self.project.query(
                "ASSERT SUITE RUN release_gate;",
                auto_display=False,
            )
        report = raised.exception.result.latest.value
        self.assertEqual(report.test_count, 3)
        self.assertEqual(report.blocking_failure_count, 2)

        non_blocking = self.project.query(
            "ASSERT SUITE RUN release_gate FAIL_ON never;",
            auto_display=False,
        )
        self.assertTrue(non_blocking.success)
        self.assertEqual(non_blocking.latest.value.failed_count, 3)

    def test_failed_assertion_can_continue_to_later_statements(self):
        run = self.project.query(
            "ASSERT ID UNIQUE; HEAD 2;",
            continue_on_error=True,
            auto_display=False,
        )

        self.assertFalse(run.success)
        self.assertEqual(run.failed_count, 1)
        self.assertEqual(run.completed_count, 1)
        self.assertEqual(run.latest.statement.kind, "HEAD")
        self.assertEqual(len(run.latest.data), 2)

    def test_suite_export_load_and_drop_round_trip(self):
        output = self.root / "quality-suite.json"
        self.project.query(
            f"""
            ASSERT SUITE ADD portable Revenue NOT NULL NAME "Revenue required";
            ASSERT SUITE ADD portable ROW_COUNT >= 4;
            ASSERT SUITE EXPORT portable TO "{output}";
            ASSERT SUITE DROP portable;
            ASSERT SUITE LOAD restored FROM "{output}";
            """,
            auto_display=False,
        )

        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["format_version"], 1)
        self.assertEqual(payload["test_count"], 2)
        self.assertEqual(self.project.quality_suite("restored").test_count, 2)
        self.assertNotIn("portable", self.project.state.quality_test_suites)

    def test_named_dataset_suite_targeting(self):
        clean = self.root / "clean.csv"
        pd.DataFrame(
            {
                "ID": [1, 2, 3],
                "Revenue": [10.0, 20.0, 30.0],
                "Region": ["North", "South", "West"],
            }
        ).to_csv(clean, index=False)

        run = self.project.query(
            f"""
            ADD DATASET clean FROM "{clean}";
            ASSERT SUITE ADD gate ID UNIQUE;
            ASSERT SUITE ADD gate Revenue NOT NULL;
            ASSERT DATASET clean SUITE RUN gate;
            """,
            auto_display=False,
        )

        self.assertTrue(run.success)
        self.assertEqual(run.latest.value.dataset, "clean")
        self.assertEqual(run.latest.value.passed_count, 2)

    def test_python_api_accepts_quality_assertion_objects(self):
        report = self.project.assert_quality(
            QualityAssertion(
                subject="column",
                column="Revenue",
                predicate="min",
                expected=-5,
                name="Revenue lower bound",
            )
        )

        self.assertTrue(report.success)
        self.assertEqual(report.results[0].assertion.display_name, "Revenue lower bound")
        self.assertIn("quality_tests", self.project.session_info()["workflow_state"])

    def test_quality_results_are_included_in_project_reports(self):
        quality = self.project.assert_quality(
            QualityAssertion(
                subject="row_count",
                predicate="compare",
                operator="=",
                expected=4,
                name="Expected import size",
            )
        )
        report = AutoDQReport(
            dataset=str(self.dataset),
            session=self.project.session,
            quality_tests=quality,
        )
        output = self.root / "quality-report.json"

        JSONExporter().export(report, output)
        payload = json.loads(output.read_text(encoding="utf-8"))
        markup = HTMLExporter()._build_html(report)

        self.assertEqual(payload["quality_tests"]["passed_count"], 1)
        self.assertIn("Data Quality Tests", markup)
        self.assertIn("Expected import size", markup)

    def test_blocking_assertion_returns_cli_failure_status(self):
        workflow = self.root / "quality-gate.adql"
        workflow.write_text(
            f'DATASET "{self.dataset}"; ASSERT Revenue NOT NULL;',
            encoding="utf-8",
        )
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["run", str(workflow)])

        self.assertEqual(status, 1)
        self.assertIn("[ERROR]", stdout.getvalue())
        self.assertIn("ADQL failed", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
