from dataclasses import dataclass


@dataclass
class VisualizationSpec:
    chart_type: str
    x: str
    y: str | None = None
    aggregation: str | None = None
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None

    def to_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "x": self.x,
            "y": self.y,
            "aggregation": self.aggregation,
            "title": self.title,
            "x_label": self.x_label,
            "y_label": self.y_label,
        }