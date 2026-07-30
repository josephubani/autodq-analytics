# AutoDQ 0.1.7 Release Notes

AutoDQ 0.1.7 adds explicit datatype formatting to ADQL. String date/time
columns can now be parsed with a declared pattern, mixed-format inference, or
ISO-8601 handling, while numeric columns can be rounded to a deliberate number
of decimal places during conversion.

## Datetime formatting

Use familiar date tokens:

```adql
SET TYPE Created_At datetime FORMAT "DD/MM/YYYY HH:mm:ss";
SET TYPE Month_End datetime FORMAT "DD-MMM-YYYY";
```

Python `strftime` directives are also accepted:

```adql
SET TYPE Created_At datetime FORMAT "%d/%m/%Y %H:%M:%S";
```

Named modes cover inferred, mixed, and ISO data:

```adql
SET TYPE Imported_At datetime FORMAT AUTO DAYFIRST true;
SET TYPE Imported_At datetime FORMAT MIXED DAYFIRST true UTC true;
SET TYPE Api_Timestamp datetime FORMAT ISO8601 UTC true;
```

Invalid non-empty values are safely converted to missing datetime values and
reported in the command result and session audit event.

## Numeric precision

Use `DECIMALS` with the float-family conversion names:

```adql
SET TYPE Revenue float DECIMALS 2;
SET TYPE Margin numeric DECIMALS 4;
SET TYPE Tax decimal DECIMALS 2;
```

`DECIMALS` accepts values from 0 through 15. Rounding remains numeric so later
ADQL queries, models, visualizations, and exports continue to treat the column
as a number.

## Named datasets and reusable snapshots

Formatting works on the active dataset or through a named dataset target, and
the converted result can be retained with `LET`:

```adql
SET DATASET customers TYPE Created_At datetime
    FORMAT "YYYY-MM-DD HH:mm:ss";
LET typed_customers = CURRENT;
EXPORT typed_customers TO "exports/typed-customers.csv" OVERWRITE;
```

## Release components

- AutoDQ Python package: `0.1.7`
- AutoDQ ADQL VS Code extension: `0.3.0`

Upgrade with:

```bash
python -m pip install --upgrade autodq==0.1.7
```

Install `autodq-adql-0.3.0.vsix` through **Extensions: Install from VSIX...**
to update manually installed VS Code support.
