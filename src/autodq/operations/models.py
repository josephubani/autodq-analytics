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
class OperationalColumnMap:
    entity: str | None = None
    time: str | None = None
    start: str | None = None
    end: str | None = None
    status: str | None = None
    stage: str | None = None
    duration: str | None = None
    value: str | None = None
    cost: str | None = None
    quantity: str | None = None
    capacity: str | None = None
    group_by: list[str] = field(default_factory=list)
    duration_unit: str = "units"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "time": self.time,
            "start": self.start,
            "end": self.end,
            "status": self.status,
            "stage": self.stage,
            "duration": self.duration,
            "value": self.value,
            "cost": self.cost,
            "quantity": self.quantity,
            "capacity": self.capacity,
            "group_by": self.group_by,
            "duration_unit": self.duration_unit,
        }


@dataclass(slots=True)
class OperationalDetection:
    dataset_type: str
    confidence: float
    is_operational: bool
    evidence: list[str]
    columns: OperationalColumnMap
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_type": self.dataset_type,
            "confidence": self.confidence,
            "is_operational": self.is_operational,
            "evidence": self.evidence,
            "columns": self.columns.to_dict(),
            "warnings": self.warnings,
        }


@dataclass(slots=True)
class OperationalKPI:
    key: str
    name: str
    value: Any
    unit: str
    status: str
    description: str
    source_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "description": self.description,
            "source_columns": self.source_columns,
        }


@dataclass(slots=True)
class OperationalTrend:
    period: str
    records: int
    average_duration: float | None = None
    failure_rate: float | None = None
    total_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "records": self.records,
            "average_duration": self.average_duration,
            "failure_rate": self.failure_rate,
            "total_value": self.total_value,
        }


@dataclass(slots=True)
class ProcessSegment:
    dimension: str
    segment: str
    records: int
    share_percent: float
    average_duration: float | None = None
    median_duration: float | None = None
    p95_duration: float | None = None
    failure_rate: float | None = None
    sla_breach_rate: float | None = None
    total_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "segment": self.segment,
            "records": self.records,
            "share_percent": self.share_percent,
            "average_duration": self.average_duration,
            "median_duration": self.median_duration,
            "p95_duration": self.p95_duration,
            "failure_rate": self.failure_rate,
            "sla_breach_rate": self.sla_breach_rate,
            "total_value": self.total_value,
        }


@dataclass(slots=True)
class OperationalBottleneck:
    dimension: str
    segment: str
    severity: str
    score: float
    records: int
    share_percent: float
    delay_ratio: float | None
    failure_rate: float | None
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "segment": self.segment,
            "severity": self.severity,
            "score": self.score,
            "records": self.records,
            "share_percent": self.share_percent,
            "delay_ratio": self.delay_ratio,
            "failure_rate": self.failure_rate,
            "evidence": self.evidence,
        }


@dataclass(slots=True)
class OperationalDriver:
    outcome: str
    feature: str
    driver_type: str
    direction: str
    strength: float
    effect: float
    segment: str | None
    records: int
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "feature": self.feature,
            "driver_type": self.driver_type,
            "direction": self.direction,
            "strength": self.strength,
            "effect": self.effect,
            "segment": self.segment,
            "records": self.records,
            "evidence": self.evidence,
        }


@dataclass(slots=True)
class OperationalReport:
    dataset_name: str
    rows_analyzed: int
    detection: OperationalDetection
    kpis: list[OperationalKPI] = field(default_factory=list)
    trends: list[OperationalTrend] = field(default_factory=list)
    process_segments: list[ProcessSegment] = field(default_factory=list)
    bottlenecks: list[OperationalBottleneck] = field(default_factory=list)
    root_causes: list[OperationalDriver] = field(default_factory=list)
    sla_target: float | None = None
    period: str = "month"
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def kpi_count(self) -> int:
        return len(self.kpis)

    @property
    def bottleneck_count(self) -> int:
        return len(self.bottlenecks)

    @property
    def driver_count(self) -> int:
        return len(self.root_causes)

    def view(self, section: str) -> "OperationalAnalysisView":
        return OperationalAnalysisView(report=self, section=section)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "rows_analyzed": self.rows_analyzed,
            "detection": self.detection.to_dict(),
            "kpi_count": self.kpi_count,
            "kpis": [item.to_dict() for item in self.kpis],
            "trends": [item.to_dict() for item in self.trends],
            "process_segments": [item.to_dict() for item in self.process_segments],
            "bottleneck_count": self.bottleneck_count,
            "bottlenecks": [item.to_dict() for item in self.bottlenecks],
            "driver_count": self.driver_count,
            "root_causes": [item.to_dict() for item in self.root_causes],
            "sla_target": self.sla_target,
            "period": self.period,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_notebook_html(self) -> str:
        return self.view("overview").to_notebook_html()

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()


