from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar


@dataclass(slots=True)
class VisualizationStyle:
    """Portable styling options shared by every AutoDQ chart."""

    SUPPORTED_THEMES: ClassVar[tuple[str, ...]] = (
        "light",
        "dark",
        "journal",
        "presentation",
    )
    SUPPORTED_TEMPLATES: ClassVar[tuple[str, ...]] = (
        "notebook",
        "publication",
        "presentation",
    )

    subtitle: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    theme: str | None = None
    color: str | None = None
    palette: str | list[str] | tuple[str, ...] | None = None
    figsize: tuple[float, float] | None = None
    dpi: int | None = None
    grid: bool | None = None
    legend: bool | None = None
    legend_position: str = "best"
    template: str | None = None
    transparent: bool | None = None

    def __post_init__(self) -> None:
        if self.figsize is not None:
            self.figsize = tuple(self.figsize)

        self.validate()

    def validate(self) -> None:
        if self.theme is not None and self.theme not in self.SUPPORTED_THEMES:
            supported = ", ".join(self.SUPPORTED_THEMES)
            raise ValueError(
                f"Unsupported visualization theme: {self.theme}. "
                f"Supported themes: {supported}."
            )

        if (
            self.template is not None
            and self.template not in self.SUPPORTED_TEMPLATES
        ):
            supported = ", ".join(self.SUPPORTED_TEMPLATES)
            raise ValueError(
                f"Unsupported visualization template: {self.template}. "
                f"Supported templates: {supported}."
            )

        if self.figsize is not None:
            if len(self.figsize) != 2 or any(
                float(value) <= 0 for value in self.figsize
            ):
                raise ValueError(
                    "figsize must contain two positive numbers."
                )

            self.figsize = (
                float(self.figsize[0]),
                float(self.figsize[1]),
            )

        if self.dpi is not None and (
            isinstance(self.dpi, bool)
            or not isinstance(self.dpi, int)
            or self.dpi <= 0
        ):
            raise ValueError("dpi must be a positive integer.")

        for option in ("grid", "legend", "transparent"):
            value = getattr(self, option)

            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{option} must be True or False.")

        if isinstance(self.palette, (list, tuple)) and not self.palette:
            raise ValueError("palette cannot be empty.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "subtitle": self.subtitle,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "theme": self.theme,
            "color": self.color,
            "palette": (
                list(self.palette)
                if isinstance(self.palette, tuple)
                else self.palette
            ),
            "figsize": (
                list(self.figsize)
                if self.figsize is not None
                else None
            ),
            "dpi": self.dpi,
            "grid": self.grid,
            "legend": self.legend,
            "legend_position": self.legend_position,
            "template": self.template,
            "transparent": self.transparent,
        }


