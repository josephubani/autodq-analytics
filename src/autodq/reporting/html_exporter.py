from autodq.utils.ml_formatting import pretty_algorithm_name

class HTMLExporter:
    """
    Exports professional AutoDQ HTML reports in multiple styles.
    Supported styles:
    - executive
    - dark
    - print
    """

    def export(self, report, path, style: str = "executive"):
        html = self._build_html(report, style=style)

        with open(path, "w", encoding="utf-8") as file:
            file.write(html)

    def _build_html(self, report, style: str = "executive"):
        validation = report.validation
        cleaning = report.cleaning
        diagnosis = report.diagnosis
        recommendations = report.recommendations or []

        model = getattr(report, "model", None)
        prediction = getattr(report, "prediction", None)

        quality_before = validation.quality_score_before if validation else None
        quality_after = validation.quality_score_after if validation else None
        quality_change = validation.quality_score_change if validation else None

        issue_count = diagnosis.issue_count if diagnosis else 0
        successful_actions = cleaning.successful_actions if cleaning else 0
        total_actions = cleaning.action_count if cleaning else 0

        missing_before = validation.missing_values.before if validation else "N/A"
        missing_after = validation.missing_values.after if validation else "N/A"
        duplicate_before = validation.duplicate_rows.before if validation else "N/A"
        duplicate_after = validation.duplicate_rows.after if validation else "N/A"
        rows_before = validation.rows.before if validation else "N/A"
        rows_after = validation.rows.after if validation else "N/A"
        columns_before = validation.columns.before if validation else "N/A"
        columns_after = validation.columns.after if validation else "N/A"

        theme_css = self._theme_css(style)

        issue_rows = self._build_issue_rows(diagnosis)
        recommendation_rows = self._build_recommendation_rows(recommendations)
        cleaning_rows = self._build_cleaning_rows(cleaning)

        visualization_cards = self._build_visualization_cards(
            getattr(report, "visualizations", None)
        )

        rendered_visualization_cards = self._build_rendered_visualization_cards(
            getattr(report, "rendered_visualizations", None)
        )

        model_section = self._build_model_section(model)
        prediction_section = self._build_prediction_section(prediction)

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AutoDQ Executive Report</title>
<style>
{theme_css}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: var(--bg);
    color: var(--text);
}}

.page {{
    max-width: 1220px;
    margin: 0 auto;
    padding: 32px;
}}

.hero {{
    background: var(--hero);
    color: var(--hero-text);
    padding: 34px;
    border-radius: var(--radius-lg);
    margin-bottom: 24px;
    box-shadow: var(--shadow);
}}

.hero h1 {{
    margin: 0;
    font-size: 34px;
}}

.hero p {{
    margin-top: 10px;
    color: var(--hero-muted);
    font-size: 16px;
}}

.meta {{
    margin-top: 20px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    font-size: 14px;
}}

.meta span {{
    background: var(--pill);
    padding: 8px 12px;
    border-radius: 999px;
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}}

.card {{
    background: var(--card);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border);
}}

.card h3 {{
    margin: 0;
    font-size: 14px;
    color: var(--muted);
    font-weight: 700;
}}

.metric {{
    margin-top: 10px;
    font-size: 30px;
    font-weight: 800;
    overflow-wrap: anywhere;
}}

.metric-small {{
    margin-top: 8px;
    color: var(--muted);
    font-size: 13px;
}}

.section {{
    margin-bottom: 24px;
}}

.section-title {{
    font-size: 22px;
    margin: 8px 0 14px;
}}

.two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}

.quality-wrap {{
    display: flex;
    align-items: center;
    gap: 28px;
}}

.gauge {{
    width: 170px;
    height: 170px;
    border-radius: 50%;
    background: conic-gradient(var(--success) {quality_after or 0}%, var(--gauge-bg) 0);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}

.gauge::before {{
    content: "";
    width: 118px;
    height: 118px;
    background: var(--card);
    border-radius: 50%;
    position: absolute;
}}

.gauge-value {{
    position: relative;
    font-size: 32px;
    font-weight: 800;
    color: var(--primary);
}}

.quality-info h2 {{
    margin: 0;
    font-size: 32px;
}}

.quality-info p {{
    color: var(--muted);
    margin: 8px 0;
}}

.change {{
    display: inline-block;
    margin-top: 8px;
    color: white;
    background: var(--success);
    padding: 8px 12px;
    border-radius: 999px;
    font-weight: 700;
}}

.before-after-bars {{
    display: grid;
    gap: 14px;
}}

.bar-row {{
    display: grid;
    grid-template-columns: 150px 1fr 80px;
    gap: 10px;
    align-items: center;
    font-size: 14px;
}}

.bar-track {{
    height: 12px;
    border-radius: 999px;
    background: var(--bar-bg);
    overflow: hidden;
}}

.bar-fill {{
    height: 100%;
    border-radius: 999px;
    background: var(--primary);
}}

.chart-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}}

