from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pandas as pd


def serializable_value(value: Any) -> Any:
    """Return a JSON-safe representation of common analytics values."""
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, (datetime, date, pd.Timestamp, Path)):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): serializable_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serializable_value(item) for item in value]

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


@dataclass(slots=True)
class DashboardMetric:
    """A primary value displayed at the top of an AutoDQ dashboard."""

    key: str
    label: str
    value: Any
    display: str
    description: str = ""
    status: str = "neutral"

    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = (
        "neutral",
        "good",
        "warning",
        "bad",
    )

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("Dashboard metric key cannot be empty.")

        if not self.label.strip():
            raise ValueError("Dashboard metric label cannot be empty.")

        if self.status not in self.SUPPORTED_STATUSES:
            supported = ", ".join(self.SUPPORTED_STATUSES)
            raise ValueError(
                f"Unsupported metric status: {self.status}. "
                f"Supported statuses: {supported}."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": serializable_value(self.value),
            "display": self.display,
            "description": self.description,
            "status": self.status,
        }


@dataclass(slots=True)
class Dashboard:
    """Reusable dashboard for notebooks and standalone HTML export."""

    title: str
    subtitle: str
    dataset: str
    stage: str
    theme: str = "light"
    metrics: list[DashboardMetric] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    cleaning: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    domain: dict[str, Any] | None = None
    automation: dict[str, Any] | None = None
    model: dict[str, Any] | None = None
    prediction: dict[str, Any] | None = None
    columns: list[dict[str, Any]] = field(default_factory=list)
    preview: list[dict[str, Any]] = field(default_factory=list)
    charts: list[Any] = field(default_factory=list, repr=False)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    path: Path | None = None
    auto_display: bool = field(default=True, repr=False)

    SUPPORTED_THEMES: ClassVar[tuple[str, ...]] = (
        "light",
        "dark",
        "executive",
    )

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.subtitle = self.subtitle.strip()
        self.theme = self.theme.lower().strip()

        if not self.title:
            raise ValueError("Dashboard title cannot be empty.")

        if self.theme not in self.SUPPORTED_THEMES:
            supported = ", ".join(self.SUPPORTED_THEMES)
            raise ValueError(
                f"Unsupported dashboard theme: {self.theme}. "
                f"Supported themes: {supported}."
            )

    @property
    def metric_count(self) -> int:
        return len(self.metrics)

    @property
    def chart_count(self) -> int:
        return len(self.charts)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def preview_row_count(self) -> int:
        return len(self.preview)

    def get_metric(self, key: str) -> DashboardMetric:
        for metric in self.metrics:
            if metric.key == key:
                return metric

        raise KeyError(f"Dashboard metric was not found: {key}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "dataset": self.dataset,
            "stage": self.stage,
            "theme": self.theme,
            "metric_count": self.metric_count,
            "chart_count": self.chart_count,
            "issue_count": self.issue_count,
            "preview_row_count": self.preview_row_count,
            "metrics": [item.to_dict() for item in self.metrics],
            "issues": serializable_value(self.issues),
            "recommendations": serializable_value(self.recommendations),
            "cleaning": serializable_value(self.cleaning),
            "review": serializable_value(self.review),
            "domain": serializable_value(self.domain),
            "automation": serializable_value(self.automation),
            "model": serializable_value(self.model),
            "prediction": serializable_value(self.prediction),
            "columns": serializable_value(self.columns),
            "preview": serializable_value(self.preview),
            "charts": [
                serializable_value(chart.to_dict())
                for chart in self.charts
            ],
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat(),
            "path": str(self.path) if self.path is not None else None,
        }

    def to_html(self) -> str:
        """Render this dashboard as a self-contained HTML document."""
        from autodq.dashboard.html_renderer import DashboardHTMLRenderer

        return DashboardHTMLRenderer().render(self)

    def to_notebook_html(self, height: int = 900) -> str:
        """Embed the dashboard in an isolated, interactive notebook frame."""
        import html

        if (
            isinstance(height, bool)
            or not isinstance(height, int)
            or height < 300
        ):
            raise ValueError("Notebook dashboard height must be at least 300.")

        source = html.escape(self.to_html(), quote=True)
        title = html.escape(self.title, quote=True)
        return (
            f'<iframe title="{title}" srcdoc="{source}" '
            f'sandbox="allow-scripts allow-downloads allow-modals" '
            f'style="width:100%;height:{height}px;border:0;" '
            'loading="lazy"></iframe>'
        )

    def save(
        self,
        output: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Save this dashboard as a standalone HTML file."""
        from autodq.dashboard.html_renderer import DashboardHTMLRenderer

        self.path = DashboardHTMLRenderer().save(
            self,
            output=output,
            overwrite=overwrite,
        )
        return self.path

    def show(self) -> "Dashboard":
        """Display the dashboard in Jupyter when IPython is available."""
        try:
            from IPython.display import HTML, display
        except ImportError:
            print(
                f"{self.title}: {self.metric_count} metrics, "
                f"{self.chart_count} charts"
            )
        else:
            display(HTML(self.to_notebook_html()))

        return self

    def _repr_html_(self) -> str | None:
        if not self.auto_display:
            return None

        return self.to_notebook_html()
