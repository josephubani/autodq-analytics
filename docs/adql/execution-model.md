# ADQL 2.0 Execution Model

This document is normative for AutoDQ ADQL 2.0 runtimes.

## 1. Runtime unit

An ADQL execution operates against exactly one in-memory AutoDQ project. The
project owns:

- a registry of named datasets;
- one active dataset;
- the target column;
- workflow artifacts derived from the active dataset;
- an optional cleaning-review working copy and audit trail;
- model, prediction, visualization, report, dashboard, and workspace state;
- session events and bounded ADQL run history.

Statements execute in source order. A later statement observes every
successful state change made by earlier statements in the same project.

## 2. Dataset registry and active dataset

The dataset registry maps a case-sensitive normalized name to a tabular data
snapshot and optional source path. Leading and trailing whitespace is removed
from names. Exactly one registered dataset may be active.

`ADD DATASET` registers data without changing the active dataset. `USE DATASET`
changes the active dataset. A `COMMAND DATASET name ...` selector performs the
same activation immediately before executing that command and leaves the
selected dataset active afterward.

When activation changes datasets, the runtime MUST:

1. save the active `CURRENT` data back into its registry entry;
2. make the selected registry entry active;
3. copy its tabular data into `CURRENT`;
4. update the project dataset path when one exists; and
5. invalidate derived workflow artifacts for the previously active context.

Requesting the already active dataset MUST preserve its existing workflow
artifacts.

The following operations read registered data without activating it:

- `SELECT ... FROM registered_name`
- `EXPORT registered_name TO ...`
- `LET new_name = DATASET registered_name`

## 3. Built-in stages

ADQL exposes four canonical stages:

```text
CURRENT -> CLEANED -> ENGINEERED -> PREDICTIONS
```

`CURRENT` is the active dataset. `CLEANED`, `ENGINEERED`, and `PREDICTIONS`
exist only after a successful operation creates them. Reading or exporting an
unavailable stage is an execution error.

The aliases `RAW` and `DATA` resolve to `CURRENT`. The alias `FEATURES`
resolves to `ENGINEERED`.

Stages are project artifacts, not automatically registered datasets. Use
`LET` to preserve a stage before switching the active dataset or replacing the
stage:

```adql
CLEANING APPLY;
LET clean_customers = CLEANED;
```

## 4. Artifact invalidation

Derived artifacts are valid only for the active dataset state from which they
were produced. Changing the active dataset invalidates profile, diagnosis,
recommendation, decision, review, cleaning, validation, feature, model,
prediction, explanation, visualization, BLUE, automatic-run, and dashboard
artifacts.

Direct changes to `CURRENT`, including `SET TYPE`, MUST invalidate downstream
artifacts. Review-working-copy mutations invalidate an existing finalized
`CLEANED` stage until cleaning is finalized again.

Read-only commands such as `SELECT`, `HEAD`, `TAIL`, `SAMPLE`, `SESSION`,
`HISTORY`, and `HELP` do not invalidate workflow artifacts.

## 5. Cleaning-review transaction

The cleaning-review subsystem maintains:

- an immutable copy of the data at review start;
- a mutable working copy;
- proposed cleaning actions and approval status;
- domain rules and validation results;
- outlier review state; and
- an append-only audit trail.

`EDIT`, mutating `MISSING` statements, `DUPLICATES DROP`, and
`OUTLIERS TREAT` update the review working copy immediately. A later summary or
review statement sees those staged changes. They do not update `CURRENT` and
do not create `CLEANED` by themselves.

`APPROVE` and `REJECT` change proposed-action status. `CLEANING PREVIEW`
simulates selected actions without committing a stage. `CLEAN` and
`CLEANING APPLY` finalize the working copy plus approved automatic actions into
`CLEANED`. Finalization also appends execution events to the audit trail.

The transaction is intentionally non-destructive: `CURRENT` remains the
before-cleaning comparison source. `VALIDATE` compares `CURRENT` to `CLEANED`.

## 6. LET snapshot semantics

`LET` creates a registered dataset snapshot. Its target name MUST be a valid
assignment identifier and cannot be a built-in source name.

Sources behave as follows:

| Source | Snapshot contents |
| --- | --- |
| `CURRENT`, `CLEANED`, `ENGINEERED`, `PREDICTIONS` | Copy of that stage |
| `DATASET name` | Copy of the named registry entry |
| `SELECT ...` | Copy of the bounded query result |

Every assignment resets the snapshot index to a zero-based integer sequence.
The snapshot is independent: later source mutations cannot change it. `LET`
does not activate the new dataset.

An existing target name causes an execution error unless `OVERWRITE` is
present. The active dataset cannot be overwritten. For a `SELECT` assignment,
the default 1,000-row query limit applies unless an explicit valid `LIMIT` is
provided.

## 7. Merge and concatenation

`MERGE` and `CONCAT` register their result under `AS output_name` or the
operation's default name. `MAKE_ACTIVE` defaults to true. When true, the result
becomes active and normal activation invalidation applies. When false, the
current active dataset and its artifacts remain active.

## 8. Automatic workflow

`AUTO` delegates to the allowlisted `project.auto()` workflow.

- `review` discovers and prepares work without applying dataset changes.
- `clean` includes approval and cleaning according to its options.
- `full` additionally enables modeling, prediction, and explanation when the
  data and target support them.

Explicit options override mode defaults. `CONTINUE_ON_ERROR` controls stage
behavior inside the automatic workflow; host-level continue-on-error controls
whether later ADQL statements execute after a failed statement. These are
distinct controls.

## 9. Statement failure and atomicity

Parsing and script validation occur before project execution. A syntax or
validation failure MUST leave project state unchanged.

Statement execution is sequential. Successful prior statements are not rolled
back when a later statement fails. A runtime SHOULD validate inputs before a
mutation and SHOULD stage complex changes on a copy so a failed statement does
not leave a partially modified table. ADQL 2.0 does not define multi-statement
transactions or rollback syntax.

Without host continue-on-error, the first execution failure stops the run.
With continue-on-error, the failed result is retained and later statements are
attempted against the state left by earlier successful statements.

## 10. Cell execution

Code cells share a project only within the host session that executes them.
Markdown and empty cells produce no statements and no state changes.

- **Run file** executes all code cells in document order.
- **Run through cell N** executes code cells from the beginning through N in
  one project.
- **Run cell N only** initializes a fresh project from the document dataset
  declaration or host override, then executes only the selected cell.
- A persistent notebook kernel MAY retain a project across separate cell
  requests. Restarting that kernel creates a new project session.

The `DATASET` declaration is inspected to initialize standalone execution even
when a later cell is selected. It is executed as an ordinary statement only
when its cell is included in the selected execution.

## 11. Paths and external effects

During `.adql` file execution, relative paths in statements resolve against the
document directory. This includes dataset, export, report, dashboard, model,
SHAP, gallery, workspace, and audit paths where applicable.

External writes require an explicit writing command. Unless `OVERWRITE` is
accepted by that command, an existing output path MUST cause an error rather
than being silently replaced.

## 12. History and session observations

Each completed run is appended to bounded project ADQL history after execution.
`HISTORY` therefore observes earlier runs, not the run currently producing its
output. Session events follow the same principle: an inspection statement's
own event is visible only to a later inspection.

`SESSION`, `SESSION EVENTS`, and `SESSION DATASETS` are read-only observations
of the current project. Rendering those observations does not alter their
semantic value.
