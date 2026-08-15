# AutoDQ 0.1.15 Release Notes

AutoDQ 0.1.15 adds production-oriented schema contracts and drift detection.
ADQL 2.3 can now define what a valid dataset must look like, preserve a compact
approved baseline, and gate later batches when their structure or statistical
behavior changes.

## Schema contracts

A contract is a versioned, portable JSON definition. It supports:

- required and optional columns;
- canonical data types;
- nullability and uniqueness;
- numeric and datetime minimum and maximum bounds;
- categorical allowed values;
- regular-expression patterns;
- per-column severity; and
- an explicit policy for unexpected columns.

Inference is deliberately conservative. Ranges are not inferred unless
requested, and allowed values are inferred only for low-cardinality columns.
Rules can then be refined explicitly.

```adql
SCHEMA CONTRACT CREATE sales_v1 FROM approved_sales
    VERSION 1.0.0 EXTRA_COLUMNS warning;
SCHEMA CONTRACT ADD sales_v1 COLUMN Transaction_ID
    TYPE integer REQUIRED true NULLABLE false UNIQUE true;
SCHEMA CONTRACT ADD sales_v1 COLUMN Revenue
    TYPE numeric REQUIRED true NULLABLE false MIN 0;
SCHEMA CONTRACT VALIDATE sales_v1 DATASET august_sales FAIL_ON error;
```

Validation is non-mutating and returns one structured row per check with the
observed value, expectation, failed count, severity, status, and message.

## Statistical drift baselines

A drift baseline contains compact summaries rather than source rows. Detection
covers:

- missing, added, and changed-type columns;
- missing-value percentage movement;
- distinct-ratio movement;
- Population Stability Index (PSI);
- values outside the baseline range;
- unseen categorical values;
- duplicate-rate change; and
- row-count change.

```adql
DRIFT BASELINE CREATE sales_baseline FROM approved_sales;
DRIFT DETECT REFERENCE sales_baseline DATASET august_sales
    CONTRACT sales_v1
    FAIL_ON warning
    PSI_WARNING 0.10 PSI_ERROR 0.25
    MISSING_WARNING 2 MISSING_ERROR 5;
```

Checks are classified as `stable`, `moderate`, or `major`. The stability score
is transparent:

```text
(stable checks + 0.5 × moderate checks) / all checks × 100
```

`FAIL_ON error` blocks major drift, `FAIL_ON warning` blocks moderate or major
drift, and `FAIL_ON never` records the report without stopping the workflow.
Adding `CONTRACT name` includes schema failures in the drift gate.

## Python API

```python
project.create_schema_contract("sales_v1", dataset="approved_sales")
project.add_schema_rule(
    "sales_v1",
    "Revenue",
    dtype="numeric",
    required=True,
    nullable=False,
    minimum=0,
)
schema = project.validate_schema("sales_v1", dataset="august_sales")

project.create_drift_baseline("sales_baseline", dataset="approved_sales")
drift = project.detect_drift(
    "sales_baseline",
    dataset="august_sales",
    contract="sales_v1",
    fail_on="warning",
)
```

Contracts and baselines accept the active dataset, a registered dataset name,
or a pandas DataFrame. The latest reports are available in project state and
are included in HTML and JSON project reports.

## Persistence and portability

`WORKSPACE SAVE` persists contract JSON under `contracts/` and drift baseline
JSON under `drift_baselines/`. Reopening the workspace restores the reusable
definitions. The latest dataset-derived reports reset when the active dataset
changes.

Definitions can also travel independently:

```adql
SCHEMA CONTRACT EXPORT sales_v1 TO "contracts/sales-v1.json" OVERWRITE;
SCHEMA CONTRACT LOAD sales_v1 FROM "contracts/sales-v1.json" OVERWRITE;
DRIFT BASELINE EXPORT sales_baseline TO "baselines/sales.json" OVERWRITE;
DRIFT BASELINE LOAD sales_baseline FROM "baselines/sales.json" OVERWRITE;
```

Artifact loading enforces bounded file sizes, bounded column counts, format
versions, safe paths in ADQL, and complete structural validation.

## Coordinated versions

- AutoDQ Python package: `0.1.15`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.8`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.15
```

Install `autodq-adql-0.3.8.vsix` through **Extensions: Install from VSIX...**
and reload VS Code.

## Compatibility

The new commands and public Python methods are additive. Existing ADQL 2.x
files, quality suites, cleaning flows, readiness analysis, modeling, SHAP,
BLUE diagnostics, reports, and saved notebook output remain supported.
