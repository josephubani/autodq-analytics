# Changelog

All notable AutoDQ changes are recorded here. Versions follow semantic
versioning and Python package releases follow PEP 440.

## Unreleased

### Changed

- Prepared AutoDQ ADQL as a public Visual Studio Marketplace extension with a
  validated VSIX, guarded publication workflow, Marketplace listing metadata,
  and workspace-trust protections.
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
