import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd

from autodq import (
    PIPELINE_SCHEMA_VERSION,
    PipelineExitCode,
    PipelineRunSpec,
    PipelineRunner,
    __version__,
)
from autodq.cli import main


class PipelineRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.dataset = self.root / "sales.csv"
        pd.DataFrame(
            {
                "Order_ID": [1, 2, 3, 4],
                "Region": ["North", "South", "East", "West"],
                "Revenue": [100.0, 150.0, 75.0, 200.0],
            }
        ).to_csv(self.dataset, index=False)
        self.workflow = self.root / "pipeline.adql"
        self.workflow.write_text(
            "# %% [Dataset]\n"
            'DATASET "sales.csv" TARGET Revenue;\n'
            "# %% [Quality]\n"
            "PROFILE;\n"
            "# %% [Output]\n"
            'EXPORT CURRENT TO "exports/current.csv" OVERWRITE;\n',
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_pipeline_run_returns_contract_metrics_logs_and_artifacts(self):
        spec = PipelineRunSpec(
            workflow="pipeline.adql",
            working_directory=str(self.root),
            result_path="runs/result.json",
            run_id="fabric-run-42",
            metadata={"orchestrator": "fabric", "attempt": 1},
        )

        result = PipelineRunner().run(spec)

        self.assertTrue(result.success)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.exit_code, PipelineExitCode.SUCCESS)
        self.assertEqual(result.metrics["cell_count"], 3)
        self.assertEqual(result.metrics["statement_count"], 3)
        self.assertEqual(result.metrics["rows"], 4)
        self.assertEqual(len(result.artifacts), 1)
        self.assertEqual(result.artifacts[0].kind, "dataset")
        self.assertEqual(result.artifacts[0].name, "current.csv")
        self.assertTrue((self.root / "exports" / "current.csv").is_file())
        self.assertIn("Current dataset exported", result.stdout)
        self.assertEqual(result.stderr, "")

        result_path = self.root / "runs" / "result.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], PIPELINE_SCHEMA_VERSION)
        self.assertEqual(payload["run_id"], "fabric-run-42")
        self.assertEqual(payload["metadata"]["orchestrator"], "fabric")
        self.assertEqual(payload["environment"]["autodq_version"], __version__)
        self.assertTrue(payload["result_uri"].startswith("file://"))
        self.assertEqual(payload["artifacts"][0]["kind"], "dataset")

    def test_failed_quality_gate_uses_workflow_failed_exit_code(self):
        failing = self.root / "failing.adql"
        failing.write_text(
            "# %% [Dataset]\n"
            'DATASET "sales.csv" TARGET Revenue;\n'
            "# %% [Gate]\n"
            "ASSERT Revenue MIN 1000;\n",
            encoding="utf-8",
        )

        result = PipelineRunner().run(
            PipelineRunSpec(
                workflow=str(failing),
                working_directory=str(self.root),
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.exit_code, PipelineExitCode.WORKFLOW_FAILED)
        self.assertEqual(result.metrics["failed_cell_count"], 1)
        self.assertEqual(result.metrics["failed_statement_count"], 1)
        self.assertIsNone(result.error_type)
        self.assertEqual(result.events[-1].event, "run_failed")

    def test_missing_input_is_structured_configuration_error_and_is_saved(self):
        result = PipelineRunner().run(
            PipelineRunSpec(
                workflow="missing.adql",
                working_directory=str(self.root),
                result_path="missing-result.json",
            )
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(
            result.exit_code,
            PipelineExitCode.CONFIGURATION_ERROR,
        )
        self.assertEqual(result.error_type, "FileNotFoundError")
        payload = json.loads(
            (self.root / "missing-result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(payload["error_type"], "FileNotFoundError")

    def test_existing_result_fails_before_the_workflow_runs(self):
        result_path = self.root / "existing.json"
        result_path.write_text("original", encoding="utf-8")

        result = PipelineRunner().run(
            PipelineRunSpec(
                workflow=str(self.workflow),
                result_path=str(result_path),
            )
        )

        self.assertEqual(result.exit_code, PipelineExitCode.CONFIGURATION_ERROR)
        self.assertEqual(result.error_type, "FileExistsError")
        self.assertEqual(result_path.read_text(encoding="utf-8"), "original")
        self.assertFalse((self.root / "exports" / "current.csv").exists())

    def test_spec_json_uses_its_directory_for_relative_references(self):
        specification = self.root / "run-spec.json"
        specification.write_text(
            json.dumps(
                {
                    "schema_version": PIPELINE_SCHEMA_VERSION,
                    "workflow": "pipeline.adql",
                    "result_path": "runs/from-spec.json",
                    "overwrite_result": True,
                    "run_id": "databricks-job-7",
                    "metadata": {"job": "daily-quality"},
                }
            ),
            encoding="utf-8",
        )

        spec = PipelineRunSpec.from_json(specification)
        result = PipelineRunner().run(spec)

        self.assertTrue(result.success)
        self.assertEqual(
            Path(spec.working_directory).resolve(),
            self.root.resolve(),
        )
        self.assertTrue((self.root / "runs" / "from-spec.json").is_file())

    def test_pipeline_cli_prints_one_machine_readable_json_document(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                [
                    "pipeline",
                    "--workflow",
                    "pipeline.adql",
                    "--working-directory",
                    str(self.root),
                    "--run-id",
                    "adf-activity-9",
                    "--metadata",
                    '{"orchestrator":"adf"}',
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0, stderr.getvalue())
        self.assertEqual(payload["run_id"], "adf-activity-9")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["metadata"]["orchestrator"], "adf")
        self.assertNotIn("Cell 1", stdout.getvalue())

    def test_pipeline_cli_returns_json_for_an_invalid_specification(self):
        invalid = self.root / "invalid.json"
        invalid.write_text('{"unexpected": true}', encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["pipeline", "--spec", str(invalid)])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, PipelineExitCode.CONFIGURATION_ERROR)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(payload["error_type"], "ValueError")
        self.assertTrue(payload["run_id"])

    def test_artifact_store_failure_uses_internal_error_exit_code(self):
        class FailingStore:
            def location(self, reference, **options):
                return "memory://pipeline-result.json"

            def write_json(self, reference, payload, **options):
                raise RuntimeError("artifact service unavailable")

        result = PipelineRunner(artifact_store=FailingStore()).run(
            PipelineRunSpec(
                workflow=str(self.workflow),
                result_path="pipeline-result.json",
            )
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.exit_code, PipelineExitCode.INTERNAL_ERROR)
        self.assertEqual(result.error_type, "RuntimeError")
        self.assertIn("artifact service unavailable", result.error_message)
        self.assertEqual(result.events[-1].event, "result_write_failed")

    def test_unsupported_source_uri_requests_a_platform_connector(self):
        result = PipelineRunner().run(
            PipelineRunSpec(workflow="abfss://container/workflow.adql")
        )

        self.assertEqual(result.exit_code, PipelineExitCode.CONFIGURATION_ERROR)
        self.assertIn("platform-specific source resolver", result.error_message)

    def test_pipeline_spec_rejects_unknown_and_conflicting_options(self):
        with self.assertRaisesRegex(ValueError, "Unknown pipeline"):
            PipelineRunSpec.from_dict(
                {"workflow": "test.adql", "unexpected": True}
            )

        with self.assertRaisesRegex(ValueError, "either cell"):
            PipelineRunSpec(
                workflow="test.adql",
                cell=1,
                through_cell=2,
            )

    def test_captured_logs_respect_the_configured_character_limit(self):
        captured = PipelineRunner._bounded_log("x" * 2_000, 1_000)

        self.assertEqual(len(captured), 1_000)
        self.assertIn("log character(s) omitted", captured)


if __name__ == "__main__":
    unittest.main()
