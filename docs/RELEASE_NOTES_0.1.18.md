# AutoDQ 0.1.18 Release Notes

AutoDQ 0.1.18 makes `LET` assignments quiet and intentional across Python,
terminal, Jupyter, and executable `.adql` notebooks.

## Compact LET confirmation

`LET` now displays a compact assignment confirmation containing:

- the registered dataset name;
- the assignment source;
- row and column counts; and
- whether `OVERWRITE` replaced an existing snapshot.

It does not render the assigned rows automatically. This prevents large stage
or `SELECT` assignments from repeating an entire table just because a reusable
snapshot was created.

```adql
LET cleaned_sales = CLEANED;
LET regional_sales = SELECT Region,
                            SUM(Revenue) AS total_revenue
                     FROM CURRENT
                     GROUP BY Region;
```

Use an explicit inspection command when row output is wanted:

```adql
HEAD cleaned_sales 10;
SELECT * FROM regional_sales LIMIT 25;
```

## Compatibility and semantics

- The assigned DataFrame remains available on the Python `ADQLResult.data`
  property for programmatic consumers.
- The complete independent snapshot remains registered under its `LET` name
  for `SELECT`, `HEAD`, `PROFILE`, `EXPORT`, `USE DATASET`, and other
  dataset-aware commands.
- `LET` still does not activate the assigned dataset.
- ADQL remains language version `2.3`; this release changes presentation, not
  grammar or assignment semantics.

## Versions

- AutoDQ Python package: `0.1.18`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.11`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.18
```

For manual VS Code installation, build or download
`autodq-adql-0.3.11.vsix`, then use **Extensions: Install from VSIX...**.
