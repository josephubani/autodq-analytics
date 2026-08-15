# AutoDQ 0.1.17 Release Notes

AutoDQ 0.1.17 completes the Python 3.10 and Python 3.11 compatibility repair
for HTML report generation. It supersedes AutoDQ 0.1.16.

## Complete Python 3.10 and 3.11 compatibility

AutoDQ 0.1.16 moved the empty BLUE visual-insights fallback out of an outer
f-string, but a separate empty BLUE prescriptions fallback still used the same
Python 3.12-only nested multiline construct. Python 3.10 and 3.11 therefore
continued to reject the exporter during import.

AutoDQ 0.1.17 prepares both fallback sections before rendering the report
f-string. The exporter now safely renders:

```text
No BLUE visual interpretations are available.
No BLUE prescriptions are available.
```

Compatibility coverage now verifies both empty sections and prevents nested
multiline `or` fallbacks from returning to the exporter. The complete AutoDQ
source package is also syntax-checked against the Python 3.10 target.

## Coordinated versions

- AutoDQ Python package: `0.1.17`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.10`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.17
```

Install `autodq-adql-0.3.10.vsix` through **Extensions: Install from VSIX...**
and reload VS Code.

## Compatibility

This patch does not change ADQL syntax or public APIs. Existing `.adql`
notebooks, saved outputs, workspaces, datasets, contracts, baselines, quality
suites, reports, dashboards, models, SHAP explanations, and BLUE diagnostics
remain compatible.
