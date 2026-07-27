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
- Rich tables, quality reports, cleaning recommendations, model explanations,
  and inline charts
- Saved output restoration for text, HTML, tables, and charts after reopening
  an `.adql` notebook
- Collapsible and bounded previews for large outputs
- Rich `AUTO MODE review|clean|full` workflow summaries

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

# %% [Regional totals]
SELECT Region,
       SUM(Revenue) AS total_revenue,
       COUNT(*) AS transactions
FROM CURRENT
WHERE Region IS NOT NULL
GROUP BY Region
ORDER BY total_revenue DESC;
```

Open the file with **AutoDQ ADQL Notebook**, then run cells from top to bottom.
The first code cell automatically initializes the dataset when required.

## Notebook sessions and output

Each open ADQL notebook receives one persistent AutoDQ session. Use
**ADQL: Restart Session** from the Command Palette when you need a completely
fresh project.

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
