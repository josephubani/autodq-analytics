# AutoDQ 0.1.25 Release Notes

AutoDQ 0.1.25 adds governed prescriptive analytics, constrained action
optimization, and what-if scenarios through the Python API and ADQL 2.7.

## Prescriptive analytics

The new prescriptive engine turns existing operational analytics and
multi-echelon inventory evidence into a transparent action plan. Each action
contains:

- its originating report and evidence;
- a human-readable target, description, and rationale;
- expected impact and a normalized impact score;
- an explicit planning-cost estimate and cost basis;
- priority, risk, confidence, optimization score, and governance status; and
- source metadata for audit and review.

The engine supports balanced planning and objectives for delay, failure, cost,
value, capacity, and inventory shortage. It uses SciPy mixed-integer linear
optimization when available, with a deterministic greedy fallback. Portfolios
can be constrained by budget, maximum actions, minimum confidence, and maximum
risk.

Python users can call `prescribe()`, `optimize_prescriptions()`, `what_if()`,
`approve_prescription()`, `approve_all_prescriptions()`,
`reject_prescription()`, `execute_prescription()`, `prescription_audit()`, and
`export_prescription_audit()`.

## ADQL 2.7

ADQL adds four case-insensitive commands:

```adql
PRESCRIBE OBJECTIVE reduce_delay SOURCE operations
    MAX_ACTIONS 5 MIN_CONFIDENCE 0.60 MAX_RISK medium;

SCENARIO NAME "Faster service"
    DURATION_CHANGE -20 FAILURE_CHANGE -10 COST_CHANGE 5;

OPTIMIZE OBJECTIVE reduce_delay MAX_ACTIONS 3;

ACTION LIST STATUS selected;
ACTION APPROVE A001 ACTOR "operations lead";
ACTION EXECUTE A001 ACTOR "operations lead";
ACTION AUDIT TO "action-audit.json" OVERWRITE;
```

`SCENARIO` compares an unchanged KPI baseline with explicit percentage-change
assumptions. `ACTION EXECUTE` only records that an approved recommendation was
implemented; it never modifies source data or an external system. Every
optimization, scenario, approval, rejection, and execution decision is added
to the audit trail.

## Reporting, notebooks, and dashboards

- Prescriptive overviews, action tables, scenarios, and audit trails render as
  theme-aware notebook HTML.
- Dashboards and HTML/JSON reports include the latest prescriptive plan.
- `examples/prescriptive_operations.adql` demonstrates a complete governed
  workflow.
- The VS Code grammar highlights all new commands, actions, objectives,
  constraints, scenario options, statuses, and risk levels case-insensitively.

## Versions

- AutoDQ Python package: `0.1.25`
- ADQL language: `2.7`
- AutoDQ ADQL VS Code extension: `0.3.18`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.25
```

For manual VS Code installation, download `autodq-adql-0.3.18.vsix` from the
matching GitHub release and install it with `--force`.
