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
DATASET "sales.csv" TARGET Revenue;

# %% [Automatic review]
AUTO MODE review VISUALIZE false CONTINUE_ON_ERROR false;

# %% [Regional summary]
SELECT Region,
       SUM(Revenue) AS total_revenue,
       COUNT(*) AS transactions
FROM CURRENT
WHERE Region IS NOT NULL
GROUP BY Region
ORDER BY total_revenue DESC;
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

## Continue from here

- [Python API reference](API_REFERENCE.md)
- [ADQL language reference](ADQL_SPEC.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Complete sales workflow](../examples/sales_analysis.adql)
