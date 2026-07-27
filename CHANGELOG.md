# Changelog

All notable AutoDQ changes are recorded here. Versions follow semantic
versioning and Python package releases follow PEP 440.

## Unreleased

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
