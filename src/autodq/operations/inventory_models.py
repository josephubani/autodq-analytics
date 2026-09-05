from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from typing import Any


def _display(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


@dataclass(slots=True)
class InventoryColumnMap:
    item: str | None = None
    location: str | None = None
    echelon: str | None = None
    parent_location: str | None = None
    time: str | None = None
    on_hand: str | None = None
    on_order: str | None = None
    backorder: str | None = None
    demand: str | None = None
    lead_time: str | None = None
    safety_stock: str | None = None
    unit_cost: str | None = None
    capacity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item": self.item,
            "location": self.location,
            "echelon": self.echelon,
            "parent_location": self.parent_location,
            "time": self.time,
            "on_hand": self.on_hand,
            "on_order": self.on_order,
            "backorder": self.backorder,
            "demand": self.demand,
            "lead_time": self.lead_time,
            "safety_stock": self.safety_stock,
            "unit_cost": self.unit_cost,
            "capacity": self.capacity,
        }


@dataclass(slots=True)
class InventoryDetection:
    dataset_type: str
    confidence: float
    is_inventory: bool
    is_multi_echelon: bool
    columns: InventoryColumnMap
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_type": self.dataset_type,
            "confidence": self.confidence,
            "is_inventory": self.is_inventory,
            "is_multi_echelon": self.is_multi_echelon,
            "columns": self.columns.to_dict(),
            "evidence": list(self.evidence),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class InventoryKPI:
    key: str
    name: str
    value: Any
    unit: str
    status: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "description": self.description,
        }


@dataclass(slots=True)
class InventoryNode:
    item: str
    location: str
    echelon: str
    parent_location: str | None
    on_hand: float
    on_order: float
    backorders: float
    inventory_position: float
    daily_demand: float
    lead_time_days: float
    safety_stock: float
    reorder_point: float
    target_stock: float
    coverage_days: float | None
    shortage_units: float
    excess_units: float
    stockout_risk_percent: float
    unit_cost: float | None
    inventory_value: float | None
    capacity: float | None
    capacity_utilization: float | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }


@dataclass(slots=True)
class EchelonSummary:
    echelon: str
    node_count: int
    item_count: int
    location_count: int
    on_hand: float
    inventory_position: float
    daily_demand: float
    shortage_units: float
    excess_units: float
    at_risk_nodes: int
    inventory_value: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }


@dataclass(slots=True)
class InventoryRecommendation:
    action: str
    item: str
    source_location: str | None
    target_location: str
    source_echelon: str | None
    target_echelon: str
    quantity: float
    priority: str
    expected_shortage_reduction: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }


@dataclass(slots=True)
class InventoryReport:
    dataset_name: str
    rows_analyzed: int
    snapshot_rows: int
    detection: InventoryDetection
    service_level: float
    horizon_days: int
    kpis: list[InventoryKPI] = field(default_factory=list)
    nodes: list[InventoryNode] = field(default_factory=list)
    echelons: list[EchelonSummary] = field(default_factory=list)
    recommendations: list[InventoryRecommendation] = field(default_factory=list)
    snapshot_at: str | None = None
    top: int = 10
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def at_risk_count(self) -> int:
        return sum(item.status in {"critical", "warning"} for item in self.nodes)

    @property
    def transfer_count(self) -> int:
        return sum(item.action == "transfer" for item in self.recommendations)

    @property
    def replenishment_count(self) -> int:
        return sum(item.action == "replenish" for item in self.recommendations)

    def view(self, section: str) -> "InventoryAnalysisView":
        return InventoryAnalysisView(report=self, section=section)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "rows_analyzed": self.rows_analyzed,
            "snapshot_rows": self.snapshot_rows,
            "snapshot_at": self.snapshot_at,
            "detection": self.detection.to_dict(),
            "service_level": self.service_level,
            "horizon_days": self.horizon_days,
            "node_count": self.node_count,
            "at_risk_count": self.at_risk_count,
            "transfer_count": self.transfer_count,
            "replenishment_count": self.replenishment_count,
            "kpis": [item.to_dict() for item in self.kpis],
            "nodes": [item.to_dict() for item in self.nodes],
            "echelons": [item.to_dict() for item in self.echelons],
            "recommendations": [
                item.to_dict() for item in self.recommendations
            ],
            "generated_at": self.generated_at.isoformat(),
        }

    def to_notebook_html(self) -> str:
        return self.view("overview").to_notebook_html()

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()


