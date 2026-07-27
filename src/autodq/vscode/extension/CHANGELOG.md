# Change Log

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
