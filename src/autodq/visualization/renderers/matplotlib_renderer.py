from __future__ import annotations

import io
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import is_color_like

from autodq.visualization.models import VisualizationStyle


class MatplotlibVisualizationRenderer:
    """Render reusable AutoDQ chart specifications with Matplotlib."""

    SUPPORTED_FORMATS = {"png", "svg", "pdf", "jpg", "jpeg"}
    PALETTES = {
        "autodq": [
            "#2563eb",
            "#14b8a6",
            "#f59e0b",
            "#8b5cf6",
            "#ef4444",
            "#06b6d4",
        ],
        "colorblind": [
            "#0072b2",
            "#e69f00",
            "#009e73",
            "#cc79a7",
            "#d55e00",
            "#56b4e9",
        ],
        "warm": ["#7f1d1d", "#dc2626", "#f97316", "#fbbf24"],
        "cool": ["#1e3a8a", "#2563eb", "#0891b2", "#0d9488"],
        "monochrome": ["#111827", "#4b5563", "#9ca3af", "#d1d5db"],
    }
    THEMES = {
        "light": {
            "figure": "#ffffff",
            "axes": "#ffffff",
            "text": "#172033",
            "grid_color": "#d7deea",
            "spine": "#a8b3c5",
            "color": "#2563eb",
            "palette": "autodq",
            "cmap": "Blues",
            "title_size": 14,
            "label_size": 10,
        },
        "dark": {
            "figure": "#111827",
            "axes": "#172033",
            "text": "#f3f4f6",
            "grid_color": "#475569",
            "spine": "#64748b",
            "color": "#60a5fa",
            "palette": [
                "#60a5fa",
                "#2dd4bf",
                "#fbbf24",
                "#c084fc",
                "#fb7185",
            ],
            "cmap": "magma",
            "title_size": 14,
            "label_size": 10,
        },
        "journal": {
            "figure": "#ffffff",
            "axes": "#ffffff",
            "text": "#111111",
            "grid_color": "#d4d4d4",
            "spine": "#333333",
            "color": "#303030",
            "palette": "monochrome",
            "cmap": "Greys",
            "title_size": 11,
            "label_size": 9,
        },
        "presentation": {
            "figure": "#ffffff",
            "axes": "#ffffff",
            "text": "#0f172a",
            "grid_color": "#cbd5e1",
            "spine": "#64748b",
            "color": "#7c3aed",
            "palette": [
                "#7c3aed",
                "#2563eb",
                "#0d9488",
                "#ea580c",
                "#db2777",
            ],
            "cmap": "viridis",
            "title_size": 20,
            "label_size": 14,
        },
    }
    TEMPLATES = {
        "notebook": {
            "theme": "light",
            "figsize": (9, 5.5),
            "dpi": 160,
            "grid": True,
            "legend": False,
            "transparent": False,
        },
        "publication": {
            "theme": "journal",
            "figsize": (7, 4.5),
            "dpi": 300,
            "grid": False,
            "legend": False,
            "transparent": False,
        },
        "presentation": {
            "theme": "presentation",
            "figsize": (12, 7),
            "dpi": 180,
            "grid": True,
            "legend": True,
            "transparent": False,
        },
    }

    def render_report(
        self,
        visualization_report,
        output_dir: str | Path,
        format: str = "png",
    ) -> list[dict]:
        output_dir = Path(output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered = []

        if visualization_report is None:
            return rendered

        for chart in visualization_report.charts:
            try:
                image_path = self.render_chart(
                    chart,
                    output_dir=output_dir,
                    format=format,
                )
                rendered.append(
                    {
                        "chart_id": chart.chart_id,
                        "title": chart.title,
                        "description": chart.description,
                        "chart_type": chart.chart_type,
                        "stage": chart.stage,
                        "image_path": str(image_path),
                    }
                )
            except Exception as error:
                rendered.append(
                    {
                        "chart_id": getattr(chart, "chart_id", "unknown"),
                        "title": getattr(chart, "title", "Untitled"),
                        "description": getattr(chart, "description", ""),
                        "chart_type": getattr(chart, "chart_type", "unknown"),
                        "stage": getattr(chart, "stage", "current"),
                        "image_path": None,
                        "error": str(error),
                    }
                )

        return rendered

    def render_chart(
        self,
        chart,
        output_dir: str | Path,
        format: str = "png",
    ) -> Path:
        file_format = self._validate_format(format)
        filename = f"{self._safe_filename(chart.chart_id)}.{file_format}"
        return self.save_chart(
            chart,
            Path(output_dir) / filename,
            format=file_format,
        )

    def save_chart(
        self,
        chart,
        output: str | Path,
        format: str | None = None,
        dpi: int | None = None,
        transparent: bool | None = None,
    ) -> Path:
        output_path = Path(output).expanduser()
        inferred_format = output_path.suffix.lower().lstrip(".")
        file_format = self._validate_format(
            format or inferred_format or "png"
        )

        if output_path.is_dir():
            output_path = output_path / (
                f"{self._safe_filename(chart.chart_id)}.{file_format}"
            )
        elif output_path.suffix.lower().lstrip(".") != file_format:
            output_path = output_path.with_suffix(f".{file_format}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        figure, resolved = self.build_figure(chart)
        save_dpi = dpi or resolved["dpi"]
        save_transparent = (
            transparent
            if transparent is not None
            else resolved["transparent"]
        )

        try:
            figure.savefig(
                output_path,
                format=file_format,
                dpi=save_dpi,
                bbox_inches="tight",
                transparent=save_transparent,
                facecolor=figure.get_facecolor(),
            )
        finally:
            plt.close(figure)

        return output_path.resolve()

    def render_bytes(self, chart, format: str = "png") -> bytes:
        file_format = self._validate_format(format)
        figure, resolved = self.build_figure(chart)
        buffer = io.BytesIO()

        try:
            figure.savefig(
                buffer,
                format=file_format,
                dpi=resolved["dpi"],
                bbox_inches="tight",
                transparent=resolved["transparent"],
                facecolor=figure.get_facecolor(),
            )
        finally:
            plt.close(figure)

        return buffer.getvalue()

    def show_chart(self, chart) -> None:
        figure, _ = self.build_figure(chart)

        try:
            plt.show()
        finally:
            plt.close(figure)

    def build_figure(self, chart):
        builders = {
            "bar": self._build_bar,
            "scatter": self._build_scatter,
            "histogram": self._build_histogram,
            "boxplot": self._build_boxplot,
            "correlation_heatmap": self._build_correlation_heatmap,
            "blue_residuals_vs_fitted": (
                self._build_blue_residuals_vs_fitted
            ),
            "blue_qq_plot": self._build_blue_qq_plot,
            "blue_cooks_distance": self._build_blue_cooks_distance,
            "blue_vif_chart": self._build_blue_vif_chart,
        }
        builder = builders.get(chart.chart_type)

        if builder is None:
            raise ValueError(
                f"Unsupported visualization type: {chart.chart_type}"
            )

        resolved = self.resolve_style(getattr(chart, "style", None))
        figure, axis = self._new_figure(resolved)
        grid_axis = builder(axis, chart, resolved)
        self._finish_figure(
            figure,
            axis,
            chart,
            resolved,
            grid_axis=grid_axis,
        )
        return figure, resolved

    def resolve_style(
        self,
        style: VisualizationStyle | None,
    ) -> dict:
        style = style or VisualizationStyle()
        resolved = {
            "theme": "light",
            "figsize": (9, 5),
            "dpi": 160,
            "grid": True,
            "legend": False,
            "transparent": False,
        }

        if style.template is not None:
            resolved.update(self.TEMPLATES[style.template])

        for name in (
            "theme",
            "figsize",
            "dpi",
            "grid",
            "legend",
            "transparent",
        ):
            value = getattr(style, name)

            if value is not None:
                resolved[name] = value

        theme = dict(self.THEMES[resolved["theme"]])
        resolved.update(theme)
        resolved["legend_position"] = style.legend_position
        resolved["subtitle"] = style.subtitle
        resolved["x_label"] = style.x_label
        resolved["y_label"] = style.y_label

        if style.color is not None:
            if not is_color_like(style.color):
                raise ValueError(
                    f"Invalid Matplotlib color: {style.color}"
                )

            resolved["color"] = style.color

        palette = style.palette or resolved["palette"]
        resolved["colors"] = self._resolve_palette(palette)

        if style.color is not None:
            resolved["colors"] = [style.color]

        return resolved

    def _new_figure(self, resolved: dict):
        figure, axis = plt.subplots(
            figsize=resolved["figsize"],
            facecolor=resolved["figure"],
        )
        axis.set_facecolor(resolved["axes"])
        return figure, axis

    def _finish_figure(
        self,
        figure,
        axis,
        chart,
        resolved: dict,
        grid_axis: str = "both",
    ) -> None:
        title = chart.title

        if resolved["subtitle"]:
            title = f"{title}\n{resolved['subtitle']}"

        axis.set_title(
            title,
            color=resolved["text"],
            fontsize=resolved["title_size"],
            pad=14,
        )

        horizontal = (
            chart.chart_type == "blue_vif_chart"
            or (chart.chart_type == "bar" and len(chart.data) >= 6)
        )

        if horizontal:
            if resolved["x_label"] is not None:
                axis.set_ylabel(resolved["x_label"])

            if resolved["y_label"] is not None:
                axis.set_xlabel(resolved["y_label"])
        else:
            if resolved["x_label"] is not None:
                axis.set_xlabel(resolved["x_label"])

            if resolved["y_label"] is not None:
                axis.set_ylabel(resolved["y_label"])

        axis.xaxis.label.set_color(resolved["text"])
        axis.yaxis.label.set_color(resolved["text"])
        axis.xaxis.label.set_size(resolved["label_size"])
        axis.yaxis.label.set_size(resolved["label_size"])
        axis.tick_params(colors=resolved["text"])

        for spine in axis.spines.values():
            spine.set_color(resolved["spine"])

        if resolved["grid"]:
            axis.grid(
                visible=True,
                axis=grid_axis,
                color=resolved["grid_color"],
                alpha=0.55,
                linewidth=0.7,
            )
        else:
            axis.grid(visible=False)
        axis.set_axisbelow(True)

        if resolved["legend"]:
            handles, labels = axis.get_legend_handles_labels()

            if handles:
                legend = axis.legend(
                    handles,
                    labels,
                    loc=resolved["legend_position"],
                )
                legend.get_frame().set_facecolor(resolved["axes"])

                for text in legend.get_texts():
                    text.set_color(resolved["text"])

        figure.tight_layout()

    def _build_bar(self, axis, chart, resolved: dict) -> str:
        labels = [str(row.get(chart.x, "N/A")) for row in chart.data]
        values = [row.get(chart.y, 0) for row in chart.data]
        colors = self._repeat_colors(resolved["colors"], len(labels))

        if len(labels) >= 6:
            axis.barh(
                labels,
                values,
                color=colors,
                label=chart.y or "value",
            )
            axis.invert_yaxis()
            axis.set_xlabel(chart.y or "value")
            return "x"

        axis.bar(
            labels,
            values,
            color=colors,
            label=chart.y or "value",
        )
        axis.set_ylabel(chart.y or "value")
        axis.tick_params(axis="x", rotation=25)
        return "y"

    def _build_scatter(self, axis, chart, resolved: dict) -> str:
        x_values = [row.get(chart.x) for row in chart.data]
        y_values = [row.get(chart.y) for row in chart.data]
        axis.scatter(
            x_values,
            y_values,
            alpha=0.72,
            color=resolved["color"],
            label=f"{chart.x} vs {chart.y}",
        )
        axis.set_xlabel(chart.x or "x")
        axis.set_ylabel(chart.y or "y")
        return "both"

    def _build_histogram(self, axis, chart, resolved: dict) -> str:
        labels = [str(row.get(chart.x, "N/A")) for row in chart.data]
        values = [row.get(chart.y, 0) for row in chart.data]
        colors = self._repeat_colors(resolved["colors"], len(labels))
        positions = range(len(labels))
        axis.bar(
            positions,
            values,
            color=colors,
            label=chart.y or "count",
        )
        axis.set_xlabel(chart.x or "bin")
        axis.set_ylabel(chart.y or "count")
        axis.set_xticks(list(positions))
        axis.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        return "y"

    def _build_boxplot(self, axis, chart, resolved: dict) -> str:
        values = [
            row.get("value")
            for row in chart.data
            if isinstance(row.get("value"), (int, float))
        ]

        if values:
            result = axis.boxplot(
                values,
                vert=True,
                patch_artist=True,
            )
            result["boxes"][0].set_facecolor(resolved["color"])
            result["boxes"][0].set_alpha(0.65)
            result["boxes"][0].set_label(chart.y or "value")
        else:
            axis.text(
                0.5,
                0.5,
                "No numeric values available",
                ha="center",
                va="center",
                color=resolved["text"],
            )

        axis.set_ylabel(chart.y or "value")
        return "y"

    def _build_correlation_heatmap(
        self,
        axis,
        chart,
        resolved: dict,
    ) -> str:
        if not chart.data:
            axis.text(
                0.5,
                0.5,
                "No numeric columns available",
                ha="center",
                va="center",
                color=resolved["text"],
            )
            axis.axis("off")
            return "both"

        features = [row["feature"] for row in chart.data]
        matrix = np.asarray(
            [
                [row.get(feature, 0) for feature in features]
                for row in chart.data
            ],
            dtype=float,
        )
        image = axis.imshow(
            matrix,
            aspect="auto",
            cmap=resolved["cmap"],
            vmin=-1,
            vmax=1,
        )
        axis.set_xticks(range(len(features)))
        axis.set_yticks(range(len(features)))
        axis.set_xticklabels(features, rotation=45, ha="right", fontsize=8)
        axis.set_yticklabels(features, fontsize=8)
        colorbar = axis.figure.colorbar(
            image,
            ax=axis,
            fraction=0.046,
            pad=0.04,
        )
        colorbar.ax.tick_params(colors=resolved["text"])
        return "both"

    def _build_blue_residuals_vs_fitted(
        self,
        axis,
        chart,
        resolved: dict,
    ) -> str:
        x_values = [row["fitted_value"] for row in chart.data]
        y_values = [row["residual"] for row in chart.data]
        axis.scatter(
            x_values,
            y_values,
            alpha=0.65,
            color=resolved["color"],
            label="Residual",
        )
        axis.axhline(
            y=0,
            linestyle="--",
            linewidth=1,
            color=resolved["spine"],
        )
        axis.set_xlabel("Fitted values")
        axis.set_ylabel("Residuals")
        return "both"

    def _build_blue_qq_plot(self, axis, chart, resolved: dict) -> str:
        theoretical = np.asarray(
            [row["theoretical_quantile"] for row in chart.data],
            dtype=float,
        )
        observed = np.asarray(
            [row["observed_residual"] for row in chart.data],
            dtype=float,
        )
        axis.scatter(
            theoretical,
            observed,
            alpha=0.65,
            color=resolved["color"],
            label="Residual quantile",
        )

        if len(theoretical) > 1:
            slope, intercept = np.polyfit(theoretical, observed, 1)
            axis.plot(
                theoretical,
                slope * theoretical + intercept,
                linestyle="--",
                linewidth=1,
                color=resolved["spine"],
                label="Reference",
            )

        axis.set_xlabel("Theoretical quantiles")
        axis.set_ylabel("Observed residual quantiles")
        return "both"

    def _build_blue_cooks_distance(
        self,
        axis,
        chart,
        resolved: dict,
    ) -> str:
        observations = [row["observation"] for row in chart.data]
        distances = [row["cooks_distance"] for row in chart.data]
        threshold = chart.data[0]["threshold"] if chart.data else 0
        axis.vlines(
            observations,
            0,
            distances,
            linewidth=0.8,
            color=resolved["color"],
        )
        axis.scatter(
            observations,
            distances,
            s=12,
            color=resolved["color"],
            label="Cook's distance",
        )
        axis.axhline(
            y=threshold,
            linestyle="--",
            linewidth=1,
            color=resolved["spine"],
            label="Review threshold",
        )
        axis.set_xlabel("Observation")
        axis.set_ylabel("Cook's distance")
        return "both"

    def _build_blue_vif_chart(self, axis, chart, resolved: dict) -> str:
        ordered = sorted(
            ((row["feature"], row["vif"]) for row in chart.data),
            key=lambda item: item[1],
        )
        features = [feature for feature, _ in ordered]
        values = [value for _, value in ordered]
        colors = self._repeat_colors(resolved["colors"], len(features))
        axis.barh(features, values, color=colors, label="VIF")
        axis.axvline(
            x=5,
            linestyle="--",
            linewidth=1,
            color=resolved["spine"],
            label="Review",
        )
        axis.axvline(
            x=10,
            linestyle=":",
            linewidth=1,
            color=resolved["spine"],
            label="Severe",
        )
        axis.set_xlabel("Variance Inflation Factor")
        axis.set_ylabel("Feature")
        return "x"

    def _resolve_palette(self, palette) -> list:
        if isinstance(palette, (list, tuple)):
            colors = list(palette)

            if not all(is_color_like(color) for color in colors):
                raise ValueError("palette contains an invalid color.")

            return colors

        if palette in self.PALETTES:
            return list(self.PALETTES[palette])

        try:
            colormap = plt.get_cmap(str(palette))
        except ValueError as error:
            named = ", ".join(sorted(self.PALETTES))
            raise ValueError(
                f"Unknown visualization palette: {palette}. "
                f"Use a Matplotlib colormap or one of: {named}."
            ) from error

        return [colormap(value) for value in np.linspace(0.15, 0.85, 8)]

    @staticmethod
    def _repeat_colors(colors: list, count: int) -> list:
        if count <= 0:
            return []

        return [colors[index % len(colors)] for index in range(count)]

    @classmethod
    def _validate_format(cls, format: str) -> str:
        normalized = format.lower().strip().lstrip(".")

        if normalized not in cls.SUPPORTED_FORMATS:
            supported = ", ".join(sorted(cls.SUPPORTED_FORMATS))
            raise ValueError(
                f"Unsupported visualization format: {format}. "
                f"Supported formats: {supported}."
            )

        return normalized

    @staticmethod
    def _safe_filename(value: str) -> str:
        filename = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
        return filename or "autodq_chart"
