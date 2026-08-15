# AutoDQ Analytics Domain Query Language Specification

| Field | Value |
| --- | --- |
| Language | AutoDQ Analytics Domain Query Language (ADQL) |
| Language version | 2.3 |
| Specification status | Stable |
| Text encoding | UTF-8 |
| Canonical file extension | `.adql` |

This document is the normative definition of ADQL 2.3. It defines the
language independently of a particular user interface or AutoDQ package
release. The public Python constant `autodq.ADQL_LANGUAGE_VERSION` identifies
the language version implemented by an installed AutoDQ package.

The companion documents are part of this specification:

- [`grammar.ebnf`](grammar.ebnf) defines the concrete syntax.
- [`execution-model.md`](execution-model.md) defines project, dataset, stage,
  cell, and mutation semantics.
- [`data-types.md`](data-types.md) defines literals and column conversions.
- [`errors.md`](errors.md) defines failure categories and CLI outcomes.
- [`compatibility.md`](compatibility.md) defines language-version guarantees.

[`../ADQL_SPEC.md`](../ADQL_SPEC.md) is the non-normative user guide and
command reference. If the guide conflicts with this specification, this
specification takes precedence.

## 1. Normative terminology

The words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and
**MAY** describe conformance requirements.

- A conforming parser MUST accept every program allowed by the grammar and
  semantic rules and MUST reject unsupported commands and options.
- A conforming validator MUST enforce the safety limits in section 10 before
  executing project operations.
- A conforming runtime MUST preserve the state transitions defined by the
  execution model.
- A conforming notebook integration MUST execute code cells in document order
  when cumulative execution is requested and MUST NOT execute Markdown cells.

Presentation details such as colors, table styling, collapsed sections, and
chart rendering are not language semantics.

## 2. Source text

An ADQL source is Unicode text encoded as UTF-8. Keywords and unquoted enum
values are case-insensitive. Dataset names, column names, aliases, paths, and
string values retain their spelling.

Statements are separated by semicolons. A trailing semicolon is optional for
the final statement. Newlines are whitespace and do not terminate statements.

```adql
PROFILE;
SELECT Region, SUM(Revenue) AS total
FROM CURRENT
GROUP BY Region;
```

The following comments are supported outside quoted values:

```adql
# shell-style line comment
-- SQL-style line comment
```

A first-line shebang such as `#!/usr/bin/env autodq` is a `#` comment and has
no language-level effect.

## 3. Lexical elements

### 3.1 Keywords

All commands, clauses, option names, aggregate names, built-in data sources,
booleans, and null words defined in `grammar.ebnf` are reserved when they
appear in their grammatical positions. Their matching is case-insensitive.

Hyphens and underscores are equivalent only in option keys processed as
options. For example, `RANDOM-STATE` and `RANDOM_STATE` select the same option.
This equivalence does not apply to dataset or column names.

### 3.2 Identifiers

An assignment identifier used on the left side of `LET` MUST begin with an
ASCII letter or underscore and continue with ASCII letters, digits, or
underscores. It MUST contain at most 128 characters and MUST NOT replace a
built-in data source.

Column names, output aliases, and registered dataset names MAY be quoted with
single quotes, double quotes, or backticks when they contain spaces or words
that would otherwise be read as clauses.

```adql
SELECT `Order Date`, "Gross Sales" AS gross FROM CURRENT;
```

Identifiers MUST NOT be empty or contain a semicolon, carriage return, or
newline. A registered dataset selector MUST contain at most 255 characters.

### 3.3 Literals

ADQL has string, integer, floating-point, Boolean, and null literals. Literal
conversion is defined in [`data-types.md`](data-types.md). Option values that
contain whitespace MUST be quoted.

### 3.4 Lists and mappings

Most command lists use comma-separated values without surrounding brackets:

```adql
APPROVE 1,2,3;
FEATURE APPLY NAMES margin,volume_band;
```

`IN` and `NOT IN` lists require parentheses. `EDIT ... CHANGES` accepts a
quoted, non-empty Python-literal dictionary whose keys are column names. ADQL
does not evaluate arbitrary Python expressions.

## 4. Documents and notebook cells

The canonical source-file extension is `.adql`. A document MAY contain code
and Markdown cells introduced by either comment marker:

```adql
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;

-- %% [markdown] Business context
# Revenue review

This Markdown cell is not executable.

# %% [code] Analysis
PROFILE;
```

