# AutoDQ ADQL for VS Code

This extension makes `.adql` a first-class AutoDQ language and notebook format.

- Syntax highlighting, comments, folding, and cell symbols
- `# %% [Cell title]` and `-- %% [Cell title]` cell boundaries
- Markdown cells with `# %% [markdown] Title`
- Run File, Run through Cell, and Run Cell Only actions
- A persistent notebook session with rich tables, reports, and charts

The session keeps the current AutoDQ project in memory as cells run. Use
**ADQL: Restart Session** from the Command Palette when you want a completely
fresh state.

Large notebook results are shown as bounded previews by default: up to 25 rows
or collection items and 12,000 structured-output characters. The complete
result stays in the active AutoDQ project for later statements and exports.
Change `autodq.notebook.maxOutputRows` or
`autodq.notebook.maxOutputCharacters` in VS Code Settings when a larger or
smaller preview is useful.

Install the AutoDQ package first. The extension searches upward from each
`.adql` file and automatically uses the nearest `.venv/bin/autodq` (or Windows
equivalent). You can override this with `autodq.commandPath`.
