# AutoDQ 0.1.11 Release Notes

AutoDQ 0.1.11 introduces executable data-quality contracts through ADQL
`ASSERT`, reusable quality-test suites, and matching Python APIs. It also
expands AutoDQ's built-in dataset knowledge and advances the formal language
contract to ADQL 2.1.

## Executable data-quality assertions

Direct assertions inspect the active or explicitly named dataset without
changing its values:

```adql
ASSERT Transaction_ID UNIQUE;
ASSERT Revenue BETWEEN 0 AND 1000000;
ASSERT Region NOT NULL SEVERITY warning;
ASSERT MISSING_PERCENT <= 5;
ASSERT DUPLICATE_ROWS = 0;
ASSERT QUALITY_SCORE >= 90;
```

Checks cover column existence, completeness, uniqueness, datatype, minimum and
maximum bounds, inclusive ranges, allowed values, full-string regular
expressions, row and column counts, missingness, exact duplicates, distinct
values, and the AutoDQ quality score.

Every result includes its status, severity, observed and expected values,
failing-row count, and a readable explanation. Blocking failures produce a
structured failed ADQL result and make the CLI return exit status `1`, making
assertions suitable for notebooks, automation, and CI release gates.

## Reusable quality-test suites

Add multiple expectations to one named suite and run them together:

```adql
ASSERT SUITE ADD sales_gate Transaction_ID UNIQUE
    NAME "Transaction IDs are unique";
ASSERT SUITE ADD sales_gate Revenue MIN 0
    NAME "Revenue is non-negative";
ASSERT SUITE ADD sales_gate MISSING_PERCENT Region <= 2
    SEVERITY warning NAME "Region completeness";

ASSERT SUITE SHOW sales_gate;
ASSERT SUITE RUN sales_gate FAIL_ON warning;
```

`FAIL_ON error` is the default. `warning`, `info`, and `never` allow workflows
to choose exactly which failed severities stop execution. Suites support
`ADD`, `RUN`, `SHOW`, `LIST`, and `DROP`, and can be shared using versioned JSON:

```adql
ASSERT SUITE EXPORT sales_gate TO "tests/sales-gate.json" OVERWRITE;
ASSERT SUITE LOAD restored_gate FROM "tests/sales-gate.json";
ASSERT DATASET customers SUITE RUN restored_gate;
```

Suite definitions remain available across active-dataset switches during the
project session. The latest result is included in AutoDQ HTML and JSON reports.

## Python quality-test API

Python workflows can construct the same contracts using `QualityAssertion`,
`QualityTestSuite`, `QualityTestReport`, and `QualityTestEngine`. The public
project APIs include:

- `assert_quality()`;
- `add_quality_test()` and `run_quality_suite()`;
- `quality_suite()`, `quality_suite_frame()`, and `list_quality_suites()`;
- `drop_quality_suite()`; and
- `export_quality_suite()` and `load_quality_suite()`.

## Expanded dataset knowledge

The conservative built-in knowledge catalog now contains 87 semantic rules
and more than 390 aliases across retail, finance, banking, insurance,
healthcare, education, HR, logistics, marketing, geospatial, IoT, and general
operational datasets. Matching now handles snake case, kebab case,
punctuation, whitespace, and CamelCase while preferring specific multi-word
concepts over generic token matches.

## ADQL 2.1 and VS Code 0.3.4

ADQL 2.1 formally specifies assertion syntax, severity and failure behavior,
suite lifecycle and JSON portability, named-dataset targeting, safety limits,
structured errors, and artifact invalidation. The bundled AutoDQ ADQL VS Code
extension 0.3.4 adds complete syntax coloring and notebook documentation for
assertions, quality metrics, predicates, suite operations, and thresholds.

## Release components

- AutoDQ Python package: `0.1.11`
- ADQL language: `2.1`
- AutoDQ ADQL VS Code extension: `0.3.4`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.11
```

Install `autodq-adql-0.3.4.vsix` through **Extensions: Install from VSIX...**
to update manually installed Visual Studio Code support.
