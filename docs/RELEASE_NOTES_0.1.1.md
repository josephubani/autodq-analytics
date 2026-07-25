# AutoDQ 0.1.1 Release Notes

AutoDQ 0.1.1 improves large-output handling in executable `.adql` notebooks.
The notebook still opens each result as a bounded, readable preview, but a
truncated result now includes a **View full output** control.

## Highlights

- Expand truncated dataframes, structured analytics, matrices, profiles,
  diagnoses, and cleaning recommendations without rerunning the cell.
- Collapse a complete result again with **Hide full output**.
- Save and reopen the notebook without losing either the preview or its
  complete expandable result.
- Keep the full result in a scrollable panel so it does not take over the
  entire notebook.

## Installation

```bash
python -m pip install --upgrade autodq==0.1.1
```

Install the matching AutoDQ ADQL 0.2.4 VSIX in Visual Studio Code through
**Extensions: Install from VSIX...**.

## Compatibility

AutoDQ supports Python 3.10 through 3.13 on Linux, macOS, and Windows.
