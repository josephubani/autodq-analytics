import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import (
    ADQLExecutionError,
    ADQLParser,
    ADQLSyntaxError,
    ADQLValidationError,
    ADQLValidator,
    AutoDQ,
    DriftBaseline,
    SchemaContract,
)
from autodq.models.report import AutoDQReport
from autodq.reporting.html_exporter import HTMLExporter
from autodq.reporting.json_exporter import JSONExporter


class SchemaDriftTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        rng = np.random.default_rng(42)
        self.baseline = pd.DataFrame(
            {
                "Transaction_ID": [f"T-{index:04d}" for index in range(300)],
                "Revenue": rng.normal(100, 12, 300).round(2),
                "Region": rng.choice(["North", "South", "East"], 300),
                "Created_At": pd.date_range("2026-01-01", periods=300, freq="h"),
            }
        )
        self.current = self.baseline.copy()
        self.current["Revenue"] = self.current["Revenue"] + 250
        self.current.loc[:35, "Region"] = "West"
        self.current.loc[:30, "Revenue"] = np.nan
        self.current["Unexpected"] = "new"
        self.baseline_path = self.root / "baseline.csv"
        self.current_path = self.root / "current.csv"
        self.baseline.to_csv(self.baseline_path, index=False)
        self.current.to_csv(self.current_path, index=False)
        self.project = AutoDQ(str(self.baseline_path))
        self.project.load()
        self.project.add_dataset("baseline", data=self.baseline)
        self.project.add_dataset("current", data=self.current)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_contract_inference_manual_rules_and_validation(self):
        contract = self.project.create_schema_contract(
            "sales_v1",
            dataset="baseline",
            extra_columns="warning",
        )
        self.project.add_schema_rule(
            "sales_v1",
            "Revenue",
            dtype="numeric",
            nullable=False,
            minimum=0,
        )
        report = self.project.validate_schema(
            "sales_v1", dataset="current", fail_on="never"
        )
        self.assertIsInstance(contract, SchemaContract)
        self.assertEqual(contract.column_count, 4)
        self.assertFalse(report.results[0].message == "")
        failed_rules = {
            (item.column, item.rule)
            for item in report.results
            if not item.passed
        }
        self.assertIn(("Revenue", "not_null"), failed_rules)
        self.assertIn(("Unexpected", "extra_column"), failed_rules)
        self.assertTrue(report.success)
        self.assertEqual(report.fail_on, "never")

    def test_schema_gate_preserves_structured_failed_result(self):
        self.project.create_schema_contract("sales_v1", dataset="baseline")
        self.project.add_schema_rule(
            "sales_v1", "Revenue", nullable=False, severity="error"
        )
        with self.assertRaises(ADQLExecutionError) as raised:
            self.project.query(
                "SCHEMA CONTRACT VALIDATE sales_v1 DATASET current;",
                auto_display=False,
            )
        result = raised.exception.result.latest
        self.assertEqual(result.error_type, "ADQLContractError")
        self.assertIsNotNone(result.data)
        self.assertGreater(result.value.blocking_failure_count, 0)

    def test_contract_export_load_is_versioned(self):
        contract = self.project.create_schema_contract("sales_v1", dataset="baseline")
        output = self.root / "sales-v1.json"
        self.project.export_schema_contract("sales_v1", output)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["format_version"], 1)
        self.assertEqual(payload["contract_version"], "1.0.0")
        self.project.drop_schema_contract("sales_v1")
        restored = self.project.load_schema_contract("restored", output)
        self.assertEqual(restored.column_count, contract.column_count)
        self.assertEqual(restored.name, "restored")

    def test_identical_data_is_stable_and_shift_is_detected(self):
        baseline = self.project.create_drift_baseline(
            "sales_baseline", dataset="baseline"
        )
        stable = self.project.detect_drift(
            "sales_baseline", dataset="baseline", fail_on="never"
        )
        shifted = self.project.detect_drift(
            "sales_baseline", dataset="current", fail_on="never"
        )
        self.assertIsInstance(baseline, DriftBaseline)
        self.assertEqual(stable.stability_score, 100.0)
        self.assertEqual(stable.major_count, 0)
        self.assertGreater(shifted.major_count, 0)
        self.assertLess(shifted.stability_score, 100.0)
        metrics = set(shifted.to_frame()["metric"])
        self.assertIn("population_stability_index", metrics)
        self.assertIn("missing_percent", metrics)
        self.assertIn("added_column", metrics)

    def test_drift_gate_and_optional_contract(self):
        self.project.create_schema_contract("sales_v1", dataset="baseline")
        self.project.create_drift_baseline("sales_baseline", dataset="baseline")
        with self.assertRaises(ADQLExecutionError) as raised:
            self.project.query(
                "DRIFT DETECT REFERENCE sales_baseline DATASET current "
                "CONTRACT sales_v1 FAIL_ON error;",
                auto_display=False,
            )
        result = raised.exception.result.latest
        self.assertEqual(result.error_type, "ADQLDriftError")
        self.assertGreater(result.value.major_count, 0)
        self.assertEqual(result.value.contract_name, "sales_v1")

    def test_baseline_export_and_load_without_raw_reference(self):
        original = self.project.create_drift_baseline(
            "sales_baseline", dataset="baseline"
        )
        output = self.root / "sales-baseline.json"
        self.project.export_drift_baseline("sales_baseline", output)
        self.project.drop_drift_baseline("sales_baseline")
        restored = self.project.load_drift_baseline("restored", output)
        self.assertEqual(restored.row_count, original.row_count)
        self.assertEqual(restored.profiled_column_count, 4)
        report = self.project.detect_drift(
            "restored", dataset="baseline", fail_on="never"
        )
        self.assertEqual(report.stability_score, 100.0)

    def test_parser_accepts_full_case_insensitive_language(self):
        source = f'''
        schema contract create sales_v1 from baseline infer_ranges false
            infer_categories true extra_columns warning;
        ScHeMa CoNtRaCt AdD sales_v1 CoLuMn Revenue TyPe numeric
            NuLlAbLe false MiN 0 SeVeRiTy error;
        SCHEMA CONTRACT SHOW sales_v1;
        SCHEMA CONTRACT LIST;
        SCHEMA CONTRACT EXPORT sales_v1 TO "{self.root / 'contract.json'}" OVERWRITE;
        DRIFT BASELINE CREATE sales_base FROM baseline;
        DRIFT BASELINE SHOW sales_base;
        DRIFT BASELINE LIST;
        DRIFT BASELINE EXPORT sales_base TO "{self.root / 'baseline.json'}" OVERWRITE;
        DRIFT DETECT REFERENCE sales_base DATASET current CONTRACT sales_v1
            FAIL_ON never PSI_WARNING 0.1 PSI_ERROR 0.25;
        '''
        script = ADQLParser().parse(source)
        ADQLValidator().validate(script)
        self.assertEqual(script.statement_count, 10)
        run = self.project.query(
            source,
            continue_on_error=False,
            auto_display=False,
        )
        self.assertTrue(run.success)
        self.assertEqual(run.latest.value.baseline_name, "sales_base")

    def test_invalid_schema_and_drift_are_rejected_before_execution(self):
        parser = ADQLParser()
        for source in (
            "SCHEMA;",
            "SCHEMA CONTRACT CREATE;",
            "SCHEMA CONTRACT ADD sales COLUMN Revenue;",
            "DRIFT;",
            "DRIFT DETECT DATASET current;",
            "DRIFT BASELINE EXPORT base;",
        ):
            with self.subTest(source=source):
                with self.assertRaises(ADQLSyntaxError):
                    parser.parse(source)
        for source in (
            "SCHEMA CONTRACT CREATE sales EXTRA_COLUMNS maybe;",
            "SCHEMA CONTRACT ADD sales COLUMN Revenue TYPE mystery;",
            "SCHEMA CONTRACT VALIDATE sales FAIL_ON sometimes;",
            "SCHEMA CONTRACT EXPORT sales TO contract.csv;",
            "DRIFT DETECT REFERENCE base PSI_WARNING 0.3 PSI_ERROR 0.2;",
            "DRIFT BASELINE LOAD base FROM baseline.csv;",
        ):
            with self.subTest(source=source):
                with self.assertRaises(ADQLValidationError):
                    ADQLValidator().validate(parser.parse(source))

    def test_reports_have_rich_html_and_do_not_mutate_data(self):
        before = self.project.dataset_manager.get_data("current").copy()
        self.project.create_schema_contract("sales_v1", dataset="baseline")
        schema = self.project.validate_schema(
            "sales_v1", dataset="current", fail_on="never"
        )
        self.project.create_drift_baseline("sales_base", dataset="baseline")
        drift = self.project.detect_drift(
            "sales_base", dataset="current", fail_on="never"
        )
        self.assertIn("Schema Contract Validation", schema.to_notebook_html())
        self.assertIn("Data Drift Detection", drift.to_notebook_html())
        pd.testing.assert_frame_equal(
            before,
            self.project.dataset_manager.get_data("current"),
        )

    def test_workspace_persists_contracts_and_baselines(self):
        workspace_root = self.root / "workspaces"
        project = AutoDQ.create_workspace(
            "Schema Monitoring",
            str(self.baseline_path),
            workspace_root=str(workspace_root),
        )
        project.load()
        project.create_schema_contract("sales_v1")
        project.create_drift_baseline("sales_base")
        project.save_workspace(include_model=False)
        restored = AutoDQ.open_workspace(
            "schema-monitoring",
            workspace_root=str(workspace_root),
            load_model=False,
        )
        self.assertEqual(list(restored.state.schema_contracts), ["sales_v1"])
        self.assertEqual(list(restored.state.drift_baselines), ["sales_base"])
        self.assertTrue(
            (restored.workspace.contracts_dir / "sales_v1.json").is_file()
        )
        self.assertTrue(
            (restored.workspace.drift_baselines_dir / "sales_base.json").is_file()
        )

    def test_project_exports_include_schema_and_drift_reports(self):
        self.project.create_schema_contract("sales_v1", dataset="baseline")
        schema = self.project.validate_schema(
            "sales_v1", dataset="current", fail_on="never"
        )
        self.project.create_drift_baseline("sales_base", dataset="baseline")
        drift = self.project.detect_drift(
            "sales_base", dataset="current", fail_on="never"
        )
        report = AutoDQReport(
            dataset="current",
            session=self.project.session,
            schema_validation=schema,
            drift=drift,
        )
        json_path = self.root / "monitoring.json"
        html_path = self.root / "monitoring.html"
        JSONExporter().export(report, json_path)
        HTMLExporter().export(report, html_path)
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        markup = html_path.read_text(encoding="utf-8")
        self.assertEqual(payload["schema_validation"]["contract_name"], "sales_v1")
        self.assertEqual(payload["drift"]["baseline_name"], "sales_base")
        self.assertIn("Schema Contract Validation", markup)
        self.assertIn("Schema and Data Drift", markup)


if __name__ == "__main__":
    unittest.main()
