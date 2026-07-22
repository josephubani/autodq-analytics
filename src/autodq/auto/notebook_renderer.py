from __future__ import annotations

from html import escape


class AutoNotebookRenderer:
    """Render a compact project.auto() run summary in notebooks."""

    def render(self, result) -> str:
        rows = []

        for stage in result.stages:
            status = self._status(stage.status)
            summary = ", ".join(
                f"{key}={value}"
                for key, value in stage.summary.items()
            ) or "-"
            rows.append(
                "<tr>"
                f"<td>{escape(stage.name)}</td>"
                f"<td><span class='adq-auto-status adq-auto-{status}'>"
                f"{escape(stage.status)}</span></td>"
                f"<td>{escape(stage.message)}</td>"
                f"<td>{escape(summary)}</td>"
                f"<td>{stage.duration_seconds:.3f}s</td>"
                "</tr>"
            )

        next_actions = "".join(
            f"<li>{escape(item)}</li>" for item in result.next_actions
        ) or "<li>No follow-up action is required.</li>"
        overall = "Complete" if result.success else "Needs attention"
        overall_class = "completed" if result.success else "failed"
        return f"""
        <style>
        .adq-auto {{font-family:Inter,Arial,sans-serif;border:1px solid #dbeafe;
          border-radius:14px;padding:18px;background:#fff;color:#172033}}
        .adq-auto h3 {{margin:0 0 14px;color:#0f3d8a}}
        .adq-auto-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));
          gap:9px;margin-bottom:14px}}
        .adq-auto-card {{background:#f4f8ff;border-radius:10px;padding:10px}}
        .adq-auto-card strong {{display:block;font-size:1.22rem;color:#0f3d8a}}
        .adq-auto-card span {{font-size:.8rem;color:#667085}}
        .adq-auto-table {{overflow-x:auto}}
        .adq-auto table {{border-collapse:collapse;width:100%;font-size:.82rem}}
        .adq-auto th,.adq-auto td {{padding:8px;border-bottom:1px solid #e7edf6;
          text-align:left;vertical-align:top}}
        .adq-auto th {{background:#f8fafc;color:#344054}}
        .adq-auto-status {{padding:3px 8px;border-radius:999px;font-weight:600}}
        .adq-auto-completed {{background:#dcfce7;color:#166534}}
        .adq-auto-reused {{background:#dbeafe;color:#1e40af}}
        .adq-auto-skipped {{background:#f3f4f6;color:#4b5563}}
        .adq-auto-failed {{background:#fee2e2;color:#991b1b}}
        .adq-auto-next {{background:#fff7ed;border-radius:10px;padding:10px 14px;margin-top:14px}}
        </style>
        <div class="adq-auto">
            <h3>AutoDQ Automatic Workflow</h3>
            <div class="adq-auto-grid">
                {self._card("Status", overall, overall_class)}
                {self._card("Mode", result.config.mode)}
                {self._card("Completed", result.completed_count)}
                {self._card("Reused", result.reused_count)}
                {self._card("Skipped", result.skipped_count)}
                {self._card("Failed", result.failed_count)}
                {self._card("Duration", f'{result.duration_seconds:.2f}s')}
            </div>
            <div class="adq-auto-table"><table>
                <thead><tr><th>Stage</th><th>Status</th><th>Message</th>
                <th>Summary</th><th>Time</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table></div>
            <div class="adq-auto-next"><strong>Next actions</strong>
                <ul>{next_actions}</ul></div>
        </div>
        """

    @staticmethod
    def _card(label: str, value, css_class: str = "") -> str:
        return (
            f"<div class='adq-auto-card {escape(css_class)}'>"
            f"<strong>{escape(str(value))}</strong>"
            f"<span>{escape(label)}</span></div>"
        )

    @staticmethod
    def _status(status: str) -> str:
        if status in {"completed", "reused", "skipped", "failed"}:
            return status

        return "skipped"
