from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class UncertaintyCalibration:
    """Inference-safe calibration data retained with a trained model."""

    problem_type: str
    method: str
    calibration_size: int
    scores: list[float] = field(default_factory=list)
    class_labels: list[Any] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def available(self) -> bool:
        if self.problem_type == "regression":
            return bool(self.scores)

        return bool(self.class_labels)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_type": self.problem_type,
            "method": self.method,
            "calibration_size": self.calibration_size,
            "scores": self.scores,
            "class_labels": self.class_labels,
            "metrics": self.metrics,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "UncertaintyCalibration | None":
        if not data:
            return None

        generated_at = datetime.now()

        if data.get("generated_at"):
            try:
                generated_at = datetime.fromisoformat(
                    str(data["generated_at"])
                )
            except ValueError:
                pass

        return cls(
            problem_type=str(data["problem_type"]),
            method=str(data["method"]),
            calibration_size=int(data.get("calibration_size", 0)),
            scores=[float(value) for value in data.get("scores", [])],
            class_labels=list(data.get("class_labels", [])),
            metrics={
                str(key): float(value)
                for key, value in data.get("metrics", {}).items()
            },
            generated_at=generated_at,
        )
