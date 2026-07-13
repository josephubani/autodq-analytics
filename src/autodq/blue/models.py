from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class BLUEAssumptionResult:
    """
    Result for one linear-model assumption test.
    """

    assumption: str
    status: str
    statistic: float | None = None
    p_value: float | None = None
    threshold: float | None = None
    interpretation: str = ""
    recommendation: str = ""
    severity: str = "low"
    confidence: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "assumption": self.assumption,
            "status": self.status,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "threshold": self.threshold,
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
            "severity": self.severity,
            "confidence": self.confidence,
            "details": self.details,
        }


@dataclass(slots=True)
class VIFResult:
    """
    Variance Inflation Factor result for one feature.
    """

    feature: str
    vif: float
    severity: str
    interpretation: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "vif": self.vif,
            "severity": self.severity,
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
        }


@dataclass(slots=True)
class BLUEReport:
    """
    Complete BLUE diagnostic report.
    """

    target: str
    rows_analyzed: int
    features_analyzed: int
    overall_status: str
    suitability_score: float
    assumptions: list[BLUEAssumptionResult] = field(default_factory=list)
    vif_results: list[VIFResult] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def passed_assumptions(self) -> int:
        return sum(
            result.status == "passed"
            for result in self.assumptions
        )

    @property
    def failed_assumptions(self) -> int:
        return sum(
            result.status == "failed"
            for result in self.assumptions
        )

    @property
    def warning_assumptions(self) -> int:
        return sum(
            result.status == "warning"
            for result in self.assumptions
        )

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "rows_analyzed": self.rows_analyzed,
            "features_analyzed": self.features_analyzed,
            "overall_status": self.overall_status,
            "suitability_score": self.suitability_score,
            "passed_assumptions": self.passed_assumptions,
            "failed_assumptions": self.failed_assumptions,
            "warning_assumptions": self.warning_assumptions,
            "assumptions": [
                result.to_dict()
                for result in self.assumptions
            ],
            "vif_results": [
                result.to_dict()
                for result in self.vif_results
            ],
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "generated_at": self.generated_at.isoformat(),
        }