`[markdown]` selects a Markdown cell. `[code]` explicitly selects a code cell.
Any other bracketed value is the title of a code cell. Text before the first
marker forms a `Preamble` code cell only when it contains executable source.

A standalone document MUST contain at least one executable code cell. It MUST
declare exactly one `DATASET` as its first executable statement unless a
dataset override is supplied by the host. Relative paths declared inside a
document are resolved from the document directory. Host-supplied paths are
resolved according to the host environment.

Saved notebook output caches delimited by the AutoDQ output-cache markers are
comments. A conforming runtime MUST ignore the cache during parsing and
execution. Output-cache encoding is a notebook protocol concern, not ADQL
syntax.

## 5. Processing phases

A conforming implementation processes source in these phases:

1. Split the document into code and Markdown cells.
2. Remove line comments from executable source while preserving quoted text.
3. Split code into semicolon-delimited statements outside quotes and
   parentheses.
4. Parse statements into a structured representation.
5. Validate the complete script and each selected cell before its execution.
6. Execute selected statements in source order against one AutoDQ project.
7. Produce one structured result per attempted statement.

Parsing and validation MUST NOT invoke project operations or mutate datasets.
Execution stops at the first failed statement unless the host explicitly
enables continue-on-error behavior.

## 6. Data sources and dataset targeting

The built-in sources are:

| Source word | Canonical stage | Meaning |
| --- | --- | --- |
| `CURRENT`, `RAW`, `DATA` | `current` | Active dataset in memory |
| `CLEANED` | `cleaned` | Most recently finalized cleaning result |
| `ENGINEERED`, `FEATURES` | `engineered` | Most recent feature-engineering result |
| `PREDICTIONS` | `predictions` | Prediction rows produced by the active model |

A registered dataset name is also a valid source where the grammar permits
one. Built-in source words take precedence over registered names.

Dataset-scoped commands accept an explicit selector immediately after the
command:

```adql
PROFILE DATASET customers;
MODEL DATASET customers TARGET Churn USING random_forest_classifier;
```

The simple workflow commands plus `READINESS` and `FEATURES` also accept the
short positional form:

```adql
PROFILE customers;
READINESS customers;
```

`READINESS` MAY compare the active analysis dataset with a registered baseline:

```adql
READINESS REFERENCE production_baseline;
READINESS DATASET cleaned_sales REFERENCE production_baseline;
```

The optional `REFERENCE` dataset is read without being activated or mutated.
The explicit `DATASET` selector, when present, activates the analysis dataset
before scoring and leaves it active afterward.

The readiness result MUST expose seven weighted components totaling 100
possible points: sample sufficiency (10), data quality (25), feature readiness
(15), target readiness (15), leakage safety (15), multicollinearity (10), and
feature stability (10). The overall score is:

```text
earned component points / assessed component points * 100
```

An unassessed component MUST be excluded from both values and MUST reduce the
reported assessment coverage; it MUST NOT receive assumed credit. Feature
stability is unassessed without `REFERENCE`. With a suitable reference,
numeric and categorical feature distributions are compared using Population
Stability Index (PSI): values at or below 0.10 are stable, values through 0.25
are moderate shift, and values above 0.25 are unstable.

A dataset selector activates that registered dataset before the command and
leaves it active afterward. `SELECT ... FROM dataset`, `EXPORT dataset ...`,
and `LET name = DATASET dataset` read a named dataset without activating it.
See [`execution-model.md`](execution-model.md) for invalidation rules.

## 7. Statement classes

The exact production for every statement is in `grammar.ebnf`. This table
defines its purpose and primary state effect.

