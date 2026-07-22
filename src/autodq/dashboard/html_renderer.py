from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

from autodq.visualization.renderers.matplotlib_renderer import (
    MatplotlibVisualizationRenderer,
)


class DashboardHTMLRenderer:
    """Render a portable AutoDQ dashboard without external dependencies."""

    def __init__(self) -> None:
        self.chart_renderer = MatplotlibVisualizationRenderer()

    def render(self, dashboard) -> str:
        nav_items = [
            ("overview", "Overview"),
            ("quality", "Data quality"),
        ]

        if dashboard.charts:
            nav_items.append(("charts", "Visualizations"))

        if dashboard.cleaning or dashboard.review or dashboard.domain:
            nav_items.append(("workflow", "Cleaning & review"))

        if dashboard.model or dashboard.prediction:
            nav_items.append(("modeling", "Model & predictions"))

        if dashboard.preview or dashboard.columns:
            nav_items.append(("data", "Data explorer"))

        navigation = "".join(
            f'<a href="#{self._e(anchor)}">{self._e(label)}</a>'
            for anchor, label in nav_items
        )
        body = "".join(
            [
                self._overview(dashboard),
                self._quality(dashboard),
                self._charts(dashboard),
                self._workflow(dashboard),
                self._modeling(dashboard),
                self._data_explorer(dashboard),
            ]
        )
        initial_theme = "dark" if dashboard.theme == "dark" else "light"
        dashboard_theme = self._e(dashboard.theme)
        return f"""<!doctype html>
<html lang="en" data-theme="{initial_theme}" data-dashboard-theme="{dashboard_theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{self._e(dashboard.title)}</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f4f7fb;
  --surface: #ffffff;
  --surface-soft: #eef3fa;
  --text: #172033;
  --muted: #64748b;
  --border: #d9e2ef;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --good: #087f5b;
  --good-soft: #d3f9d8;
  --warning: #9a6700;
  --warning-soft: #fff3bf;
  --bad: #c92a2a;
  --bad-soft: #ffe3e3;
  --shadow: 0 12px 32px rgba(30, 50, 80, .08);
}}
html[data-dashboard-theme="executive"] {{
  --bg: #eef3f7;
  --surface: #ffffff;
  --surface-soft: #e8f2f1;
  --text: #14242b;
  --muted: #5b6f78;
  --border: #cfdde1;
  --accent: #0f766e;
  --accent-soft: #ccfbf1;
  --shadow: 0 14px 34px rgba(20, 55, 65, .09);
}}
html[data-theme="dark"] {{
  color-scheme: dark;
  --bg: #0b1120;
  --surface: #111827;
  --surface-soft: #172033;
  --text: #f1f5f9;
  --muted: #a9b5c7;
  --border: #30405a;
  --accent: #60a5fa;
  --accent-soft: #1e3a5f;
  --good: #5ee6b0;
  --good-soft: #153c35;
  --warning: #ffd166;
  --warning-soft: #443819;
  --bad: #ff8787;
  --bad-soft: #4a2024;
  --shadow: 0 14px 36px rgba(0, 0, 0, .24);
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.5;
}}
button, input, select {{ font: inherit; }}
button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible {{
  outline: 3px solid color-mix(in srgb, var(--accent) 42%, transparent);
  outline-offset: 2px;
}}
.shell {{ width: min(1440px, 100%); margin: 0 auto; padding: 24px; }}
.topbar {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 26px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--surface);
  box-shadow: var(--shadow);
}}
.eyebrow {{ margin: 0 0 6px; color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
h1 {{ margin: 0; font-size: clamp(1.65rem, 4vw, 2.65rem); line-height: 1.14; }}
.subtitle {{ max-width: 760px; margin: 10px 0 0; color: var(--muted); }}
.toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }}
.button {{
  appearance: none;
  min-height: 40px;
  padding: 8px 13px;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text);
  background: var(--surface-soft);
  cursor: pointer;
}}
.button:hover {{ border-color: var(--accent); }}
nav {{ display: flex; flex-wrap: wrap; gap: 7px; padding: 14px 2px 4px; }}
nav a {{ color: var(--muted); text-decoration: none; padding: 7px 10px; border-radius: 8px; }}
nav a:hover {{ color: var(--text); background: var(--surface-soft); }}
section {{ margin-top: 26px; scroll-margin-top: 16px; }}
.section-heading {{ display: flex; justify-content: space-between; align-items: end; gap: 18px; margin-bottom: 12px; }}
.section-heading h2 {{ margin: 0; font-size: 1.25rem; }}
.section-heading p {{ margin: 3px 0 0; color: var(--muted); font-size: .9rem; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
.metric {{ padding: 17px; border: 1px solid var(--border); border-radius: 15px; background: var(--surface); }}
.metric-label {{ color: var(--muted); font-size: .82rem; }}
.metric-value {{ margin-top: 4px; font-size: 1.65rem; font-weight: 750; letter-spacing: -.02em; }}
.metric-description {{ margin-top: 4px; color: var(--muted); font-size: .78rem; }}
.metric[data-status="good"] {{ border-top: 3px solid var(--good); }}
.metric[data-status="warning"] {{ border-top: 3px solid var(--warning); }}
.metric[data-status="bad"] {{ border-top: 3px solid var(--bad); }}
.panel {{ padding: 18px; border: 1px solid var(--border); border-radius: 15px; background: var(--surface); }}
.panel h3 {{ margin: 0 0 12px; font-size: 1rem; }}
.panel-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 14px; }}
.empty {{ padding: 28px; border: 1px dashed var(--border); border-radius: 14px; color: var(--muted); text-align: center; background: var(--surface); }}
.badge {{ display: inline-block; padding: 3px 8px; border-radius: 999px; background: var(--surface-soft); color: var(--muted); font-size: .74rem; }}
.badge-good {{ background: var(--good-soft); color: var(--good); }}
.badge-warning {{ background: var(--warning-soft); color: var(--warning); }}
.badge-bad {{ background: var(--bad-soft); color: var(--bad); }}
.controls {{ display: flex; flex-wrap: wrap; gap: 9px; margin-bottom: 13px; }}
.control {{ min-height: 40px; padding: 8px 11px; border: 1px solid var(--border); border-radius: 10px; color: var(--text); background: var(--surface); }}
.charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(440px, 100%), 1fr)); gap: 16px; }}
.chart-card {{ margin: 0; overflow: hidden; border: 1px solid var(--border); border-radius: 16px; background: var(--surface); }}
.chart-card img {{ display: block; width: 100%; height: auto; background: var(--surface); }}
.chart-card figcaption {{ padding: 13px 15px 15px; border-top: 1px solid var(--border); }}
.chart-title {{ font-weight: 700; }}
.chart-description {{ margin-top: 3px; color: var(--muted); font-size: .84rem; }}
.chart-meta {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
.chart-error {{ padding: 36px 18px; color: var(--bad); background: var(--bad-soft); }}
.table-wrap {{ width: 100%; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: .86rem; }}
th, td {{ padding: 10px 11px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
th {{ color: var(--muted); font-size: .73rem; letter-spacing: .04em; text-transform: uppercase; background: var(--surface-soft); }}
tbody tr:last-child td {{ border-bottom: 0; }}
.numeric {{ text-align: right; font-variant-numeric: tabular-nums; }}
.key-value {{ display: grid; grid-template-columns: minmax(120px, .8fr) 1.2fr; gap: 8px 16px; margin: 0; }}
.key-value dt {{ color: var(--muted); }}
.key-value dd {{ margin: 0; font-weight: 650; word-break: break-word; }}
.recommendations {{ margin: 0; padding-left: 20px; }}
.recommendations li + li {{ margin-top: 9px; }}
.hidden {{ display: none !important; }}
footer {{ margin: 30px 0 4px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--muted); font-size: .78rem; }}
@media (max-width: 720px) {{
  .shell {{ padding: 12px; }}
  .topbar {{ padding: 18px; flex-direction: column; }}
  .toolbar {{ justify-content: flex-start; }}
  .section-heading {{ align-items: flex-start; flex-direction: column; }}
  .key-value {{ grid-template-columns: 1fr; gap: 2px; }}
  .key-value dd {{ margin-bottom: 8px; }}
}}
@media print {{
  :root {{ --bg: #fff; --surface: #fff; --text: #111; --muted: #555; --border: #ccc; }}
  .toolbar, nav, .controls {{ display: none !important; }}
  .shell {{ width: 100%; padding: 0; }}
  .topbar, .panel, .metric, .chart-card {{ box-shadow: none; break-inside: avoid; }}
}}
</style>
</head>
<body>
<main class="shell">
  <header class="topbar">
    <div>
      <p class="eyebrow">AutoDQ dashboard · {self._e(dashboard.stage)} stage</p>
      <h1>{self._e(dashboard.title)}</h1>
      <p class="subtitle">{self._e(dashboard.subtitle)}</p>
    </div>
    <div class="toolbar" aria-label="Dashboard actions">
      <button class="button" type="button" id="theme-toggle">Toggle theme</button>
      <button class="button" type="button" id="print-dashboard">Print / PDF</button>
    </div>
  </header>
  <nav aria-label="Dashboard sections">{navigation}</nav>
  {body}
  <footer>
    Generated by AutoDQ at {self._e(dashboard.generated_at.isoformat(timespec="seconds"))}.
    Dataset: {self._e(dashboard.dataset)}.
  </footer>
</main>
<script>
(function () {{
  "use strict";
  var root = document.documentElement;
  var themeButton = document.getElementById("theme-toggle");
  var printButton = document.getElementById("print-dashboard");
  if (themeButton) {{
    themeButton.addEventListener("click", function () {{
      root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    }});
  }}
  if (printButton) {{
    printButton.addEventListener("click", function () {{ window.print(); }});
  }}

  var chartSearch = document.getElementById("chart-search");
  var chartType = document.getElementById("chart-type");
  var chartStage = document.getElementById("chart-stage");
  var chartStatus = document.getElementById("chart-status");
  function filterCharts() {{
    var query = chartSearch ? chartSearch.value.toLowerCase().trim() : "";
    var type = chartType ? chartType.value : "all";
    var stage = chartStage ? chartStage.value : "all";
    var visible = 0;
    document.querySelectorAll(".chart-card").forEach(function (card) {{
      var matches = (!query || card.dataset.search.indexOf(query) !== -1) &&
        (type === "all" || card.dataset.chartType === type) &&
        (stage === "all" || card.dataset.chartStage === stage);
      card.classList.toggle("hidden", !matches);
      if (matches) {{ visible += 1; }}
    }});
    if (chartStatus) {{ chartStatus.textContent = visible + " chart" + (visible === 1 ? "" : "s") + " shown"; }}
  }}
  [chartSearch, chartType, chartStage].forEach(function (control) {{
    if (control) {{ control.addEventListener("input", filterCharts); }}
  }});
  filterCharts();

  var dataSearch = document.getElementById("data-search");
  if (dataSearch) {{
    dataSearch.addEventListener("input", function () {{
      var query = dataSearch.value.toLowerCase().trim();
      document.querySelectorAll("#preview-table tbody tr").forEach(function (row) {{
        row.classList.toggle("hidden", query && row.textContent.toLowerCase().indexOf(query) === -1);
      }});
    }});
  }}

  var download = document.getElementById("download-preview");
  if (download) {{
    download.addEventListener("click", function () {{
      var rows = Array.from(document.querySelectorAll("#preview-table tr"));
      var csv = rows.map(function (row) {{
        return Array.from(row.querySelectorAll("th,td")).map(function (cell) {{
          return '"' + cell.textContent.replace(/"/g, '""') + '"';
        }}).join(",");
      }}).join("\\n");
      var url = URL.createObjectURL(new Blob([csv], {{ type: "text/csv;charset=utf-8" }}));
      var link = document.createElement("a");
      link.href = url;
      link.download = "autodq-dashboard-preview.csv";
      link.click();
      URL.revokeObjectURL(url);
    }});
  }}
}}());
</script>
</body>
</html>
"""

    def save(
        self,
        dashboard,
        output: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        output_path = Path(output).expanduser()

        if output_path.suffix.lower() != ".html":
            raise ValueError("Dashboard output must end with .html.")

        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Dashboard already exists: {output_path}. "
                "Pass overwrite=True to replace it."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(dashboard), encoding="utf-8")
        return output_path.resolve()

    def _overview(self, dashboard) -> str:
        cards = "".join(
            f"""<article class="metric" data-status="{self._e(item.status)}">
  <div class="metric-label">{self._e(item.label)}</div>
  <div class="metric-value">{self._e(item.display)}</div>
  <div class="metric-description">{self._e(item.description)}</div>
</article>"""
            for item in dashboard.metrics
        )
        return f"""<section id="overview">
  <div class="section-heading"><div><h2>Overview</h2><p>The selected dataset stage at a glance.</p></div></div>
  <div class="metric-grid">{cards}</div>
</section>"""

    def _quality(self, dashboard) -> str:
        issue_rows = "".join(
            f"""<tr>
  <td><span class="badge {self._severity_badge(item.get('severity'))}">{self._e(item.get('severity', 'unknown'))}</span></td>
  <td>{self._e(str(item.get('issue_type', '')).replace('_', ' ').title())}</td>
  <td>{self._e(item.get('message', ''))}</td>
  <td>{self._e(', '.join(item.get('affected_columns') or []) or '—')}</td>
</tr>"""
            for item in dashboard.issues
        )
        issues = (
            f"""<div class="panel table-wrap"><table>
<thead><tr><th>Severity</th><th>Issue</th><th>Finding</th><th>Columns</th></tr></thead>
<tbody>{issue_rows}</tbody></table></div>"""
            if issue_rows
            else '<div class="empty">No data-quality issues were detected.</div>'
        )
        recommendation_items = "".join(
            f"<li><strong>{self._e(item.get('strategy', 'Review'))}:</strong> {self._e(item.get('reason', item.get('action', '')))}</li>"
            for item in dashboard.recommendations[:12]
        )
        recommendations = ""

        if recommendation_items:
            recommendations = f"""<div class="panel" style="margin-top:14px">
<h3>Recommended actions</h3><ol class="recommendations">{recommendation_items}</ol></div>"""

        return f"""<section id="quality">
  <div class="section-heading"><div><h2>Data quality</h2><p>{dashboard.issue_count} diagnosed issue{'' if dashboard.issue_count == 1 else 's'}.</p></div></div>
  {issues}{recommendations}
</section>"""

    def _charts(self, dashboard) -> str:
        if not dashboard.charts:
            return ""

        chart_types = sorted({chart.chart_type for chart in dashboard.charts})
        chart_stages = sorted({chart.stage for chart in dashboard.charts})
        type_options = "".join(
            f'<option value="{self._e(item)}">{self._e(item.replace("_", " ").title())}</option>'
            for item in chart_types
        )
        stage_options = "".join(
            f'<option value="{self._e(item)}">{self._e(item.title())}</option>'
            for item in chart_stages
        )
        cards = "".join(self._chart_card(dashboard, chart) for chart in dashboard.charts)
        return f"""<section id="charts">
  <div class="section-heading">
    <div><h2>Visualizations</h2><p id="chart-status">{dashboard.chart_count} charts shown</p></div>
  </div>
  <div class="controls" aria-label="Visualization filters">
    <input class="control" id="chart-search" type="search" placeholder="Search charts" aria-label="Search charts">
    <select class="control" id="chart-type" aria-label="Filter by chart type"><option value="all">All chart types</option>{type_options}</select>
    <select class="control" id="chart-stage" aria-label="Filter by data stage"><option value="all">All stages</option>{stage_options}</select>
  </div>
  <div class="charts-grid">{cards}</div>
</section>"""

    def _chart_card(self, dashboard, chart) -> str:
        try:
            chart_to_render = chart.clone()

            if chart_to_render.style.theme is None:
                chart_to_render.style.theme = (
                    "dark" if dashboard.theme == "dark" else "light"
                )

            image_bytes = self.chart_renderer.render_bytes(
                chart_to_render,
                format="png",
            )
            encoded = base64.b64encode(image_bytes).decode("ascii")
            visual = (
                f'<img src="data:image/png;base64,{encoded}" '
                f'alt="{self._e(chart.title)}">'
            )
        except Exception as error:
            warning = f"{chart.chart_id}: {error}"

            if warning not in dashboard.warnings:
                dashboard.warnings.append(warning)

            visual = (
                '<div class="chart-error" role="alert">'
                f"Chart could not be rendered: {self._e(error)}</div>"
            )

        search = " ".join(
            [chart.title, chart.description, chart.chart_type, chart.stage]
        ).lower()
        return f"""<figure class="chart-card" data-chart-type="{self._e(chart.chart_type)}" data-chart-stage="{self._e(chart.stage)}" data-search="{self._e(search)}">
  {visual}
  <figcaption>
    <div class="chart-title">{self._e(chart.title)}</div>
    <div class="chart-description">{self._e(chart.description)}</div>
    <div class="chart-meta"><span class="badge">{self._e(chart.chart_type)}</span><span class="badge">{self._e(chart.stage)}</span></div>
  </figcaption>
</figure>"""

    def _workflow(self, dashboard) -> str:
        panels = []

        if dashboard.cleaning:
            panels.append(
                self._summary_panel(
                    "Cleaning execution",
                    {
                        "Actions": dashboard.cleaning.get("action_count", 0),
                        "Successful": dashboard.cleaning.get("successful_actions", 0),
                    },
                )
            )

        if dashboard.review:
            panels.append(
                self._summary_panel(
                    "Interactive review",
                    {
                        "Pending": dashboard.review.get("pending_count", 0),
                        "Approved": dashboard.review.get("approved_count", 0),
                        "Rejected": dashboard.review.get("rejected_count", 0),
                        "Manual changes": dashboard.review.get("audit_count", 0),
                        "Reviewed outliers": dashboard.review.get("outlier_count", 0),
                    },
                )
            )

        if dashboard.domain:
            panels.append(
                self._summary_panel(
                    "Domain validation",
                    {
                        "Rules": dashboard.domain.get("rule_count", 0),
                        "Violations": dashboard.domain.get("violation_count", 0),
                        "Invalid rows": dashboard.domain.get("invalid_row_count", 0),
                        "Status": "Valid" if dashboard.domain.get("is_valid") else "Needs review",
                    },
                )
            )

        if dashboard.automation:
            panels.append(
                self._summary_panel(
                    "Automatic workflow",
                    {
                        "Mode": dashboard.automation.get("mode", "—"),
                        "Status": "Completed" if dashboard.automation.get("success") else "Failed",
                        "Completed stages": dashboard.automation.get("completed_count", 0),
                        "Reused stages": dashboard.automation.get("reused_count", 0),
                        "Failed stages": dashboard.automation.get("failed_count", 0),
                    },
                )
            )

        if not panels:
            return ""

        return f"""<section id="workflow">
  <div class="section-heading"><div><h2>Cleaning & review</h2><p>Decision, audit, and validation status.</p></div></div>
  <div class="panel-grid">{''.join(panels)}</div>
</section>"""

    def _modeling(self, dashboard) -> str:
        if not dashboard.model and not dashboard.prediction:
            return ""

        panels = []

        if dashboard.model:
            metrics = {
                key.upper(): self._format_number(value)
                for key, value in dashboard.model.get("metrics", {}).items()
                if key not in {"problem_type", "algorithm"} and value is not None
            }
            details = {
                "Target": dashboard.model.get("target"),
                "Problem type": dashboard.model.get("problem_type"),
                "Algorithm": dashboard.model.get("algorithm"),
                "Features": dashboard.model.get("feature_count"),
                **metrics,
            }
            panels.append(self._summary_panel("Model", details))

        if dashboard.prediction:
            details = {
                "Predictions": dashboard.prediction.get("prediction_count"),
                "Uncertainty": (
                    dashboard.prediction.get("uncertainty_method")
                    if dashboard.prediction.get("uncertainty_available")
                    else "Unavailable"
                ),
                "Confidence level": self._format_percent(
                    dashboard.prediction.get("confidence_level")
                ),
                "Empirical coverage": self._format_percent(
                    dashboard.prediction.get("empirical_coverage")
                ),
                "Mean confidence": self._format_percent(
                    dashboard.prediction.get("mean_confidence")
                ),
                "Low-confidence rows": dashboard.prediction.get("low_confidence_count"),
            }
            panels.append(self._summary_panel("Predictions", details))

        return f"""<section id="modeling">
  <div class="section-heading"><div><h2>Model & predictions</h2><p>Latest trained-model and uncertainty results.</p></div></div>
  <div class="panel-grid">{''.join(panels)}</div>
</section>"""

    def _data_explorer(self, dashboard) -> str:
        if not dashboard.preview and not dashboard.columns:
            return ""

        column_rows = "".join(
            f"""<tr><td>{self._e(item.get('column'))}</td><td>{self._e(item.get('dtype'))}</td>
<td>{self._e(item.get('semantic_type') or '—')}</td><td class="numeric">{self._e(item.get('missing'))}</td>
<td class="numeric">{self._e(item.get('unique'))}</td></tr>"""
            for item in dashboard.columns
        )
        columns = f"""<div class="panel"><h3>Column profile</h3><div class="table-wrap"><table>
<thead><tr><th>Column</th><th>Type</th><th>Semantic type</th><th class="numeric">Missing</th><th class="numeric">Unique</th></tr></thead>
<tbody>{column_rows}</tbody></table></div></div>"""
        preview = ""

        if dashboard.preview:
            headers = list(dashboard.preview[0])
            header_cells = "".join(f"<th>{self._e(item)}</th>" for item in headers)
            rows = "".join(
                "<tr>" + "".join(
                    f"<td>{self._e(self._display_value(row.get(column)))}</td>"
                    for column in headers
                ) + "</tr>"
                for row in dashboard.preview
            )
            preview = f"""<div class="panel" style="margin-top:14px"><h3>Data preview</h3>
<div class="controls"><input class="control" id="data-search" type="search" placeholder="Filter preview rows" aria-label="Filter preview rows">
<button class="button" type="button" id="download-preview">Download preview CSV</button></div>
<div class="table-wrap"><table id="preview-table"><thead><tr>{header_cells}</tr></thead><tbody>{rows}</tbody></table></div></div>"""

        return f"""<section id="data">
  <div class="section-heading"><div><h2>Data explorer</h2><p>Column-level structure and a bounded row preview.</p></div></div>
  {columns}{preview}
</section>"""

    def _summary_panel(self, title: str, values: dict[str, Any]) -> str:
        items = "".join(
            f"<dt>{self._e(label)}</dt><dd>{self._e(self._display_value(value))}</dd>"
            for label, value in values.items()
            if value is not None
        )
        return f'<article class="panel"><h3>{self._e(title)}</h3><dl class="key-value">{items}</dl></article>'

    @staticmethod
    def _format_number(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.4f}"

        return str(value)

    @staticmethod
    def _format_percent(value: Any) -> str:
        if value is None:
            return "—"

        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _display_value(value: Any) -> str:
        if value is None:
            return "—"

        if isinstance(value, bool):
            return "Yes" if value else "No"

        if isinstance(value, float):
            return f"{value:.4f}"

        return str(value)

    @staticmethod
    def _severity_badge(severity: Any) -> str:
        normalized = str(severity).lower()

        if normalized in {"critical", "high"}:
            return "badge-bad"

        if normalized in {"medium", "low"}:
            return "badge-warning"

        return "badge-good"

    @staticmethod
    def _e(value: Any) -> str:
        return html.escape(str(value), quote=True)
