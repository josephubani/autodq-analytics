# AutoDQ 0.1.12 Release Notes

AutoDQ 0.1.12 is a language-conformance and reliability release. It makes
ADQL-controlled language words consistently case-insensitive, completes VS
Code syntax coloring, aligns BLUE source validation with the core API, and
adds comprehensive tests across the complete AutoDQ and ADQL feature surface.

## Case-insensitive ADQL language words

Commands, actions, clauses, options, operators, datatypes, booleans, built-in
data sources, and enum values now accept uppercase, lowercase, or mixed case:

```adql
profile;
vIsUaLiZe BaR X Region Y Revenue ThEmE DaRk;
mOdEl TaRgEt Revenue uSiNg DeCiSiOn_TrEe_ReGrEsSoR;
sHaP ChArT BeEsWaRm;
```

Only ADQL-owned words are normalized. Dataset names, column names, aliases,
paths, chart titles, and quoted string values retain their exact spelling.
This means `CustomerData`, `Gross_Sales`, and `"Revenue CASE"` are never
silently renamed.

Boolean options accept every ADQL 2.1 form, including `true`, `false`, `yes`,
`no`, `on`, `off`, `1`, and `0`. Optional flags such as `OVERWRITE yes` are
handled consistently as well.

## BLUE source contract

`BLUE SOURCE` is now synchronized across the formal EBNF grammar, validator,
runtime, help, and documentation. The two supported analysis modes are:

```adql
BLUE SOURCE data;
BLUE SOURCE trained_model;
```

Use a named dataset through the normal dataset selector rather than as the
source value:

```adql
SET DATASET customers TARGET Spend;
BLUE DATASET customers SOURCE data MAX_FEATURES 10;
```

Invalid source values are rejected during ADQL validation with a direct error
instead of failing later inside the BLUE core API.

## Complete syntax coloring

The AutoDQ ADQL VS Code extension 0.3.5 adds semantic TextMate scopes for all
normative ADQL words. This includes SHAP `beeswarm` and `dependence`, the
`str` datatype alias, boolean aliases, BLUE `trained_model`, and built-in chart
types such as `boxplot`, `correlation_heatmap`, and `missing_values`.

Contextual boolean coloring distinguishes an option value such as
`UNCERTAINTY ON` from the `ON` clause used by dataset operations.

## Conformance and regression coverage

The release adds automated guarantees that:

- every one of the 53 public ADQL commands parses in mixed case;
- all public commands appear in ADQL `HELP`;
- ADQL identifiers and user strings preserve their spelling;
- every normative grammar word has a specialized syntax scope;
- mixed-case workflows reach the real profiling, statistics, correlation,
  readiness, features, BLUE, visualization, dashboard, model, prediction,
  uncertainty, explainability, SHAP, and quality-assertion APIs; and
- Python distributions and the bundled VS Code extension remain installable.

ADQL remains at language version `2.1` because these changes enforce its
existing case-insensitivity contract without introducing incompatible syntax.

## Release components

- AutoDQ Python package: `0.1.12`
- ADQL language: `2.1`
- AutoDQ ADQL VS Code extension: `0.3.5`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.12
```

Install `autodq-adql-0.3.5.vsix` through **Extensions: Install from VSIX...**
to update manually installed Visual Studio Code support.