.chart-card {{
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    background: var(--card);
}}

.chart-title {{
    font-size: 14px;
    color: var(--muted);
    font-weight: 700;
    margin-bottom: 12px;
}}

.mini-bars {{
    display: flex;
    align-items: flex-end;
    gap: 18px;
    height: 130px;
    margin-top: 12px;
}}

.mini-bar-wrap {{
    flex: 1;
    text-align: center;
}}

.mini-bar {{
    width: 100%;
    min-height: 4px;
    border-radius: 8px 8px 0 0;
    background: var(--primary);
}}

.mini-bar.after {{
    background: var(--success);
}}

.mini-label {{
    margin-top: 8px;
    font-size: 12px;
    color: var(--muted);
}}

.mini-value {{
    font-weight: 800;
    margin-top: 4px;
}}

.rendered-viz-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
}}

.rendered-viz-card {{
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    background: var(--card);
}}

.rendered-viz-card img {{
    width: 100%;
    border-radius: 12px;
    background: white;
    margin-top: 12px;
}}

.visualization-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}}

.viz-card {{
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    background: var(--card);
}}

.viz-title {{
    font-weight: 800;
    margin-bottom: 6px;
}}

.viz-description {{
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 14px;
}}

.viz-bar-row {{
    display: grid;
    grid-template-columns: 130px 1fr 70px;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
    font-size: 13px;
}}

.viz-bar-label {{
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.viz-bar-track {{
    height: 12px;
    border-radius: 999px;
    background: var(--bar-bg);
    overflow: hidden;
}}

.viz-bar-fill {{
    height: 100%;
    background: var(--primary);
    border-radius: 999px;
}}

.viz-meta {{
    margin-top: 10px;
    color: var(--muted);
    font-size: 12px;
}}

.model-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}}

.leaderboard-row {{
    display: grid;
    grid-template-columns: 70px 1fr 120px;
    gap: 12px;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid var(--border);
}}

.importance-row {{
    display: grid;
    grid-template-columns: 180px 1fr 80px;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
    font-size: 13px;
}}

.prediction-table {{
    font-size: 13px;
}}

.recommendation-list {{
    margin: 0;
    padding-left: 22px;
}}

.recommendation-list li {{
    margin-bottom: 10px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 14px;
}}

th, td {{
    padding: 12px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
}}

