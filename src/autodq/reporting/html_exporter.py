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
    .grid, .two-col {{
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
        <p>Automated profiling, diagnosis, evidence-aware recommendations, cleaning validation, and workflow summary.</p>
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
            confidence = f"{round(rec.confidence * 100, 2)}%" if rec.confidence is not None else "N/A"

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
            columns = ", ".join(action.affected_columns) if action.affected_columns else "-"
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