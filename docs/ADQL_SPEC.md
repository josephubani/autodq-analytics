# AutoDQ Analytics Domain Query Language (ADQL) v2 User Guide

ADQL is a standalone, safe language for querying AutoDQ data and running
explicit AutoDQ workflow operations. A `.adql` file can replace a notebook for
repeatable analytics while retaining named, executable cells. ADQL does not
evaluate Python expressions or expose arbitrary object methods.

This file is the practical command guide. The normative definition of ADQL
2.3 is the [formal language specification](adql/SPECIFICATION.md), accompanied
by its [EBNF grammar](adql/grammar.ebnf),
[execution model](adql/execution-model.md),
[data-type rules](adql/data-types.md), [error model](adql/errors.md), and
[compatibility policy](adql/compatibility.md).

## Standalone `.adql` files

A self-contained file starts by declaring its dataset. Relative paths are
resolved from the `.adql` file's own directory, not from the terminal's current
directory.

```adql
#!/usr/bin/env autodq
# %% [Dataset]
DATASET "../datasets/sample/sales.csv" TARGET Revenue;

# %% [Quality]
PROFILE;
DIAGNOSE;

# %% [Analysis]
SELECT Region, SUM(Revenue) AS total_revenue
FROM CURRENT
GROUP BY Region
ORDER BY total_revenue DESC;
```

Run the complete file from any terminal:

```bash
autodq run examples/sales_analysis.adql
```

The shorter form is equivalent:

```bash
autodq examples/sales_analysis.adql
```

On macOS and Linux, a file containing the shown shebang can also be made
executable once and run directly:

```bash
chmod +x examples/sales_analysis.adql
./examples/sales_analysis.adql
```

Use `autodq validate analysis.adql` to check the entire file without running
it, and `autodq cells analysis.adql` to list its cells.

### Notebook-style cells

Both marker styles are supported:

```adql
# %% [Named cell]
PROFILE;

-- %% [Another cell]
HEAD 10;
```

Run one cell in a fresh project initialized from the file's `DATASET`:

```bash
autodq run analysis.adql --cell 3
```

Run cells 1 through 3 in one shared project session, which is the usual
notebook behavior:

```bash
autodq run analysis.adql --through-cell 3
```

Markdown cells use a typed cell marker and contain ordinary Markdown rather
than ADQL statements:

```adql
# %% [markdown] Business context
# Regional revenue review

This analysis compares revenue and transaction volume by region.
```

### VS Code

AutoDQ includes its own VS Code extension for `.adql` files:

```bash
autodq vscode install
```

Restart VS Code after installation. Opening a `.adql` file then provides
theme-aware highlighting for commands, clauses, options, functions, literals,
operators, data sources, and user-defined column names and aliases, plus named
cells, Run File, Run through Cell, Run Cell Only,
and a notebook editor with rich cell outputs. The notebook kernel retains one
AutoDQ project per open document, so later cells reuse data, models, cleaning
decisions, and charts created by earlier cells. The first executed code cell
automatically bootstraps required preceding cells. Use **ADQL: Restart
Session** from the Command Palette to clear that state. The extension searches upward from
the `.adql` file and automatically detects the nearest `.venv/bin/autodq`.
The VS Code setting `autodq.commandPath` can override that executable when
needed.

## Python API

```python
result = project.query("""
SELECT Region, SUM(Revenue) AS total_revenue
FROM CURRENT
WHERE Revenue > 100
GROUP BY Region
ORDER BY total_revenue DESC
LIMIT 10;
""")

result.data
```

`project.adql(...)` is an alias for `project.query(...)`.

Execute a UTF-8 cell-based script against an existing project with:

```python
result = project.run_adql("analysis.adql")
```

`project.query()` returns an `ADQLRunResult`. `project.run_adql()` and
`ADQLFileRunner.run()` return an `ADQLFileResult`, with one run per cell and a
reference to the initialized project. Their most useful attributes are:

- `result.success`
- `result.cell_runs`
- `result.latest`
- `result.data` — DataFrame returned by the final statement
- `result.value` — structured object returned by the final statement
- `result.project` — the AutoDQ project created for a standalone file

## SELECT grammar

