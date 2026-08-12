# ADQL 2.2 Data Types and Conversion Rules

This document is normative for ADQL literals, option coercion, query values,
and `SET TYPE` conversions.

## 1. Language literals

ADQL parses these scalar literal classes:

| Class | Examples | Runtime value |
| --- | --- | --- |
| String | `"North"`, `'High priority'` | Unicode string |
| Integer | `0`, `-12`, `450` | Integer |
| Floating point | `2.5`, `.75`, `1e-4` | Floating-point number |
| Boolean | `TRUE`, `FALSE` | Boolean |
| Null | `NULL`, `NONE` | Missing/null value |
| Bare value | `North`, `median`, `executive` | String token |

Single- and double-quoted strings support backslash escapes accepted by Python
string-literal syntax. Quoted ADQL values MUST evaluate to strings; tuples,
lists, dictionaries, and other Python literal types are not general ADQL
literals.

`EDIT ... CHANGES` is the sole mapping-literal exception. It requires a quoted,
non-empty dictionary literal with non-empty string keys:

```adql
EDIT ROW 4 CHANGES '{"Region": "North", "Revenue": 125.50}';
```

The dictionary is parsed as data. It is never evaluated as executable Python.

## 2. Option coercion

Command option names define their expected value category. Boolean options
accept these case-insensitive spellings:

```text
true:  true, yes, 1, on
false: false, no, 0, off
```

Integer options reject decimal spellings. Positive-integer options require a
value greater than zero. Numeric options use floating-point conversion.
Comma-separated list options cannot contain empty items.

`FIGSIZE` accepts `width,height` or `widthxheight`; both dimensions MUST be
positive numbers.

## 3. Tabular values

ADQL operates on pandas-backed tables. Column storage types are therefore
pandas dtypes, while ADQL exposes a stable set of conversion names. Missing
values MAY be represented internally by pandas or NumPy null values. ADQL
renderers and serialized results represent missing scalars as null.

Query comparisons use the active column's stored type. ADQL does not perform a
general implicit cast between arbitrary strings, datetimes, and numbers.
Users SHOULD apply `SET TYPE` before numeric or datetime analysis when source
data was loaded with an unsuitable type.

## 4. SET TYPE aliases

`SET TYPE column dtype` accepts these aliases:

| Canonical result | Accepted names |
| --- | --- |
| Datetime | `datetime`, `date`, `timestamp` |
| String | `str`, `string`, `text` |
| Nullable integer | `int`, `integer` |
| Floating point | `float`, `numeric`, `number`, `decimal` |
| Categorical | `category`, `categorical` |

Conversions change `CURRENT` directly. Derived project artifacts are
invalidated after a successful conversion.

### 4.1 Datetime

Datetime conversion uses coercion: invalid non-null inputs become missing
datetime values and are counted in the statement result.

`FORMAT` accepts:

- `AUTO` or `INFER` for pandas inference;
- `MIXED` for row-by-row format inference;
- `ISO`, `ISO8601`, or `ISO-8601` for ISO-8601 variants;
- a Python `strftime` pattern; or
- an ADQL human-readable pattern.

Human-readable tokens are case-sensitive:

| Token | Meaning |
| --- | --- |
| `YYYY`, `YY` | Four- or two-digit year |
| `MMMM`, `MMM`, `MM`, `M` | Full, abbreviated, two-digit, or numeric month |
| `DD`, `D` | Day of month |
| `HH`, `hh` | 24-hour or 12-hour hour |
| `mm`, `ss`, `SSS` | Minute, second, fractional second |
| `A` | AM/PM marker |
| `Z` | Numeric timezone offset |

`DAYFIRST` and `YEARFIRST` are valid only with inferred `AUTO`/`INFER` or
`MIXED` parsing. An explicit format already fixes field order. `UTC true`
returns timezone-aware UTC values.

```adql
SET TYPE Created_At datetime FORMAT "DD/MM/YYYY HH:mm:ss";
SET TYPE Api_Time timestamp FORMAT ISO8601 UTC true;
SET TYPE Imported_At date FORMAT MIXED DAYFIRST true;
```

The format string MUST be non-empty, contain at most 255 characters, and MUST
NOT contain a null byte, carriage return, newline, or semicolon.

### 4.2 String

String conversion converts each value through its string representation.
Because this operation follows pandas string conversion, existing null values
may acquire a textual representation. Users SHOULD inspect missingness after
conversion when null preservation matters.

### 4.3 Integer

Integer conversion first coerces values to numeric. Invalid and non-integral
values become missing. The result uses pandas nullable `Int64` storage.

`DECIMALS` is permitted only as `DECIMALS 0` for integer conversion; it does
not round non-integral source values into integers.

### 4.4 Floating point and decimal aliases

`float`, `numeric`, `number`, and `decimal` all produce pandas floating-point
numeric storage. Invalid source values become missing.

`DECIMALS n` rounds stored values to `n` decimal places, where `n` MUST be
between 0 and 15 inclusive.

```adql
SET TYPE Revenue float DECIMALS 2;
SET TYPE Margin decimal DECIMALS 4;
```

ADQL 2.2 `decimal` is an alias for floating-point conversion; it is not an
arbitrary-precision decimal type. Rounding changes numeric values, not merely
their display formatting.

### 4.5 Category

Category conversion uses pandas categorical storage and preserves the distinct
values represented by the source column.

## 5. Missing-value strategies

`MISSING FILL` accepts:

| Strategy | Meaning |
| --- | --- |
| `auto` | Median for eligible numeric columns; mode otherwise |
| `constant` | Use the required non-null `VALUE` |
| `mean` | Numeric arithmetic mean |
| `median` | Numeric median |
| `mode` | Most frequent non-missing value |
| `zero` | Numeric zero or the applicable zero value |
| `ffill` | Previous non-missing value |
| `bfill` | Next non-missing value |
| `interpolate` | Numeric interpolation |

Providing `VALUE` selects `constant` by default. `VALUE` MUST NOT be supplied
for another strategy, and a constant value cannot be null.

## 6. Null query semantics

Use `IS NULL` and `IS NOT NULL` to test missing values. Equality against
`NULL` is not a substitute for these operators.

String predicates (`CONTAINS`, `STARTS WITH`, and `ENDS WITH`) operate through
the runtime's string-aware column handling. Relational comparisons are subject
to the column's dtype and may fail at execution when values are incomparable.

## 7. Serialization

Structured ADQL results convert NumPy scalar values to corresponding Python
scalars. Datetimes, dates, paths, and pandas timestamps serialize as strings.
Missing scalars serialize as null. DataFrame results serialize as column names,
row counts, and bounded record previews; the full in-memory result remains
available to the current runtime until replaced or the session ends.
