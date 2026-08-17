# Changelog

All notable AutoDQ changes are recorded here. Versions follow semantic
versioning and Python package releases follow PEP 440.

## Unreleased

## 0.1.19 - 2026-08-16

### Changed

- Removed the fixed 100-statement validation limit from ADQL scripts and
  executable `.adql` notebooks.
- Preserved source-size, query-row, WHERE-condition, command allowlist, and
  explicit-mutation safeguards independently of notebook length.
- Advanced the bundled AutoDQ ADQL VS Code extension to 0.3.12 so long
  notebooks run consistently in VS Code and the CLI.
- Made `sales_auto.adql` the public sales example and excluded the personal
  `sales_analysis.adql` notebook from Git, source distributions, documentation,
  and release validation.

### Validation

- Added regression coverage that validates a 250-statement ADQL script.

## 0.1.18 - 2026-08-16

### Changed

- Changed ADQL `LET` rendering to show a compact assignment confirmation with
  the dataset name, source, dimensions, and overwrite status instead of
  automatically repeating the assigned table.
- Preserved the assigned DataFrame on the Python result object and the complete
  independent snapshot in the dataset registry for later queries and exports.
- Advanced the bundled AutoDQ ADQL VS Code extension to 0.3.11 with the same
  compact `LET` behavior in executable `.adql` notebook cells.

### Fixed

- Prevented large `LET ... = SELECT ...` and stage assignments from flooding
  terminal, Jupyter, and VS Code notebook output with unnecessary row previews.

## 0.1.17 - 2026-08-15

### Fixed

- Removed the remaining Python 3.12-only nested multiline fallback from the
  BLUE prescriptions table in the HTML exporter, completing Python 3.10 and
  3.11 import compatibility.
- Extended compatibility coverage to render both empty BLUE visual insights
  and empty BLUE prescriptions and to reject multiline `or` fallbacks in the
  exporter source.

### Changed

- Advanced the bundled AutoDQ ADQL VS Code extension to 0.3.10 so manual VSIX
  installations include the corrected AutoDQ 0.1.17 runtime.

## 0.1.16 - 2026-08-15

### Fixed

- Restored Python 3.10 and 3.11 import compatibility in the HTML report
  exporter by removing a Python 3.12-only nested f-string expression from the
  BLUE visual-insights fallback.
- Added a focused regression test that renders the BLUE section when no
  interpreted visual diagnostics are available.

### Changed

- Advanced the bundled AutoDQ ADQL VS Code extension to 0.3.9 so manual VSIX
  installations include the corrected AutoDQ 0.1.16 runtime.

## 0.1.15 - 2026-08-15

### Added

- Added versioned schema contracts with conservative inference, explicit
  column constraints, severity-aware validation, rich reports, JSON
  portability, and workspace persistence.
- Added compact statistical drift baselines and transparent detection for
  schema changes, missingness, distinct ratios, PSI, unseen categories,
  out-of-range values, duplicate rate, and row-count movement.
- Added Python APIs and ADQL 2.3 `SCHEMA CONTRACT` and `DRIFT` commands with
  current-data, named-dataset, and reusable JSON workflows.
- Added schema and drift sections to HTML and JSON project reports and
  theme-aware notebook output.

### Changed

- Advanced the bundled AutoDQ ADQL VS Code extension to 0.3.8 with complete,
  case-insensitive highlighting for schema-contract and drift syntax.
- Persisted contract and baseline definitions with workspaces while correctly
  invalidating only dataset-derived validation and drift reports on dataset
  changes.

### Safety

- Contract validation and drift detection are non-mutating operations.
- Drift baseline artifacts contain bounded statistical summaries and never
  contain source rows.

## 0.1.14 - 2026-08-12

### Added

- Replaced the opaque ML-readiness total with seven visible weighted
  components, per-component points, observed metrics, deductions,
  recommendations, assessment coverage, and the exact normalized formula.
- Added optional baseline comparison through Python `ml_readiness()` and ADQL
  `READINESS REFERENCE dataset` using feature-level Population Stability Index
  thresholds.
- Added rich readiness scorecards to Jupyter, ADQL notebook, console, JSON,
  automatic-workflow, and project-report outputs.

### Changed

- Advanced the language to ADQL 2.2 and the bundled AutoDQ ADQL extension to
  0.3.7 for the additive `READINESS ... REFERENCE ...` clause.
- Excluded unassessed components from the score denominator instead of
  silently awarding assumed credit; assessment coverage reports the measured
  share of the 100-point model.

### Fixed

- Connected feature-readiness skew and heavy-tail scoring to the actual
  `InterpretationReport.interpretations` collection.
- Prevented target correlations flagged as leakage from also being counted as
  predictor multicollinearity.

## 0.1.13 - 2026-08-07

### Fixed

- Made ADQL quality predicates use a visible control-keyword syntax scope so
  `NOT NULL`, `BETWEEN`, `EXISTS`, and `MATCHES` no longer inherit an
  uncolored operator style in common VS Code themes.
