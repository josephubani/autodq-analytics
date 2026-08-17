# AutoDQ ADQL for Visual Studio Code

AutoDQ ADQL turns `.adql` files into executable analytics notebooks inside
Visual Studio Code. It combines a safe, SQL-like analytics language with
AutoDQ's data-quality, cleaning, visualization, modeling, and reporting
workflow.

## Features

- Comprehensive, theme-aware highlighting for ADQL commands, actions,
  clauses, options, functions, data sources, literals, operators, column names,
  aliases, comments, cell markers, and punctuation
- Named cells using `# %% [Cell title]` or `-- %% [Cell title]`
- Markdown cells using `# %% [markdown] Title`
- **Run File**, **Run through Cell**, and **Run Cell Only** actions
- A persistent notebook session that retains datasets, reviews, models, and
  charts between cells
- Direct named-dataset workflows such as `PROFILE customers`,
  `AUTO DATASET customers MODE review`, and `SELECT * FROM customers`
- Reusable dataset assignments with `LET`, including cleaned stages and
  safe `SELECT` results, with compact confirmations instead of repeated tables
- Explicit datetime parsing and numeric precision through `SET TYPE`, with
  human or `strftime` patterns, mixed/ISO modes, UTC, and decimal rounding
- Audited `MISSING` summaries, datatype-aware fills, interpolation, and
  row/column removal staged through the cleaning review
- Exact-row duplicate tables and audited `DUPLICATES DROP` retention policies
  that finalize into the reusable `CLEANED` stage
- Executable `ASSERT` quality checks and reusable named test suites with
  severity thresholds, structured results, and portable JSON definitions
- Versioned `SCHEMA CONTRACT` definitions and compact `DRIFT` baselines with
  named-dataset gates, transparent stability scoring, JSON portability, and
  workspace persistence
- A theme-aware interactive `REVIEW` panel for selecting actions, approving,
  rejecting with reasons, previewing, editing rows, inspecting audit history,
  and applying reviewed changes to `CLEANED`
- Rich session inspection with `SESSION`, `SESSION EVENTS LIMIT n`, and
  `SESSION DATASETS`
- Rich tables, quality reports, cleaning recommendations, model explanations,
  and inline charts
- Saved output restoration for text, HTML, tables, and charts after reopening
  an `.adql` notebook
- Collapsible and bounded previews for large outputs
- Rich `AUTO MODE review|clean|full` workflow summaries
- Transparent `READINESS` scorecards with component points, deductions,
  assessment coverage, and optional `REFERENCE`-dataset PSI stability

## Requirements

Install AutoDQ in the Python environment used by your project:

```bash
python -m pip install autodq
```

The extension searches upward from an `.adql` file for the nearest project
environment:

- Windows: `.venv\Scripts\autodq.exe`
- macOS and Linux: `.venv/bin/autodq`

If AutoDQ is installed elsewhere, set `autodq.commandPath` to the complete
`autodq` executable path in Visual Studio Code Settings.

## Quick start

```adql
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;

# %% [Automatic review]
AUTO MODE review VISUALIZE false CONTINUE_ON_ERROR false;

# %% [Reusable reviewed data]
LET reviewed_sales = CURRENT;

# %% [Regional totals]
LET regional_totals = SELECT Region,
                             SUM(Revenue) AS total_revenue,
                             COUNT(*) AS transactions
                      FROM CURRENT
                      WHERE Region IS NOT NULL
                      GROUP BY Region
                      ORDER BY total_revenue DESC;

# %% [Export]
EXPORT regional_totals TO "regional-totals.csv" OVERWRITE;
```

Format string dates and numeric precision in a cell before analysis:

```adql
SET TYPE Created_At datetime FORMAT "DD/MM/YYYY HH:mm:ss";
SET TYPE Api_Time datetime FORMAT ISO8601 UTC true;
SET TYPE Revenue decimal DECIMALS 2;
```

Resolve remaining missing values in a review cell:

```adql
MISSING SUMMARY;
MISSING FILL City VALUE "Not provided";
MISSING FILL ALL STRATEGY auto;
DUPLICATES SUMMARY;
DUPLICATES DROP KEEP first;
CLEANING APPLY;
MISSING SUMMARY;
LET cleaned_sales = CLEANED;
```

Create a data-quality gate in its own cell:

```adql
ASSERT SUITE ADD sales_gate Transaction_ID UNIQUE
    NAME "Transaction IDs are unique";
ASSERT SUITE ADD sales_gate Revenue MIN 0;
ASSERT SUITE ADD sales_gate MISSING_PERCENT Region <= 2
    SEVERITY warning;
ASSERT SUITE RUN sales_gate FAIL_ON warning;
```

