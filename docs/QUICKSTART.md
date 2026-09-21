# AutoDQ Quickstart

This guide takes a new user from installation to a reviewed data-quality
workflow, a reusable chart, and an executable ADQL notebook.

## Install and verify

Create a virtual environment, install the public package, and confirm the
command-line entry point:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install autodq
autodq --version
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. If the
`autodq` command is not on your shell path, use `python -m autodq` in its place.

## Run a safe Python review

```python
from autodq import AutoDQ

project = AutoDQ("sales.csv", target="Revenue")

result = project.auto(
    mode="review",
    visualize=False,
    auto_display=False,
)

print(result.success)
print(result.next_actions)
review = project.state.cleaning_review
```

`review` mode profiles and diagnoses the dataset and prepares cleaning actions,
but does not modify the data. Inspect the actions before approving them:

```python
for action in review.actions:
    print(action.action_id, action.status, action.action)

project.approve(1)
project.reject(2, reason="Requires a business-owner decision")
project.cleaning_preview(max_rows=10)
```

To approve every executable recommendation and apply it, use the deliberate
cleaning workflow:

```python
clean_result = project.auto(
    mode="clean",
    visualize=False,
    auto_display=False,
)

validation = project.state.validation_report
```

## Create and export a chart

```python
chart = project.visualize(
    chart="bar",
    x="Region",
    y="Revenue",
    stage="cleaned",
    title="Revenue by Region",
    subtitle="Average revenue after approved cleaning",
    x_label="Region",
    y_label="Average revenue",
    theme="journal",
    dpi=200,
)

chart.show()
chart.save("reports/revenue-by-region.png")
```

## Run the same idea as an ADQL notebook

Create `sales_review.adql` next to `sales.csv`:

```adql
# %% [Dataset]
DATASET 'sales.csv' TARGET Revenue;

# %% [Automatic review]
AUTO MODE review VISUALIZE false CONTINUE ON ERROR false;

# %% [Session state]
SESSION;

# %% [Regional summary]
SELECT Region,
       SUM(Revenue) AS "Total Revenue",
       COUNT(*) AS transactions
FROM CURRENT
WHERE Region IS NOT NULL
GROUP BY Region
ORDER BY "Total Revenue" DESC;
```

## Save and reuse a result with LET

`LET` turns a stage or query result into a named dataset for later cells:

`LET` prints only a compact assignment confirmation. It does not repeat the
assigned table; use `HEAD "Regional Summary" 10` or a bounded `SELECT` when you
want to inspect the saved snapshot.

```adql
# %% [Reusable regional result]
LET "Regional Summary" = SELECT Region,
                              SUM(Revenue) AS "Total Revenue"
                       FROM CURRENT
                       WHERE Region IS NOT NULL
                       GROUP BY Region;

# %% [Export the assigned result]
EXPORT "Regional Summary" TO 'regional-summary.csv' OVERWRITE;
```

After cleaning, the same pattern captures the complete cleaned stage:

```adql
LET "Cleaned Sales" = CLEANED;
EXPORT "Cleaned Sales" TO 'cleaned-sales.csv' OVERWRITE;
```

## Resolve remaining missing values

Automatic cleaning may intentionally leave domain-sensitive values for review.
Use `MISSING SUMMARY` to see what remains, then choose a fill or removal policy:

```adql
# %% [Missing-value review]
MISSING SUMMARY;
MISSING FILL City VALUE 'Not provided';
MISSING FILL "Customer Age" STRATEGY median;
MISSING FILL ALL STRATEGY auto;

# %% [Finalize and retain]
CLEANING APPLY;
MISSING SUMMARY;
LET "Complete Sales" = CLEANED;
EXPORT "Complete Sales" TO 'complete-sales.csv' OVERWRITE;
AUDIT EXPORT TO 'missing-value-audit.json';
```

Use `MISSING DROP ROWS COLUMNS City HOW any` when complete cases are required,
or `MISSING DROP COLUMNS MIN PERCENT 50` when a highly incomplete field is not
analytically useful.

## Inspect and remove exact duplicate rows

