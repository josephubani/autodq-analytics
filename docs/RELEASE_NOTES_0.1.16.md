# AutoDQ 0.1.16 Release Notes

AutoDQ 0.1.16 is a compatibility patch for Python 3.10 and Python 3.11.
It preserves all AutoDQ 0.1.15 schema-contract, drift-detection, ADQL 2.3,
modeling, SHAP, BLUE, cleaning, and reporting behavior.

## Python 3.10 and 3.11 compatibility

The HTML exporter used a nested triple-quoted string inside a triple-quoted
f-string expression for the empty BLUE visual-insights message. Python 3.12's
new f-string parser accepts that construct, but Python 3.10 and 3.11 reject it
during module import.

The fallback markup is now prepared before the report f-string is rendered.
This works on every supported Python version and produces the same report
message:

```text
No BLUE visual interpretations are available.
```

A regression test now renders this exact fallback path so the supported
Python-version matrix cannot silently regress.

## Coordinated versions

- AutoDQ Python package: `0.1.16`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.9`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.16
```

Install `autodq-adql-0.3.9.vsix` through **Extensions: Install from VSIX...**
and reload VS Code.

## Compatibility

This patch does not change ADQL syntax or public APIs. Existing `.adql`
notebooks, saved outputs, workspaces, datasets, contracts, baselines, quality
suites, reports, dashboards, models, SHAP explanations, and BLUE diagnostics
remain compatible.
