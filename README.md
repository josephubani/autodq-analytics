# AutoDQ Analytics

AutoDQ is an end-to-end analytics workflow framework for tabular data. It
profiles datasets, diagnoses quality problems, recommends and reviews cleaning
actions, engineers features, trains explainable models, generates
visualizations and dashboards, and runs complete workflows from Python,
Jupyter, the command line, or standalone `.adql` notebooks.

## Highlights

- CSV, XLSX, and XLS dataset loading
- Dataset profiling, semantic inference, and quality scoring
- Missing-value, duplicate, outlier, datatype, and leakage diagnosis
- Knowledge-aware cleaning recommendations and approval workflows
- Manual row editing, domain validation, outlier treatment, and audit trails
- Descriptive statistics, distribution analysis, and correlations
- Feature engineering and ML-readiness analysis
- Regression and classification with prediction uncertainty
- SHAP explanations and publication-ready SHAP plots
- BLUE regression diagnostics, visual interpretation, and prescriptions
- Reusable visualization objects, galleries, HTML reports, and dashboards
- Multi-workspace project isolation and model persistence
- `project.auto()` for an automated workflow
- ADQL files with executable notebook cells and rich VS Code output

## Requirements

- Python 3.10 or newer
- macOS, Linux, or Windows

## Installation

Install the released package from PyPI:

```bash
python -m pip install autodq
```

Until the first PyPI release, install directly from the project source:

```bash
git clone https://github.com/josephubani/autodq-analytics.git
cd autodq-analytics
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

For editable development and release tools:

```bash
python -m pip install -e ".[dev]"
```

## Python quick start

```python
from autodq import AutoDQ

project = AutoDQ("datasets/sample/sales.csv", target="Revenue")

profile = project.profile()
diagnosis = project.diagnose()
recommendations = project.recommend()
review = project.review_cleaning()

review.approve_all()
project.clean()
validation = project.validate_cleaning()

chart = project.visualize(
    chart="bar",
    x="Region",
    y="Revenue",
    title="Revenue by Region",
    x_label="Region",
    y_label="Average revenue",
    theme="journal",
)
chart.show()
```

## ADQL notebooks

ADQL is AutoDQ's standalone analytics language. A `.adql` file can contain
named executable cells and markdown cells, while retaining project state
between executions.

```adql
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;

# %% [Data quality]
PROFILE;
DIAGNOSE;
RECOMMEND;

# %% [Regional analysis]
SELECT Region,
       SUM(Revenue) AS total_revenue,
       COUNT(*) AS transactions
FROM CURRENT
GROUP BY Region
ORDER BY total_revenue DESC;

# %% [Visualization]
VISUALIZE bar X Region Y Revenue
    TITLE "Revenue by Region"
    THEME journal;
```

Run the file from a terminal:

```bash
autodq run analysis.adql
```

Inspect or validate cells without executing the workflow:

```bash
autodq cells analysis.adql
autodq validate analysis.adql
```

Run through a particular cell:

```bash
autodq run analysis.adql --through-cell 3
```

## VS Code support

The Python distribution bundles the AutoDQ ADQL extension. Install it with:

```bash
autodq vscode install
```

Reload VS Code after installation. `.adql` files then receive syntax
highlighting, named notebook cells, rich tables and charts, cell-by-cell
execution, and an AutoDQ file icon.

## Command-line interface

```text
autodq --version
autodq run workflow.adql
autodq validate workflow.adql
autodq cells workflow.adql
autodq vscode path
autodq vscode install
```

The package can also be executed as a Python module:

```bash
python -m autodq --version
```

## Development

Run the test suite:

```bash
python -m unittest discover -s tests
```

Build and verify release artifacts:

```bash
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist
```

For the complete release process, see the
[AutoDQ release guide](https://github.com/josephubani/autodq-analytics/blob/main/docs/RELEASING.md).

## Documentation

- [ADQL language reference](https://github.com/josephubani/autodq-analytics/blob/main/docs/ADQL_SPEC.md)
- [System architecture](https://github.com/josephubani/autodq-analytics/blob/main/docs/ARCHITECTURE.md)
- [Plugin development](https://github.com/josephubani/autodq-analytics/blob/main/docs/PLUGIN_GUIDE.md)
- [Project roadmap](https://github.com/josephubani/autodq-analytics/blob/main/docs/ROADMAP.md)
- [Package and release procedure](https://github.com/josephubani/autodq-analytics/blob/main/docs/RELEASING.md)

## License

AutoDQ is released under the
[MIT License](https://github.com/josephubani/autodq-analytics/blob/main/LICENSE).

## Author

Joseph Ubani  
Master of Data Analytics, University of Niagara Falls Canada
