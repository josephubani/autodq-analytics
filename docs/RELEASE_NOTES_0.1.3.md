# AutoDQ 0.1.3 Release Notes

AutoDQ 0.1.3 adds comprehensive, theme-aware ADQL syntax highlighting to the
bundled Visual Studio Code extension. ADQL notebook code is now visually
separated from ordinary text across the complete language vocabulary.

## What changed

- Every supported ADQL command and workflow action receives a syntax scope.
- SQL-style clauses, workflow options, aggregate functions, data sources,
  constants, enum values, operators, and punctuation are highlighted.
- Options such as `NULLABLE`, `DESCRIPTION`, `ALLOWED`, `COLUMNS`, and `IQR`
  are recognized directly by the grammar.
- Column names and aliases receive a variable scope, including names such as
  `Revenue`, `Customer_Age`, and `total_revenue`.
- Backtick-quoted identifiers, strings, numbers, comments, and named cell
  markers have dedicated scopes.
- Colors remain controlled by the active VS Code theme, so the grammar works
  in both dark and light themes without hardcoded foreground colors.

## Versions

- AutoDQ Python package: `0.1.3`
- AutoDQ ADQL VS Code extension: `0.2.6`

## Upgrade

Upgrade AutoDQ with:

```bash
python -m pip install --upgrade autodq==0.1.3
```

Install `autodq-adql-0.2.6.vsix` through **Extensions: Install from VSIX...**
in VS Code. Then run **Developer: Reload Window** or close and reopen VS Code.
