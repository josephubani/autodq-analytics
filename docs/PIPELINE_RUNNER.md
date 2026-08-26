# AutoDQ Pipeline Runner

The AutoDQ pipeline runner executes an ADQL workflow through a stable JSON
contract designed for schedulers, CI systems, and future Fabric, Azure Data
Factory, Databricks, and Snowflake adapters. It is headless: workflow output is
captured in the result instead of being mixed with the orchestrator response.

This release provides the platform-neutral foundation and local filesystem
connectors. It does not yet provide credentials or native cloud connectors.

## Python API

```python
from autodq import PipelineRunSpec, PipelineRunner

spec = PipelineRunSpec(
    workflow="workflows/sales-quality.adql",
    dataset="datasets/daily-sales.csv",
    target="Revenue",
    run_id="daily-sales-2026-08-26",
    working_directory="/opt/autodq",
    result_path="artifacts/daily-sales-result.json",
    overwrite_result=True,
    metadata={
        "orchestrator": "fabric",
        "pipeline": "daily-sales-quality",
        "attempt": 1,
    },
)

result = PipelineRunner().run(spec)

print(result.status)
print(result.exit_code)
print(result.metrics)
print([artifact.uri for artifact in result.artifacts])
```

`PipelineRunner.run()` does not raise for normal workflow, quality-gate, input,
or configuration failures. It returns a structured `PipelineRunResult` so an
orchestrator can inspect the status and exit code consistently.

## Run specification JSON

A run can be stored as JSON and submitted without changing the workflow:

```json
{
  "schema_version": "1.0",
  "workflow": "workflows/sales-quality.adql",
  "dataset": "datasets/daily-sales.csv",
  "target": "Revenue",
  "continue_on_error": false,
  "working_directory": "/opt/autodq",
  "result_path": "artifacts/daily-sales-result.json",
  "overwrite_result": true,
  "run_id": "daily-sales-2026-08-26",
  "metadata": {
    "orchestrator": "databricks",
    "job": "daily-sales-quality"
  }
}
```

When `working_directory` is omitted from a specification file, paths are
resolved relative to the directory containing that file.

## Command line

Run a workflow directly:

```bash
autodq pipeline \
  --workflow workflows/sales-quality.adql \
  --dataset datasets/daily-sales.csv \
  --target Revenue \
  --run-id daily-sales-2026-08-26 \
  --metadata '{"orchestrator":"adf","attempt":1}' \
  --result artifacts/daily-sales-result.json \
  --overwrite-result
```

Run a saved specification:

```bash
autodq pipeline --spec pipeline-run.json
```

The command prints exactly one JSON result document to standard output. Output
produced by AutoDQ, pandas, visualization libraries, or ADQL statements is
captured under `logs.stdout` and `logs.stderr`.

## Exit codes

| Code | Name | Meaning |
|---:|---|---|
| `0` | `SUCCESS` | Every selected ADQL cell and statement completed. |
| `1` | `WORKFLOW_FAILED` | The workflow ran, but an assertion, contract, drift gate, or statement failed. |
| `2` | `CONFIGURATION_ERROR` | The specification, input, path, or ADQL configuration was invalid. |
| `3` | `INTERNAL_ERROR` | An unexpected runtime or result-storage failure occurred. |

These codes are exposed through `PipelineExitCode` and are stable integration
points for conditional pipeline branches.

## Result contract

Each result contains:

- A unique `run_id`, status, success flag, and exit code.
- UTC start and finish timestamps and elapsed duration.
- Resolved workflow, dataset, and result URIs.
- User-supplied orchestration metadata.
- AutoDQ, Python, implementation, and platform versions.
- Cell, statement, row, column, event, and timing metrics.
- Discovered exported datasets, reports, dashboards, models, visualizations,
  quality suites, schema contracts, drift baselines, and audit files.
- Lifecycle events suitable for audit and monitoring.
- Captured and bounded stdout/stderr logs.
- The complete serializable ADQL file result.

Result files are written atomically by the local artifact store. Existing files
are rejected unless `overwrite_result` is enabled.

## Connector boundary

The runner accepts replaceable `PipelineSourceResolver` and
`PipelineArtifactStore` implementations:

```python
runner = PipelineRunner(
    source_resolver=my_platform_source_resolver,
    artifact_store=my_platform_artifact_store,
)
```

The built-in `LocalSourceResolver` accepts local paths and `file://` URIs. It
rejects other URI schemes with an actionable message. Future platform adapters
can materialize a Fabric OneLake, ADLS, DBFS, Unity Catalog, or Snowflake
reference and can persist the run result to the platform's artifact store
without changing AutoDQ or ADQL execution.

## Security and operational behavior

- Metadata must be JSON serializable and should not contain passwords, tokens,
  or connection strings.
- Run IDs are restricted to safe letters, numbers, periods, underscores, and
  hyphens.
- Result destinations are checked before the workflow starts so an accidental
  overwrite does not waste compute or partially execute a pipeline.
- Captured logs default to 100,000 characters per stream and can be bounded
  between 1,000 and 1,000,000 characters.
- ADQL safety validation, explicit mutation rules, quality gates, schema
  contracts, and drift failure behavior are preserved unchanged.
