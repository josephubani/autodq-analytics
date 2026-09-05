# AutoDQ 0.1.24 Release Notes

AutoDQ 0.1.24 adds operational analytics and multi-echelon inventory
management through the Python API and ADQL 2.6.

## Operational analytics

AutoDQ can now infer operational structure from transaction, service,
logistics, manufacturing, healthcare, financial, and generic process data.
The new analysis includes:

- explainable throughput, cycle-time, SLA, outcome, value, cost, volume,
  capacity, and completeness KPIs;
- stage, status, and time-period process summaries;
- bottleneck ranking using delay, adverse outcomes, workload concentration,
  backlog, and SLA evidence; and
- root-cause signals reported explicitly as statistical associations rather
  than proof of causation.

Python users can call `operations()`, `operational_kpis()`,
`process_analysis()`, `bottlenecks()`, and `operational_root_causes()`.
ADQL adds `OPERATIONS`, `KPI`, `PROCESS`, `BOTTLENECKS`, and `ROOT CAUSE`.

## Multi-echelon inventory management

The new inventory engine recognizes or explicitly maps SKU, location,
echelon, parent location, snapshot time, on-hand stock, on-order stock,
backorders, daily demand, lead time, safety stock, unit cost, and capacity.

It calculates:

- network inventory position as on hand plus on order minus backorders;
- days of coverage, reorder points, planning targets, and service readiness;
- shortage, excess, stockout risk, inventory value, and capacity utilization;
- rollups for each network echelon; and
- bounded same-SKU transfer recommendations followed by residual external or
  upstream replenishment requirements.

When a timestamp is available, AutoDQ uses the latest row for each
SKU-location-echelon node. It never transfers between different SKUs or more
than a donor's calculated excess. Recommendations remain decision support;
transport cost, shelf life, lot size, routing, supplier, and policy constraints
must be validated before execution.

ADQL provides focused notebook commands:

```adql
INVENTORY SERVICE_LEVEL 95 HORIZON 30 TOP 20;
INVENTORY NETWORK SERVICE_LEVEL 95 HORIZON 30 TOP 20;
INVENTORY REBALANCE SERVICE_LEVEL 95 HORIZON 30 TOP 20;
```

Named datasets and explicit role mappings are supported. A complete runnable
example is available in `examples/inventory_network.adql` with the bundled
`datasets/sample/inventory_network.csv` sample.

## Reporting and editor support

- Notebook output includes theme-aware inventory overview, network, and
  rebalancing views.
- Console output, dashboards, HTML reports, and JSON reports include the
  latest inventory analysis.
- The VS Code grammar highlights all operational and inventory commands,
  actions, options, and policy values case-insensitively.
- Existing valid ADQL 2.x workflows remain compatible.

## Versions

- AutoDQ Python package: `0.1.24`
- ADQL language: `2.6`
- AutoDQ ADQL VS Code extension: `0.3.17`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.24
```

For manual VS Code installation, download `autodq-adql-0.3.17.vsix` from the
matching GitHub release and install it with `--force`.
