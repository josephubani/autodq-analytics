# AutoDQ 0.1.23 Release Notes

AutoDQ 0.1.23 introduces concise schema-contract and drift syntax in ADQL 2.5.
It keeps the existing schema and drift engines, artifacts, validation rules,
and reports unchanged while making the common workflow easier to read and
teach.

## Concise workflow

```adql
CONTRACT sales_contract FROM cleaned_sales;
CONTRACT sales_contract REQUIRE Transaction_ID TYPE integer NOT NULL UNIQUE;
CONTRACT sales_contract REQUIRE Revenue TYPE numeric NOT NULL MIN 0;

CHECK CONTRACT sales_contract ON august_sales FAIL ON error;

BASELINE sales_baseline FROM cleaned_sales;
CHECK DRIFT sales_baseline ON august_sales
    CONTRACT sales_contract
    SENSITIVITY normal
    FAIL ON warning;
```

`CONTRACT ... REQUIRE` implies that the column is required. `NOT NULL` is the
readable form of `NULLABLE false`, and bare `UNIQUE` means `UNIQUE true`.

## Sensitivity presets

| Preset | PSI warning/error | Missingness warning/error |
| --- | --- | --- |
| `strict` | 0.05 / 0.15 | 1 / 2 percentage points |
| `normal` | 0.10 / 0.25 | 2 / 5 percentage points |
| `relaxed` | 0.20 / 0.35 | 5 / 10 percentage points |

Explicit `PSI_WARNING`, `PSI_ERROR`, `MISSING_WARNING`, and `MISSING_ERROR`
options override the selected preset.

## Artifact management

```adql
CONTRACT SHOW sales_contract;
CONTRACT LIST;
CONTRACT SAVE sales_contract TO "contracts/sales.json" OVERWRITE;
CONTRACT LOAD restored_contract FROM "contracts/sales.json" OVERWRITE;
CONTRACT DROP restored_contract;

BASELINE SHOW sales_baseline;
BASELINE LIST;
BASELINE SAVE sales_baseline TO "baselines/sales.json" OVERWRITE;
BASELINE LOAD restored_baseline FROM "baselines/sales.json" OVERWRITE;
BASELINE DROP restored_baseline;
```

## Compatibility

All valid ADQL 2.4 programs remain valid. The original
`SCHEMA CONTRACT ...` and `DRIFT ...` commands call the same implementations
and remain fully supported. Concise and legacy forms can be mixed safely in a
single notebook.

## Versions

- AutoDQ Python package: `0.1.23`
- ADQL language: `2.5`
- AutoDQ ADQL VS Code extension: `0.3.16`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.23
```

For manual VS Code installation, download `autodq-adql-0.3.16.vsix` from the
matching GitHub release and choose **Extensions: Install from VSIX...**.