- Added a syntax-scope regression check for assertion predicates and bundled
  the corrected AutoDQ ADQL 0.3.6 extension with the Python distribution.

## 0.1.12 - 2026-08-07

### Changed

- Completed a cross-feature runtime audit covering AutoDQ analysis, cleaning,
  workspaces, visualization, dashboards, modeling, persistence, uncertainty,
  SHAP, BLUE, quality suites, and the ADQL notebook surface.
- Made all ADQL-controlled command words, actions, clauses, options, boolean
  forms, and enum values consistently case-insensitive while preserving the
  exact spelling of dataset names, columns, aliases, paths, titles, and string
  values.
- Expanded ADQL help coverage to every public command and completed VS Code
  semantic highlighting for SHAP chart names, datatype aliases, boolean forms,
  and built-in visualization values.

### Fixed

- Aligned `BLUE SOURCE` validation, the formal grammar, runtime execution, and
  documentation around the supported `data` and `trained_model` sources.
- Normalized ADQL-controlled enum values before dispatch so mixed-case chart,
  model, cleaning, report, dashboard, and formatting values execute exactly
  like their lowercase equivalents.

## 0.1.11 - 2026-08-07

### Added

- Added non-mutating ADQL `ASSERT` checks for column existence, completeness,
  uniqueness, type, numeric bounds, allowed values, regex patterns, dataset
  counts, missingness, exact duplicates, distinct values, and quality score.
- Added reusable data-quality suites with `ADD`, `RUN`, `SHOW`, `LIST`, `DROP`,
  versioned JSON `EXPORT`/`LOAD`, severity levels, configurable failure
  thresholds, named-dataset targeting, and structured notebook/CLI results.
- Added public Python quality-test models and APIs plus quality-test sections
  in HTML and JSON project reports.
- Expanded the built-in knowledge catalog from 11 to 87 conservative semantic
  rules with more than 390 aliases spanning retail, finance, banking,
  insurance, healthcare, education, HR, logistics, marketing, geospatial, IoT,
  and general operational datasets.
- Added rule metadata for applicable domains, sensitivity, units, scales,
  formats, and recommended quality checks where those details are useful.

### Changed

- Advanced the formal language version to ADQL 2.1 and synchronized the EBNF,
  compatibility policy, error model, execution model, help, and VS Code syntax
  vocabulary.
- Updated the bundled AutoDQ ADQL VS Code extension to 0.3.4 with complete
  assertion, quality-metric, suite-operation, severity, and threshold
  highlighting.
- Made knowledge matching aware of snake case, kebab case, punctuation,
  whitespace, and CamelCase while preserving the existing `KnowledgeRule` and
  `KnowledgeEngine` APIs.
- Prefer specific multi-word concepts over generic terms and require token
  matches, preventing false positives such as treating `average_revenue` as an
  age column.

## 0.1.10 - 2026-08-02

### Added

- Published the normative ADQL 2.0 language specification, machine-readable
  EBNF grammar, execution model, data-type rules, error model, and compatibility
  policy.
- Exposed `ADQL_LANGUAGE_VERSION` through the public Python API and added
  conformance tests that keep the runtime command inventory synchronized with
  the specification and grammar.
- Added a versioned, allowlisted notebook protocol for interactive cleaning
  review actions while retaining the existing static HTML representation for
  the CLI, Jupyter, and older VS Code extensions.
- Added kernel-level review actions for selected approval, rejection with an
  audit reason, previews, approve-all, manual row edits, refresh, and applying
  the staged result to `CLEANED`.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.3.3 with a
  theme-aware interactive `REVIEW` panel and saved-output session restoration.

## 0.1.9 - 2026-07-31

### Added

- Added first-class ADQL `DUPLICATES SUMMARY` output that displays every row
  belonging to each exact-duplicate group, including source index, group ID,
  and occurrence count.
- Added audited `DUPLICATES DROP KEEP first|last|none` removal staged through
  the cleaning review until `CLEANING APPLY`.
- Added matching Python APIs: `duplicate_summary()` and `drop_duplicates()`.
- Added named-dataset targeting and end-to-end `LET ... = CLEANED` acceptance
  coverage for deduplicated results.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.3.2 with highlighting
  and documentation for exact-duplicate workflows.

## 0.1.8 - 2026-07-29

### Added

- Added first-class ADQL `MISSING` workflows for summaries, datatype-aware
  fills, and audited missing row or column removal.
- Added matching Python APIs: `missing_summary()`, `fill_missing()`,
  `drop_missing_rows()`, and `drop_missing_columns()`.
- Added cell-level audit records for every filled value and row/column removal,
  with all mutations staged in the cleaning review until `CLEANING APPLY`.
- Added named-dataset targeting and rich dataframe results for every `MISSING`
  operation.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.3.1 with highlighting
  and documentation for the complete missing-value vocabulary.

## 0.1.7 - 2026-07-29

### Added

- Added explicit ADQL datetime parsing through `SET TYPE ... datetime FORMAT`,
  including human-readable patterns, Python `strftime` patterns, `AUTO`,
  `MIXED`, and `ISO8601` modes.
