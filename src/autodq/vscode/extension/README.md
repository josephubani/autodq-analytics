# AutoDQ ADQL for VS Code

This extension makes `.adql` a first-class AutoDQ language and notebook format.

- Syntax highlighting, comments, folding, and cell symbols
- `# %% [Cell title]` and `-- %% [Cell title]` cell boundaries
- Run File, Run through Cell, and Run Cell Only actions
- A notebook editor and AutoDQ kernel for `.adql` files

Install the AutoDQ package first. The extension automatically uses the
workspace's `.venv/bin/autodq` (or Windows equivalent). You can override this
with `autodq.commandPath`.
