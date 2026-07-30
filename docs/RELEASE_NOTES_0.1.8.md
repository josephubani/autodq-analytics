# AutoDQ 0.1.8 Release Notes

AutoDQ 0.1.8 adds a first-class, audited missing-value workflow to ADQL and the
Python project API. Automatic cleaning can still leave domain-sensitive values
for review; this release gives users an explicit way to fill or remove them and
verify that missing counts reach the intended level.

## Audited missing-value workflows

Inspect missing values without changing data:

```adql
MISSING SUMMARY;
```

Apply datatype-aware or deliberate fills:

```adql
MISSING FILL City VALUE "Not provided";
MISSING FILL Customer_Age STRATEGY median;
MISSING FILL Revenue STRATEGY interpolate;
MISSING FILL ALL STRATEGY auto;
```

`auto` uses median for numeric columns and mode for other datatypes. Available
explicit strategies are `constant`, `mean`, `median`, `mode`, `zero`, `ffill`,
`bfill`, and `interpolate`.

Remove incomplete observations or fields when imputation is not appropriate:

```adql
MISSING DROP ROWS COLUMNS City,Region HOW any;
MISSING DROP ROWS COLUMNS Phone,Email HOW all;
MISSING DROP COLUMNS Notes,Unused;
MISSING DROP COLUMNS MIN_PERCENT 50;
```

Every filled cell, removed row, and removed column is recorded in the cleaning
audit. Mutations are staged until `CLEANING APPLY`, and the active model target
cannot be removed.

## Named datasets and reusable results

Missing-value commands support the standard dataset selector:

```adql
MISSING DATASET customers SUMMARY;
MISSING DATASET customers FILL City VALUE "Not provided";
CLEANING DATASET customers APPLY;
LET complete_customers = CLEANED;
EXPORT complete_customers TO "complete-customers.csv" OVERWRITE;
```

## Python API

The matching public methods are:

- `missing_summary()`
- `fill_missing()`
- `drop_missing_rows()`
- `drop_missing_columns()`

They use the same cleaning review and audit trail as ADQL.

## Release components

- AutoDQ Python package: `0.1.8`
- AutoDQ ADQL VS Code extension: `0.3.1`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.8
```

Install `autodq-adql-0.3.1.vsix` through
**Extensions: Install from VSIX...** to update manually installed VS Code
support.