- Added `DAYFIRST`, `YEARFIRST`, and `UTC` datetime conversion options.
- Added `DECIMALS` precision for `float`, `numeric`, `number`, and `decimal`
  conversions, with safe coercion details returned in command output and the
  session audit trail.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.3.0 with highlighting
  and notebook documentation for all datatype-formatting options.

## 0.1.6 - 2026-07-29

### Added

- Added ADQL `LET` assignments for reusable in-memory dataset snapshots from
  `CURRENT`, `CLEANED`, `ENGINEERED`, `PREDICTIONS`, registered datasets, and
  safe `SELECT` results.
- Added `AutoDQ.assign_dataset()` as the core project API used by `LET`.
- Added end-to-end acceptance coverage for assigning cleaned data, querying a
  saved result, exporting it, and inspecting it through session datasets.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.2.9 with `LET`
  highlighting and notebook documentation.

## 0.1.5 - 2026-07-29

### Added

- Added read-only ADQL session inspection with `SESSION`,
  `SESSION EVENTS [LIMIT n]`, and `SESSION DATASETS`.
- Added structured Python APIs for session summaries, recent events, and
  registered datasets through `session_info()`, `session_events()`, and
  `session_datasets()`.
- Added a rich, theme-aware session summary for VS Code ADQL notebooks.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.2.8.

## 0.1.4 - 2026-07-27

### Added

- Added named-dataset workflow targeting across stateful ADQL commands,
  including concise calls such as `PROFILE customers` and the universal
  `COMMAND DATASET name ...` selector.
- Added direct registered-dataset sources for `SELECT ... FROM name` and
  `EXPORT name TO ...` without changing the active workflow dataset.
- Added `export_named_dataset()` to the Python project API.

### Fixed

- Prevented repeated commands targeting the same active dataset from clearing
  profile, diagnosis, cleaning, feature, and model state between statements.
- Added actionable unknown-dataset errors listing the available names.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.2.7.

## 0.1.3 - 2026-07-26

### Added

- Added comprehensive, theme-aware ADQL syntax scopes for all supported
  commands, workflow actions, clauses, options, aggregate functions, data
  sources, constants, enum values, operators, and punctuation.
- Added distinct highlighting for column names, aliases, and backtick-quoted
  identifiers so user-defined ADQL names no longer blend into plain text.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.2.6.

## 0.1.2 - 2026-07-26

### Fixed

- Prevented standalone dashboard and report CSS from leaking a white background
  into dark-themed VS Code ADQL notebook outputs.
- Kept complete dashboard output isolated in its sandboxed notebook iframe while
  retaining expandable full results for other structured outputs.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.2.5.

## 0.1.1 - 2026-07-25

### Added

- Added an expandable **View full output** control to every truncated ADQL
  notebook dataframe, report, recommendation list, matrix, and structured
  result.
- Preserved the complete expandable output when an `.adql` notebook is saved,
  closed, and reopened.

### Changed

- Updated the bundled AutoDQ ADQL VS Code extension to 0.2.4.
- Persisted saved ADQL notebook outputs across close and reopen while keeping
  the embedded output cache executable as ordinary ADQL comments.
- Prepared AutoDQ ADQL as a public Visual Studio Marketplace extension with a
  validated VSIX, guarded publication workflow, Marketplace listing metadata,
  and workspace-trust protections.
- Added account-independent ADQL extension distribution through versioned
  GitHub Releases, including permanent VSIX downloads and SHA-256 checksums.
- Added a clean-environment wheel smoke test covering installation, dependency
  integrity, Python API usage, ADQL `AUTO`, CLI entry points, and bundled VS
  Code assets.
- Added public release acceptance tests that execute outside the source tree.
- Added a user quickstart, troubleshooting guide, post-release verification,
  and automatic GitHub release creation for future PyPI publications.
- Updated public documentation to reflect the live PyPI release.

## 0.1.0 - 2026-07-22

Initial alpha release.

### Added

- End-to-end profiling, diagnosis, recommendations, interactive cleaning, and validation.
- Feature engineering, regression and classification, prediction uncertainty, SHAP explanations, and BLUE diagnostics.
- Reusable visualizations, galleries, reports, and standalone HTML dashboards.
- Multi-workspace projects, multi-dataset operations, and model persistence.
- `project.auto()` review, clean, and full workflow presets.
- ADQL as a standalone cell-based language with rich VS Code notebook output.
- ADQL `AUTO` support with full public workflow options and rich stage summaries.
- Command-line tools, bundled VS Code extension and `.adql` icons, wheel and source distributions.
- Automated compatibility matrix configured for Python 3.10–3.13 on Linux,
  macOS, and Windows.
- Tokenless TestPyPI publishing workflow using GitHub Trusted Publishing.
- Protected, version-gated production PyPI Trusted Publishing workflow.

### Release status

- Published to TestPyPI and production PyPI through GitHub Trusted Publishing.
- Clean installation, dependency, CLI, Python API, and full ADQL `AUTO`
  verification passed against the production artifact.