```text
SELECT [DISTINCT] expression [, expression ...]
FROM CURRENT | CLEANED | ENGINEERED | PREDICTIONS | registered_dataset
[WHERE condition [AND condition ...]]
[GROUP BY column [, column ...]]
[ORDER BY output_column [ASC | DESC] [, ...]]
[LIMIT positive_integer]
```

Column names containing spaces can be wrapped in backticks or quotes.

```adql
SELECT `Order Date`, Revenue FROM CURRENT LIMIT 20;
```

`FROM` also accepts the exact name of a dataset registered with
`ADD DATASET`. A named `SELECT` reads that dataset without changing the active
workflow dataset.

### Expressions

- Plain columns: `Region`
- Aliases: `Region AS sales_region`
- Wildcard: `*`
- Aggregates: `COUNT`, `SUM`, `AVG`, `MEAN`, `MIN`, `MAX`, `MEDIAN`, `NUNIQUE`
- Row count: `COUNT(*)`

All non-aggregate columns must appear in `GROUP BY` when an aggregate is used.
`ORDER BY` refers to the output name, including aliases.

### Conditions

ADQL v2 supports conditions joined with `AND`:

- `=`, `!=`, `<`, `<=`, `>`, `>=`
- `IN (...)`, `NOT IN (...)`
- `IS NULL`, `IS NOT NULL`
- `CONTAINS`, `STARTS WITH`, `ENDS WITH`

Use quoted strings, numeric values, booleans, or `NULL` literals.

```adql
SELECT Region, Revenue
FROM CURRENT
WHERE Region IN ("North", "South")
  AND Revenue >= 500
ORDER BY Revenue DESC
LIMIT 25;
```

`OR` is intentionally not available in v2. Use `IN (...)` or separate queries.

## Workflow commands

ADQL's own language words are case-insensitive: commands, actions, clauses,
options, operators, types, booleans, and built-in enum values may use upper,
lower, or mixed case. Dataset names, column names, aliases, paths, chart
titles, and quoted strings retain their exact spelling. Option values with
spaces must be quoted.

These statements are equivalent:

```adql
VISUALIZE BAR X Region Y Revenue THEME DARK;
visualize bar x Region y Revenue theme dark;
vIsUaLiZe BaR x Region y Revenue tHeMe DaRk;
```

```adql
LOAD;
PROFILE;
STATISTICS;
INTERPRET;
DIAGNOSE;
RECOMMEND;
DECIDE;
PREVIEW;
REVIEW;
APPROVE ALL;
APPROVE 1,2;
REJECT 3 REASON "Requires domain review";
CLEAN;
VALIDATE;
```

### Automatic workflow

```adql
AUTO MODE review VISUALIZE false;
AUTO MODE clean;
AUTO MODE full
    APPLY_FEATURES true
    ALGORITHM decision_tree_regressor
    REPORT "reports/automatic.html"
    CONTINUE_ON_ERROR true;
```

`AUTO` calls `project.auto()` through the same allowlisted execution layer as
other ADQL statements. Its result is retained in project state and appears in
VS Code as a collapsible workflow summary containing stage statuses, timing,
failures, and next actions.

| Option | Value | Purpose |
| --- | --- | --- |
| `MODE` | `review`, `clean`, `full` | Select the safe workflow preset. |
| `VISUALIZE` | Boolean | Generate recommended visualizations. |
| `APPROVE_ALL` | Boolean | Override automatic approval behavior. |
| `APPLY_CLEANING` | Boolean | Apply approved cleaning actions. |
| `APPLY_FEATURES` | Boolean | Apply recommended feature engineering. |
| `TRAIN_MODEL` | Boolean | Train a model when a target is available. |
| `PREDICT` | Boolean | Generate model predictions. |
| `EXPLAIN` | Boolean | Generate model explanations. |
| `ALGORITHM` | Name | Choose `auto` or a supported model algorithm. |
| `TEST_SIZE` | Number | Set the evaluation fraction between 0 and 1. |
| `RANDOM_STATE` | Integer | Make supported operations reproducible. |
| `REPORT` / `REPORT_OUTPUT` | `.html` or `.json` path | Export the automatic report relative to the `.adql` file. |
| `REPORT_STYLE` | Name | Select the report presentation style. |
| `SAVE_WORKSPACE` | Boolean | Persist an attached workspace after the run. |
| `REFRESH` | Boolean | Recompute stages instead of reusing project state. |
| `CONTINUE_ON_ERROR` | Boolean | Continue after a failed automatic stage. |
| `RAISE_ON_ERROR` | Boolean | Raise immediately with the partial automatic result. |

