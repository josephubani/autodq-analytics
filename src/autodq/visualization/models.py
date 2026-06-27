from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class VisualizationSpec:
    """
    A chart specification that can later be rendered in console, HTML, Streamlit,
    notebooks, or exported reports.
    """

    chart_id: str
    chart_type: str
    title: str
    description: str
    data: list[dict]
    x: str | None = None
    y: str | None = None
    stage: str = "current"
    recommended: bool = False

    def to_dict(self) -> dict:
        return {
            "chart_id": self.chart_id,
            "chart_type": self.chart_type,
            "title": self.title,
            "description": self.description,
            "x": self.x,
            "y": self.y,
            "stage": self.stage,
            "recommended": self.recommended,
            "data": self.data,
        }


@dataclass(slots=True)
class VisualizationReport:
    """
    Collection of visualization specifications.
    """

    charts: list[VisualizationSpec] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def chart_count(self) -> int:
        return len(self.charts)

    def to_dict(self) -> dict:
        return {
            "chart_count": self.chart_count,
            "generated_at": self.generated_at.isoformat(),
            "charts": [chart.to_dict() for chart in self.charts],
        }