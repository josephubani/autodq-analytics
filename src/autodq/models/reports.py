from dataclasses import dataclass, field

from autodq.models.issues import DataIssue


@dataclass
class DiagnosisReport:
    issues: list[DataIssue] = field(default_factory=list)
    quality_score: float | None = None
    summary: str | None = None
    raw_details: dict = field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def has_issues(self) -> bool:
        return self.issue_count > 0

    def to_dict(self) -> dict:
        return {
            "issue_count": self.issue_count,
            "quality_score": self.quality_score,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
            "raw_details": self.raw_details,
        }

    def to_markdown(self) -> str:
        lines = [
            "# AutoDQ Data Quality Diagnosis",
            "",
            f"**Quality Score:** {self.quality_score if self.quality_score is not None else 'N/A'}",
            "",
            f"**Issues Found:** {self.issue_count}",
            "",
        ]

        if self.summary:
            lines.extend([self.summary, ""])

        for issue in self.issues:
            lines.append(f"## {issue.issue_type.replace('_', ' ').title()}")
            lines.append(f"**Severity:** {issue.severity}")
            lines.append(f"**Message:** {issue.message}")

            if issue.affected_columns:
                lines.append(f"**Affected Columns:** {', '.join(issue.affected_columns)}")

            if issue.recommendation:
                lines.append(f"**Recommendation:** {issue.recommendation}")

            if issue.confidence is not None:
                lines.append(f"**Confidence:** {round(issue.confidence * 100, 2)}%")

            lines.append("")

        return "\n".join(lines)