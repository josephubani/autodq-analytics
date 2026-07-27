# AutoDQ 0.1.2 Release Notes

AutoDQ 0.1.2 prevents standalone HTML styling from changing the colors of
surrounding ADQL notebook outputs in dark-themed VS Code windows.

## Highlights

- Keep dashboards inside their existing sandboxed notebook iframe.
- Reject standalone HTML documents and global `html`, `body`, `:root`, or `*`
  CSS from the shared notebook output renderer.
- Preserve **View full output** for complete dataframes and structured reports.
- Continue restoring expandable outputs after saving and reopening `.adql`
  notebooks.

## Installation

```bash
python -m pip install --upgrade autodq==0.1.2
```

Install the matching AutoDQ ADQL 0.2.5 VSIX through
**Extensions: Install from VSIX...** in Visual Studio Code.

After upgrading, rerun and save affected cells to replace older cached HTML
outputs that may still contain the leaking standalone styles.

## Compatibility

AutoDQ supports Python 3.10 through 3.13 on Linux, macOS, and Windows.