th {{
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

.badge {{
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}}

.success {{
    background: var(--success-soft);
    color: var(--success-text);
}}

.skipped {{
    background: var(--warning-soft);
    color: var(--warning-text);
}}

.medium {{
    background: var(--warning-soft);
    color: var(--warning-text);
}}

.high {{
    background: var(--danger-soft);
    color: var(--danger-text);
}}

.footer {{
    color: var(--muted);
    text-align: center;
    margin-top: 32px;
    font-size: 13px;
}}

@media print {{
    body {{
        background: white;
        color: black;
    }}

    .page {{
        max-width: none;
        padding: 0;
    }}

    .card, .hero {{
        box-shadow: none;
        break-inside: avoid;
    }}
}}

@media (max-width: 900px) {{
    .grid,
    .two-col,
    .chart-grid,
    .visualization-grid,
    .rendered-viz-grid,
    .model-grid {{
        grid-template-columns: 1fr;
    }}

    .quality-wrap {{
        flex-direction: column;
        align-items: flex-start;
    }}
}}
</style>
</head>

<body>
<div class="page">

    <div class="hero">
        <h1>AutoDQ Executive Data Quality Report</h1>
        <p>Automated profiling, diagnosis, evidence-aware recommendations, cleaning validation, visualization, machine learning, and prediction summary.</p>
        <div class="meta">
            <span>Dataset: {report.dataset}</span>
            <span>Style: {style}</span>
            <span>Generated: {report.generated_at.strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>Quality Before</h3>
            <div class="metric">{quality_before if quality_before is not None else "N/A"}</div>
            <div class="metric-small">Initial quality score</div>
        </div>

        <div class="card">
            <h3>Quality After</h3>
            <div class="metric">{quality_after if quality_after is not None else "N/A"}</div>
            <div class="metric-small">After approved cleaning</div>
        </div>

        <div class="card">
            <h3>Issues Detected</h3>
            <div class="metric">{issue_count}</div>
            <div class="metric-small">Detected by diagnosis engine</div>
        </div>

        <div class="card">
            <h3>Actions Successful</h3>
            <div class="metric">{successful_actions}/{total_actions}</div>
            <div class="metric-small">Executed safely</div>
        </div>
    </div>

    <div class="section card">
        <h2 class="section-title">Quality Score Gauge</h2>
        <div class="quality-wrap">
            <div class="gauge">
                <div class="gauge-value">{quality_after if quality_after is not None else "N/A"}</div>
            </div>
            <div class="quality-info">
                <h2>{quality_before if quality_before is not None else "N/A"} → {quality_after if quality_after is not None else "N/A"}</h2>
                <p>Overall quality score after approved cleaning actions.</p>
                <span class="change">Improvement: {quality_change if quality_change is not None else "N/A"}</span>
            </div>
        </div>
    </div>

    <div class="section two-col">
        <div class="card">
            <h2 class="section-title">Before vs After Comparison</h2>
            <table>
                <tr><th>Metric</th><th>Before</th><th>After</th><th>Meaning</th></tr>
                <tr><td>Missing Values</td><td>{missing_before}</td><td>{missing_after}</td><td>Resolved {self._positive_reduction(missing_before, missing_after)}</td></tr>
                <tr><td>Duplicate Rows</td><td>{duplicate_before}</td><td>{duplicate_after}</td><td>Removed {self._positive_reduction(duplicate_before, duplicate_after)}</td></tr>
                <tr><td>Rows</td><td>{rows_before}</td><td>{rows_after}</td><td>Removed {self._positive_reduction(rows_before, rows_after)}</td></tr>
                <tr><td>Columns</td><td>{columns_before}</td><td>{columns_after}</td><td>No structural column loss</td></tr>
            </table>
        </div>

        <div class="card">
            <h2 class="section-title">Before vs After Visual</h2>
            <div class="before-after-bars">
                {self._metric_bar("Missing values", missing_before, missing_after)}
                {self._metric_bar("Duplicate rows", duplicate_before, duplicate_after)}
                {self._metric_bar("Rows", rows_before, rows_after)}
                {self._metric_bar("Quality score", quality_before, quality_after)}
            </div>
        </div>
    </div>

    <div class="section card">
        <h2 class="section-title">Visual Cleaning Impact</h2>
        <div class="chart-grid">
            {self._comparison_card("Missing Values", missing_before, missing_after)}
            {self._comparison_card("Duplicate Rows", duplicate_before, duplicate_after)}
            {self._comparison_card("Rows", rows_before, rows_after)}
            {self._comparison_card("Quality Score", quality_before, quality_after)}
        </div>
    </div>

    <div class="section card">
        <h2 class="section-title">Rendered Visualization Assets</h2>
        <div class="rendered-viz-grid">
            {rendered_visualization_cards}
        </div>
    </div>

    <div class="section card">
        <h2 class="section-title">Visualization Engine Output</h2>
        <div class="visualization-grid">
            {visualization_cards}
        </div>
    </div>

    {model_section}

    {prediction_section}

    <div class="section card">
        <h2 class="section-title">Issue Breakdown</h2>
        <table>
            <tr><th>Issue</th><th>Severity</th><th>Confidence</th></tr>
            {issue_rows}
        </table>
    </div>

    <div class="section card">
        <h2 class="section-title">Evidence-Aware Recommendations</h2>
        <table>
            <tr>
                <th>#</th>
                <th>Issue</th>
                <th>Strategy</th>
                <th>Columns</th>
                <th>Confidence</th>
                <th>Reason</th>
            </tr>
            {recommendation_rows}
        </table>
    </div>

    <div class="section card">
        <h2 class="section-title">Cleaning Actions Table</h2>
        <table>
            <tr>
                <th>Action</th>
                <th>Issue</th>
                <th>Strategy</th>
                <th>Status</th>
                <th>Columns</th>
                <th>Rows Before</th>
                <th>Rows After</th>
                <th>Message</th>
            </tr>
            {cleaning_rows}
        </table>
    </div>

    <div class="footer">
        Generated by AutoDQ Analytics — Intelligent Data Quality and Analytics Workflow Framework.
    </div>

</div>
</body>
</html>
"""

    def _theme_css(self, style: str) -> str:
        if style == "dark":
            return """
:root {
    --bg: #020617;
    --card: #0f172a;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --primary: #38bdf8;
    --success: #22c55e;
    --hero: linear-gradient(135deg, #020617, #1e3a8a);
    --hero-text: #ffffff;
    --hero-muted: #bfdbfe;
    --pill: rgba(255,255,255,0.12);
    --border: #1e293b;
    --shadow: 0 12px 30px rgba(0,0,0,.35);
    --radius: 18px;
    --radius-lg: 22px;
    --gauge-bg: #1e293b;
    --bar-bg: #1e293b;
    --success-soft: #052e16;
    --success-text: #86efac;
    --warning-soft: #422006;
    --warning-text: #fbbf24;
    --danger-soft: #450a0a;
    --danger-text: #fca5a5;
}
"""

        if style == "print":
            return """
:root {
    --bg: #ffffff;
    --card: #ffffff;
    --text: #111827;
    --muted: #4b5563;
    --primary: #111827;
    --success: #15803d;
    --hero: #ffffff;
    --hero-text: #111827;
    --hero-muted: #4b5563;
    --pill: #f3f4f6;
    --border: #d1d5db;
    --shadow: none;
    --radius: 6px;
    --radius-lg: 6px;
    --gauge-bg: #e5e7eb;
    --bar-bg: #e5e7eb;
    --success-soft: #dcfce7;
    --success-text: #166534;
    --warning-soft: #fef3c7;
    --warning-text: #92400e;
    --danger-soft: #fee2e2;
    --danger-text: #991b1b;
}
"""

        return """
:root {
    --bg: #f4f7fb;
    --card: #ffffff;
    --text: #1f2937;
    --muted: #6b7280;
    --primary: #2563eb;
    --success: #16a34a;
    --hero: linear-gradient(135deg, #1e3a8a, #2563eb);
    --hero-text: #ffffff;
    --hero-muted: #dbeafe;
    --pill: rgba(255,255,255,0.15);
    --border: #e5e7eb;
    --shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    --radius: 18px;
    --radius-lg: 22px;
    --gauge-bg: #e5e7eb;
    --bar-bg: #e5e7eb;
    --success-soft: #dcfce7;
    --success-text: #166534;
    --warning-soft: #fef3c7;
    --warning-text: #92400e;
    --danger-soft: #fee2e2;
    --danger-text: #991b1b;
}
"""

    def _positive_reduction(self, before, after):
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            return max(0, before - after)

        return "N/A"

    def _metric_bar(self, label, before, after):
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            return ""

        max_value = max(before, after, 1)
        before_width = round((before / max_value) * 100, 2)
        after_width = round((after / max_value) * 100, 2)

        return f"""
        <div>
            <div class="bar-row">
                <strong>{label} before</strong>
                <div class="bar-track"><div class="bar-fill" style="width:{before_width}%"></div></div>
                <span>{before}</span>
            </div>
            <div class="bar-row">
                <strong>{label} after</strong>
                <div class="bar-track"><div class="bar-fill" style="width:{after_width}%"></div></div>
                <span>{after}</span>
            </div>
        </div>
        """

    def _comparison_card(self, label, before, after):
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            return ""

        max_value = max(before, after, 1)
        before_height = round((before / max_value) * 100, 2)
        after_height = round((after / max_value) * 100, 2)

        change = after - before
        change_label = f"{change:+}"

        return f"""
        <div class="chart-card">
            <div class="chart-title">{label}</div>

            <div class="mini-bars">
                <div class="mini-bar-wrap">
                    <div class="mini-bar" style="height:{before_height}%"></div>
                    <div class="mini-label">Before</div>
                    <div class="mini-value">{before}</div>
                </div>

                <div class="mini-bar-wrap">
                    <div class="mini-bar after" style="height:{after_height}%"></div>
                    <div class="mini-label">After</div>
                    <div class="mini-value">{after}</div>
                </div>
            </div>

            <div class="metric-small">Change: {change_label}</div>
        </div>
        """

    def _build_rendered_visualization_cards(self, rendered_visualizations):
        if not rendered_visualizations:
            return """
            <div class="rendered-viz-card">
                <div class="viz-title">No rendered chart assets</div>
                <div class="viz-description">
                    No chart image files were generated for this report.
                </div>
            </div>
            """

        cards = []

        for chart in rendered_visualizations:
            if chart.get("image_path") is None:
                cards.append(
                    f"""
                    <div class="rendered-viz-card">
                        <div class="viz-title">{chart.get("title", "Chart")}</div>
                        <div class="viz-description">
                            {chart.get("error", "Chart could not be rendered.")}
                        </div>
                    </div>
                    """
                )
                continue

            image_path = self._relative_chart_path(chart["image_path"])

            cards.append(
                f"""
                <div class="rendered-viz-card">
                    <div class="viz-title">{chart.get("title", "Chart")}</div>
                    <div class="viz-description">{chart.get("description", "")}</div>
                    <img src="{image_path}" alt="{chart.get("title", "Chart")}">
                    <div class="viz-meta">
                        Chart ID: {chart.get("chart_id")} | Type: {chart.get("chart_type")} | Stage: {chart.get("stage")}
                    </div>
                </div>
                """
            )

        return "\n".join(cards)

    def _relative_chart_path(self, image_path):
        image_path = str(image_path)

        if "reports/charts/" in image_path:
            return image_path.split("reports/")[-1]

        return image_path

    def _build_visualization_cards(self, visualization_report):
        if visualization_report is None or not visualization_report.charts:
            return """
            <div class="viz-card">
                <div class="viz-title">No visualizations generated</div>
                <div class="viz-description">
                    Run project.visualize() before generating the report.
                </div>
            </div>
            """

        cards = []

        for chart in visualization_report.charts:
            cards.append(self._render_visualization_card(chart))

        return "\n".join(cards)

    def _render_visualization_card(self, chart):
        if chart.chart_type == "bar":
            visual = self._render_bar_visual(chart)
        elif chart.chart_type == "scatter":
            visual = self._render_scatter_visual(chart)
        else:
            visual = "<p class='viz-description'>Unsupported chart preview.</p>"

        return f"""
        <div class="viz-card">
            <div class="viz-title">{chart.title}</div>
            <div class="viz-description">{chart.description}</div>
            {visual}
            <div class="viz-meta">
                Chart ID: {chart.chart_id} | Type: {chart.chart_type} | Stage: {chart.stage}
            </div>
        </div>
        """

    def _render_bar_visual(self, chart):
        if not chart.data or chart.x is None or chart.y is None:
            return "<p class='viz-description'>No data available.</p>"

        values = [
            row.get(chart.y, 0)
            for row in chart.data
            if isinstance(row.get(chart.y, 0), (int, float))
        ]

        max_value = max(values) if values else 1

        if max_value == 0:
            max_value = 1

        rows = []

        for row in chart.data[:12]:
            label = str(row.get(chart.x, "N/A"))
            value = row.get(chart.y, 0)

            if not isinstance(value, (int, float)):
                value = 0

            width = round((value / max_value) * 100, 2)

            rows.append(
                f"""
                <div class="viz-bar-row">
                    <span class="viz-bar-label">{label}</span>
                    <div class="viz-bar-track">
                        <div class="viz-bar-fill" style="width:{width}%"></div>
                    </div>
                    <strong>{value}</strong>
                </div>
                """
            )

        return "\n".join(rows)

    def _render_scatter_visual(self, chart):
        if not chart.data or chart.x is None or chart.y is None:
            return "<p class='viz-description'>No data available.</p>"

        rows = []

        for row in chart.data[:8]:
            rows.append(
                f"""
                <tr>
                    <td>{row.get(chart.x, "N/A")}</td>
                    <td>{row.get(chart.y, "N/A")}</td>
                </tr>
                """
            )

        return f"""
        <table>
            <tr>
                <th>{chart.x}</th>
                <th>{chart.y}</th>
            </tr>
            {"".join(rows)}
        </table>
        """

    def _build_model_section(self, model):
        if model is None:
            return """
            <div class="section card">
                <h2 class="section-title">Machine Learning Model</h2>
                <p class="metric-small">No model has been trained yet.</p>
            </div>
            """

        metrics = model.metrics

        if model.problem_type == "regression":
            metric_cards = f"""
            {self._model_metric_card("MAE", metrics.mae)}
            {self._model_metric_card("RMSE", metrics.rmse)}
            {self._model_metric_card("R²", metrics.r2)}
            {self._model_metric_card("Problem", model.problem_type)}
            """
        else:
            metric_cards = f"""
            {self._model_metric_card("Accuracy", metrics.accuracy)}
            {self._model_metric_card("Precision", metrics.precision)}
            {self._model_metric_card("Recall", metrics.recall)}
            {self._model_metric_card("F1", metrics.f1)}
            """

        comparison_rows = self._build_model_comparison_rows(model)
        importance_rows = self._build_feature_importance_rows(model)
        recommendation_rows = self._build_model_recommendation_rows(model)

        return f"""
        <div class="section card">
            <h2 class="section-title">Machine Learning Model Summary</h2>

            <div class="model-grid">
                <div class="card">
                    <h3>Best Algorithm</h3>
                    <div class="metric">{pretty_algorithm_name(model.algorithm)}</div>
                    <div class="metric-small">Selected by AutoDQ</div>
                </div>

                <div class="card">
                    <h3>Target</h3>
                    <div class="metric">{model.target}</div>
                    <div class="metric-small">Prediction target</div>
                </div>

                <div class="card">
                    <h3>Features Used</h3>
                    <div class="metric">{model.feature_count}</div>
                    <div class="metric-small">Training features</div>
                </div>

                <div class="card">
                    <h3>Predictions Stored</h3>
                    <div class="metric">{model.prediction_count}</div>
                    <div class="metric-small">Sample predictions</div>
                </div>
            </div>
        </div>

        <div class="section card">
            <h2 class="section-title">Model Performance Metrics</h2>
            <div class="model-grid">
                {metric_cards}
            </div>
        </div>

        <div class="section two-col">
            <div class="card">
                <h2 class="section-title">Model Comparison Leaderboard</h2>
                {comparison_rows}
            </div>

            <div class="card">
                <h2 class="section-title">Top Feature Importance</h2>
                {importance_rows}
            </div>
        </div>

        <div class="section card">
            <h2 class="section-title">Model Recommendations</h2>
            <ul class="recommendation-list">
                {recommendation_rows}
            </ul>
        </div>
        """

    def _model_metric_card(self, title, value):
        return f"""
        <div class="chart-card">
            <div class="chart-title">{title}</div>
            <div class="metric">{value if value is not None else "N/A"}</div>
        </div>
        """

    def _build_model_comparison_rows(self, model):
        if not getattr(model, "model_comparison", None):
            return "<p class='metric-small'>No model comparison available.</p>"

        rows = []

        for item in model.model_comparison:
            medal = (
                "🥇"
                if item.rank == 1
                else "🥈"
                if item.rank == 2
                else "🥉"
                if item.rank == 3
                else item.rank
            )

            rows.append(
                f"""
                <div class="leaderboard-row">
                    <strong>{medal}</strong>
                    <span>{pretty_algorithm_name(item.algorithm)}</span>
                    <strong>{item.primary_metric}: {item.primary_score}</strong>
                </div>
                """
            )

        return "\n".join(rows)

    def _build_feature_importance_rows(self, model):
        if not getattr(model, "feature_importance", None):
            return "<p class='metric-small'>No feature importance available.</p>"

        rows = []
        max_importance = max(
            [item.importance for item in model.feature_importance[:10]] or [1]
        )

        if max_importance == 0:
            max_importance = 1

        for item in model.feature_importance[:10]:
            width = round((item.importance / max_importance) * 100, 2)

            rows.append(
                f"""
                <div class="importance-row">
                    <span>{item.feature}</span>
                    <div class="bar-track">
                        <div class="bar-fill" style="width:{width}%"></div>
                    </div>
                    <strong>{round(item.importance, 4)}</strong>
                </div>
                """
            )

        return "\n".join(rows)

    def _build_model_recommendation_rows(self, model):
        if not getattr(model, "recommendations", None):
            return "<li>No model recommendations available.</li>"

        return "\n".join(
            f"<li>{recommendation}</li>"
            for recommendation in model.recommendations
        )

    def _build_prediction_section(self, prediction):
        if prediction is None:
            return """
            <div class="section card">
                <h2 class="section-title">Prediction Results</h2>
                <p class="metric-small">No predictions generated yet.</p>
            </div>
            """

        rows = []

        for item in prediction.predictions[:20]:
            rows.append(
                f"""
                <tr>
                    <td>{item.row_id}</td>
                    <td>{item.actual}</td>
                    <td>{self._format_prediction_value(item.predicted)}</td>
                    <td>{item.residual}</td>
                    <td>{item.absolute_error}</td>
                    <td>{item.percent_error}</td>
                    <td>{item.confidence}%</td>
                    <td>{", ".join(item.top_features) if item.top_features else "-"}</td>
                </tr>
                """
            )

        return f"""
        <div class="section card">
            <h2 class="section-title">Prediction Results</h2>

            <div class="grid">
                <div class="card">
                    <h3>Predictions</h3>
                    <div class="metric">{prediction.prediction_count}</div>
                    <div class="metric-small">Stored in report</div>
                </div>

                <div class="card">
                    <h3>Target</h3>
                    <div class="metric">{prediction.target}</div>
                    <div class="metric-small">Prediction target</div>
                </div>

                <div class="card">
                    <h3>Algorithm</h3>
                    <div class="metric">{pretty_algorithm_name(prediction.algorithm)}</div>
                    <div class="metric-small">Trained model</div>
                </div>

                <div class="card">
                    <h3>Problem Type</h3>
                    <div class="metric">{prediction.problem_type}</div>
                    <div class="metric-small">ML task</div>
                </div>
            </div>

            <table class="prediction-table">
                <tr>
                    <th>Row</th>
                    <th>Actual</th>
                    <th>Predicted</th>
                    <th>Residual</th>
                    <th>Abs Error</th>
                    <th>% Error</th>
                    <th>Confidence</th>
                    <th>Top Drivers</th>
                </tr>
                {"".join(rows)}
            </table>
        </div>
        """

    def _format_prediction_value(self, value):
        if isinstance(value, (int, float)):
            return round(float(value), 4)

        return value

    def _build_issue_rows(self, diagnosis):
        if diagnosis is None or not diagnosis.issues:
            return '<tr><td colspan="3">No issues available.</td></tr>'

        rows = []

        for issue in diagnosis.issues:
            rows.append(
                f"""
                <tr>
                    <td>{issue.issue_type}</td>
                    <td><span class="badge {issue.severity}">{issue.severity}</span></td>
                    <td>{round(issue.confidence * 100, 2) if issue.confidence else "N/A"}%</td>
                </tr>
                """
            )

        return "\n".join(rows)

    def _build_recommendation_rows(self, recommendations):
        if not recommendations:
            return '<tr><td colspan="6">No recommendations available.</td></tr>'

        rows = []

        for index, rec in enumerate(recommendations, start=1):
            columns = ", ".join(rec.affected_columns) if rec.affected_columns else "-"
            confidence = (
                f"{round(rec.confidence * 100, 2)}%"
                if rec.confidence is not None
                else "N/A"
            )

            reason = rec.reason

            if len(reason) > 280:
                reason = reason[:280] + "..."

            rows.append(
                f"""
                <tr>
                    <td>{index}</td>
                    <td>{rec.issue_type}</td>
                    <td>{rec.strategy}</td>
                    <td>{columns}</td>
                    <td>{confidence}</td>
                    <td>{reason}</td>
                </tr>
                """
            )

        return "\n".join(rows)

    def _build_cleaning_rows(self, cleaning):
        if cleaning is None or not cleaning.actions:
            return '<tr><td colspan="8">No cleaning actions available.</td></tr>'

        rows = []

        for action in cleaning.actions:
            columns = (
                ", ".join(action.affected_columns)
                if action.affected_columns
                else "-"
            )
            status_class = "success" if action.status == "success" else "skipped"

            rows.append(
                f"""
                <tr>
                    <td>{action.action_id}</td>
                    <td>{action.issue_type}</td>
                    <td>{action.strategy}</td>
                    <td><span class="badge {status_class}">{action.status}</span></td>
                    <td>{columns}</td>
                    <td>{action.rows_before}</td>
                    <td>{action.rows_after}</td>
                    <td>{action.message}</td>
                </tr>
                """
            )

        return "\n".join(rows)
