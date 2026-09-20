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
class PrescriptiveConstraint:
    budget: float | None = None
    max_actions: int = 5
    min_confidence: float = 0.5
    max_risk: str = "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget": self.budget,
            "max_actions": self.max_actions,
            "min_confidence": self.min_confidence,
            "max_risk": self.max_risk,
        }


@dataclass(slots=True)
class PrescriptiveAction:
    action_id: str
    title: str
    action_type: str
    objective: str
    source: str
    target: str
    description: str
    rationale: str
    expected_impact: float
    impact_unit: str
    impact_score: float
    estimated_cost: float
    cost_unit: str
    cost_basis: str
    priority: str
    risk: str
    confidence: float
    status: str = "proposed"
    optimization_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "title": self.title,
            "action_type": self.action_type,
            "objective": self.objective,
            "source": self.source,
            "target": self.target,
            "description": self.description,
            "rationale": self.rationale,
            "expected_impact": self.expected_impact,
            "impact_unit": self.impact_unit,
            "impact_score": self.impact_score,
            "estimated_cost": self.estimated_cost,
            "cost_unit": self.cost_unit,
            "cost_basis": self.cost_basis,
            "priority": self.priority,
            "risk": self.risk,
            "confidence": self.confidence,
            "status": self.status,
            "optimization_score": self.optimization_score,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class WhatIfScenario:
    scenario_id: str
    name: str
    changes: dict[str, float]
    baseline_metrics: dict[str, float]
    projected_metrics: dict[str, float]
    metric_deltas: dict[str, float]
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "changes": dict(self.changes),
            "baseline_metrics": dict(self.baseline_metrics),
            "projected_metrics": dict(self.projected_metrics),
            "metric_deltas": dict(self.metric_deltas),
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(slots=True)
class OptimizationSummary:
    objective: str
    method: str
    status: str
    candidate_count: int
    eligible_count: int
    selected_action_ids: list[str]
    total_estimated_cost: float
    total_impact_score: float
    constraints: PrescriptiveConstraint
    feasible: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "method": self.method,
            "status": self.status,
            "candidate_count": self.candidate_count,
            "eligible_count": self.eligible_count,
            "selected_action_ids": list(self.selected_action_ids),
            "selected_count": len(self.selected_action_ids),
            "total_estimated_cost": self.total_estimated_cost,
            "total_impact_score": self.total_impact_score,
            "constraints": self.constraints.to_dict(),
            "feasible": self.feasible,
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class PrescriptionAuditEntry:
    event: str
    action_id: str | None
    previous_status: str | None
    new_status: str | None
    actor: str
    reason: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "action_id": self.action_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "actor": self.actor,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(slots=True)
class PrescriptivePlan:
    dataset_name: str
    objective: str
    actions: list[PrescriptiveAction] = field(default_factory=list)
    scenarios: list[WhatIfScenario] = field(default_factory=list)
    optimization: OptimizationSummary | None = None
    audit_trail: list[PrescriptionAuditEntry] = field(default_factory=list)
    source_reports: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def selected_actions(self) -> list[PrescriptiveAction]:
        return [
            item for item in self.actions
            if item.status in {"selected", "approved", "executed"}
        ]

    @property
    def approved_actions(self) -> list[PrescriptiveAction]:
        return [
            item for item in self.actions
            if item.status in {"approved", "executed"}
        ]

    def get_action(self, action_id: str) -> PrescriptiveAction:
        normalized = str(action_id).strip().casefold()
        for action in self.actions:
            if action.action_id.casefold() == normalized:
                return action
        raise KeyError(f"Prescription action was not found: {action_id}")

    def view(self, section: str = "overview") -> "PrescriptiveAnalysisView":
        return PrescriptiveAnalysisView(plan=self, section=section)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "objective": self.objective,
            "source_reports": list(self.source_reports),
            "action_count": len(self.actions),
            "selected_count": len(self.selected_actions),
            "approved_count": len(self.approved_actions),
            "scenario_count": len(self.scenarios),
            "actions": [item.to_dict() for item in self.actions],
            "scenarios": [item.to_dict() for item in self.scenarios],
            "optimization": (
                self.optimization.to_dict() if self.optimization else None
            ),
            "audit_trail": [item.to_dict() for item in self.audit_trail],
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat(),
        }

    def to_notebook_html(self) -> str:
        return self.view("overview").to_notebook_html()

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()