@dataclass(slots=True)
class OperationalAnalysisView:
    report: OperationalReport
    section: str

    def to_dict(self) -> dict[str, Any]:
        payload = self.report.to_dict()
        section = self.section.lower()
        common = {
            "section": section,
            "dataset_name": payload["dataset_name"],
            "rows_analyzed": payload["rows_analyzed"],
            "generated_at": payload["generated_at"],
        }
        if section == "overview":
            return {
                **common,
                "detection": payload["detection"],
                "kpis": payload["kpis"][:6],
                "bottleneck_count": payload["bottleneck_count"],
                "driver_count": payload["driver_count"],
            }
        if section == "kpis":
            return {**common, "kpis": payload["kpis"]}
        if section == "process":
            return {
                **common,
                "trends": payload["trends"],
                "process_segments": payload["process_segments"],
            }
        if section == "bottlenecks":
            return {**common, "bottlenecks": payload["bottlenecks"]}
        if section == "root_causes":
            return {
                **common,
                "association_warning": (
                    "Drivers are statistical associations, not proof of causation."
                ),
                "root_causes": payload["root_causes"],
            }
        return payload

    def to_notebook_html(self) -> str:
        section = self.section.lower()
        headings = {
            "overview": "Operational Overview",
            "kpis": "Operational KPIs",
            "process": "Process Analysis",
            "bottlenecks": "Operational Bottlenecks",
            "root_causes": "Operational Root-Cause Signals",
        }
        body = {
            "overview": self._overview_html,
            "kpis": self._kpi_html,
            "process": self._process_html,
            "bottlenecks": self._bottleneck_html,
            "root_causes": self._root_cause_html,
        }.get(section, self._overview_html)()
        title = headings.get(section, headings["overview"])
        return f"""<style>{self._css()}</style>
<section class="autodq-operations">
  <header><h2>{escape(title)}</h2><p>{escape(self.report.dataset_name)} · {self.report.rows_analyzed:,} rows</p></header>
  {body}
</section>"""

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()

    def _overview_html(self) -> str:
        detection = self.report.detection
        mapping = detection.columns.to_dict()
        mapped = "".join(
            f"<tr><th>{escape(key.replace('_', ' ').title())}</th><td>{escape(_display(value))}</td></tr>"
            for key, value in mapping.items()
            if value not in (None, [], "units")
        )
        evidence = "".join(f"<li>{escape(item)}</li>" for item in detection.evidence)
        warnings = "".join(f"<li>{escape(item)}</li>" for item in detection.warnings)
        warning_block = (
            f"<details><summary>Inference notes ({len(detection.warnings)})</summary><ul>{warnings}</ul></details>"
            if warnings else ""
        )
        return f"""
<div class="op-cards">
  {self._card('Dataset type', detection.dataset_type.replace('_', ' ').title())}
  {self._card('Operational confidence', f'{detection.confidence * 100:.1f}%')}
  {self._card('KPIs calculated', self.report.kpi_count)}
  {self._card('Bottlenecks flagged', self.report.bottleneck_count)}
</div>
<div class="op-grid"><div><h3>Recognized columns</h3><table>{mapped}</table></div>
<div><h3>Why AutoDQ recognized it</h3><ul>{evidence}</ul>{warning_block}</div></div>
{self._kpi_html(limit=6)}"""

    def _kpi_html(self, limit: int | None = None) -> str:
        items = self.report.kpis[:limit] if limit else self.report.kpis
        rows = "".join(
            "<tr>"
            f"<td><strong>{escape(item.name)}</strong></td>"
            f"<td>{escape(_display(item.value))}</td>"
            f"<td>{escape(item.unit)}</td>"
            f"<td><span class=\"op-status op-{escape(item.status)}\">{escape(item.status.title())}</span></td>"
            f"<td>{escape(item.description)}</td>"
            "</tr>"
            for item in items
        )
        if not rows:
            return "<p>No operational KPIs could be calculated from the available columns.</p>"
        return f"""<table class="op-table"><thead><tr><th>KPI</th><th>Value</th><th>Unit</th><th>Status</th><th>Meaning</th></tr></thead><tbody>{rows}</tbody></table>"""

    def _process_html(self) -> str:
        segment_rows = "".join(
            "<tr>"
            f"<td>{escape(item.dimension)}</td><td><strong>{escape(item.segment)}</strong></td>"
            f"<td>{item.records:,}</td><td>{item.share_percent:.1f}%</td>"
            f"<td>{escape(_display(item.average_duration))}</td>"
            f"<td>{escape(_display(item.failure_rate))}</td>"
            f"<td>{escape(_display(item.total_value))}</td></tr>"
            for item in self.report.process_segments
        ) or '<tr><td colspan="7">No process stage or status column was available.</td></tr>'
        trend_rows = "".join(
            f"<tr><td>{escape(item.period)}</td><td>{item.records:,}</td>"
            f"<td>{escape(_display(item.average_duration))}</td>"
            f"<td>{escape(_display(item.failure_rate))}</td>"
            f"<td>{escape(_display(item.total_value))}</td></tr>"
            for item in self.report.trends
        ) or '<tr><td colspan="5">No usable operational timestamp was available.</td></tr>'
        return f"""
<h3>Stage and status flow</h3><table class="op-table"><thead><tr><th>Dimension</th><th>Segment</th><th>Records</th><th>Share</th><th>Avg duration</th><th>Failure %</th><th>Total value</th></tr></thead><tbody>{segment_rows}</tbody></table>
<details><summary>Time trend ({len(self.report.trends)} periods)</summary><table class="op-table"><thead><tr><th>Period</th><th>Records</th><th>Avg duration</th><th>Failure %</th><th>Total value</th></tr></thead><tbody>{trend_rows}</tbody></table></details>"""

    def _bottleneck_html(self) -> str:
        rows = "".join(
            "<tr>"
            f"<td><span class=\"op-status op-{escape(item.severity)}\">{escape(item.severity.title())}</span></td>"
            f"<td>{escape(item.dimension)}</td><td><strong>{escape(item.segment)}</strong></td>"
            f"<td>{item.score:.1f}</td><td>{item.records:,}</td>"
            f"<td>{item.share_percent:.1f}%</td><td>{escape(_display(item.delay_ratio))}</td>"
            f"<td>{escape(item.evidence)}</td></tr>"
            for item in self.report.bottlenecks
        )
        if not rows:
            return "<p>No material bottlenecks were detected with the available evidence.</p>"
        return f"""<table class="op-table"><thead><tr><th>Severity</th><th>Dimension</th><th>Segment</th><th>Score</th><th>Records</th><th>Share</th><th>Delay ratio</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table>"""

    def _root_cause_html(self) -> str:
        rows = "".join(
            "<tr>"
            f"<td>{escape(item.outcome)}</td><td><strong>{escape(item.feature)}</strong></td>"
            f"<td>{escape(item.driver_type.replace('_', ' '))}</td>"
            f"<td>{escape(item.segment or '—')}</td><td>{escape(item.direction)}</td>"
            f"<td>{item.strength:.3f}</td><td>{escape(item.evidence)}</td></tr>"
            for item in self.report.root_causes
        )
        if not rows:
            return "<p>No sufficiently strong operational drivers were detected.</p>"
        return f"""<p class="op-note"><strong>Interpret carefully:</strong> these are statistical associations, not proof of causation.</p><table class="op-table"><thead><tr><th>Outcome</th><th>Feature</th><th>Type</th><th>Segment</th><th>Direction</th><th>Strength</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table>"""

    @staticmethod
    def _card(label: str, value: Any) -> str:
        return f'<div class="op-card"><span>{escape(label)}</span><strong>{escape(_display(value))}</strong></div>'

    @staticmethod
    def _css() -> str:
        return """
.autodq-operations{color:var(--vscode-foreground,#172033);font-family:var(--vscode-font-family,ui-sans-serif,system-ui);line-height:1.45}
.autodq-operations header h2{font-size:19px;margin:5px 0 2px}.autodq-operations header p{color:var(--vscode-descriptionForeground,#64748b);margin:0 0 12px}
.op-cards{display:grid;gap:9px;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));margin:12px 0}.op-card{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:8px;padding:10px}.op-card span{color:var(--vscode-descriptionForeground,#64748b);display:block;font-size:11px;text-transform:uppercase}.op-card strong{display:block;font-size:18px;margin-top:3px}
.op-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.op-grid h3,.autodq-operations h3{font-size:14px;margin:14px 0 6px}.op-table,.op-grid table{border-collapse:collapse;font-size:12px;width:100%}.op-table th,.op-table td,.op-grid th,.op-grid td{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:7px 8px;text-align:left;vertical-align:top}.op-table th,.op-grid th{background:var(--vscode-editor-background,#f6f8fb)}
.op-status{border-radius:999px;display:inline-block;font-size:10px;font-weight:700;padding:2px 7px}.op-good{background:var(--vscode-testing-iconPassed,#166534);color:#fff}.op-warning,.op-medium{background:var(--vscode-editorWarning-foreground,#92400e);color:#fff}.op-critical,.op-high{background:var(--vscode-testing-iconFailed,#991b1b);color:#fff}.op-neutral,.op-low{border:1px solid var(--vscode-panel-border,#d9e2ef)}.op-note{background:var(--vscode-textBlockQuote-background,#eef3fa);border-left:3px solid var(--vscode-textLink-foreground,#2563eb);padding:9px 11px}.autodq-operations details{border-top:1px solid var(--vscode-panel-border,#d9e2ef);margin-top:10px;padding-top:8px}.autodq-operations summary{cursor:pointer;font-weight:600}
"""
