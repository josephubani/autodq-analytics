from __future__ import annotations

from html import escape
from typing import Any

from autodq.review.models import serializable_value


class ReviewNotebookRenderer:
    """Render compact, dependency-free cleaning review cards."""

    def render_review(self, review) -> str:
        action_rows = []

        for action in review.actions:
            columns = ", ".join(action.affected_columns) or "-"
            action_rows.append(
                "<tr>"
                f"<td>{action.action_id}</td>"
                f"<td>{self._value(action.issue_type)}</td>"
                f"<td>{self._value(action.strategy)}</td>"
                f"<td>{self._value(columns)}</td>"
                f"<td><span class='adq-status adq-{self._status(action.status)}'>"
                f"{self._value(action.status)}</span></td>"
                "</tr>"
            )

        recent_audit = review.audit_trail[-8:]
        audit_rows = [
            "<tr>"
            f"<td>{item.audit_id}</td>"
            f"<td>{self._value(item.event_type)}</td>"
            f"<td>{self._value(item.row_index)}</td>"
            f"<td>{self._value(item.column)}</td>"
            f"<td>{self._value(item.reason or '-')}</td>"
            "</tr>"
            for item in recent_audit
        ]
        outlier_count = (
            review.outlier_report.outlier_count
            if review.outlier_report is not None
            else 0
        )
        violation_count = (
            review.domain_report.violation_count
            if review.domain_report is not None
            else 0
        )
        return self._shell(
            title="Interactive Cleaning & Domain Review",
            body=f"""
            <div class="adq-grid">
                {self._metric("Pending", review.pending_count)}
                {self._metric("Approved", review.approved_count)}
                {self._metric("Rejected", review.rejected_count)}
                {self._metric("Outliers", outlier_count)}
                {self._metric("Domain violations", violation_count)}
                {self._metric("Audit entries", review.audit_count)}
            </div>
            <p class="adq-help">
                Use <code>review.approve([1, 3])</code>,
                <code>review.reject(2)</code>,
                <code>review.edit_row(index, {{...}})</code>, and
                <code>review.treat_outliers(column)</code>.
            </p>
            <h4>Cleaning decisions</h4>
            <div class="adq-table-wrap"><table>
                <thead><tr><th>ID</th><th>Issue</th><th>Strategy</th>
                <th>Columns</th><th>Status</th></tr></thead>
                <tbody>{''.join(action_rows) or self._empty_row(5)}</tbody>
            </table></div>
            <h4>Recent audit activity</h4>
            <div class="adq-table-wrap"><table>
                <thead><tr><th>ID</th><th>Event</th><th>Row</th>
                <th>Column</th><th>Reason</th></tr></thead>
                <tbody>{''.join(audit_rows) or self._empty_row(5)}</tbody>
            </table></div>
            """,
        )

    def render_domain_report(self, report) -> str:
        rows = [
            "<tr>"
            f"<td>{self._value(item.rule_id)}</td>"
            f"<td>{self._value(item.row_index)}</td>"
            f"<td>{self._value(item.column)}</td>"
            f"<td>{self._value(item.value)}</td>"
            f"<td>{self._value(item.message)}</td>"
            "</tr>"
            for item in report.violations[:100]
        ]
        return self._shell(
            title="Domain Validation",
            body=f"""
            <div class="adq-grid">
                {self._metric("Rules", report.rule_count)}
                {self._metric("Checked rows", report.checked_rows)}
                {self._metric("Invalid rows", report.invalid_row_count)}
                {self._metric("Violations", report.violation_count)}
            </div>
            <div class="adq-table-wrap"><table>
                <thead><tr><th>Rule</th><th>Row</th><th>Column</th>
                <th>Value</th><th>Violation</th></tr></thead>
                <tbody>{''.join(rows) or self._empty_row(5, 'No violations')}</tbody>
            </table></div>
            """,
        )

    def render_outlier_report(self, report) -> str:
        rows = [
            "<tr>"
            f"<td>{self._value(item.row_index)}</td>"
            f"<td>{self._value(item.column)}</td>"
            f"<td>{item.value:.4f}</td>"
            f"<td>{item.lower_bound:.4f}</td>"
            f"<td>{item.upper_bound:.4f}</td>"
            f"<td>{self._value(item.direction)}</td>"
            "</tr>"
            for item in report.records[:100]
        ]
        return self._shell(
            title="Outlier Review",
            body=f"""
            <div class="adq-grid">
                {self._metric("Method", report.method)}
                {self._metric("Columns checked", len(report.checked_columns))}
                {self._metric("Columns affected", report.column_count)}
                {self._metric("Outliers", report.outlier_count)}
            </div>
            <div class="adq-table-wrap"><table>
                <thead><tr><th>Row</th><th>Column</th><th>Value</th>
                <th>Lower</th><th>Upper</th><th>Direction</th></tr></thead>
                <tbody>{''.join(rows) or self._empty_row(6, 'No outliers')}</tbody>
            </table></div>
            """,
        )

    def render_action_previews(self, previews) -> str:
        sections = []

        for item in previews:
            before = self._records_table(item.before_sample)
            after = self._records_table(item.after_sample)
            sections.append(
                f"""
                <div class="adq-preview">
                    <h4>Action {item.action_id}: {self._value(item.issue_type)}</h4>
                    <p><strong>Strategy:</strong> {self._value(item.strategy)} ·
                    <strong>Status:</strong> {self._value(item.status)} ·
                    <strong>Affected rows:</strong> {item.affected_row_count}</p>
                    <details><summary>Preview details</summary>
                    <pre>{self._value(item.details)}</pre></details>
                    <div class="adq-two-col">
                        <div><h5>Before</h5>{before}</div>
                        <div><h5>After</h5>{after}</div>
                    </div>
                </div>
                """
            )

        return self._shell(
            title="Interactive Cleaning Preview",
            body="".join(sections) or "<p>No matching actions.</p>",
        )

    def _records_table(self, records: list[dict[str, Any]]) -> str:
        if not records:
            return "<p class='adq-help'>No sample rows.</p>"

        columns = []

        for record in records:
            for column in record:
                if column not in columns:
                    columns.append(column)

        header = "".join(f"<th>{self._value(item)}</th>" for item in columns)
        rows = []

        for record in records:
            cells = "".join(
                f"<td>{self._value(record.get(column))}</td>"
                for column in columns
            )
            rows.append(f"<tr>{cells}</tr>")

        return (
            "<div class='adq-table-wrap'><table><thead><tr>"
            f"{header}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )

    def _shell(self, title: str, body: str) -> str:
        return f"""
        <style>
        .adq-review {{font-family:Inter,Arial,sans-serif;border:1px solid #dbeafe;
          border-radius:14px;padding:18px;background:#fff;color:#172033}}
        .adq-review h3 {{margin:0 0 14px;color:#0f3d8a}}
        .adq-review h4 {{margin:18px 0 8px}}
        .adq-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));
          gap:9px;margin-bottom:12px}}
        .adq-metric {{background:#f4f8ff;border-radius:10px;padding:10px}}
        .adq-metric strong {{display:block;font-size:1.25rem;color:#0f3d8a}}
        .adq-metric span,.adq-help {{font-size:.83rem;color:#667085}}
        .adq-table-wrap {{overflow-x:auto}}
        .adq-review table {{border-collapse:collapse;width:100%;font-size:.83rem}}
        .adq-review th,.adq-review td {{padding:8px;border-bottom:1px solid #e7edf6;
          text-align:left;vertical-align:top}}
        .adq-review th {{background:#f8fafc;color:#344054}}
        .adq-status {{padding:3px 8px;border-radius:999px;font-weight:600}}
        .adq-approved {{background:#dcfce7;color:#166534}}
        .adq-rejected {{background:#fee2e2;color:#991b1b}}
        .adq-pending {{background:#fef3c7;color:#92400e}}
        .adq-two-col {{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
        .adq-preview {{border-top:1px solid #e7edf6;padding-top:8px}}
        .adq-review pre {{white-space:pre-wrap;font-size:.78rem}}
        @media(max-width:760px) {{.adq-two-col {{grid-template-columns:1fr}}}}
        </style>
        <div class="adq-review"><h3>{self._value(title)}</h3>{body}</div>
        """

    def _metric(self, label: str, value: Any) -> str:
        return (
            "<div class='adq-metric'>"
            f"<strong>{self._value(value)}</strong>"
            f"<span>{self._value(label)}</span></div>"
        )

    @staticmethod
    def _empty_row(columns: int, message: str = "No records") -> str:
        return f"<tr><td colspan='{columns}'>{escape(message)}</td></tr>"

    @staticmethod
    def _status(status: str) -> str:
        normalized = str(status).lower()
        return normalized if normalized in {"pending", "approved", "rejected"} else "pending"

    @staticmethod
    def _value(value: Any) -> str:
        return escape(str(serializable_value(value)))