@dataclass(slots=True)
class PrescriptiveAnalysisView:
    plan: PrescriptivePlan
    section: str = "overview"

    def to_dict(self) -> dict[str, Any]:
        payload = self.plan.to_dict()
        section = self.section.lower()
        common = {
            "dataset_name": payload["dataset_name"],
            "objective": payload["objective"],
            "generated_at": payload["generated_at"],
        }
        if section == "overview":
            return {
                **common,
                "source_reports": payload["source_reports"],
                "action_count": payload["action_count"],
                "selected_count": payload["selected_count"],
                "approved_count": payload["approved_count"],
                "scenario_count": payload["scenario_count"],
                "optimization": payload["optimization"],
                "warnings": payload["warnings"],
            }
        if section == "actions":
            return {**common, "actions": payload["actions"]}
        if section == "scenarios":
            return {**common, "scenarios": payload["scenarios"]}
        if section == "audit":
            return {**common, "audit_trail": payload["audit_trail"]}
        return payload

    def to_notebook_html(self) -> str:
        section = self.section.lower()
        titles = {
            "overview": "Prescriptive Analytics Plan",
            "actions": "Prioritized Actions",
            "scenarios": "What-if Scenarios",
            "audit": "Prescription Audit Trail",
        }
        body = {
            "overview": self._overview_html,
            "actions": self._actions_html,
            "scenarios": self._scenarios_html,
            "audit": self._audit_html,
        }.get(section, self._overview_html)()
        return f"""<style>{self._css()}</style>
<section class="autodq-prescriptive">
  <header><h2>{escape(titles.get(section, titles['overview']))}</h2>
  <p>{escape(self.plan.dataset_name)} · Objective: {escape(self.plan.objective.replace('_', ' '))}</p></header>
  {body}
</section>"""

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()

    def _overview_html(self) -> str:
        optimization = self.plan.optimization
        warning_items = "".join(
            f"<li>{escape(item)}</li>" for item in self.plan.warnings
        )
        warnings = (
            f"<details><summary>Planning notes ({len(self.plan.warnings)})</summary><ul>{warning_items}</ul></details>"
            if warning_items else ""
        )
        optimization_note = "No optimization has been run."
        if optimization is not None:
            optimization_note = (
                f"{optimization.method} selected "
                f"{len(optimization.selected_action_ids)} of "
                f"{optimization.eligible_count} eligible actions; "
                f"impact score {_display(optimization.total_impact_score)}."
            )
        return f"""
<div class="rx-cards">
  {self._card('Candidate actions', len(self.plan.actions))}
  {self._card('Selected actions', len(self.plan.selected_actions), 'selected')}
  {self._card('Approved actions', len(self.plan.approved_actions), 'approved')}
  {self._card('What-if scenarios', len(self.plan.scenarios))}
</div>
<p class="rx-note">{escape(optimization_note)}</p>
{warnings}
{self._actions_html(selected_only=True)}"""

    def _actions_html(self, selected_only: bool = False) -> str:
        actions = self.plan.selected_actions if selected_only else self.plan.actions
        rows = "".join(
            "<tr>"
            f"<td><strong>{escape(item.action_id)}</strong></td>"
            f"<td><span class=\"rx-status rx-{escape(item.status)}\">{escape(item.status.title())}</span></td>"
            f"<td>{escape(item.title)}</td><td>{escape(item.source)}</td>"
            f"<td>{_display(item.expected_impact)} {escape(item.impact_unit)}</td>"
            f"<td>{_display(item.estimated_cost)} {escape(item.cost_unit)}</td>"
            f"<td>{item.confidence * 100:.1f}%</td>"
            f"<td>{escape(item.risk.title())}</td>"
            f"<td>{escape(item.rationale)}</td></tr>"
            for item in actions
        )
        if not rows:
            message = "No actions were selected." if selected_only else "No prescriptive actions were generated."
            return f"<p>{escape(message)}</p>"
        return f"""<table class="rx-table"><thead><tr><th>ID</th><th>Status</th><th>Action</th><th>Source</th><th>Expected impact</th><th>Estimated cost</th><th>Confidence</th><th>Risk</th><th>Why</th></tr></thead><tbody>{rows}</tbody></table>"""

    def _scenarios_html(self) -> str:
        cards = []
        for scenario in self.plan.scenarios:
            rows = "".join(
                f"<tr><td>{escape(key.replace('_', ' ').title())}</td>"
                f"<td>{_display(scenario.baseline_metrics.get(key))}</td>"
                f"<td>{_display(value)}</td>"
                f"<td>{_display(scenario.metric_deltas.get(key))}</td></tr>"
                for key, value in scenario.projected_metrics.items()
            )
            cards.append(
                f"<details open><summary>{escape(scenario.name)} ({escape(scenario.scenario_id)})</summary>"
                f"<table class=\"rx-table\"><thead><tr><th>Metric</th><th>Baseline</th><th>Projected</th><th>Delta</th></tr></thead><tbody>{rows}</tbody></table></details>"
            )
        return "".join(cards) or "<p>No what-if scenarios have been evaluated.</p>"

    def _audit_html(self) -> str:
        rows = "".join(
            "<tr>"
            f"<td>{escape(item.timestamp.isoformat(timespec='seconds'))}</td>"
            f"<td>{escape(item.event)}</td><td>{escape(item.action_id or '—')}</td>"
            f"<td>{escape(item.previous_status or '—')} → {escape(item.new_status or '—')}</td>"
            f"<td>{escape(item.actor)}</td><td>{escape(item.reason or '—')}</td></tr>"
            for item in self.plan.audit_trail
        )
        if not rows:
            return "<p>No approval or execution decisions have been recorded.</p>"
        return f"""<table class="rx-table"><thead><tr><th>Time</th><th>Event</th><th>Action</th><th>Status change</th><th>Actor</th><th>Reason</th></tr></thead><tbody>{rows}</tbody></table>"""

    @staticmethod
    def _card(label: str, value: Any, status: str = "neutral") -> str:
        return f'<div class="rx-card rx-{escape(status)}"><span>{escape(label)}</span><strong>{escape(_display(value))}</strong></div>'

    @staticmethod
    def _css() -> str:
        return """
.autodq-prescriptive{color:var(--vscode-foreground,#172033);font-family:var(--vscode-font-family,ui-sans-serif,system-ui);line-height:1.45}.autodq-prescriptive header h2{font-size:19px;margin:5px 0 2px}.autodq-prescriptive header p{color:var(--vscode-descriptionForeground,#64748b);margin:0 0 12px}.rx-cards{display:grid;gap:9px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:12px 0}.rx-card{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:8px;padding:10px}.rx-card span{color:var(--vscode-descriptionForeground,#64748b);display:block;font-size:11px;text-transform:uppercase}.rx-card strong{display:block;font-size:17px;margin-top:3px}.rx-selected{border-left:4px solid var(--vscode-textLink-foreground,#2563eb)}.rx-approved,.rx-executed{border-left:4px solid var(--vscode-testing-iconPassed,#166534)}.rx-rejected{border-left:4px solid var(--vscode-testing-iconFailed,#991b1b)}.rx-note{background:var(--vscode-textBlockQuote-background,#eef3fa);border-left:3px solid var(--vscode-textLink-foreground,#2563eb);padding:9px 11px}.rx-table{border-collapse:collapse;font-size:12px;width:100%}.rx-table th,.rx-table td{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:7px 8px;text-align:left;vertical-align:top}.rx-table th{background:var(--vscode-editor-background,#f6f8fb)}.rx-status{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:999px;display:inline-block;font-size:10px;font-weight:700;padding:2px 7px}.autodq-prescriptive details{border-top:1px solid var(--vscode-panel-border,#d9e2ef);margin-top:10px;padding-top:8px}.autodq-prescriptive summary{cursor:pointer;font-weight:600}
"""