@dataclass(slots=True)
class InventoryAnalysisView:
    report: InventoryReport
    section: str

    def to_dict(self) -> dict[str, Any]:
        payload = self.report.to_dict()
        common = {
            "dataset_name": payload["dataset_name"],
            "detection": payload["detection"],
            "service_level": payload["service_level"],
            "horizon_days": payload["horizon_days"],
            "snapshot_at": payload["snapshot_at"],
        }
        section = self.section.lower()
        if section == "overview":
            return {
                **common,
                "kpis": payload["kpis"],
                "node_count": payload["node_count"],
                "at_risk_count": payload["at_risk_count"],
            }
        if section == "network":
            return {
                **common,
                "echelons": payload["echelons"],
                "nodes": payload["nodes"],
            }
        if section == "rebalancing":
            return {
                **common,
                "recommendations": payload["recommendations"],
                "transfer_count": payload["transfer_count"],
                "replenishment_count": payload["replenishment_count"],
            }
        return payload

    def to_notebook_html(self) -> str:
        section = self.section.lower()
        title = {
            "overview": "Multi-Echelon Inventory Overview",
            "network": "Inventory Network",
            "rebalancing": "Inventory Rebalancing Plan",
        }.get(section, "Multi-Echelon Inventory")
        body = {
            "overview": self._overview_html,
            "network": self._network_html,
            "rebalancing": self._rebalancing_html,
        }.get(section, self._overview_html)()
        return f"""<style>{self._css()}</style>
<section class="autodq-inventory">
  <header><h2>{escape(title)}</h2><p>{escape(self.report.dataset_name)} · {self.report.rows_analyzed:,} source rows</p></header>
  {body}
</section>"""

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()

    def _overview_html(self) -> str:
        detection = self.report.detection
        mapping = "".join(
            f"<tr><th>{escape(key.replace('_', ' ').title())}</th><td>{escape(_display(value))}</td></tr>"
            for key, value in detection.columns.to_dict().items()
            if value is not None
        )
        warnings = "".join(
            f"<li>{escape(item)}</li>" for item in detection.warnings
        )
        warning_block = (
            f"<details><summary>Inventory notes ({len(detection.warnings)})</summary><ul>{warnings}</ul></details>"
            if warnings else ""
        )
        cards = "".join(
            self._card(item.name, f"{_display(item.value)} {item.unit}".strip(), item.status)
            for item in self.report.kpis[:8]
        )
        return f"""
<div class="inv-cards">
  {self._card('Inventory confidence', f'{detection.confidence * 100:.1f}%')}
  {self._card('Network nodes', self.report.node_count)}
  {self._card('At-risk nodes', self.report.at_risk_count, 'critical' if self.report.at_risk_count else 'good')}
  {self._card('Planning horizon', f'{self.report.horizon_days} days')}
</div>
<div class="inv-grid"><div><h3>Recognized inventory roles</h3><table>{mapping}</table></div>
<div><h3>Network assessment</h3><p>{escape(detection.dataset_type.replace('_', ' ').title())}</p>{warning_block}</div></div>
<h3>Inventory KPIs</h3><div class="inv-cards">{cards}</div>"""

    def _network_html(self) -> str:
        echelon_rows = "".join(
            "<tr>"
            f"<td><strong>{escape(item.echelon)}</strong></td><td>{item.node_count:,}</td>"
            f"<td>{item.location_count:,}</td><td>{_display(item.on_hand)}</td>"
            f"<td>{_display(item.daily_demand)}</td><td>{_display(item.shortage_units)}</td>"
            f"<td>{_display(item.excess_units)}</td><td>{item.at_risk_nodes:,}</td></tr>"
            for item in self.report.echelons
        ) or '<tr><td colspan="8">No inventory network could be calculated.</td></tr>'
        node_rows = "".join(
            "<tr>"
            f"<td><span class=\"inv-status inv-{escape(item.status)}\">{escape(item.status.title())}</span></td>"
            f"<td>{escape(item.item)}</td><td>{escape(item.location)}</td>"
            f"<td>{escape(item.echelon)}</td><td>{_display(item.inventory_position)}</td>"
            f"<td>{_display(item.daily_demand)}</td><td>{_display(item.coverage_days)}</td>"
            f"<td>{_display(item.shortage_units)}</td><td>{_display(item.excess_units)}</td>"
            f"<td>{item.stockout_risk_percent:.1f}%</td></tr>"
            for item in self.report.nodes[: max(self.report.top, 10)]
        ) or '<tr><td colspan="10">Required inventory columns were not available.</td></tr>'
        return f"""
<h3>Echelon rollup</h3><table class="inv-table"><thead><tr><th>Echelon</th><th>Nodes</th><th>Locations</th><th>On hand</th><th>Daily demand</th><th>Shortage</th><th>Excess</th><th>At risk</th></tr></thead><tbody>{echelon_rows}</tbody></table>
<h3>Priority inventory nodes</h3><table class="inv-table"><thead><tr><th>Status</th><th>Item</th><th>Location</th><th>Echelon</th><th>Position</th><th>Daily demand</th><th>Coverage days</th><th>Shortage</th><th>Excess</th><th>Stockout risk</th></tr></thead><tbody>{node_rows}</tbody></table>"""

    def _rebalancing_html(self) -> str:
        rows = "".join(
            "<tr>"
            f"<td><span class=\"inv-status inv-{escape(item.priority)}\">{escape(item.priority.title())}</span></td>"
            f"<td>{escape(item.action.title())}</td><td>{escape(item.item)}</td>"
            f"<td>{escape(item.source_location or 'External supply')}</td>"
            f"<td>{escape(item.target_location)}</td><td>{_display(item.quantity)}</td>"
            f"<td>{_display(item.expected_shortage_reduction)}</td>"
            f"<td>{escape(item.rationale)}</td></tr>"
            for item in self.report.recommendations
        )
        if not rows:
            return "<p>No transfer or replenishment action is currently required, or the necessary inventory roles were unavailable.</p>"
        return f"""<p class="inv-note">Transfers never mix SKUs and never allocate more than a donor's calculated excess. Validate transport, shelf-life, and policy constraints before execution.</p>
<table class="inv-table"><thead><tr><th>Priority</th><th>Action</th><th>Item</th><th>From</th><th>To</th><th>Quantity</th><th>Shortage reduced</th><th>Rationale</th></tr></thead><tbody>{rows}</tbody></table>"""

    @staticmethod
    def _card(label: str, value: Any, status: str = "neutral") -> str:
        return f'<div class="inv-card inv-card-{escape(status)}"><span>{escape(label)}</span><strong>{escape(_display(value))}</strong></div>'

    @staticmethod
    def _css() -> str:
        return """
.autodq-inventory{color:var(--vscode-foreground,#172033);font-family:var(--vscode-font-family,ui-sans-serif,system-ui);line-height:1.45}.autodq-inventory header h2{font-size:19px;margin:5px 0 2px}.autodq-inventory header p{color:var(--vscode-descriptionForeground,#64748b);margin:0 0 12px}
.inv-cards{display:grid;gap:9px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:12px 0}.inv-card{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:8px;padding:10px}.inv-card span{color:var(--vscode-descriptionForeground,#64748b);display:block;font-size:11px;text-transform:uppercase}.inv-card strong{display:block;font-size:17px;margin-top:3px}.inv-card-critical,.inv-card-high{border-left:4px solid var(--vscode-testing-iconFailed,#991b1b)}.inv-card-warning,.inv-card-medium{border-left:4px solid var(--vscode-editorWarning-foreground,#92400e)}.inv-card-good{border-left:4px solid var(--vscode-testing-iconPassed,#166534)}
.inv-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.autodq-inventory h3{font-size:14px;margin:14px 0 6px}.inv-table,.inv-grid table{border-collapse:collapse;font-size:12px;width:100%}.inv-table th,.inv-table td,.inv-grid th,.inv-grid td{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:7px 8px;text-align:left;vertical-align:top}.inv-table th,.inv-grid th{background:var(--vscode-editor-background,#f6f8fb)}
.inv-status{border-radius:999px;display:inline-block;font-size:10px;font-weight:700;padding:2px 7px}.inv-critical,.inv-high{background:var(--vscode-testing-iconFailed,#991b1b);color:#fff}.inv-warning,.inv-medium{background:var(--vscode-editorWarning-foreground,#92400e);color:#fff}.inv-balanced,.inv-good{background:var(--vscode-testing-iconPassed,#166534);color:#fff}.inv-excess,.inv-low,.inv-neutral{border:1px solid var(--vscode-panel-border,#d9e2ef)}.inv-note{background:var(--vscode-textBlockQuote-background,#eef3fa);border-left:3px solid var(--vscode-textLink-foreground,#2563eb);padding:9px 11px}.autodq-inventory details{border-top:1px solid var(--vscode-panel-border,#d9e2ef);margin-top:10px;padding-top:8px}.autodq-inventory summary{cursor:pointer;font-weight:600}
"""
