# AutoDQ Python API

This reference covers the public workflow surface of `autodq.AutoDQ`. Most
methods return a report, dataframe, or reusable visualization object and also
store the result in `project.state` for later Python or ADQL operations.

## Create a project

```python
from autodq import AutoDQ

project = AutoDQ("sales.csv", target="Revenue")
```

Use `load()`, `change_dataset(path)`, `set_target(column)`, and
`set_type(column, dtype)` to control the active dataset.

## Automatic workflow

```python
result = project.auto(
    mode="full",
    visualize=True,
    apply_features=True,
    algorithm="random_forest_regressor",
    report_output="reports/auto-report.html",
    continue_on_error=True,
)
```

Modes:

- `review`: profile, analyze, diagnose, recommend, and prepare a cleaning review.
- `clean`: perform the review workflow, approve executable actions, clean, and validate.
- `full`: perform the clean workflow, then model, predict, and explain when a target exists.

The returned `AutoRunResult` provides `success`, stage counts,
`duration_seconds`, `next_actions`, `stage(name)`, `to_dict()`, `to_html()`, and
`show()`.

## Data quality and cleaning

| Area | Methods |
| --- | --- |
| Knowledge and profiling | `apply_knowledge()`, `profile()`, `statistics()`, `interpret()` |
| Diagnosis | `diagnose()`, `recommend()`, `decide()`, `preview()` |
| Interactive review | `review_cleaning()`, `approve()`, `reject()`, `approve_all()` |
| Manual review | `edit_row()`, `cleaning_preview()`, `apply_cleaning_review()` |
| Domains and outliers | `add_domain_rule()`, `validate_domain()`, `review_outliers()`, `treat_outliers()` |
| Cleaning | `clean()`, `validate_cleaning()`, `export_cleaning_audit()` |

## Analysis, features, and modeling

| Area | Methods |
| --- | --- |
| Correlation | `correlation()`, `show_correlation()` |
| ML readiness | `ml_readiness()`, `show_ml_readiness()` |
| Features | `features()`, `create_feature()`, `apply_features()`, `export_engineered()` |
| Modeling | `model()`, `save_model()`, `load_model()`, `show_model()` |
| Prediction | `predict()`, `show_predictions()`, `export_predictions()` |
| Explainability | `explain()`, `visualize_shap()`, `show_explanations()` |
| BLUE diagnostics | `blue()`, `visualize_blue()`, `interpret_blue_visuals()`, `prescribe_blue()` |

## Visualization and reporting

Use `visualize()` to create a reusable chart with `show()` and `save()`.
Gallery operations include `list_visualizations()`, `get_visualization()`,
`filter_visualizations()`, `customize_visualization()`,
`save_visualizations()`, and `clear_visualizations()`.

Use `dashboard()` for a standalone HTML dashboard and `generate_report()` for
HTML or JSON analytical reports.

## ADQL

```python
result = project.query("PROFILE; DIAGNOSE;", auto_display=False)
file_result = project.run_adql("analysis.adql", through_cell=3)
```

`query()` and its `adql()` alias execute allowlisted statements against the
current project. `run_adql()` executes a cell-based standalone file while
retaining state between selected cells. See [ADQL_SPEC.md](ADQL_SPEC.md) for
the language reference.

## Workspaces and datasets

Create or open a workspace with `AutoDQ.create_workspace()` and
`AutoDQ.open_workspace()`. Use `save_workspace()`, `workspace_info()`, and
`AutoDQ.list_workspaces()` for persistence and discovery.

Within a project, use `add_dataset()`, `use_dataset()`, `merge_datasets()`, and
`concat_datasets()` for multi-dataset analysis.

## Exports and inspection

Convenience methods include `head()`, `tail()`, `sample()`, `view()`, `info()`,
`export_current()`, `export_cleaned()`, and `export_predictions()`.