Show the actual rows before deciding whether repeated records are invalid:

```adql
# %% [Exact duplicate review]
DUPLICATES SUMMARY;
```

The table contains every member of every exact-duplicate group, with its
original row index, group number, and occurrence count. Stage a removal policy,
finalize it into `CLEANED`, and preserve the result with `LET`:

```adql
DUPLICATES DROP KEEP first REASON 'Repeated source-system import';
DUPLICATES SUMMARY;
CLEANING APPLY;

LET "Unique Sales" = CLEANED;
EXPORT "Unique Sales" TO 'unique-sales.csv' OVERWRITE;
AUDIT EXPORT TO 'duplicate-removal-audit.json';
```

Use `KEEP last` when the final occurrence is authoritative. `KEEP none`
removes every member of each duplicate group and should only be used when no
copy should remain. Named datasets are supported with
`DUPLICATES DATASET customers SUMMARY`.

## Convert dates and control numeric precision

Convert a string datetime column before profiling or modeling:

```adql
SET TYPE "Created At" datetime FORMAT 'DD/MM/YYYY HH:mm:ss';
SET TYPE Revenue decimal DECIMALS 2;

PROFILE;
LET "Typed Sales" = CURRENT;
EXPORT "Typed Sales" TO 'typed-sales.csv' OVERWRITE;
```

For a column containing several date styles, use mixed parsing. Add `UTC true`
when all results should be normalized to UTC:

```adql
SET TYPE "Imported At" datetime FORMAT MIXED DAYFIRST true UTC true;
```

Validate and run it:

```bash
autodq validate sales_review.adql
autodq run sales_review.adql
```

Install the bundled VS Code support for rich, cell-by-cell output:

```bash
autodq vscode install
```

Restart VS Code and open the `.adql` file with the ADQL notebook editor.

## Protect later data with a contract and baseline

After cleaning and approving a representative dataset, preserve it and create
two reusable safeguards:

```adql
LET approved_sales = CLEANED;

CONTRACT sales_v1 FROM "Approved Sales";
CONTRACT sales_v1 REQUIRE "Transaction ID" TYPE integer NOT NULL;
CONTRACT sales_v1 REQUIRE Revenue TYPE numeric NOT NULL MIN 0;

BASELINE sales_baseline FROM "Approved Sales";
```

When a later batch is registered, validate its structure and compare its
distributions without changing it:

```adql
CHECK CONTRACT sales_v1 ON "August Sales" FAIL ON error;
CHECK DRIFT sales_baseline ON "August Sales"
    CONTRACT sales_v1 SENSITIVITY normal FAIL ON warning;
```

Export the JSON definitions when they should travel independently of a saved
workspace:

```adql
CONTRACT SAVE sales_v1 TO 'contracts/sales-v1.json' OVERWRITE;
BASELINE SAVE sales_baseline TO 'baselines/sales.json' OVERWRITE;
```

## Turn operational evidence into governed actions

After running `OPERATIONS` or `INVENTORY`, create a prescriptive plan and
compare a non-mutating scenario:

```adql
OPERATIONS DURATION "Delivery Days" STATUS Returned
    GROUP BY Region,"Sales Channel" SLA 5;

PRESCRIBE OBJECTIVE reduce_delay SOURCE operations
    MAX ACTIONS 5 MIN CONFIDENCE 0.60 MAX RISK medium;

SCENARIO NAME 'Faster delivery'
    DURATION CHANGE -20 FAILURE CHANGE -10 COST CHANGE 5;

OPTIMIZE OBJECTIVE reduce_delay MAX ACTIONS 3;
ACTION LIST STATUS selected;
```

Approve, reject, and record implementation explicitly. Recorded execution is
audit-only and does not call an external system:

```adql
ACTION APPROVE A001 ACTOR 'operations lead';
ACTION EXECUTE A001 ACTOR 'operations lead';
ACTION AUDIT TO 'reports/action-audit.json' OVERWRITE;
```

## Continue from here

- [Python API reference](API_REFERENCE.md)
- [ADQL language reference](ADQL_SPEC.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Automatic sales workflow](../examples/sales_auto.adql)
