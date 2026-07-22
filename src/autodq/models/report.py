from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class AutoDQReport:
    """
    Complete AutoDQ report object used by report exporters.
    """

    dataset: str
    session: object

    profile: dict | None = None
    statistics: object | None = None
    interpretations: object | None = None
    diagnosis: object | None = None
    recommendations: list | None = None
    decision_plan: object | None = None
    preview: object | None = None
    cleaning: object | None = None
    cleaning_review: object | None = None
    domain_validation: object | None = None
    automation: object | None = None
    dashboard: object | None = None
    validation: object | None = None

    visualizations: object | None = None
    rendered_visualizations: list | None = None

    model: object | None = None
    prediction: object | None = None
    explainability: object | None = None
    blue: object | None = None

    generated_at: datetime = field(default_factory=datetime.now)
