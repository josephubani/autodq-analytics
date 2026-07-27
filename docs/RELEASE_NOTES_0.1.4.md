# AutoDQ 0.1.4 Release Notes

AutoDQ 0.1.4 adds consistent named-dataset workflow targeting throughout
ADQL. Registering another dataset no longer requires a separate `USE DATASET`
statement before every workflow.

## Named workflow datasets

Commands with no other positional argument accept the dataset name directly:

```adql
ADD DATASET customers FROM "customers.csv";
PROFILE customers;
DIAGNOSE customers;
RECOMMEND customers;
```

Every stateful command also supports a universal selector immediately after
the command name:

```adql
AUTO DATASET customers MODE review VISUALIZE false;
HEAD DATASET customers 10;
DOMAIN DATASET customers ADD Customer_Age MIN 18 MAX 100;
REPORT DATASET customers TO "customers-report.html" OVERWRITE;
```

Targeting activates the named dataset before execution. Later commands without
a selector continue on that dataset. Repeating the same selector is
idempotent and preserves earlier profile, diagnosis, cleaning, feature, and
model artifacts.

## Direct queries and exports

Registered datasets can also be read without changing the active workflow
dataset:

```adql
SELECT Customer_ID, Region FROM customers LIMIT 25;
EXPORT customers TO "customers-export.csv" OVERWRITE;
```

Unknown names now produce an actionable error containing every registered
dataset name. The Python API also exposes `project.export_named_dataset()`.

## Versions

- AutoDQ Python package: `0.1.4`
- AutoDQ ADQL VS Code extension: `0.2.7`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.4
```

Install `autodq-adql-0.2.7.vsix` through **Extensions: Install from VSIX...**
in VS Code, then run **Developer: Reload Window**.
