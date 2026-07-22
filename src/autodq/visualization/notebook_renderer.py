from __future__ import annotations

import base64
import html
from pathlib import Path


class NotebookVisualizationRenderer:
    """Render responsive, self-contained visualization cards in notebooks."""

    _CSS = """
    <style>
      .autodq-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
        gap: 18px;
        margin: 12px 0 22px;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      }
      .autodq-card {
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-radius: 14px;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.08);
        overflow: hidden;
      }
      .autodq-card__header { padding: 15px 18px 8px; }
      .autodq-card__title {
        color: #172033;
        font-size: 16px;
        font-weight: 700;
        line-height: 1.35;
        margin: 0;
      }
      .autodq-card__subtitle {
        color: #52627a;
        font-size: 13px;
        margin: 4px 0 0;
      }
      .autodq-card__image {
        background: #ffffff;
        display: block;
        height: auto;
        max-width: 100%;
        width: 100%;
      }
      .autodq-card__footer {
        border-top: 1px solid #edf1f7;
        color: #52627a;
        font-size: 12px;
        line-height: 1.5;
        padding: 11px 18px 14px;
      }
      .autodq-badge {
        background: #e8f0ff;
        border-radius: 999px;
        color: #2256b3;
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-right: 6px;
        padding: 3px 8px;
        text-transform: uppercase;
      }
      .autodq-error {
        background: #fff1f2;
        color: #9f1239;
        padding: 18px;
      }
      .autodq-empty {
        background: #f8fafc;
        border: 1px dashed #94a3b8;
        border-radius: 12px;
        color: #52627a;
        padding: 24px;
      }
    </style>
    """

    def __init__(self):
        self._renderer = None

    @property
    def renderer(self):
        if self._renderer is None:
            from autodq.visualization.renderers.matplotlib_renderer import (
                MatplotlibVisualizationRenderer,
            )

            self._renderer = MatplotlibVisualizationRenderer()

        return self._renderer

    def render(
        self,
        visualization_report,
        output_dir: str | Path | None = None,
    ) -> list[dict]:
        if visualization_report is None or not self.is_notebook():
            return []

        rendered = []

        if output_dir is not None:
            rendered = self.renderer.render_report(
                visualization_report=visualization_report,
                output_dir=output_dir,
            )
        else:
            rendered = [
                {
                    "chart_id": chart.chart_id,
                    "title": chart.title,
                    "chart_type": chart.chart_type,
                    "stage": chart.stage,
                    "image_path": None,
                }
                for chart in visualization_report.charts
            ]

        self._display_html(self.render_report_html(visualization_report))
        return rendered

    def render_chart_html(self, chart) -> str:
        return f"{self._CSS}<div class='autodq-gallery'>{self._card(chart)}</div>"

    def render_report_html(self, visualization_report) -> str:
        charts = list(getattr(visualization_report, "charts", []))

        if not charts:
            return (
                f"{self._CSS}<div class='autodq-empty'>"
                "No visualizations are available.</div>"
            )

        cards = "".join(self._card(chart) for chart in charts)
        return f"{self._CSS}<div class='autodq-gallery'>{cards}</div>"

    def show_chart(self, chart) -> None:
        if self.is_notebook():
            self._display_html(self.render_chart_html(chart))
            return

        self.renderer.show_chart(chart)

    def show_report(self, visualization_report) -> None:
        if self.is_notebook():
            self._display_html(
                self.render_report_html(visualization_report)
            )
            return

        for chart in visualization_report.charts:
            self.renderer.show_chart(chart)

    def is_notebook(self) -> bool:
        try:
            from IPython import get_ipython

            shell = get_ipython()

            if shell is None:
                return False

            return shell.__class__.__name__ in {
                "ZMQInteractiveShell",
                "Shell",
                "GoogleShell",
            }
        except Exception:
            return False

    def _card(self, chart) -> str:
        title = html.escape(str(getattr(chart, "title", "Untitled")))
        description = html.escape(
            str(getattr(chart, "description", ""))
        )
        chart_type = html.escape(
            str(getattr(chart, "chart_type", "unknown"))
        )
        stage = html.escape(str(getattr(chart, "stage", "current")))
        style = getattr(chart, "style", None)
        subtitle_value = getattr(style, "subtitle", None)
        subtitle = (
            f"<p class='autodq-card__subtitle'>"
            f"{html.escape(str(subtitle_value))}</p>"
            if subtitle_value
            else ""
        )

        try:
            image_bytes = self.renderer.render_bytes(chart, format="png")
            encoded = base64.b64encode(image_bytes).decode("ascii")
            image_markup = (
                "<img class='autodq-card__image' "
                f"alt='{title}' "
                f"src='data:image/png;base64,{encoded}'>"
            )
        except Exception as error:
            image_markup = (
                "<div class='autodq-error'>Could not render chart: "
                f"{html.escape(str(error))}</div>"
            )

        recommended = (
            "<span class='autodq-badge'>Recommended</span>"
            if getattr(chart, "recommended", False)
            else ""
        )
        return (
            "<article class='autodq-card'>"
            "<header class='autodq-card__header'>"
            f"<h3 class='autodq-card__title'>{title}</h3>"
            f"{subtitle}</header>"
            f"{image_markup}"
            "<footer class='autodq-card__footer'>"
            f"{recommended}"
            f"<span class='autodq-badge'>{chart_type}</span>"
            f"<span class='autodq-badge'>{stage}</span>"
            f"<div>{description}</div>"
            "</footer></article>"
        )

    @staticmethod
    def _display_html(markup: str) -> None:
        try:
            from IPython.display import HTML, display
        except ImportError:
            return

        display(HTML(markup))