`review` is the default and does not alter the dataset. `clean` approves and
applies executable cleaning actions. `full` also enables modeling, prediction,
and explainability. Use `CONTINUE_ON_ERROR true` for exploratory notebooks
where later independent stages should still run.

### Visualization

```adql
VISUALIZE bar X Region Y Revenue
    TITLE "Revenue by Region"
    X_LABEL "Sales region"
    Y_LABEL "Revenue (CAD)"
    THEME dark;
```

The `VISUALIZE` options map to `project.visualize()`, including `COLUMN`,
`STAGE`, `SUBTITLE`, `COLOR`, `PALETTE`, `FIGSIZE`, `DPI`, `GRID`, `LEGEND`,
`SAVE`, and `FORMAT`.

### Modeling and prediction uncertainty

```adql
MODEL TARGET Revenue USING decision_tree_regressor
    USE_ENGINEERED false TEST_SIZE 0.2;

PREDICT CONFIDENCE 0.95 UNCERTAINTY true;

EXPLAIN MAX_ROWS 20 USE_ENGINEERED true;
SHAP CHART summary;
SHAP CHART waterfall ROW 0 SAVE "charts/row-0-shap.png";

MODEL SAVE TO "models/revenue-model" OVERWRITE;
MODEL LOAD FROM "models/revenue-model";
```

### Workspaces and multiple datasets

```adql
WORKSPACE CREATE sales_review ROOT ".autodq/workspaces";
WORKSPACE SAVE INCLUDE_MODEL true;
WORKSPACE INFO;
WORKSPACE LIST ROOT ".autodq/workspaces";

ADD DATASET costs FROM "costs.csv";
LIST DATASETS;
PROFILE costs;
DIAGNOSE costs;
AUTO DATASET costs MODE review VISUALIZE false;
VISUALIZE DATASET costs bar X Category Y Amount;
SELECT Category, SUM(Amount) AS total_amount FROM costs GROUP BY Category;
EXPORT costs TO "exports/costs.csv" OVERWRITE;
USE DATASET costs;
MERGE main WITH costs AS sales_with_costs ON Product HOW left;
CONCAT january,february AS q1_sales AXIS 0;
```

Named dataset targeting is available across stateful workflow commands:

- Commands that otherwise accept no arguments support the concise form
  `PROFILE costs`, `DIAGNOSE costs`, `RECOMMEND costs`, `READINESS costs`, and
  similar calls.
- Every dataset-scoped command supports the universal leading selector
  `COMMAND DATASET name ...`. For example,
  `AUTO DATASET costs MODE review`, `HEAD DATASET costs 10`,
  `DOMAIN DATASET costs ADD Amount MIN 0`, and
  `REPORT DATASET costs TO "costs-report.html"`.
- Targeting a dataset activates it before the command runs. Later commands
  without a selector continue using that dataset. Repeating the same dataset
  selector preserves profile, diagnosis, cleaning, feature, and model state.
- `SELECT ... FROM name` and `EXPORT name TO ...` access a registered dataset
  directly without changing the active workflow dataset.

Dataset names are user-defined identifiers and are matched exactly. An unknown
name reports all currently registered datasets. `USE DATASET name` remains
available when you only want to change the active dataset without running
another operation.

### Reusable dataset assignments with LET

`LET` registers an in-memory dataset snapshot in the current project. The
assigned name works anywhere a registered dataset name is accepted, including
`SELECT`, `EXPORT`, `USE DATASET`, concise workflow targeting, `LIST DATASETS`,
and `SESSION DATASETS`.

Successful assignments display a compact confirmation instead of previewing
the assigned rows. The confirmation reports the dataset name, source, row and
column counts, and whether an existing snapshot was overwritten. Query the
name explicitly with `SELECT` or `HEAD` when you want to inspect its contents.

