# AutoDQ 0.1.20 Release Notes

AutoDQ 0.1.20 keeps every workflow stage consistent as data moves through
ADQL and the Python API. It prevents older dataset snapshots, charts, models,
and predictions from being reused after their upstream data has changed.

## Live named datasets

Operations that accept a registered dataset name now read the live active dataset
when that name is active. A `SET TYPE` conversion is therefore visible
immediately to schema contracts, drift baselines, readiness references,
merges, concatenations, `LET`, queries, and exports.

Overwriting the active name with `ADD DATASET ... OVERWRITE` now keeps that
dataset active and safely resets outputs derived from the replaced data.

## Safe workflow invalidation

AutoDQ now invalidates only the downstream stages that can no longer be
trusted:

- applying cleaning clears older validation, engineered data, models,
  predictions, explanations, model-dependent BLUE results, and dashboards;
- applying or creating features clears older models and predictions so a
  following `PREDICT` retrains through the normal project workflow; and
- changing the target clears target-dependent correlation, readiness,
  features, modeling, prediction, explanation, and BLUE outputs.

Charts derived from invalidated stages are removed from the gallery. Switching
or replacing the active dataset clears the gallery completely, preventing a
dashboard for one dataset from displaying charts created from another.

## Clear visualization diagnostics

ADQL now explains how to recover when `STAGE cleaned` or `STAGE engineered`
is unavailable. For a named snapshot that already contains the desired data,
use `STAGE current`; otherwise run `CLEAN`, `CLEANING APPLY`, or
`FEATURE APPLY` first. Unknown visualization stages now fail clearly instead
of silently using current data.

## Validation

The release passes 219 Python tests, all VS Code extension tests, bytecode
compilation, the full automatic sales workflow, schema contract and drift
monitoring workflows, source-distribution inspection, and clean-wheel smoke
tests.

## Versions

- AutoDQ Python package: `0.1.20`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.13`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.20
```

For manual VS Code installation, download `autodq-adql-0.3.13.vsix` from the
matching GitHub release and use **Extensions: Install from VSIX...**.