@dataclass(slots=True)
class VisualizationSpec:
    """Reusable chart specification for notebooks, files, and reports."""

    chart_id: str
    chart_type: str
    title: str
    description: str
    data: list[dict]
    x: str | None = None
    y: str | None = None
    column: str | None = None
    stage: str = "current"
    recommended: bool = False
    style: VisualizationStyle = field(default_factory=VisualizationStyle)

    def customize(
        self,
        *,
        title: str | None = None,
        subtitle: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        theme: str | None = None,
        color: str | None = None,
        palette: str | list[str] | tuple[str, ...] | None = None,
        figsize: tuple[float, float] | None = None,
        dpi: int | None = None,
        grid: bool | None = None,
        legend: bool | None = None,
        legend_position: str | None = None,
        template: str | None = None,
        transparent: bool | None = None,
    ) -> "VisualizationSpec":
        """Update this chart in place and return it for method chaining."""
        updated_title = self.title

        if title is not None:
            if not title.strip():
                raise ValueError("Visualization title cannot be empty.")

            updated_title = title.strip()

        updated_style = deepcopy(self.style)

        updates = {
            "subtitle": subtitle,
            "x_label": x_label,
            "y_label": y_label,
            "theme": theme,
            "color": color,
            "palette": palette,
            "figsize": figsize,
            "dpi": dpi,
            "grid": grid,
            "legend": legend,
            "legend_position": legend_position,
            "template": template,
            "transparent": transparent,
        }

        for name, value in updates.items():
            if value is not None:
                setattr(updated_style, name, value)

        updated_style.validate()
        self.title = updated_title
        self.style = updated_style
        return self

    def clone(self, chart_id: str | None = None) -> "VisualizationSpec":
        """Return an independent copy suitable for another presentation."""
        cloned = deepcopy(self)

        if chart_id is not None:
            cloned.chart_id = chart_id

        return cloned

    def reset_style(self) -> "VisualizationSpec":
        self.style = VisualizationStyle()
        return self

    def show(self) -> "VisualizationSpec":
        """Display the chart using the active notebook or GUI backend."""
        from autodq.visualization.notebook_renderer import (
            NotebookVisualizationRenderer,
        )

        NotebookVisualizationRenderer().show_chart(self)
        return self

    def save(
        self,
        output: str | Path,
        *,
        format: str | None = None,
        dpi: int | None = None,
        transparent: bool | None = None,
    ) -> Path:
        """Save this chart as PNG, SVG, PDF, JPG, or JPEG."""
        from autodq.visualization.renderers.matplotlib_renderer import (
            MatplotlibVisualizationRenderer,
        )

        return MatplotlibVisualizationRenderer().save_chart(
            self,
            output=output,
            format=format,
            dpi=dpi,
            transparent=transparent,
        )

    def to_html(self) -> str:
        from autodq.visualization.notebook_renderer import (
            NotebookVisualizationRenderer,
        )

        return NotebookVisualizationRenderer().render_chart_html(self)

    def _repr_html_(self) -> str:
        return self.to_html()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_id": self.chart_id,
            "chart_type": self.chart_type,
            "title": self.title,
            "description": self.description,
            "x": self.x,
            "y": self.y,
            "column": self.column,
            "stage": self.stage,
            "recommended": self.recommended,
            "style": self.style.to_dict(),
            "data": self.data,
        }


@dataclass(slots=True)
class VisualizationReport:
    """Reusable collection of visualization specifications."""

    charts: list[VisualizationSpec] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    auto_display: bool = field(default=True, repr=False)

    @property
    def chart_count(self) -> int:
        return len(self.charts)

    @property
    def latest(self) -> VisualizationSpec | None:
        return self.charts[-1] if self.charts else None

    def get(self, chart_id: str) -> VisualizationSpec:
        for chart in self.charts:
            if chart.chart_id == chart_id:
                return chart

        raise KeyError(f"Visualization was not found: {chart_id}")

    def customize(self, **options) -> "VisualizationReport":
        for chart in self.charts:
            chart.customize(**options)

        return self

    def show(self) -> "VisualizationReport":
        from autodq.visualization.notebook_renderer import (
            NotebookVisualizationRenderer,
        )

        NotebookVisualizationRenderer().show_report(self)
        return self

    def save(
        self,
        output_dir: str | Path,
        *,
        format: str = "png",
    ) -> list[Path]:
        from autodq.visualization.renderers.matplotlib_renderer import (
            MatplotlibVisualizationRenderer,
        )

        rendered = MatplotlibVisualizationRenderer().render_report(
            self,
            output_dir=output_dir,
            format=format,
        )
        failures = [item for item in rendered if item.get("error")]

        if failures:
            details = "; ".join(
                f"{item['chart_id']}: {item['error']}"
                for item in failures
            )
            raise RuntimeError(
                f"One or more visualizations could not be saved: {details}"
            )

        return [
            Path(item["image_path"])
            for item in rendered
            if item.get("image_path") is not None
        ]

    def to_html(self) -> str:
        from autodq.visualization.notebook_renderer import (
            NotebookVisualizationRenderer,
        )

        return NotebookVisualizationRenderer().render_report_html(self)

    def _repr_html_(self) -> str | None:
        if not self.auto_display:
            return None

        return self.to_html()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_count": self.chart_count,
            "generated_at": self.generated_at.isoformat(),
            "charts": [chart.to_dict() for chart in self.charts],
        }