Assign the active project stage:

```adql
CLEAN customers;
LET cleaned_customers = CLEANED;
EXPORT cleaned_customers TO "exports/cleaned-customers.csv" OVERWRITE;
```

Copy a registered dataset without activating it:

```adql
LET customer_snapshot = DATASET customers;
SELECT * FROM customer_snapshot LIMIT 25;
```

Assign a safe SQL-like query result:

```adql
LET regional_sales = SELECT Region,
                            SUM(Revenue) AS total_revenue,
                            COUNT(*) AS transactions
                     FROM CURRENT
                     WHERE Region IS NOT NULL
                     GROUP BY Region;

EXPORT regional_sales TO "exports/regional-sales.xlsx";
PROFILE regional_sales;
```

Use `OVERWRITE` to replace an existing non-active assignment:

```adql
LET regional_sales = SELECT Region, SUM(Revenue) AS total_revenue
                     FROM CURRENT GROUP BY Region OVERWRITE;
```

Assignment names use identifier syntax: letters or `_` first, followed by
letters, numbers, or `_`. Built-in stage names are reserved. `LET` never
silently replaces an existing name and does not allow overwriting the active
dataset. It stores a snapshot, so later changes to the source do not mutate the
assigned data. A `SELECT` assignment uses the same default 1,000-row safety
limit as an ordinary query; add an explicit `LIMIT` when a different bounded
size is required. Stage assignments retain the complete available stage.

`LET` assigns tabular data only. It does not evaluate Python, create scalar
variables, or interpolate arbitrary values into later statements.

### Explicit missing-value handling

`MISSING` provides deliberate, audited control when automatic recommendations
leave missing cells for domain review. Start with a column summary:

```adql
MISSING SUMMARY;
```

The result shows each column's dtype, missing count and percentage, non-missing
count, and a datatype-aware recommended strategy.

Fill one or more columns:

```adql
MISSING FILL City VALUE "Not provided";
MISSING FILL Customer_Age STRATEGY median;
MISSING FILL COLUMNS Revenue,Profit STRATEGY mean;
MISSING FILL Revenue STRATEGY interpolate;
MISSING FILL Region STRATEGY ffill;
MISSING FILL ALL STRATEGY auto;
```

Supported strategies are:

| Strategy | Behavior |
| --- | --- |
| `auto` | Uses median for numeric columns and mode for other datatypes. |
| `constant` / `VALUE` | Uses an explicit non-null value, with safe type coercion. |
| `mean`, `median` | Fills numeric columns from their observed distribution. |
| `mode` | Uses the most frequent non-missing value. |
| `zero` | Fills numeric columns with zero. |
| `ffill`, `bfill` | Carries the previous or next observed value. |
| `interpolate` | Interpolates numeric values in both directions. |

`VALUE` automatically selects the `constant` strategy. An all-null column has
no mean, median, or mode, so the result reports
`no_replacement_available`; use an explicit `VALUE`, or remove the column.

Remove incomplete rows or columns when filling would be misleading:

```adql
MISSING DROP ROWS;
MISSING DROP ROWS COLUMNS City,Region HOW any;
MISSING DROP ROWS COLUMNS Phone,Email HOW all;
MISSING DROP COLUMNS Notes,Unused;
MISSING DROP COLUMNS COLUMNS Legacy_Code,Import_Comment;
MISSING DROP COLUMNS MIN_PERCENT 50;
```

`HOW any` removes a row when any selected column is missing; `HOW all` requires
all selected columns to be missing. `MIN_PERCENT` is inclusive and accepts a
value from 0 through 100. AutoDQ refuses to remove every column or the active
model target.

All fills and removals are first staged in `review.working_data`. Every changed
cell, removed row, and removed column receives an audit entry. Finalize the
review and export the complete audit with:

```adql
CLEANING APPLY;
MISSING SUMMARY;
LET complete_sales = CLEANED;
EXPORT complete_sales TO "exports/complete-sales.csv" OVERWRITE;
AUDIT EXPORT TO "reports/missing-value-audit.json";
```

Like other stateful commands, `MISSING` accepts a named dataset selector:

