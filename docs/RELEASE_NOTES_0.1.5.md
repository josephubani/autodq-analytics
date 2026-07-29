# AutoDQ 0.1.5 Release Notes

AutoDQ 0.1.5 adds read-only ADQL session inspection so notebook users can see
which dataset and workflow artifacts are currently retained before continuing
an analysis.

## ADQL session inspection

Show a rich summary of the active project session:

```adql
SESSION;
```

The summary includes the active dataset, target, row and column counts,
workspace, start time, registered datasets, completed workflow steps, event
count, ADQL run count, and the availability of profiling, cleaning, feature,
modeling, prediction, explanation, visualization, and dashboard artifacts.

Inspect recent workflow events or registered datasets as tables:

```adql
SESSION EVENTS;
SESSION EVENTS LIMIT 20;
SESSION DATASETS;
```

Events are returned newest first. Dataset output marks the active dataset and
shows dimensions, source paths, and registration timestamps. All three forms
are read-only and work in the terminal, Python-driven ADQL, and the persistent
VS Code notebook session.

## Python API

The same state is available programmatically:

```python
summary = project.session_info()
events = project.session_events(limit=20)
datasets = project.session_datasets()
```

`project.show_session()` continues to print the console history and now also
returns the structured summary.

## Versions

- AutoDQ Python package: `0.1.5`
- AutoDQ ADQL VS Code extension: `0.2.8`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.5
```

Install `autodq-adql-0.2.8.vsix` through **Extensions: Install from VSIX...**
in VS Code, then run **Developer: Reload Window**.
