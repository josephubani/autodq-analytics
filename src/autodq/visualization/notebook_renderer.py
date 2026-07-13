from __future__ import annotations

from pathlib import Path

from autodq.visualization.renderers.matplotlib_renderer import (
    MatplotlibVisualizationRenderer,
)


class NotebookVisualizationRenderer:
    """
    Renders newly created AutoDQ visualizations directly in notebooks.
    """

    def __init__(self):
        self.renderer = MatplotlibVisualizationRenderer()

    def render(
        self,
        visualization_report,
        output_dir: str | Path = ".autodq/notebook_charts",
    ) -> list[dict]:
        if visualization_report is None:
            return []

        if not self._is_notebook():
            return []

        output_dir = Path(output_dir)
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        rendered = self.renderer.render_report(
            visualization_report=visualization_report,
            output_dir=output_dir,
        )

        try:
            from IPython.display import Image, display
        except ImportError:
            return rendered

        for chart in rendered:
            image_path = chart.get("image_path")

            if image_path is None:
                continue

            display(
                Image(
                    filename=str(image_path),
                )
            )

        return rendered

    def _is_notebook(self) -> bool:
        try:
            from IPython import get_ipython

            shell = get_ipython()

            if shell is None:
                return False

            shell_name = shell.__class__.__name__

            return shell_name in {
                "ZMQInteractiveShell",
                "Shell",
                "GoogleShell",
            }

        except Exception:
            return False