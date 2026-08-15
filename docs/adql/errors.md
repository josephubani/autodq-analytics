# ADQL 2.3 Error Model

This document defines the stable ADQL error categories and failure reporting
requirements.

## 1. Error categories

AutoDQ exposes seven public exception classes:

| Class | Phase | Meaning |
| --- | --- | --- |
| `ADQLError` | Any | Base class for language-level failures |
| `ADQLSyntaxError` | Parse | Source cannot be represented by ADQL grammar |
| `ADQLValidationError` | Validate | Parsed source violates a safety or semantic rule |
| `ADQLAssertionError` | Execute | A valid quality assertion reached its configured failure level |
| `ADQLContractError` | Execute | Schema validation reached its configured failure level |
| `ADQLDriftError` | Execute | Drift detection reached its configured failure level |
| `ADQLExecutionError` | Execute | A valid statement failed while operating on project state |

All seven are language-facing categories. The underlying cause of an
execution failure MAY be a project exception such as `KeyError`, `ValueError`,
or `RuntimeError`; the ADQL executor wraps it in `ADQLExecutionError` when
execution is configured to raise.

## 2. Syntax errors

Syntax errors include:

- unsupported commands;
- missing required clauses or options;
- unsupported or duplicate options;
- invalid option quoting;
- unterminated strings;
- unbalanced parentheses;
- malformed `SELECT` clause order;
- malformed lists, mappings, aliases, and assignment forms; and
- scalar values that cannot be parsed for a syntax-defined type.

Parser messages MUST identify the one-based statement number when source
contains one or more statements.

```text
Statement 2: SELECT requires exactly one FROM clause.
```

## 3. Validation errors

Validation occurs after parsing and before project execution. Validation
errors include:

- source, statement, query-row, or condition limits being exceeded;
- unsafe or unsupported file suffixes;
- values outside command-specific ranges;
- invalid stage, type, strategy, mode, or chart enum values;
- aggregate/grouping violations;
- duplicate query aliases;
- invalid dataset selectors or `LET` names; and
- combinations of individually valid options that are not valid together.

The validator MUST identify the one-based statement number. A validation
failure MUST occur before any statement in the same parsed script is executed.

## 4. Execution errors

Execution errors include:

- unknown registered datasets or columns;
- unavailable `CLEANED`, `ENGINEERED`, `PREDICTIONS`, model, or review state;
- incompatible runtime column types;
- failure of a model, visualization, report, or data operation;
- missing input files;
- existing output paths without an accepted overwrite option; and
- operating-system or dependency failures encountered by an allowlisted
  operation.

An `ADQLExecutionError` MUST expose:

- the human-readable message;
- the failing parsed statement when available;
- the partial run result when available; and
- the original cause when available.

The partial run retains completed results before the failure and a failed
result containing `error_type` and `error_message`.

An `ADQLAssertionError` MUST retain the `QualityTestReport` and its tabular
test results. The executor records that structured result before applying the
normal stop or continue-on-error policy. Hosts that raise execution failures
MAY wrap it in `ADQLExecutionError`, retaining it as the original cause.

`ADQLContractError` and `ADQLDriftError` specialize `ADQLAssertionError` and
follow the same structured-result rule. They retain the complete
`SchemaValidationReport` or `DriftReport`, respectively, including the tabular
check results that caused the gate to fail.

## 5. Continue-on-error

By default, execution stops at the first failed statement. When the host
enables continue-on-error, the executor MUST retain the failed result and MAY
attempt later statements. The overall run remains unsuccessful.

Continue-on-error does not convert a failure to a warning, does not roll back
earlier successful statements, and does not guarantee that dependent later
statements can run.

`AUTO CONTINUE_ON_ERROR` controls stages inside `AUTO`; it does not change the
host's multi-statement behavior.

## 6. Result status

Each attempted statement result has exactly one status:

- `completed` — execution returned normally;
- `failed` — execution raised an exception.

`success` is derived from status. A run is successful only when its number of
completed results equals its parsed statement count and it has no failed
results.

Markdown and empty notebook cells contain zero statements. They are skipped
and are not failures.

## 7. CLI exit status

The canonical `autodq` CLI uses:

| Exit code | Meaning |
| ---: | --- |
| `0` | Command completed successfully |
| `1` | ADQL execution completed with one or more failed statement results |
| `2` | CLI usage, file, syntax, validation, or raised language error |

Human-readable diagnostics are written to standard error for caught language
and file errors. Machine consumers SHOULD use the JSON or notebook protocol
outputs where available instead of parsing prose.

## 8. Notebook errors

The notebook protocol represents execution failure with `success: false` and
at least one plain-text output naming the exception class and message. A host
MAY additionally render an error panel, traceback, or source location.

Notebook rendering failures MUST NOT be reported as successful ADQL statement
execution when the underlying statement did not complete.

## 9. Stability of diagnostics

Exception class names, result statuses, and CLI exit meanings are normative.
Exact prose, punctuation, path formatting, and underlying dependency exception
messages are informative and MAY improve within an ADQL 2.x release.

Consumers MUST NOT depend on exact error-message strings. Future structured
error codes may be added in a backward-compatible ADQL 2.x revision.