| Commands | Normative purpose |
| --- | --- |
| `DATASET`, `LOAD`, `ADD`, `USE`, `LIST` | Declare, load, register, activate, and inspect datasets. |
| `SELECT`, `HEAD`, `TAIL`, `SAMPLE` | Read bounded tabular results without changing dataset values. |
| `LET` | Create an independent named dataset snapshot from a stage, dataset, or bounded `SELECT` result. |
| `ASSERT` | Evaluate a non-mutating data-quality expectation or manage and run a reusable quality suite. |
| `SCHEMA` | Infer, refine, validate, inspect, export, and load a versioned schema contract. |
| `DRIFT` | Create portable statistical baselines and detect schema and distribution drift. |
| `PROFILE`, `STATISTICS`, `INTERPRET`, `DIAGNOSE`, `KNOWLEDGE`, `RECOMMEND`, `DECIDE`, `PREVIEW`, `REVIEW` | Build ordered quality and review artifacts in project state. |
| `APPROVE`, `REJECT` | Change the status of proposed cleaning actions. |
| `EDIT`, `MISSING`, `DUPLICATES`, `DOMAIN`, `OUTLIERS` | Inspect or mutate the audited cleaning-review working copy. |
| `CLEAN`, `CLEANING` | Preview or finalize reviewed cleaning changes into `CLEANED`. |
| `VALIDATE` | Compare `CURRENT` with the finalized `CLEANED` stage. |
| `SET` | Change the target or directly convert a column in `CURRENT`. |
| `CORRELATION`, `READINESS`, `FEATURES`, `FEATURE` | Produce analytical and feature-engineering artifacts. |
| `MODEL`, `PREDICT`, `EXPLAIN`, `SHAP`, `BLUE` | Train, persist, predict, explain, visualize, and diagnose models. |
| `VISUALIZE`, `GALLERY`, `DASHBOARD`, `REPORT` | Create reusable charts and publication artifacts. |
| `MERGE`, `CONCAT` | Register combined datasets and optionally make the result active. |
| `WORKSPACE` | Create, open, save, inspect, or list persistent workspaces. |
| `EXPORT`, `AUDIT` | Write explicit datasets, project reports, or audit records. |
| `AUTO` | Run an allowlisted `review`, `clean`, or `full` workflow preset. |
| `SESSION`, `HISTORY`, `HELP` | Inspect runtime state, previous ADQL runs, and command help. |

Unknown commands and unknown or duplicate options MUST be rejected.

### 7.1 Required options, ranges, and defaults

Options within an option-rich command may appear in any order. Each option may
appear at most once. The following semantic constraints supplement the EBNF:

| Statement | Requirement |
| --- | --- |
| `DATASET`, `ADD DATASET` | Input path suffix MUST be `.csv`, `.xlsx`, or `.xls`. |
| `AUTO` | Mode defaults to `review`; `TEST_SIZE` is strictly between 0 and 1; `RANDOM_STATE` is an integer; report suffix is `.html` or `.json`. |
| `MODEL` | Training uses the existing target unless `TARGET` is supplied; `TEST_SIZE` is strictly between 0 and 1; save/load forms require their path clause. |
| `PREDICT` | Confidence is strictly between 0 and 1; low-confidence threshold is between 0 and 1 inclusive. |
| `EXPLAIN` | `MAX_ROWS` MUST be positive. |
| `READINESS` | `REFERENCE` MUST name a registered dataset. PSI stability requires at least 50 rows in both the current and reference datasets. |
| `SHAP` | `ROW` cannot be negative; chart is `summary`, `bar`, `beeswarm`, `waterfall`, or `dependence`. |
| `MERGE` | `WITH` is REQUIRED; `SUFFIXES` contains exactly two values. |
| `CONCAT` | The initial dataset list contains at least two names. |
| `EDIT` | `CHANGES` is a non-empty mapping with string column keys. |
| `MISSING FILL` | Strategy defaults to `constant` when `VALUE` is supplied and `auto` otherwise; `constant` requires a non-null value. |
| `MISSING DROP ROWS` | `HOW` defaults to `any` and is either `any` or `all`. |
| `MISSING DROP COLUMNS` | Exactly one of a column list or `MIN_PERCENT` is supplied; percentage is between 0 and 100 inclusive. |
| `DUPLICATES DROP` | `KEEP` defaults to `first` and is `first`, `last`, or `none`. |
| `DOMAIN ADD` | At least one constraint is REQUIRED. |
| `OUTLIERS` | `IQR` MUST be positive; `TREAT` requires `COLUMN`. |
| `CORRELATION` | `MIN_ABS` is between 0 and 1 inclusive. |
| `BLUE` | `MAX_FEATURES` is positive; `SIGNIFICANCE` is strictly between 0 and 1. |
| `DASHBOARD` | A supplied output path ends with `.html`. |
| `GALLERY SAVE` | Format is `png`, `svg`, `pdf`, `jpg`, or `jpeg`. |
| `REPORT` | Output suffix is `.html` or `.json`. |
| `EXPORT` | Output suffix is `.csv` or `.xlsx`. |
| `AUDIT EXPORT` | Output suffix is `.json` or `.csv`. |
| `ASSERT` | Severity is `error`, `warning`, or `info`; `FAIL_ON` additionally accepts `never`; suite JSON paths end with `.json`; `BETWEEN` bounds are ascending. |
| `SCHEMA` | Contract and JSON artifact names are bounded identifiers; `EXTRA_COLUMNS` is `ignore`, `info`, `warning`, or `error`; contract paths end with `.json`. |
| `DRIFT` | `REFERENCE` is required for detection; PSI and missingness warning thresholds cannot exceed error thresholds; baseline paths end with `.json`. |
| `HEAD`, `TAIL`, `SAMPLE`, `HISTORY`, `SESSION EVENTS LIMIT` | Explicit row or event counts are positive integers. |

