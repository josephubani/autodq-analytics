from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class AutoDQReport:
    """
    Complete AutoDQ report object used by all exporters.
    """

    # ---------- Required ----------
    dataset: str
    session: object

    # ---------- Optional Reports ----------
    profile: dict | None = None
    statistics: object | None = None
    interpretations: object | None = None
    diagnosis: object | None = None
    recommendations: list | None = None
    decision_plan: object | None = None
    preview: object | None = None
    cleaning: object | None = None
    validation: object | None = None

    # ---------- Visualization ----------
    visualizations: object | None = None
    rendered_visualizations: list | None = None

    # ---------- Machine Learning ----------
    model: object | None = None
    prediction: object | None = None

    # ---------- Metadata ----------
    generated_at: datetime = field(default_factory=datetime.now)