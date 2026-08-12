from dataclasses import dataclass, field
from datetime import datetime
import html
import json
from typing import Any


@dataclass(slots=True)
class MLReadinessIssue:
    issue_type: str
    severity: str
    message: str
    recommendation: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class MLReadinessComponent:
    """One transparent contribution to the overall readiness score."""

    key: str
    name: str
    score: float
    max_score: float
    status: str
    summary: str
    deductions: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    recommendation: str | None = None
    assessed: bool = True

    @property
    def deduction(self) -> float | None:
        if not self.assessed:
            return None

        return round(max(0.0, self.max_score - self.score), 2)

    @property
    def percentage(self) -> float | None:
        if not self.assessed or self.max_score <= 0:
            return None

        return round(self.score / self.max_score * 100, 2)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "score": self.score if self.assessed else None,
            "max_score": self.max_score,
            "weight_percent": self.max_score,
            "percentage": self.percentage,
            "deduction": self.deduction,
            "status": self.status,
            "assessed": self.assessed,
            "summary": self.summary,
            "deductions": self.deductions,
            "metrics": self.metrics,
            "recommendation": self.recommendation,
        }


@dataclass(slots=True)
class MLReadinessReport:
    score: float
    target: str | None
    target_type: str
    recommended_task: str
    recommended_models: list[str]
    issues: list[MLReadinessIssue] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    components: list[MLReadinessComponent] = field(default_factory=list)
    earned_points: float = 0.0
    assessed_points: float = 0.0
    total_points: float = 100.0
    assessment_coverage: float = 0.0
    score_formula: str = "earned_points / assessed_points * 100"
    reference_name: str | None = None
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def assessed_component_count(self) -> int:
        return sum(1 for component in self.components if component.assessed)

    @property
    def readiness_level(self) -> str:
        if self.score >= 90:
            return "excellent"
        if self.score >= 75:
            return "good"
        if self.score >= 60:
            return "needs_work"
        return "not_ready"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "target": self.target,
            "target_type": self.target_type,
            "recommended_task": self.recommended_task,
            "recommended_models": self.recommended_models,
            "issue_count": self.issue_count,
            "readiness_level": self.readiness_level,
            "score_formula": self.score_formula,
            "earned_points": self.earned_points,
            "assessed_points": self.assessed_points,
            "total_points": self.total_points,
            "assessment_coverage": self.assessment_coverage,
            "component_count": self.component_count,
            "assessed_component_count": self.assessed_component_count,
            "reference_name": self.reference_name,
            "components": [component.to_dict() for component in self.components],
            "component_scores": {
                component.key: (
                    component.score if component.assessed else None
                )
                for component in self.components
            },
            "strengths": self.strengths,
            "issues": [issue.to_dict() for issue in self.issues],
            "generated_at": self.generated_at.isoformat(),
        }

    def to_notebook_html(self) -> str:
        """Render a theme-aware, self-explaining readiness scorecard."""
        rows = []
        details = []

        for component in self.components:
            if component.assessed:
                points = f"{component.score:.2f} / {component.max_score:.0f}"
                deduction = f"-{component.deduction:.2f}"
            else:
                points = f"Not assessed / {component.max_score:.0f}"
                deduction = "—"

            rows.append(
                "<tr>"
                f"<td><strong>{html.escape(component.name)}</strong></td>"
                f"<td>{html.escape(points)}</td>"
                f"<td><span class=\"autodq-readiness-status autodq-readiness-status--{html.escape(component.status)}\">{html.escape(component.status.replace('_', ' ').title())}</span></td>"
                f"<td>{html.escape(deduction)}</td>"
                f"<td>{html.escape(component.summary)}</td>"
                "</tr>"
            )

            metric_rows = "".join(
                "<tr>"
                f"<th>{html.escape(str(key).replace('_', ' ').title())}</th>"
                f"<td>{html.escape(self._display_value(value))}</td>"
                "</tr>"
                for key, value in component.metrics.items()
            )
            deductions = "".join(
                f"<li>{html.escape(item)}</li>" for item in component.deductions
            ) or "<li>No points deducted.</li>"
            recommendation = (
                "<p><strong>Recommendation:</strong> "
                f"{html.escape(component.recommendation)}</p>"
                if component.recommendation
                else ""
            )
            details.append(
                "<details class=\"autodq-readiness-detail\">"
                f"<summary>{html.escape(component.name)} calculation</summary>"
                f"<p>{html.escape(component.summary)}</p>"
                f"<table>{metric_rows}</table>"
                f"<ul>{deductions}</ul>{recommendation}"
                "</details>"
            )

        reference = self.reference_name or "Not supplied"
        formula = (
            f"{self.earned_points:.2f} earned points / "
            f"{self.assessed_points:.2f} assessed points × 100 = "
            f"{self.score:.2f}"
        )
        return f"""<style>
.autodq-readiness{{color:var(--vscode-foreground,#172033);font-family:var(--vscode-font-family,ui-sans-serif,system-ui);line-height:1.45}}
.autodq-readiness h2{{font-size:18px;margin:8px 0 2px}}
.autodq-readiness-muted{{color:var(--vscode-descriptionForeground,#64748b);font-size:12px}}
.autodq-readiness-metrics{{display:grid;gap:9px;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));margin:14px 0}}
.autodq-readiness-metric{{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:8px;padding:10px 12px}}
.autodq-readiness-metric span{{color:var(--vscode-descriptionForeground,#64748b);display:block;font-size:11px;text-transform:uppercase}}
.autodq-readiness-metric strong{{display:block;font-size:19px;margin-top:3px}}
.autodq-readiness-formula{{background:var(--vscode-textBlockQuote-background,#eef3fa);border-left:3px solid var(--vscode-textLink-foreground,#2563eb);padding:9px 11px}}
.autodq-readiness-table{{border-collapse:collapse;font-size:12px;margin-top:12px;width:100%}}
.autodq-readiness-table th,.autodq-readiness-table td{{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:7px 9px;text-align:left;vertical-align:top}}
.autodq-readiness-table th{{background:var(--vscode-editor-background,#f6f8fb)}}
.autodq-readiness-status{{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:999px;display:inline-block;font-size:10px;font-weight:700;padding:2px 7px}}
.autodq-readiness-status--excellent,.autodq-readiness-status--good{{background:var(--vscode-testing-iconPassed,#166534);color:#fff}}
.autodq-readiness-status--warning{{background:var(--vscode-editorWarning-foreground,#92400e);color:#fff}}
.autodq-readiness-status--high_risk{{background:var(--vscode-testing-iconFailed,#991b1b);color:#fff}}
.autodq-readiness-status--not_assessed{{color:var(--vscode-descriptionForeground,#64748b)}}
.autodq-readiness-detail{{border-top:1px solid var(--vscode-panel-border,#d9e2ef);margin-top:8px;padding-top:8px}}
.autodq-readiness-detail summary{{cursor:pointer;font-weight:600}}
.autodq-readiness-detail table{{border-collapse:collapse;font-size:12px;width:100%}}
.autodq-readiness-detail th,.autodq-readiness-detail td{{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:5px 7px;text-align:left}}
.autodq-readiness-detail th{{color:var(--vscode-descriptionForeground,#64748b);width:190px}}
</style>
<section class="autodq-readiness">
  <h2>Machine Learning Readiness</h2>
  <p class="autodq-readiness-muted">Transparent weighted score; unassessed components are excluded instead of receiving assumed credit.</p>
  <div class="autodq-readiness-metrics">
    <div class="autodq-readiness-metric"><span>Overall score</span><strong>{self.score:.2f}/100</strong></div>
    <div class="autodq-readiness-metric"><span>Readiness level</span><strong>{html.escape(self.readiness_level.replace('_', ' ').title())}</strong></div>
    <div class="autodq-readiness-metric"><span>Assessment coverage</span><strong>{self.assessment_coverage:.1f}%</strong></div>
    <div class="autodq-readiness-metric"><span>Stability reference</span><strong>{html.escape(reference)}</strong></div>
  </div>
  <p class="autodq-readiness-formula"><strong>Calculation:</strong> {html.escape(formula)}</p>
  <table class="autodq-readiness-table">
    <thead><tr><th>Component</th><th>Points</th><th>Status</th><th>Deduction</th><th>Calculation summary</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <div>{''.join(details)}</div>
</section>"""

    def to_html(self) -> str:
        return self.to_notebook_html()

    def _repr_html_(self) -> str:
        return self.to_notebook_html()

    @staticmethod
    def _display_value(value: Any) -> str:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value)