Boolean flags written as `OVERWRITE` without a value mean true. When the
grammar permits an optional Boolean after such a flag, an explicit true or
false spelling overrides that default.

### 7.2 Data-quality assertions and suites

`ASSERT` evaluates `CURRENT` without changing dataset values. Column
assertions support existence, completeness, uniqueness, dtype, inclusive
minimum and maximum bounds, inclusive ranges, allowed values, and full-string
regular-expression matching. Missing values are evaluated only by `NOT NULL`
and missing metrics; other column predicates ignore missing values so authors
can state completeness and value-domain requirements independently.

Metric assertions support row count, column count, missing count and percent,
removable exact-duplicate rows and percent, distinct non-null values, and the
AutoDQ diagnosis quality score. `MISSING_COUNT` and `MISSING_PERCENT` MAY name
a column or inspect the complete table. `DISTINCT_COUNT` requires a column.
Duplicate metrics count rows after the first exact occurrence, matching the
default `DUPLICATES DROP KEEP first` behavior.

Each assertion has severity `error` by default. A failed assertion blocks when
its severity is at least the statement's `FAIL_ON` level. `FAIL_ON error` is
the default; `warning` also blocks warning failures, `info` blocks every
failure, and `never` records failures without failing the ADQL statement.
Blocking failures produce a structured failed result and obey normal
continue-on-error behavior.

`ASSERT SUITE ADD` stores a definition without evaluating it. `RUN` evaluates
the suite against the active or explicitly selected dataset. `SHOW`, `LIST`,
and `DROP` inspect or remove in-memory definitions. `EXPORT` and `LOAD` use the
versioned JSON suite format and require explicit overwrite permission. Suite
definitions are project-wide and survive active-dataset switches; the most
recent suite result is a dataset-derived artifact and is invalidated when the
active dataset changes.

### 7.3 Schema contracts and drift baselines

`SCHEMA CONTRACT CREATE` infers required columns, canonical data types,
nullability, identifier uniqueness, and bounded categorical domains from a
current or registered dataset. Numeric and datetime ranges are inferred only
when `INFER_RANGES true` is explicit. `ADD` creates or updates a column rule.
Contract validation is non-mutating and uses the same `error`, `warning`,
`info`, and `FAIL_ON` gate semantics as quality assertions.

Contracts use a versioned JSON format. Registered definitions survive active
dataset switches and are persisted with an attached workspace. The latest
validation report is dataset-derived and is invalidated by a dataset switch.

`DRIFT BASELINE CREATE` stores compact distributions rather than raw records.
Numeric and datetime columns retain baseline quantile bins; categorical
columns retain at most 50 frequent values plus explicit other and missing
buckets. Detection compares required and added columns, compatible dtypes,
missing percentages, distinct-value ratios, PSI, values outside baseline
ranges, complete categorical domains, duplicate rate, and batch row count.

PSI is stable at or below 0.10, moderate through 0.25, and major above 0.25 by
default. Missingness deltas use 2 and 5 percentage points. Thresholds are
configurable per `DRIFT DETECT`. The transparent stability score is
`(stable checks + 0.5 × moderate checks) / all checks × 100`. An optional
contract contributes its failed checks to the drift gate. Drift operations do
not mutate current, cleaned, engineered, or named datasets.

## 8. SELECT semantics

`SELECT` is a safe, pandas-backed analytical query. It is not general SQL and
does not execute SQL strings or Python expressions.

Clauses, when present, MUST occur in this order:

```text
SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT
```