```adql
MISSING DATASET customers SUMMARY;
MISSING DATASET customers FILL City VALUE "Not provided";
CLEANING DATASET customers APPLY;
```

### Exact duplicate inspection and removal

`DUPLICATES SUMMARY` displays the complete rows involved in exact matches
across all columns. Unlike a simple duplicate count, the result contains every
member of each group, including the occurrence that would normally be kept:

```adql
DUPLICATES SUMMARY;
```

The output adds `duplicate_group`, `occurrences`, and `source_index` metadata
before the original dataset columns. Large results use the notebook's bounded
preview and **View full output** control.

Stage an audited removal with an explicit retention policy:

```adql
DUPLICATES DROP KEEP first REASON "Repeated import";
DUPLICATES DROP KEEP last;
DUPLICATES DROP KEEP none;
```

`KEEP first` is the default and retains the first row in each group. `KEEP
last` retains the final row. `KEEP none` removes every member of every duplicate
group. Each removed row receives an `exact_duplicate_row_removed` audit entry.
The operation changes `review.working_data`; finalize and retain it with:

```adql
DUPLICATES SUMMARY;
DUPLICATES DROP KEEP first;
DUPLICATES SUMMARY;
CLEANING APPLY;
LET unique_sales = CLEANED;
EXPORT unique_sales TO "exports/unique-sales.csv" OVERWRITE;
```

Named-dataset targeting is supported:

```adql
DUPLICATES DATASET customers SUMMARY;
DUPLICATES DATASET customers DROP KEEP first;
CLEANING DATASET customers APPLY;
LET unique_customers = CLEANED;
```

### Data-quality assertions and test suites

`ASSERT` turns data expectations into executable checks without changing the
dataset. Direct checks return a table containing the observed value, expected
value, status, severity, failing-row count, and explanation:

```adql
ASSERT Revenue EXISTS;
ASSERT Revenue NOT NULL;
ASSERT Revenue TYPE numeric;
ASSERT Revenue BETWEEN 0 AND 1000000;
ASSERT Transaction_ID UNIQUE;
ASSERT Region ALLOWED North,South,East,West,Central;
ASSERT Email MATCHES "[^@]+@[^@]+" SEVERITY warning;

ASSERT ROW_COUNT > 0;
ASSERT COLUMN_COUNT >= 10;
ASSERT MISSING_PERCENT <= 5;
ASSERT MISSING_COUNT Region = 0;
ASSERT DUPLICATE_ROWS = 0;
ASSERT DISTINCT_COUNT Region >= 4;
ASSERT QUALITY_SCORE >= 90;
```

Severity is `error`, `warning`, or `info`. By default only failed `error`
checks fail the ADQL statement. Use `FAIL_ON warning`, `FAIL_ON info`, or
`FAIL_ON never` to choose the gate threshold. A blocking failure stops normal
execution, returns a structured failed result, and works with the host's
continue-on-error mode.

Group checks into a reusable suite when the same contract should run before
cleaning, modeling, export, or release:

```adql
ASSERT SUITE ADD sales_gate Transaction_ID UNIQUE
    NAME "Transaction IDs are unique";
ASSERT SUITE ADD sales_gate Revenue MIN 0
    NAME "Revenue is non-negative";
ASSERT SUITE ADD sales_gate MISSING_PERCENT Region <= 2
    SEVERITY warning NAME "Region completeness";

ASSERT SUITE SHOW sales_gate;
ASSERT SUITE RUN sales_gate FAIL_ON warning;
ASSERT SUITE LIST;
ASSERT SUITE EXPORT sales_gate TO "tests/sales-gate.json" OVERWRITE;
ASSERT SUITE LOAD restored_gate FROM "tests/sales-gate.json" OVERWRITE;
ASSERT SUITE DROP restored_gate;
```

Suites are available throughout the current project session and remain intact
when the active dataset changes. Export suite JSON to keep a contract with the
project or share it with another machine. Every form supports explicit named
dataset targeting, for example `ASSERT DATASET customers SUITE RUN customer_gate;`.

### Schema contracts and drift detection

