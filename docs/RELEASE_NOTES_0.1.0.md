# AutoDQ 0.1.0 Release Notes

AutoDQ 0.1.0 is the first complete alpha release. It packages the
entire data-quality-to-modeling workflow for Python, Jupyter, the command line,
and executable `.adql` notebooks.

## Highlights

- Analyze data quality, generate evidence-aware cleaning recommendations, and
  approve or reject individual actions before changing data.
- Run `project.auto()` or `AUTO MODE review|clean|full` for a traceable
  automatic workflow with rich stage summaries.
- Build reusable publication-ready charts and standalone HTML dashboards.
- Train models, save and reload them, generate prediction intervals, and
  inspect SHAP and BLUE diagnostics.
- Use `.adql` as a cell-based notebook in VS Code with persistent state,
  collapsible rich output, automatic chart rendering, and dedicated file icons.

## Installation

```bash
python -m pip install autodq==0.1.0
```

The release is available from
[production PyPI](https://pypi.org/project/autodq/0.1.0/).

## Compatibility

AutoDQ supports Python 3.10 through 3.13. The release workflow is configured
to exercise all four Python versions on Linux, macOS, and Windows. Runtime
support includes CSV and Excel datasets.

## Release verification

- The complete automated test suite passed.
- Linux, macOS, and Windows compatibility jobs cover Python 3.10–3.13.
- The wheel and source archive passed metadata and content inspection.
- The TestPyPI candidate installed and completed an ADQL automatic workflow.
- The production PyPI wheel installed in a clean environment with no broken
  dependencies, and its CLI, Python API, ADQL `AUTO`, and prediction workflow
  completed successfully.