Supported projections are columns, `*`, and these aggregate functions:
`COUNT`, `SUM`, `AVG`, `MEAN`, `MIN`, `MAX`, `MEDIAN`, and `NUNIQUE`.
Only `COUNT` accepts `*`.

When aggregate and plain-column projections are mixed, every plain column
MUST appear in `GROUP BY`. Output aliases are case-insensitively unique.
`ORDER BY` refers to output columns, including aliases.

`WHERE` conditions are combined only with `AND`. Supported operators are `=`,
`!=`, `<`, `<=`, `>`, `>=`, `IN`, `NOT IN`, `IS NULL`, `IS NOT NULL`,
`CONTAINS`, `STARTS WITH`, and `ENDS WITH`. ADQL 2.3 does not support `OR`,
joins inside `SELECT`, subqueries, window functions, or arbitrary functions.

`DISTINCT` is applied after projection and aggregation. Ordering is stable,
with missing values last. The runtime returns at most 1,000 rows when `LIMIT`
is omitted. An explicit `LIMIT` MUST be positive and cannot exceed 10,000.
The result records both returned rows and the total number matched before the
limit.

## 9. Mutation and audit semantics

The following commands mutate the cleaning-review working copy and MUST record
audit information for their row- or cell-level changes:

- `EDIT ROW`
- `MISSING FILL`
- `MISSING DROP ROWS`
- `MISSING DROP COLUMNS`
- `DUPLICATES DROP`
- `OUTLIERS TREAT`

These changes are visible to subsequent review commands immediately, but they
do not create a `CLEANED` stage until `CLEAN` or `CLEANING APPLY` succeeds.
`DOMAIN ADD` changes review rules; `DOMAIN VALIDATE` inspects the working copy.
`APPROVE` and `REJECT` change action decisions rather than dataset cells.

`SET TYPE` is intentionally different: it directly changes the selected
dataset's `CURRENT` stage and invalidates derived artifacts.

`LET` always stores a copy with a reset integer index. It never creates a live
reference to its source and does not activate the assigned dataset. Without
`OVERWRITE`, assigning an existing name fails. The active dataset cannot be
overwritten by `LET`.

## 10. Safety limits

A conforming AutoDQ ADQL 2.3 validator enforces:

| Limit | Value |
| --- | ---: |
| Source length | 100,000 characters |
| Statements per parsed script | 100 |
| Explicit `SELECT LIMIT` | 10,000 rows |
| `WHERE` conditions | 50 |
| Default returned query rows | 1,000 |
| Assertions loaded per quality suite | 500 |
| Quality-suite JSON size | 1 MB |
| Values in one `ALLOWED` assertion | 1,000 |
| Regular-expression length | 1,000 characters |
| Columns per schema contract or drift baseline | 1,000 |
| Schema contract JSON size | 2 MB |
| Drift baseline JSON size | 5 MB |

ADQL MUST NOT expose `eval`, `exec`, imports, attribute access, arbitrary
Python calls, shell execution, or unregistered command handlers. File writes
occur only through explicit export, report, dashboard, model, gallery,
workspace, audit, quality-suite, schema-contract, or drift-baseline export
statements.

Paths and command-specific numeric ranges MUST pass the validations described
by the command reference and error specification before the associated
operation runs.

## 11. Results

Every attempted statement produces a structured result containing:

- the parsed statement and statement number;
- `completed` or `failed` status;
- a human-readable message;
- optional tabular data or a structured value;
- duration;
- error type and message when failed.

A script is successful only when every parsed statement has a completed
result. Rich HTML, images, plain text, collapsed previews, and persisted
outputs are host renderings of these results and MUST NOT change subsequent
language behavior.

## 12. Conformance and extensions

An implementation claiming **ADQL 2.3 parser conformance** MUST implement all
productions in `grammar.ebnf`. An implementation claiming **AutoDQ ADQL 2.3
runtime conformance** MUST additionally implement every command listed by the
runtime command set and the state transitions in this specification.

Implementations MAY provide extra renderers, editors, transport protocols, and
CLI options. They MUST NOT silently reinterpret valid ADQL 2.3 syntax.
Language extensions require a later ADQL language version and MUST be rejected
as unknown syntax by implementations that do not support that version.

The AutoDQ test suite verifies that the runtime language version, specification
version, grammar command inventory, parser command inventory, and normative
examples remain synchronized.
