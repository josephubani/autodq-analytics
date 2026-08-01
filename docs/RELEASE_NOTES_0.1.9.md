# AutoDQ 0.1.9 Release Notes

AutoDQ 0.1.9 adds direct inspection and audited removal of exact duplicate rows
to ADQL and the Python project API. Users can now see the complete repeated
records before choosing a retention policy, finalize the result into the
`CLEANED` stage, and preserve it with `LET`.

## Exact duplicate inspection

Display every row belonging to every exact-match group:

```adql
DUPLICATES SUMMARY;
```

The result includes:

- `duplicate_group`: the exact-match group number
- `occurrences`: the number of rows in that group
- `source_index`: the original row index
- every original dataset column

This makes the output suitable for human review rather than returning only a
duplicate count. ADQL notebook truncation and **View full output** remain
available for large duplicate sets.

## Audited duplicate removal

Choose which occurrence AutoDQ should retain:

```adql
DUPLICATES DROP KEEP first REASON "Repeated source import";
DUPLICATES DROP KEEP last;
DUPLICATES DROP KEEP none;
```

`KEEP first` is the default. `KEEP last` retains the final occurrence, while
`KEEP none` removes all rows in every duplicate group. Every removed row is
recorded as an `exact_duplicate_row_removed` audit event.

The change is staged in the interactive cleaning review. Finalize it and create
a reusable named snapshot with:

```adql
DUPLICATES SUMMARY;
DUPLICATES DROP KEEP first;
DUPLICATES SUMMARY;
CLEANING APPLY;

LET unique_sales = CLEANED;
EXPORT unique_sales TO "unique-sales.csv" OVERWRITE;
AUDIT EXPORT TO "duplicate-removal-audit.json";
```

## Named datasets

The standard dataset selector works throughout the workflow:

```adql
DUPLICATES DATASET customers SUMMARY;
DUPLICATES DATASET customers DROP KEEP first;
CLEANING DATASET customers APPLY;
LET unique_customers = CLEANED;
```

## Python API

The equivalent Python workflow is:

```python
duplicates = project.duplicate_summary()
result = project.drop_duplicates(keep="first", reason="Repeated import")
cleaned = project.apply_cleaning_review()
```

## Release components

- AutoDQ Python package: `0.1.9`
- AutoDQ ADQL VS Code extension: `0.3.2`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.9
```

Install `autodq-adql-0.3.2.vsix` through
**Extensions: Install from VSIX...** to update manually installed VS Code
support.
