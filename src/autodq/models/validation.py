from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ValidationMetric:
    name: str
    before: float | int
    after: float | int

    @property
    def change(self):
        return self.after - self.before

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "before": self.before,
            "after": self.after,
            "change": self.change,
        }


@dataclass(slots=True)
class ValidationReport:
    missing_values: ValidationMetric
    duplicate_rows: ValidationMetric
    rows: ValidationMetric
    columns: ValidationMetric
    quality_score_before: float | None = None
    quality_score_after: float | None = None
    generated_at: datetime = datetime.now()

    @property
    def quality_score_change(self) -> float | None:
        if self.quality_score_before is None or self.quality_score_after is None:
            return None

        return round(self.quality_score_after - self.quality_score_before, 2)

    def to_dict(self) -> dict:
        return {
            "missing_values": self.missing_values.to_dict(),
            "duplicate_rows": self.duplicate_rows.to_dict(),
            "rows": self.rows.to_dict(),
            "columns": self.columns.to_dict(),
            "quality_score_before": self.quality_score_before,
            "quality_score_after": self.quality_score_after,
            "quality_score_change": self.quality_score_change,
            "generated_at": self.generated_at.isoformat(),
        }