The result appears as a notebook table. Blocking failures mark the cell as
failed, while `FAIL_ON never` records results without stopping later cells.
Use `ASSERT SUITE EXPORT ... TO "suite.json"` to keep the suite with a project.

Open the file with **AutoDQ ADQL Notebook**, then run cells from top to bottom.
The first code cell automatically initializes the dataset when required.

Inspect exactly how ML readiness is calculated and optionally compare the
active data with a registered baseline:

```adql
READINESS;
READINESS REFERENCE baseline;
READINESS DATASET cleaned_sales REFERENCE baseline;
```

The output separates sample sufficiency, data quality, feature readiness,
target readiness, leakage safety, multicollinearity, and feature stability.
Unassessed components receive no assumed credit and reduce the visible
assessment coverage.

Protect future batches with a structural contract and a distribution
baseline:

```adql
SCHEMA CONTRACT CREATE sales_v1 FROM approved_sales;
SCHEMA CONTRACT ADD sales_v1 COLUMN Revenue
    TYPE numeric REQUIRED true NULLABLE false MIN 0;
SCHEMA CONTRACT VALIDATE sales_v1 DATASET august_sales FAIL_ON error;

DRIFT BASELINE CREATE sales_baseline FROM approved_sales;
DRIFT DETECT REFERENCE sales_baseline DATASET august_sales
    CONTRACT sales_v1 FAIL_ON warning;
```

The contract and baseline remain reusable when another dataset becomes active.
Use `SCHEMA CONTRACT EXPORT|LOAD` and `DRIFT BASELINE EXPORT|LOAD` for portable
JSON artifacts, or `WORKSPACE SAVE` to persist them with the project. Neither
validation nor drift detection changes the evaluated data.

## Interactive cleaning review

Run `REVIEW;` in a notebook cell to open the interactive panel:

```adql
RECOMMEND;
DECIDE;
PREVIEW;
REVIEW;
```

Select one or more recommendations and use **Approve selected**, **Reject
selected**, or **Preview selected**. **Approve all** changes every action to
approved, while **Apply to CLEANED** executes approved actions together with
staged manual edits. The manual row editor accepts a source row index and a
JSON object such as `{"Region": "North", "Customer_Age": 36}`. Every status
change and edited cell is recorded in the existing AutoDQ audit trail.

The panel invokes the same project APIs as the equivalent `APPROVE`, `REJECT`,
`CLEANING PREVIEW`, `EDIT ROW`, and `CLEANING APPLY` statements. It does not
write back to the source CSV. If a saved notebook is reopened, the first panel
action rebuilds the in-memory workflow through the `REVIEW` cell before making
the requested change.

## Notebook sessions and output

Each open ADQL notebook receives one persistent AutoDQ session. Use
**ADQL: Restart Session** from the Command Palette when you need a completely
fresh project.

Inspect the retained project state without resetting it:

```adql
SESSION;
SESSION EVENTS LIMIT 20;
SESSION DATASETS;
```

Large results are shown as bounded previews by default: up to 25 rows or
collection items and 12,000 structured-output characters. Complete results
remain available to later statements and exports. When a preview is shortened,
select **View full output** below it to reveal the complete result in a
scrollable panel, then select **Hide full output** to collapse it again. Adjust
`autodq.notebook.maxOutputRows` and
`autodq.notebook.maxOutputCharacters` in Settings when needed.

Standalone dashboards are isolated in a sandboxed notebook frame so their
light, dark, or executive theme cannot change the surrounding VS Code notebook
colors.

Press **Save** after running cells to persist their displayed outputs. AutoDQ
stores a versioned cache at the end of the `.adql` file using comment lines,
including complete results behind expandable previews. The cache is hidden in
notebook view, ignored by the AutoDQ runtime, and restored when the notebook is
reopened. Editing a cell prevents an older non-matching cached output from
being restored for that cell. Saving very large complete outputs can increase
the `.adql` file size.

## Workspace trust

ADQL executes local workflows and can write explicitly requested reports,
models, charts, and exports. For safety, execution is disabled in untrusted and
virtual workspaces. Review an ADQL file and its output paths before running it.

## Documentation and support

- [AutoDQ documentation](https://github.com/josephubani/autodq-analytics/tree/main/docs)
- [ADQL language reference](https://github.com/josephubani/autodq-analytics/blob/main/docs/ADQL_SPEC.md)
- [Report a problem](https://github.com/josephubani/autodq-analytics/issues)

AutoDQ ADQL is released under the MIT License.
