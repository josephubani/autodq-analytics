# AutoDQ 0.1.21 Release Notes

AutoDQ 0.1.21 introduces platform-neutral pipeline execution for ADQL. The
same validated workflow that runs in VS Code, Jupyter, or `autodq run` can now
return a stable orchestration contract for scheduled jobs, CI systems, and the
future Fabric, Azure Data Factory, Databricks, and Snowflake adapters.

## Headless pipeline execution

The new public Python APIs are:

- `PipelineRunSpec`
- `PipelineRunner`
- `PipelineRunResult`
- `PipelineExitCode`
- `PipelineArtifact`
- `PipelineEvent`
- `PipelineSourceResolver`
- `PipelineArtifactStore`

The matching CLI accepts either a direct `.adql` workflow or a reusable JSON
run specification:

```bash
autodq pipeline \
  --workflow workflows/sales-quality.adql \
  --dataset datasets/daily-sales.csv \
  --target Revenue \
  --run-id daily-sales-2026-08-26 \
  --result artifacts/daily-sales-result.json \
  --overwrite-result
```

```bash
autodq pipeline --spec pipeline-run.json
```

The command prints one JSON document. Normal AutoDQ and ADQL output is captured
inside `logs.stdout` and `logs.stderr`, keeping scheduler output parseable.

## Stable pipeline result

Every run records:

- A safe run ID and user-supplied orchestration metadata.
- UTC timestamps, duration, resolved input/output URIs, and target.
- AutoDQ, Python, implementation, and platform versions.
- Cell, statement, row, column, session-event, and timing metrics.
- Bounded stdout and stderr logs.
- Auditable lifecycle events.
- The complete serializable ADQL result.
- Exported datasets, reports, dashboards, visualizations, models, cleaning
  audits, quality suites, schema contracts, and drift baselines.

The stable orchestration exit codes distinguish the final outcome:

- `0`: success
- `1`: workflow or data-quality gate failed
- `2`: invalid specification, input, path, or ADQL configuration
- `3`: unexpected runtime or result-storage failure

## Connector foundation

`LocalSourceResolver` and `LocalArtifactStore` provide the default local path
and `file://` behavior. Custom source and artifact implementations can be
injected into `PipelineRunner` without changing ADQL execution. Native cloud
credentials and connectors are intentionally planned for later releases.

Result files are written atomically. Existing destinations are protected unless
`overwrite_result` is explicitly enabled, and the destination is checked before
the workflow starts.

## Compatibility

- Existing Python `AutoDQ` projects are unchanged.
- Existing `autodq run` commands are unchanged.
- Existing `.adql` files require no changes.
- ADQL remains version `2.3`.
- VS Code notebook execution and saved outputs remain unchanged.

## Versions

- AutoDQ Python package: `0.1.21`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.14`
- Pipeline result schema: `1.0`

Upgrade AutoDQ with:

```bash
python -m pip install --upgrade autodq==0.1.21
```

For manual VS Code installation, download `autodq-adql-0.3.14.vsix` from the
matching GitHub release and install it with **Extensions: Install from VSIX**.
Upgrade the Python package separately because the VSIX does not contain the
AutoDQ Python runtime.

See [Pipeline runner](PIPELINE_RUNNER.md) for the complete run-specification,
Python API, CLI, connector, result-field, and operational behavior reference.
