# AutoDQ 0.1.14 Release Notes

AutoDQ 0.1.14 makes machine-learning readiness transparent. The final score is
now backed by visible weighted components, explicit deductions, observed
metrics, recommendations, and an assessment-coverage percentage. ADQL 2.2
also adds an optional registered reference dataset for real feature-stability
measurement.

## Transparent component scoring

The readiness model contains seven components whose maximum points total 100:

| Component | Maximum points | Calculation focus |
| --- | ---: | --- |
| Sample sufficiency | 10 | Row count against the 1,000-row full-credit threshold |
| Data quality | 25 | Missing cells (up to 18 points) and exact duplicates (up to 7) |
| Feature readiness | 15 | Numeric availability, high skew, and heavy tails |
| Target readiness | 15 | Target validity, completeness, and variation |
| Leakage safety | 15 | Numeric features with `|correlation| >= 0.95` to the target |
| Multicollinearity | 10 | Predictor pairs with `|correlation| >= 0.90` |
| Feature stability | 10 | PSI against an optional registered reference dataset |

Every component exposes its earned points, maximum points, status, source
metrics, deductions, and next recommendation. The report also shows the exact
formula:

```text
overall score = earned component points / assessed component points * 100
```

An unassessed component is excluded from both the numerator and denominator.
It receives no assumed credit. `assessment_coverage` shows the percentage of
the 100-point model that AutoDQ could actually measure.

## Feature stability with a baseline

Register a representative baseline and pass it to readiness:

```adql
ADD DATASET baseline FROM "../datasets/baseline-sales.csv";
READINESS REFERENCE baseline;
```

To score a named dataset while keeping the baseline read-only:

```adql
READINESS DATASET clean12 REFERENCE baseline;
```

The explicit `DATASET` is activated for analysis. `REFERENCE` is read without
activation or mutation. AutoDQ compares numeric and categorical features with
Population Stability Index (PSI):

- `PSI <= 0.10`: stable;
- `0.10 < PSI <= 0.25`: moderate shift;
- `PSI > 0.25`: unstable.

Without `REFERENCE`, feature stability is visibly marked **not assessed**.
Both current and reference datasets need at least 50 rows for PSI scoring.

The equivalent Python API is:

```python
report = project.ml_readiness(reference="baseline")
```

## Rich output everywhere

The component scorecard is available through:

- `project.ml_readiness()` and rich Jupyter display;
- `project.show_ml_readiness()` console output;
- ADQL notebook `READINESS` output;
- `AUTO` stage summaries;
- project HTML and JSON reports; and
- `MLReadinessReport.to_dict()` for programmatic use.

The public `MLReadinessComponent`, `MLReadinessEngine`, `MLReadinessIssue`, and
`MLReadinessReport` classes are exported from `autodq`.

## Corrections included

The previous engine looked for statistical insights on a field that the
interpretation report does not define. AutoDQ now reads the actual per-column
interpretations, so high-skew and heavy-tail deductions work. Target-feature
correlations used for leakage screening are also excluded from predictor-only
multicollinearity scoring to avoid double counting.

## Release components

- AutoDQ Python package: `0.1.14`
- ADQL language: `2.2`
- AutoDQ ADQL VS Code extension: `0.3.7`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.14
```

Install `autodq-adql-0.3.7.vsix` through **Extensions: Install from VSIX...**
to update a manually installed Visual Studio Code extension. Then run
**Developer: Reload Window**.
