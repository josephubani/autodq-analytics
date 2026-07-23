# AutoDQ Development Roadmap

## Completed

1. SHAP plots
2. Model persistence
3. Multi-workspace architecture
4. Rich Jupyter and ADQL notebook experience
   - Rich HTML outputs and automatic chart rendering
   - Visualization gallery
   - Titles, subtitles, axis labels, themes, palettes, sizing, DPI, grids,
     legends, exports, and publication-ready templates
   - Reusable visualization objects with `show()` and `save()`
5. Prediction uncertainty
6. Interactive Cleaning and Domain Review Module
   - Partial approval and rejection of cleaning actions
   - Manual row editing
   - Outlier review and treatment
   - Domain-based validation
   - Interactive cleaning previews
   - Manual-change audit trails
7. `project.auto()`
8. Dashboard generator
9. ADQL standalone language and VS Code notebook integration
10. CLI and Python packaging
    - `autodq` console command and `python -m autodq`
    - Wheel and source-distribution builds
    - Bundled ADQL VS Code extension and file icons
    - Single-sourced package version
    - Complete dependency and PyPI metadata
    - Distribution inspection and clean-install smoke testing
11. Release-candidate tests and documentation
    - Python 3.10–3.13 compatibility matrix for Linux, macOS, and Windows
    - Python API and complete ADQL `AUTO` reference documentation
    - Changelog and 0.1.0 release notes
    - Standalone ADQL automatic-workflow acceptance coverage
    - Automated wheel and source-distribution release checks
    - Isolated wheel-install smoke testing against public user interfaces
    - Quickstart, troubleshooting, release notes, and repeatable release guide

## 0.1.0 release status

- Compatibility and distribution workflows passed in the hosted repository.
- The TestPyPI candidate was installed and verified.
- AutoDQ 0.1.0 was published to production PyPI on 2026-07-22.
- The production wheel passed clean installation, dependency, CLI, Python API,
  and complete ADQL `AUTO` verification.

All items in the original AutoDQ development roadmap are complete.

## Post-0.1.0 maintenance

- Continue expanding examples and task-oriented documentation.
- Track dependency deprecations and supported Python releases.
- Require the isolated wheel smoke test for every future publication.
- Record new work under `Unreleased` in the changelog before assigning the next
  version.
- Continue resolving upstream pandas and SHAP deprecation warnings without
  delaying functional maintenance releases.
