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

## Next milestone

11. Tests, documentation, and release
    - Expand compatibility testing across Python 3.10–3.13
    - Resolve current pandas deprecation warnings
    - Complete API and ADQL reference documentation
    - Add release notes and changelog
    - Test the package on TestPyPI
    - Publish the first PyPI release
