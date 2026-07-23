# AutoDQ Analytics Domain Query Language (ADQL) v2

ADQL is a standalone, safe language for querying AutoDQ data and running
explicit AutoDQ workflow operations. A `.adql` file can replace a notebook for
repeatable analytics while retaining named, executable cells. ADQL does not
evaluate Python expressions or expose arbitrary object methods.

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

Restart VS Code after installation. Opening a `.adql` file then provides ADQL
syntax highlighting, named cells, Run File, Run through Cell, Run Cell Only,
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
FROM CURRENT | CLEANED | ENGINEERED | PREDICTIONS
[WHERE condition [AND condition ...]]
[GROUP BY column [, column ...]]
[ORDER BY output_column [ASC | DESC] [, ...]]
[LIMIT positive_integer]
```

Column names containing spaces can be wrapped in backticks or quotes.

```adql
SELECT `Order Date`, Revenue FROM CURRENT LIMIT 20;
```

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

Statements are case-insensitive. Option values with spaces must be quoted.

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
USE DATASET costs;
MERGE main WITH costs AS sales_with_costs ON Product HOW left;
CONCAT january,february AS q1_sales AXIS 0;
```

### Interactive cleaning and domain review

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

### BLUE diagnostics and visualization gallery

```adql
BLUE MAX_FEATURES 12 SIGNIFICANCE 0.05;
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

### Other commands

```adql
SET TARGET Revenue;
SET TYPE Date datetime;
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

## Safety and limits

- Commands and options are allowlisted.
- Python evaluation and arbitrary method calls are not supported.
- SELECT operates on a copy and never mutates project data.
- Mutating actions require an explicit workflow command.
- Existing export files require `OVERWRITE`.
- A query returns at most 1,000 rows by default.
- Explicit `LIMIT` supports at most 10,000 rows.
- Scripts support at most 100 statements and 100,000 source characters.
- Every executed run is recorded in `project.adql_history` and the session log.