`ASSERT` is ideal for individual data-quality tests. A schema contract is the
reusable structural agreement for an entire dataset: required columns, types,
nullability, uniqueness, bounds, allowed values, and patterns. `DRIFT` then
compares a new batch with a compact approved baseline to detect changes that
may still satisfy the schema.

```adql
SCHEMA CONTRACT CREATE sales_v1 FROM cleaned_sales
    VERSION 1.0.0
    EXTRA_COLUMNS warning
    INFER_RANGES false
    INFER_CATEGORIES true
    OVERWRITE;

SCHEMA CONTRACT ADD sales_v1 COLUMN Transaction_ID
    TYPE integer REQUIRED true NULLABLE false UNIQUE true
    SEVERITY error;
SCHEMA CONTRACT ADD sales_v1 COLUMN Revenue
    TYPE numeric REQUIRED true NULLABLE false MIN 0
    SEVERITY error;
SCHEMA CONTRACT ADD sales_v1 COLUMN Region
    TYPE string ALLOWED "North,South,East,West,Central"
    SEVERITY warning;

SCHEMA CONTRACT VALIDATE sales_v1 DATASET august_sales FAIL_ON error;
SCHEMA CONTRACT SHOW sales_v1;
SCHEMA CONTRACT LIST;
SCHEMA CONTRACT EXPORT sales_v1 TO "contracts/sales-v1.json" OVERWRITE;
SCHEMA CONTRACT LOAD restored_sales FROM "contracts/sales-v1.json" OVERWRITE;
SCHEMA CONTRACT DROP restored_sales;
```

`EXTRA_COLUMNS` accepts `ignore`, `info`, `warning`, or `error`. Contract
validation is read-only. `FAIL_ON error` blocks failed error rules;
`FAIL_ON warning` also blocks warning rules; `FAIL_ON never` only records the
report.

Create the drift baseline from a representative, approved dataset—not from a
known-bad batch:

```adql
DRIFT BASELINE CREATE sales_baseline FROM july_sales OVERWRITE;
DRIFT BASELINE SHOW sales_baseline;
DRIFT BASELINE LIST;
DRIFT BASELINE EXPORT sales_baseline TO "baselines/sales.json" OVERWRITE;
DRIFT BASELINE LOAD restored_base FROM "baselines/sales.json" OVERWRITE;

DRIFT DETECT REFERENCE sales_baseline DATASET august_sales
    CONTRACT sales_v1
    FAIL_ON warning
    PSI_WARNING 0.10 PSI_ERROR 0.25
    MISSING_WARNING 2 MISSING_ERROR 5;

DRIFT BASELINE DROP restored_base;
```

The baseline contains schema metadata, quantile buckets, bounded category
frequencies, missingness, distinct ratios, duplicate rate, and row count; it
does not contain the original rows. The report classifies checks as `stable`,
`moderate`, or `major`. Its visible score is `(stable + 0.5 × moderate) / all
checks × 100`. A `CONTRACT` clause includes contract failures in the same gate.

Contracts and baselines remain available when the active dataset changes and
are persisted by `WORKSPACE SAVE`. The latest validation and drift reports are
dataset-derived artifacts and reset when another dataset is activated.

### Interactive cleaning and domain review

In the AutoDQ ADQL VS Code notebook, `REVIEW` renders a UI for selecting,
approving, rejecting, and previewing actions; staging audited row edits; and
applying the result to `CLEANED`. Each control invokes the same operation as
the statements below. Other hosts retain the static review representation, so
the language semantics do not depend on the UI.

```adql
KNOWLEDGE;
REVIEW;
APPROVE 1,2;
REJECT 3 REASON "Business owner rejected this action";
CLEANING PREVIEW ACTIONS 1,2 MAX_ROWS 5;

EDIT ROW 17 CHANGES '{"Region": "East", "Revenue": 1250}'
    REASON "Corrected from source system";
DOMAIN ADD Revenue MIN 0 NULLABLE false;
DOMAIN ADD Region ALLOWED "North,South,East,West";
DOMAIN VALIDATE;
OUTLIERS REVIEW COLUMNS Revenue,Profit IQR 1.5;
OUTLIERS TREAT COLUMN Revenue STRATEGY clip REASON "Reviewed IQR cap";
CLEANING APPLY;
AUDIT EXPORT TO "reports/cleaning-audit.json";
```

