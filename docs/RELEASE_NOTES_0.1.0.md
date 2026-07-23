# AutoDQ 0.1.0 Release Notes

AutoDQ 0.1.0 is the first complete alpha release candidate. It packages the
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

## Installation candidate

```bash
python -m pip install autodq==0.1.0
```

The command above becomes available after the public PyPI release. Before
that, install the tested wheel from `dist/` or use the TestPyPI instructions in
[RELEASING.md](RELEASING.md).

## Compatibility

AutoDQ supports Python 3.10 through 3.13. The release workflow is configured
to exercise all four Python versions on Linux, macOS, and Windows. Runtime
support includes CSV and Excel datasets.

## Release gate

The candidate is ready for TestPyPI after the complete local test suite,
distribution inspection, and clean-wheel smoke test pass. PyPI publication is
performed only after the TestPyPI candidate is installed and verified.
