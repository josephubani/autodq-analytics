from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


class MatplotlibVisualizationRenderer:
    """
    Renders AutoDQ visualization specs as PNG files.
    """

    def render_report(self, visualization_report, output_dir: str | Path) -> list[dict]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        rendered = []

        if visualization_report is None:
            return rendered

        for chart in visualization_report.charts:
            try:
                image_path = self.render_chart(chart, output_dir)
                if image_path:
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
                        "chart_id": chart.chart_id,
                        "title": chart.title,
                        "description": chart.description,
                        "chart_type": chart.chart_type,
                        "stage": chart.stage,
                        "image_path": None,
                        "error": str(error),
                    }
                )

        return rendered

    def render_chart(self, chart, output_dir: Path) -> Path | None:
        if chart.chart_type == "bar":
            return self._render_bar(chart, output_dir)

        elif chart.chart_type == "scatter":
            return self._render_scatter(chart, output_dir)
        elif chart.chart_type == "histogram":
            return self._render_histogram(chart, output_dir)

        elif chart.chart_type == "boxplot":
            return self._render_boxplot(chart, output_dir)

        elif chart.chart_type == "correlation_heatmap":
            return self._render_correlation_heatmap(chart, output_dir)
        elif chart.chart_type == "blue_residuals_vs_fitted":
            self._render_blue_residuals_vs_fitted(
                chart,
                output_path,
        )
        elif chart.chart_type == "blue_qq_plot":
            self._render_blue_qq_plot(
                chart,
                output_path,
        )

        elif chart.chart_type == "blue_cooks_distance":
            self._render_blue_cooks_distance(
                chart,
                output_path,
        )

        elif chart.chart_type == "blue_vif_chart":
            self._render_blue_vif_chart(
                chart,
                output_path,
            )
                

        return None
    
    def _render_blue_residuals_vs_fitted(
        self,
        chart,
        output_path,
    ) -> None:
        x_values = [
            row["fitted_value"]
            for row in chart.data
        ]

        y_values = [
            row["residual"]
            for row in chart.data
        ]

        plt.figure(figsize=(9, 6))
        plt.scatter(
            x_values,
            y_values,
            alpha=0.6,
        )
        plt.axhline(
            y=0,
            linestyle="--",
            linewidth=1,
        )
        plt.title(chart.title)
        plt.xlabel("Fitted values")
        plt.ylabel("Residuals")
        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=160,
            bbox_inches="tight",
        )
        plt.close()


    def _render_blue_qq_plot(
        self,
        chart,
        output_path,
    ) -> None:
        theoretical = np.asarray(
            [
                row["theoretical_quantile"]
                for row in chart.data
            ],
            dtype=float,
        )

        observed = np.asarray(
            [
                row["observed_residual"]
                for row in chart.data
            ],
            dtype=float,
        )

        plt.figure(figsize=(9, 6))
        plt.scatter(
            theoretical,
            observed,
            alpha=0.6,
        )

        if len(theoretical) > 1:
            slope, intercept = np.polyfit(
                theoretical,
                observed,
                1,
            )

            plt.plot(
                theoretical,
                slope * theoretical + intercept,
                linestyle="--",
                linewidth=1,
            )

        plt.title(chart.title)
        plt.xlabel("Theoretical quantiles")
        plt.ylabel("Observed residual quantiles")
        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=160,
            bbox_inches="tight",
        )
        plt.close()


    def _render_blue_cooks_distance(
        self,
        chart,
        output_path,
    ) -> None:
        observations = [
            row["observation"]
            for row in chart.data
        ]

        distances = [
            row["cooks_distance"]
            for row in chart.data
        ]

        threshold = (
            chart.data[0]["threshold"]
            if chart.data
            else 0
        )

        plt.figure(figsize=(10, 6))
        plt.vlines(
            observations,
            0,
            distances,
            linewidth=0.8,
        )
        plt.scatter(
            observations,
            distances,
            s=12,
        )
        plt.axhline(
            y=threshold,
            linestyle="--",
            linewidth=1,
        )
        plt.title(chart.title)
        plt.xlabel("Observation")
        plt.ylabel("Cook’s distance")
        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=160,
            bbox_inches="tight",
        )
        plt.close()


    def _render_blue_vif_chart(
        self,
        chart,
        output_path,
    ) -> None:
        ordered = sorted(
            (
                (row["feature"], row["vif"])
                for row in chart.data
            ),
            key=lambda item: item[1],
        )

        features = [
            feature
            for feature, _ in ordered
        ]

        values = [
            value
            for _, value in ordered
        ]

        plt.figure(figsize=(10, 7))
        plt.barh(
            features,
            values,
        )
        plt.axvline(
            x=5,
            linestyle="--",
            linewidth=1,
        )
        plt.axvline(
            x=10,
            linestyle=":",
            linewidth=1,
        )
        plt.title(chart.title)
        plt.xlabel("Variance Inflation Factor")
        plt.ylabel("Feature")
        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=160,
            bbox_inches="tight",
        )
        plt.close()


    def _render_bar(self, chart, output_dir: Path) -> Path:
        labels = []
        values = []

        for row in chart.data:
            labels.append(str(row.get(chart.x, "N/A")))
            values.append(row.get(chart.y, 0))

        fig, ax = plt.subplots(figsize=(9, 5))

        if len(labels) >= 6:
            ax.barh(labels, values)
            ax.invert_yaxis()
            ax.set_xlabel(chart.y or "value")
        else:
            ax.bar(labels, values)
            ax.set_ylabel(chart.y or "value")
            ax.tick_params(axis="x", rotation=25)

        ax.set_title(chart.title)
        ax.grid(axis="x" if len(labels) >= 6 else "y", alpha=0.25)

        fig.tight_layout()

        path = output_dir / f"{chart.chart_id}.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)

        return path

    def _render_scatter(self, chart, output_dir: Path) -> Path:
        x_values = []
        y_values = []

        for row in chart.data:
            x_values.append(row.get(chart.x))
            y_values.append(row.get(chart.y))

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.scatter(x_values, y_values, alpha=0.7)
        ax.set_title(chart.title)
        ax.set_xlabel(chart.x or "x")
        ax.set_ylabel(chart.y or "y")
        ax.grid(alpha=0.25)

        fig.tight_layout()

        path = output_dir / f"{chart.chart_id}.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)

        return path
    def _render_histogram(self, chart, output_dir: Path) -> Path:
        labels = [str(row.get(chart.x, "N/A")) for row in chart.data]
        values = [row.get(chart.y, 0) for row in chart.data]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(range(len(labels)), values)
        ax.set_title(chart.title)
        ax.set_xlabel(chart.x or "bin")
        ax.set_ylabel(chart.y or "count")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.grid(axis="y", alpha=0.25)

        fig.tight_layout()

        path = output_dir / f"{chart.chart_id}.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)

        return path

    def _render_boxplot(self, chart, output_dir: Path) -> Path:
        values = [
            row.get("value")
            for row in chart.data
            if isinstance(row.get("value"), (int, float))
        ]

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.boxplot(values, vert=True, patch_artist=True)
        ax.set_title(chart.title)
        ax.set_ylabel(chart.y or "value")
        ax.grid(axis="y", alpha=0.25)

        fig.tight_layout()

        path = output_dir / f"{chart.chart_id}.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)

        return path

    def _render_correlation_heatmap(self, chart, output_dir: Path) -> Path:
        import numpy as np

        if not chart.data:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.text(0.5, 0.5, "No numeric columns available", ha="center", va="center")
            ax.axis("off")
        else:
            features = [row["feature"] for row in chart.data]
            matrix = []

            for row in chart.data:
                matrix.append([row.get(feature, 0) for feature in features])

            matrix = np.array(matrix, dtype=float)

            fig, ax = plt.subplots(figsize=(10, 8))
            image = ax.imshow(matrix, aspect="auto")
            ax.set_title(chart.title)

            ax.set_xticks(range(len(features)))
            ax.set_yticks(range(len(features)))
            ax.set_xticklabels(features, rotation=45, ha="right", fontsize=8)
            ax.set_yticklabels(features, fontsize=8)

            fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

        fig.tight_layout()

        path = output_dir / f"{chart.chart_id}.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)

        return path