### Feature engineering and analytical intelligence

```adql
CORRELATION MIN_ABS 0.3;
READINESS;
FEATURES;
FEATURE APPLY;
FEATURE CREATE Margin METHOD difference COLUMNS Revenue,Cost;
FEATURE CREATE LogRevenue METHOD log COLUMN Revenue;
FEATURE CREATE RevenueBand METHOD bin COLUMN Revenue
    BINS "0,1000,5000,10000" LABELS "Low,Medium,High";
```

`READINESS` returns a transparent weighted scorecard rather than only a final
number. Its seven components are sample sufficiency (10 points), data quality
(25), feature readiness (15), target readiness (15), leakage safety (15),
multicollinearity (10), and feature stability (10). Every component shows its
points, status, observed metrics, deductions, and recommendation.

Without a baseline, feature stability is clearly marked **not assessed** and
is excluded from the score denominator. Register a representative earlier or
production dataset to add PSI-based distribution stability:

```adql
ADD DATASET baseline FROM "../datasets/baseline-sales.csv";
READINESS REFERENCE baseline;

-- Score a named cleaned snapshot without first making the baseline active.
READINESS DATASET clean12 REFERENCE baseline;
```

The score formula is `earned points / assessed points * 100`, and assessment
coverage shows how much of the 100-point model was actually measured. PSI is
interpreted as stable at `<= 0.10`, moderate shift at `<= 0.25`, and unstable
above `0.25`.

### BLUE diagnostics and visualization gallery

```adql
BLUE SOURCE data MAX_FEATURES 12 SIGNIFICANCE 0.05;
BLUE VISUALIZE APPEND true;
BLUE INTERPRET;
BLUE PRESCRIBE;

GALLERY LIST;
GALLERY GET bar_Region_by_Revenue_current;
GALLERY CUSTOMIZE bar_Region_by_Revenue_current
    TITLE "Regional revenue" THEME journal DPI 300;
GALLERY SAVE TO "charts" FORMAT png;
GALLERY REMOVE bar_Region_by_Revenue_current;
GALLERY CLEAR;
```

`BLUE SOURCE` accepts `data` for dataframe diagnostics or `trained_model` for
diagnostics based on an already-trained compatible linear model.

### Dashboard and report export

```adql
DASHBOARD TITLE "Sales Analytics"
    THEME executive
    SAVE "reports/sales-dashboard.html"
    OVERWRITE;

REPORT TO "reports/autodq-report.json" OVERWRITE;
```

### Dataset export

```adql
EXPORT CURRENT TO "exports/current.csv" OVERWRITE;
EXPORT CLEANED TO "exports/cleaned.xlsx";
EXPORT ENGINEERED TO "exports/features.csv";
EXPORT PREDICTIONS TO "exports/predictions.csv";
```

Existing files are never replaced unless `OVERWRITE` is explicitly included.

### Datatype conversion and formatting

Use `SET TYPE` to convert a column in the active or explicitly selected
dataset. Existing two-argument conversions remain valid:

```adql
SET TYPE Customer_Age int;
SET TYPE Region category;
SET TYPE Revenue float;
SET TYPE Created_At datetime;
```

For datetime strings, `FORMAT` may be a familiar pattern, a Python `strftime`
pattern, or a named parsing mode:

```adql
SET TYPE Created_At datetime FORMAT "DD/MM/YYYY HH:mm:ss";
SET TYPE Created_At datetime FORMAT "%d/%m/%Y %H:%M:%S";
SET TYPE Api_Timestamp datetime FORMAT ISO8601 UTC true;
SET TYPE Imported_At datetime FORMAT MIXED DAYFIRST true;
SET TYPE Fiscal_Date datetime FORMAT AUTO YEARFIRST true;
```

Supported human-readable tokens are:

