# AutoDQ 0.1.6 Release Notes

AutoDQ 0.1.6 adds `LET`, a safe ADQL assignment command for preserving
tabular results as reusable named dataset snapshots.

## Assign cleaned data

After cleaning a dataset, assign the complete cleaned stage and export it by
name:

```adql
CLEAN customers;
LET cleaned_customers = CLEANED;
EXPORT cleaned_customers TO "exports/cleaned-customers.csv" OVERWRITE;
```

The assigned name also works with `SELECT`, `PROFILE`, `USE DATASET`,
`LIST DATASETS`, and `SESSION DATASETS`.

## Assign registered data or query results

```adql
LET customer_snapshot = DATASET customers;

LET regional_sales = SELECT Region,
                            SUM(Revenue) AS total_revenue
                     FROM CURRENT
                     GROUP BY Region;

SELECT * FROM regional_sales ORDER BY total_revenue DESC;
EXPORT regional_sales TO "exports/regional-sales.xlsx";
```

`LET` snapshots are independent copies. Later source changes do not mutate the
assigned data. Existing names require `OVERWRITE`, built-in stage names are
reserved, and the active dataset cannot be overwritten. `SELECT` assignments
retain the normal query limit; direct stage assignments retain the complete
available stage.

## Python API

The underlying registration API is also public:

```python
snapshot = project.assign_dataset(
    "cleaned_customers",
    cleaned_dataframe,
    overwrite=False,
)
```

## Versions

- AutoDQ Python package: `0.1.6`
- AutoDQ ADQL VS Code extension: `0.2.9`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.6
```

Install `autodq-adql-0.2.9.vsix` through **Extensions: Install from VSIX...**
in VS Code, then run **Developer: Reload Window**.
