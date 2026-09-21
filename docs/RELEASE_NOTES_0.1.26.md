# AutoDQ 0.1.26 Release Notes

AutoDQ 0.1.26 introduces ADQL 2.8, a readability and consistency release for
analytics notebooks, command results, and Visual Studio Code language support.
Existing ADQL 2.x programs remain valid.

## Readable identifiers

ADQL now uses SQL-style double quotes for identifiers that contain spaces:

```adql
LET "Cleaned Sales" = CLEANED;

SELECT Region,
       SUM(Revenue) AS "Total Revenue",
       AVG(Profit) AS "Average Profit"
FROM "Cleaned Sales"
GROUP BY Region
ORDER BY "Total Revenue" DESC;
```

A quoted identifier such as `"Customer Age"` can address a stored
`Customer_Age`, `Customer-Age`, or `Customer Age` column without renaming the
source DataFrame. The same rule applies when referencing registered datasets.
Resolution is deterministic: exact spelling wins, followed by a unique
case-insensitive match and then a unique separator-equivalent match. Ambiguous
matches fail with an error that lists the exact alternatives.

Single quotes are now the canonical notation for strings, labels, titles,
paths, and other literal text:

```adql
DATASET '../datasets/sample/sales.csv' TARGET Revenue;
REPORT TO '../reports/sales.html' STYLE executive OVERWRITE;
```

Backticks remain available for column references inside feature expressions:

```adql
FEATURE CREATE "Gross Margin" METHOD expression
    EXPRESSION '`Revenue` - `Cost`';
```

## Natural command options

Multiword options and quality metrics can be written with spaces:

```adql
AUTO MODE review CONTINUE ON ERROR false;
VISUALIZE bar X Region Y Revenue MAX ROWS 20;
ASSERT MISSING PERCENT Region <= 2 SEVERITY warning;
ASSERT SUITE RUN sales_gate FAIL ON warning;
INVENTORY SERVICE LEVEL 95 ON HAND "Units Available";
```

Underscore and hyphen spellings such as `MAX_ROWS`, `FAIL_ON`, and
`SERVICE-LEVEL` remain compatible with ADQL 2.8, but natural-space options are
the preferred public style.

## Clearer notebook results

Rich notebook output now displays readable headings such as `Customer Age`
and `Total Revenue`. This is presentation-only: exports, source columns,
dataset snapshots, and Python DataFrames retain their original names. Profile,
diagnosis, recommendation, model, SHAP, BLUE, validation, dashboard, and other
structured result sections use the same display rules.

## VS Code and examples

- The TextMate grammar colors double-quoted and backtick identifiers,
  single-quoted strings, natural-space options, and natural-space quality
  metrics case-insensitively.
- Every bundled `.adql` notebook has been migrated to the canonical ADQL 2.8
  style and validated without saved output caches.
- Parser, executor, notebook renderer, grammar, package, and distribution
  checks cover the new syntax and compatibility behavior.

## Versions

- AutoDQ Python package: `0.1.26`
- ADQL language: `2.8`
- AutoDQ ADQL VS Code extension: `0.3.19`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.26
```

For manual VS Code installation, download `autodq-adql-0.3.19.vsix` from the
matching GitHub release and install it with `--force`.