| Token | Meaning | Example |
| --- | --- | --- |
| `YYYY`, `YY` | Four- or two-digit year | `2026`, `26` |
| `MMMM`, `MMM`, `MM`, `M` | Full, abbreviated, or numeric month | `July`, `Jul`, `07` |
| `DD`, `D` | Day of month | `29` |
| `HH`, `hh` | 24-hour or 12-hour clock | `14`, `02` |
| `mm`, `ss`, `SSS` | Minute, second, fractional second | `35`, `20`, `125` |
| `A`, `Z` | AM/PM marker or numeric timezone | `PM`, `-0400` |

Pattern tokens are case-sensitive because `MM` means month while `mm` means
minute. Literal separators and text remain unchanged.

`AUTO` uses pandas inference, `MIXED` permits different formats row by row,
and `ISO8601` accepts ISO-8601 date/time variants. `DAYFIRST` and `YEARFIRST`
are valid with `AUTO` or `MIXED`; an explicit pattern already defines the
order. `UTC true` returns timezone-aware UTC values. Invalid non-empty values
are coerced to missing datetime values and counted in the command output and
session event.

Use `DECIMALS` to round numeric values during conversion:

```adql
SET TYPE Revenue float DECIMALS 2;
SET TYPE Margin numeric DECIMALS 4;
SET TYPE Tax decimal DECIMALS 2;
SET TYPE Units int DECIMALS 0;
```

Precision must be between 0 and 15 for floating-point types. `decimal` is a
numeric conversion alias backed by pandas floating-point storage; `DECIMALS`
rounds stored values but does not convert them to display strings. This keeps
the column usable by `SELECT`, modeling, visualization, and numeric exports.
The same operation can target a registered dataset directly:

```adql
SET DATASET customers TYPE Created_At datetime
    FORMAT "YYYY-MM-DD HH:mm:ss";
```

### Session inspection

Use read-only session commands to see the project state retained by the current
ADQL notebook or file execution:

```adql
SESSION;
SESSION EVENTS;
SESSION EVENTS LIMIT 20;
SESSION DATASETS;
```

`SESSION` returns the active dataset, target, dimensions, workspace, session
start time, event and ADQL run counts, registered datasets, completed steps,
and the availability of profile, cleaning, feature, model, prediction,
explanation, visualization, and dashboard artifacts. `SESSION EVENTS` returns
the newest workflow events first. `SESSION DATASETS` marks the active dataset
and includes each registered dataset's dimensions and source path.

These commands do not change project state. The current `SESSION` statement is
recorded only after its output is created, so it appears in a later event or
history query.

### Other commands

```adql
SET TARGET Revenue;
SET TYPE Date datetime FORMAT "YYYY-MM-DD";
SET TYPE Revenue decimal DECIMALS 2;
USE DATASET main;
HEAD 10;
TAIL 10;
SAMPLE 10 RANDOM_STATE 42;
HELP;
HELP MODEL;
HISTORY LIMIT 10;
```

## Scripts and comments

Statements are separated with semicolons. `--` and `#` start line comments
outside quoted values.

```adql
-- Prepare analysis
PROFILE;
DIAGNOSE;

# Return a compact regional summary
SELECT Region, COUNT(*) AS transactions
FROM CURRENT
GROUP BY Region
ORDER BY transactions DESC;
```

Use `continue_on_error=True` to execute later statements after a runtime error:

```python
result = project.query(script, continue_on_error=True)
```

## Saved notebook outputs

The AutoDQ VS Code extension can persist displayed notebook output in a
versioned cache at the end of an `.adql` file. Every cache line is an ADQL
comment between reserved `autodq-output-cache` markers. The notebook view
hides this block, while the CLI parser ignores it during validation and
execution.

The cache stores only the bounded output shown in VS Code, including text,
HTML, tables, and images. It does not replace exports or runtime project
state. Cached output is restored only when its cell fingerprint still matches
the saved cell source.

## Safety and limits

- Commands and options are allowlisted.
- Python evaluation and arbitrary method calls are not supported.
- SELECT operates on a copy and never mutates project data.
- Mutating actions require an explicit workflow command.
- Existing export files require `OVERWRITE`.
- A query returns at most 1,000 rows by default.
- Explicit `LIMIT` supports at most 10,000 rows.
- Scripts have no statement-count limit. Source text remains limited to
  100,000 characters.
- Every executed run is recorded in `project.adql_history` and the session log.
