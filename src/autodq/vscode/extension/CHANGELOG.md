# Change Log

## Unreleased

## 0.3.10 - 2026-08-15

- Bundled AutoDQ 0.1.17 with complete Python 3.10 and 3.11 compatibility in
  HTML report generation.
- Added compatibility coverage for empty BLUE visual-insight and prescription
  report sections.

## 0.3.9 - 2026-08-15

- Bundled AutoDQ 0.1.16 with Python 3.10 and 3.11 compatibility restored in
  HTML report generation.
- Added regression coverage for BLUE report rendering when visual insights
  have not been generated.

## 0.3.8 - 2026-08-15

- Added case-insensitive syntax highlighting for ADQL 2.3 `SCHEMA CONTRACT`
  and `DRIFT` commands, operations, thresholds, rule options, and severities.
- Added notebook guidance for creating, validating, exporting, loading, and
  persisting schema contracts and compact statistical baselines.
- Bundled AutoDQ 0.1.15 schema-validation and drift-detection runtime support.

## 0.3.7 - 2026-08-12

- Added syntax highlighting for the ADQL 2.2 `REFERENCE` option.
- Added notebook documentation for transparent weighted `READINESS`
  scorecards and optional PSI feature-stability baselines.
- Bundled AutoDQ 0.1.14 readiness rendering and runtime support.

## 0.3.6 - 2026-08-07

- Changed quality predicates to a visible control-keyword scope so `NOT NULL`,
  `BETWEEN`, `EXISTS`, and `MATCHES` receive clear syntax coloring in common
  VS Code themes.
- Added regression coverage for the quality-predicate TextMate scope.

## 0.3.5 - 2026-08-07

- Completed case-insensitive highlighting coverage for every ADQL command and
  language word, including SHAP chart names, `str`, boolean aliases, and
  built-in visualization values.
- Added conformance checks that keep the TextMate grammar synchronized with
  the normative ADQL grammar and runtime command inventory.

## 0.3.4 - 2026-08-07

- Added complete ADQL 2.1 highlighting for `ASSERT`, quality metrics,
  predicates, suite operations, severities, and failure thresholds.
- Documented executable notebook quality gates and portable JSON suites.

## 0.3.3 - 2026-08-02

- Made `REVIEW` a true interactive notebook panel with action selection,
  approve/reject/preview controls, approve-all, and apply-to-`CLEANED`.
- Added audited manual row editing and a recent audit-trail view directly in
  the notebook output.
- Restored the AutoDQ session automatically before a user interacts with a
  saved review output after reopening the `.adql` notebook.
- Kept static HTML review output as a compatibility fallback for older
  extensions, terminal execution, and other notebook environments.

## 0.3.2 - 2026-07-31

- Added highlighting and notebook documentation for `DUPLICATES SUMMARY` and
  audited `DUPLICATES DROP KEEP first|last|none` workflows.
- Bundled AutoDQ 0.1.9 runtime support for exact-row duplicate inspection,
  staged removal, and reusable cleaned snapshots.

## 0.3.1 - 2026-07-29

- Added highlighting and notebook documentation for ADQL `MISSING` summaries,
  datatype-aware fills, row removal, and column removal.
- Bundled AutoDQ 0.1.8 runtime support for audited missing-value workflows.

## 0.3.0 - 2026-07-29

- Added highlighting and documentation for `SET TYPE` options `FORMAT`,
  `DAYFIRST`, `YEARFIRST`, `UTC`, and `DECIMALS`.
- Bundled AutoDQ 0.1.7 runtime support for human and Python datetime patterns,
  ISO-8601/mixed parsing, timezone normalization, and numeric rounding.

## 0.2.9 - 2026-07-29

- Added syntax highlighting and notebook documentation for ADQL `LET`.
- Added reusable named snapshots for stages, registered datasets, and safe
  `SELECT` results through the bundled AutoDQ 0.1.6 runtime.

## 0.2.8 - 2026-07-29

- Added syntax highlighting and rich notebook output for `SESSION`.
- Added tabular output for `SESSION EVENTS [LIMIT n]` and `SESSION DATASETS`.
- Bundled the AutoDQ 0.1.5 runtime release metadata.

## 0.2.7 - 2026-07-27

- Documented direct named-dataset workflows such as `PROFILE customers`,
  `AUTO DATASET customers MODE review`, and `SELECT * FROM customers`.
- Bundled the AutoDQ 0.1.4 runtime release metadata for consistent manual
  VSIX and PyPI upgrades.

## 0.2.6 - 2026-07-26

- Added comprehensive, theme-aware syntax highlighting for every ADQL command,
  workflow action, clause, option, aggregate function, data source, literal,
  operator, punctuation mark, and cell marker.
- Added distinct scopes for column names, aliases, and backtick-quoted
  identifiers.
- Added grammar coverage tests for the public ADQL command and option
  vocabulary.

## 0.2.5 - 2026-07-26

- Fixed standalone dashboard and report CSS leaking light backgrounds into
  dark-themed ADQL notebooks.
- Rendered complete dashboards through their sandboxed iframe and kept other
  expanded results inside AutoDQ's VS Code theme-aware structured renderer.

## 0.2.4 - 2026-07-25

- Added **View full output** and **Hide full output** controls to truncated
  notebook results.
- Preserved complete expandable results in the saved notebook output cache.
- Kept the bounded preview as the default view so large results do not take
  over the notebook.

## 0.2.3 - 2026-07-22

- Persisted notebook text, HTML, table, and image outputs when an ADQL file is
  saved, closed, and reopened.
- Embedded the output cache as ignored ADQL comments so saved files remain
  executable from the AutoDQ CLI.
- Invalidated cached output when the corresponding cell source no longer
  matches.

## 0.2.2 - 2026-07-22

- Added a persistent ADQL notebook kernel with cell-by-cell execution.
- Added rich tables, charts, structured reports, collapsible output, and
  bounded previews.
- Added `AUTO MODE review|clean|full` notebook rendering.
- Added Windows `.venv\Scripts\autodq.exe` discovery.
- Added dedicated light and dark `.adql` file icons.
- Added Marketplace metadata and workspace-trust protections.
