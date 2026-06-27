from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AutoDQReport:

    dataset: str

    profile: dict | None

    statistics: object | None

    interpretations: object | None

    diagnosis: object | None

    recommendations: list | None

    decision_plan: object | None

    preview: object | None

    cleaning: object | None

    validation: object | None

    session: object | None

    generated_at: datetime = datetime.now()