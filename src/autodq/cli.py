from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd

from autodq.commands.errors import ADQLError
from autodq.commands.models import serializable_value
from autodq.commands.runner import ADQLFileRunner
from autodq.vscode import extension_path, install_extension


_NOTEBOOK_DEFAULT_OUTPUT_ROWS = 25
_NOTEBOOK_DEFAULT_OUTPUT_CHARACTERS = 12_000
_NOTEBOOK_MAX_OUTPUT_COLUMNS = 20
_NOTEBOOK_MAX_OUTPUTS = 30


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autodq",
        description="Run standalone AutoDQ ADQL analytics files.",
    )
    parser.add_argument("--version", action="version", version="AutoDQ 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Run a .adql file.")
    run.add_argument("path", help="Path to the .adql file.")
    run.add_argument("--dataset", help="Override or supply the dataset path.")
    run.add_argument("--target", help="Override the target column.")
    selection = run.add_mutually_exclusive_group()
    selection.add_argument("--cell", type=int, help="Run only cell N.")
    selection.add_argument(
        "--through-cell",
        type=int,
        help="Run cells 1 through N in one project session.",
    )
    run.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with later statements after a failed statement.",
    )
    run.add_argument(
        "--json",
        dest="json_path",
        help="Save the structured run result as JSON.",
    )
    run.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing --json output file.",
    )
    run.add_argument(
        "--notebook-json",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    kernel = commands.add_parser("kernel", help=argparse.SUPPRESS)
    kernel.add_argument("path")

    validate = commands.add_parser(
        "validate",
        help="Validate a .adql file without running it.",
    )
    validate.add_argument("path")
    validate.add_argument("--dataset")

    cells = commands.add_parser("cells", help="List cells in a .adql file.")
    cells.add_argument("path")

    vscode = commands.add_parser(
        "vscode",
        help="Inspect or install the bundled ADQL VS Code extension.",
    )
    vscode_commands = vscode.add_subparsers(
        dest="vscode_command",
        required=True,
    )
    vscode_commands.add_parser("path", help="Print the extension source path.")
    install = vscode_commands.add_parser(
        "install",
        help="Install ADQL language and notebook support for VS Code.",
    )
    install.add_argument("--destination")
    install.add_argument("--overwrite", action="store_true")

    return parser


def _normalise_argv(argv: list[str]) -> list[str]:
    if argv and Path(argv[0]).suffix.lower() == ".adql":
        return ["run", *argv]

    return argv


def _render_run(result) -> None:
    for cell_run in result.cell_runs:
        cell = cell_run.cell
        print(f"\nCell {cell.number}: {cell.title}")

        if not cell_run.result.results:
            print("  No executable statements.")
            continue

        for statement_result in cell_run.result.results:
            prefix = "OK" if statement_result.success else "ERROR"
            print(f"  [{prefix}] {statement_result.message}")

            if statement_result.data is not None:
                _print_dataframe(statement_result.data)
            elif statement_result.error_message:
                print(f"    {statement_result.error_message}")

    status = "completed" if result.success else "failed"
    print(
        f"\nADQL {status}: {result.completed_cell_count}/"
        f"{len(result.cell_runs)} cells in {result.duration_seconds:.4f}s"
    )


def _print_dataframe(frame: pd.DataFrame, limit: int = 50) -> None:
    with pd.option_context(
        "display.max_rows",
        limit,
        "display.max_columns",
        30,
        "display.width",
        160,
    ):
        print(frame.head(limit).to_string(index=False))

    if len(frame) > limit:
        print(f"    ... {len(frame) - limit:,} more row(s)")


def _save_json(result, path: str, *, overwrite: bool) -> Path:
    output_path = Path(path).expanduser().resolve()

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {output_path}. Use --overwrite to replace it."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def _notebook_payload(
    result,
    *,
    max_output_rows: int | None = None,
    max_output_characters: int | None = None,
) -> dict:
    """Build the rich-output protocol consumed by the VS Code notebook."""
    row_limit = _notebook_limit(
        max_output_rows,
        default=_NOTEBOOK_DEFAULT_OUTPUT_ROWS,
        minimum=5,
        maximum=500,
    )
    character_limit = _notebook_limit(
        max_output_characters,
        default=_NOTEBOOK_DEFAULT_OUTPUT_CHARACTERS,
        minimum=2_000,
        maximum=200_000,
    )
    cell_run = result.cell_runs[-1] if result.cell_runs else None
    outputs = []

    if cell_run is not None:
        for statement_result in cell_run.result.results:
            status = "OK" if statement_result.success else "ERROR"
            outputs.append(
                {
                    "mime": "text/plain",
                    "data": f"[{status}] {statement_result.message}",
                }
            )

            if statement_result.data is not None:
                outputs.append(
                    _notebook_html_output(
                        _dataframe_html(
                            statement_result.data,
                            limit=row_limit,
                        ),
                        title=(
                            f"{statement_result.statement.kind.title()} result"
                        ),
                    )
                )

            rich_value_rendered = False

            if (
                statement_result.statement.kind == "PROFILE"
                and isinstance(statement_result.value, dict)
            ):
                outputs.append(
                    _notebook_html_output(
                        _profile_html(
                            statement_result.value,
                            limit=row_limit,
                        ),
                        title="Dataset profile",
                    )
                )
                rich_value_rendered = True

            if (
                statement_result.statement.kind == "DIAGNOSE"
                and statement_result.value is not None
            ):
                outputs.append(
                    _notebook_html_output(
                        _diagnosis_html(
                            statement_result.value,
                            limit=row_limit,
                        ),
                        title="Data quality diagnosis",
                    )
                )
                rich_value_rendered = True

            if (
                statement_result.statement.kind == "RECOMMEND"
                and statement_result.value is not None
            ):
                outputs.append(
                    _notebook_html_output(
                        _recommendations_html(
                            statement_result.value,
                            limit=row_limit,
                        ),
                        title="Cleaning recommendations",
                    )
                )
                rich_value_rendered = True

            if (
                statement_result.statement.kind == "VISUALIZE"
                and statement_result.value is not None
            ):
                outputs.extend(
                    _visualization_outputs(statement_result.value)
                )
                rich_value_rendered = True

            if (
                statement_result.statement.kind == "SHAP"
                and statement_result.value is not None
            ):
                outputs.append(
                    _figure_output(
                        statement_result.value,
                        title="SHAP visualization",
                    )
                )
                rich_value_rendered = True

            if (
                statement_result.statement.kind == "BLUE"
                and statement_result.statement.parameters.get("action") == "visualize"
                and statement_result.value is not None
            ):
                outputs.extend(_visualization_outputs(statement_result.value))
                rich_value_rendered = True

            if (
                statement_result.statement.kind == "GALLERY"
                and statement_result.statement.parameters.get("action")
                in {"get", "customize"}
                and statement_result.value is not None
            ):
                outputs.extend(_visualization_outputs(statement_result.value))
                rich_value_rendered = True

            if statement_result.value is not None and not rich_value_rendered:
                outputs.append(
                    _notebook_html_output(
                        _value_html(
                            statement_result.statement.kind,
                            statement_result.value,
                            item_limit=row_limit,
                            character_limit=character_limit,
                        ),
                        title=(
                            f"{statement_result.statement.kind.title()} output"
                        ),
                    )
                )

            if statement_result.error_message:
                outputs.append(
                    {
                        "mime": "text/plain",
                        "data": statement_result.error_message,
                    }
                )

    outputs = _limit_notebook_outputs(
        outputs,
        character_limit=character_limit,
    )

    return {
        "protocol": "autodq-notebook-v1",
        "success": result.success,
        "cell": (
            {
                "number": cell_run.cell.number,
                "title": cell_run.cell.title,
            }
            if cell_run is not None
            else None
        ),
        "outputs": outputs,
    }


def _notebook_html_output(content: str, *, title: str) -> dict:
    return {
        "mime": "text/html",
        "data": _collapsible_html(content, title=title),
    }


def _collapsible_html(
    content: str,
    *,
    title: str,
    open_by_default: bool = True,
) -> str:
    open_attribute = " open" if open_by_default else ""
    return f"""<style>
.autodq-output-toggle{{border:1px solid var(--vscode-panel-border);border-radius:9px;overflow:hidden}}
.autodq-output-toggle>summary{{align-items:center;background:var(--vscode-editor-background);cursor:pointer;display:flex;font-family:var(--vscode-font-family);font-size:12px;font-weight:600;gap:8px;padding:9px 12px;user-select:none}}
.autodq-output-toggle>summary:hover{{background:var(--vscode-list-hoverBackground)}}
.autodq-output-toggle__hint{{color:var(--vscode-descriptionForeground);font-weight:400;margin-left:auto}}
.autodq-output-toggle__body{{padding:8px 12px 2px}}
</style>
<details class="autodq-output-toggle"{open_attribute}>
  <summary>
    <span>{html.escape(title)}</span>
    <span class="autodq-output-toggle__hint">Click to show or hide</span>
  </summary>
  <div class="autodq-output-toggle__body">{content}</div>
</details>"""


def _dataframe_html(
    frame: pd.DataFrame,
    limit: int = _NOTEBOOK_DEFAULT_OUTPUT_ROWS,
    column_limit: int = _NOTEBOOK_MAX_OUTPUT_COLUMNS,
) -> str:
    preview = frame.iloc[:limit, :column_limit]
    table = preview.to_html(
        index=False,
        escape=True,
        border=0,
        classes="autodq-dataframe",
    )
    notes = []

    if len(frame) > limit:
        notes.append(
            f"Showing {len(preview):,} of {len(frame):,} rows"
        )

    if len(frame.columns) > column_limit:
        notes.append(
            f"showing {len(preview.columns):,} of "
            f"{len(frame.columns):,} columns"
        )

    remainder = ""

    if notes:
        remainder = _truncation_note(
            f"{'; '.join(notes)}. The complete result remains available to "
            "later ADQL statements and exports."
        )

    return f"""<style>
.autodq-dataframe{{border-collapse:collapse;font-family:var(--vscode-font-family);font-size:12px;width:100%}}
.autodq-dataframe th,.autodq-dataframe td{{border-bottom:1px solid var(--vscode-panel-border);padding:6px 9px;text-align:left}}
.autodq-dataframe th{{font-weight:600;position:sticky;top:0}}
.autodq-dataframe-wrap{{max-height:560px;overflow:auto}}
.autodq-truncation-note{{border-left:3px solid var(--vscode-editorWarning-foreground);color:var(--vscode-descriptionForeground);font-size:12px;padding:7px 10px}}
</style><div class="autodq-dataframe-wrap">{table}</div>{remainder}"""


def _profile_html(
    profile: dict,
    limit: int = _NOTEBOOK_DEFAULT_OUTPUT_ROWS,
) -> str:
    columns = []
    column_names = list(profile.get("column_names", []))

    for column in column_names[:limit]:
        columns.append(
            "<tr>"
            f"<td>{html.escape(str(column))}</td>"
            f"<td>{html.escape(str(profile.get('data_types', {}).get(column, 'unknown')))}</td>"
            f"<td>{html.escape(str(profile.get('semantic_types', {}).get(column, 'unknown')))}</td>"
            f"<td>{int(profile.get('missing_values', {}).get(column, 0)):,}</td>"
            f"<td>{float(profile.get('missing_percentages', {}).get(column, 0)):.2f}%</td>"
            "</tr>"
        )

    total_missing = sum(profile.get("missing_values", {}).values())
    dataset = html.escape(str(profile.get("dataset_path") or "Current dataset"))
    truncation_note = ""

    if len(column_names) > limit:
        truncation_note = _truncation_note(
            f"Showing {limit:,} of {len(column_names):,} profiled columns."
        )

    return f"""<style>{_REPORT_CSS}</style>
<section class="autodq-report">
  <h2>Dataset Profile</h2>
  <p class="autodq-muted">{dataset}</p>
  <div class="autodq-metrics">
    {_metric_card('Rows', f"{int(profile.get('rows', 0)):,}")}
    {_metric_card('Columns', f"{int(profile.get('columns', 0)):,}")}
    {_metric_card('Missing cells', f"{int(total_missing):,}")}
    {_metric_card('Duplicate rows', f"{int(profile.get('duplicate_rows', 0)):,}")}
  </div>
  <div class="autodq-groups">
    {_group_line('Numeric', profile.get('numeric_columns', []))}
    {_group_line('Categorical', profile.get('categorical_columns', []))}
    {_group_line('Datetime', profile.get('datetime_columns', []))}
  </div>
  <div class="autodq-table-wrap">
    <table class="autodq-report-table">
      <thead><tr><th>Column</th><th>Data type</th><th>Semantic type</th><th>Missing</th><th>Missing %</th></tr></thead>
      <tbody>{''.join(columns)}</tbody>
    </table>
  </div>
  {truncation_note}
</section>"""


def _diagnosis_html(
    report,
    limit: int = _NOTEBOOK_DEFAULT_OUTPUT_ROWS,
) -> str:
    issue_cards = []
    issues = list(getattr(report, "issues", []))

    for issue in issues[:limit]:
        affected = ", ".join(issue.affected_columns) or "None"
        confidence = (
            f"{float(issue.confidence) * 100:.1f}%"
            if issue.confidence is not None
            else "N/A"
        )
        issue_cards.append(
            f"""<article class="autodq-issue">
  <div><span class="autodq-severity autodq-{html.escape(str(issue.severity).lower())}">{html.escape(str(issue.severity).upper())}</span>
  <strong>{html.escape(str(issue.issue_type).replace('_', ' ').title())}</strong></div>
  <p>{html.escape(str(issue.message))}</p>
  <p class="autodq-muted"><strong>Affected columns:</strong> {html.escape(affected)}</p>
  <p class="autodq-muted"><strong>Recommendation:</strong> {html.escape(str(issue.recommendation or 'No recommendation.'))}</p>
  <p class="autodq-muted"><strong>Confidence:</strong> {confidence}</p>
</article>"""
        )

    if not issue_cards:
        issue_cards.append(
            '<div class="autodq-empty">No major data quality issues detected.</div>'
        )

    score = getattr(report, "quality_score", None)
    score_text = f"{float(score):.2f}/100" if score is not None else "N/A"
    summary = html.escape(str(getattr(report, "summary", "") or ""))
    truncation_note = ""

    if len(issues) > limit:
        truncation_note = _truncation_note(
            f"Showing {limit:,} of {len(issues):,} diagnosed issues."
        )

    return f"""<style>{_REPORT_CSS}</style>
<section class="autodq-report">
  <h2>Data Quality Diagnosis</h2>
  <div class="autodq-metrics">
    {_metric_card('Quality score', score_text)}
    {_metric_card('Issues found', f"{int(getattr(report, 'issue_count', 0)):,}")}
  </div>
  <p>{summary}</p>
  <div class="autodq-issues">{''.join(issue_cards)}</div>
  {truncation_note}
</section>"""


def _recommendations_html(
    recommendations,
    limit: int = _NOTEBOOK_DEFAULT_OUTPUT_ROWS,
) -> str:
    serialized = serializable_value(recommendations)

    if isinstance(serialized, dict):
        items = serialized.get("recommendations", [])
    elif isinstance(serialized, list):
        items = serialized
    else:
        items = []

    cards = []

    for index, item in enumerate(items[:limit], start=1):
        if not isinstance(item, dict):
            continue

        issue_type = str(item.get("issue_type") or "recommendation")
        strategy = str(item.get("strategy") or "review")
        priority = str(item.get("priority") or "normal").lower()
        priority_class = (
            priority
            if priority in {"critical", "high", "medium", "low"}
            else "normal"
        )
        action = str(item.get("action") or "Review this recommendation.")
        reason = str(item.get("reason") or "No reason was provided.")
        risk = str(item.get("risk") or "No specific risk was provided.")
        affected = item.get("affected_columns") or []

        if isinstance(affected, str):
            affected = [affected]

        columns = "".join(
            f'<span class="autodq-column-chip">{html.escape(str(column))}</span>'
            for column in affected
        ) or '<span class="autodq-muted">No specific columns</span>'
        confidence = item.get("confidence")

        try:
            confidence_value = float(confidence)
            confidence_percent = (
                confidence_value * 100
                if confidence_value <= 1
                else confidence_value
            )
            confidence_text = f"{confidence_percent:.0f}% confidence"
        except (TypeError, ValueError):
            confidence_text = "Confidence not available"

        cards.append(
            f"""<article class="autodq-recommendation">
  <header class="autodq-recommendation__header">
    <span class="autodq-recommendation__number">{index}</span>
    <span class="autodq-priority autodq-priority--{priority_class}">{html.escape(priority.upper())} PRIORITY</span>
    <span class="autodq-strategy">{html.escape(strategy.replace('_', ' ').title())}</span>
  </header>
  <h3>{html.escape(action)}</h3>
  <div class="autodq-recommendation__meta">
    <span>{html.escape(issue_type.replace('_', ' ').title())}</span>
    <span>{html.escape(confidence_text)}</span>
  </div>
  <div class="autodq-column-list">{columns}</div>
  <details class="autodq-recommendation__details">
    <summary>Why this is recommended</summary>
    <p><strong>Reason:</strong> {html.escape(reason)}</p>
    <p><strong>Risk:</strong> {html.escape(risk)}</p>
  </details>
</article>"""
        )

    if not cards:
        cards.append(
            '<div class="autodq-empty">No cleaning recommendations were generated.</div>'
        )

    truncation_note = ""

    if len(items) > limit:
        truncation_note = _truncation_note(
            f"Showing {limit:,} of {len(items):,} recommendations."
        )

    return f"""<style>{_REPORT_CSS}</style>
<section class="autodq-report">
  <div class="autodq-report-heading">
    <div>
      <h2>Cleaning Recommendations</h2>
      <p class="autodq-muted">{len(items):,} evidence-aware action(s), ordered by priority.</p>
    </div>
  </div>
  <div class="autodq-recommendations">{''.join(cards)}</div>
  {truncation_note}
</section>"""


def _metric_card(label: str, value: str) -> str:
    return (
        '<div class="autodq-metric">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(value)}</strong>'
        '</div>'
    )


def _group_line(label: str, values) -> str:
    rendered = ", ".join(html.escape(str(value)) for value in values) or "None"
    return f"<p><strong>{html.escape(label)}:</strong> {rendered}</p>"


def _value_html(
    title: str,
    value,
    *,
    item_limit: int = _NOTEBOOK_DEFAULT_OUTPUT_ROWS,
    character_limit: int = _NOTEBOOK_DEFAULT_OUTPUT_CHARACTERS,
) -> str:
    rich_output_was_truncated = False

    if hasattr(value, "to_html"):
        try:
            rendered_html = value.to_html()
        except Exception:
            rendered_html = None

        if isinstance(rendered_html, str) and rendered_html.strip():
            if (
                len(rendered_html) <= character_limit
                and "<pre" not in rendered_html.lower()
            ):
                return f"""<style>{_REPORT_CSS}</style>
<div class="autodq-bounded-output">{rendered_html}</div>"""

            rich_output_was_truncated = True

    serialized = serializable_value(value)
    serialized, structure_was_truncated = _truncate_notebook_value(
        serialized,
        item_limit=item_limit,
        string_limit=max(500, min(2_000, character_limit // 4)),
    )
    was_truncated = rich_output_was_truncated or structure_was_truncated
    body = _structured_html(serialized)

    if was_truncated:
        body += _truncation_note(
            "This notebook preview was shortened. The complete result remains "
            "available to later ADQL statements and exports."
        )

    heading = html.escape(title.replace("_", " ").title())
    return f"""<style>{_REPORT_CSS}</style>
<section class="autodq-report autodq-value-report autodq-bounded-output">
  <h2>{heading}</h2>
  {body}
</section>"""


_STRUCTURED_LONG_FIELDS = {
    "action",
    "description",
    "details",
    "explanation",
    "interpretation",
    "notes",
    "reason",
    "recommendation",
    "recommendations",
    "risk",
    "warnings",
}

_STRUCTURED_FIELD_ORDER = (
    "action_id",
    "row_id",
    "rank",
    "column",
    "feature",
    "feature_a",
    "feature_b",
    "target",
    "name",
    "title",
    "label",
    "issue_type",
    "strategy",
    "status",
    "severity",
    "priority",
    "problem_type",
    "algorithm",
    "method",
    "count",
    "missing",
    "missing_percent",
    "before",
    "after",
    "change",
    "mean",
    "median",
    "minimum",
    "maximum",
    "std",
    "correlation",
    "strength",
    "direction",
    "importance",
    "confidence",
)

_STRUCTURED_SECTION_KEYS = {
    "actions",
    "assumptions",
    "audit_trail",
    "automation",
    "charts",
    "cleaning",
    "columns",
    "descriptive",
    "domain",
    "domain_report",
    "domain_rules",
    "duplicate_rows",
    "excluded_features",
    "feature_columns",
    "feature_importance",
    "feature_types",
    "global_features",
    "issues",
    "matrix",
    "metrics",
    "missing_values",
    "model",
    "model_comparison",
    "outlier_report",
    "prediction",
    "predictions",
    "prescriptions",
    "preview",
    "previews",
    "recommendations",
    "relationships",
    "review",
    "row_explanations",
    "rows",
    "summary",
    "target_relationships",
    "uncertainty_calibration",
    "vif_results",
    "visual_insights",
    "warnings",
}


def _structured_html(value, *, depth: int = 0) -> str:
    if depth >= 5:
        return '<p class="autodq-structured-note">Additional nested details omitted.</p>'

    if _is_scalar(value):
        return _structured_scalar(value)

    if isinstance(value, dict):
        items = dict(value)
        preview_message = items.pop("__preview__", None)
        content = ""

        if _is_numeric_matrix(items):
            content = _structured_matrix(items)
        elif _is_record_mapping(items) and not _is_section_mapping(items):
            records = []

            for name, item in items.items():
                if isinstance(item, dict):
                    record = {"item": name, **item}
                else:
                    record = {"item": name, "status": "No matched rule"}

                records.append(record)

            content = _structured_records_table(
                records,
                depth=depth,
                first_label="Item",
            )
        else:
            scalar_rows = []
            nested_sections = []

            for key, item in items.items():
                label = _humanize(key)

                if _is_scalar(item):
                    scalar_rows.append(
                        "<tr>"
                        f"<th>{html.escape(label)}</th>"
                        f"<td>{_structured_scalar(item, key=key)}</td>"
                        "</tr>"
                    )
                else:
                    count = _structured_count(item)
                    count_badge = (
                        f'<span class="autodq-section-count">{count:,}</span>'
                        if count is not None
                        else ""
                    )
                    nested_sections.append(
                        '<details class="autodq-structured-section">'
                        f"<summary><span>{html.escape(label)}</span>{count_badge}</summary>"
                        '<div class="autodq-structured-section__body">'
                        f"{_structured_html(item, depth=depth + 1)}"
                        "</div></details>"
                    )

            if scalar_rows:
                content += (
                    '<div class="autodq-structured-table-wrap">'
                    '<table class="autodq-key-values">'
                    + "".join(scalar_rows)
                    + "</table></div>"
                )

            content += "".join(nested_sections)

        if preview_message:
            content = (
                _structured_preview_note(str(preview_message))
                + content
            )

        return content or '<p class="autodq-empty">No structured values.</p>'

    if isinstance(value, (list, tuple)):
        items = list(value)
        preview_message = None

        if items and _is_preview_marker(items[0]):
            preview_message = str(items.pop(0))

        if not items:
            content = '<p class="autodq-empty">No items.</p>'
        elif all(_is_scalar(item) for item in items):
            content = (
                '<div class="autodq-chip-list">'
                + "".join(
                    f'<span class="autodq-data-chip">{_structured_scalar(item)}</span>'
                    for item in items
                )
                + "</div>"
            )
        elif all(isinstance(item, dict) for item in items):
            content = _structured_records_table(items, depth=depth)
        else:
            cards = []

            for index, item in enumerate(items, start=1):
                cards.append(
                    '<article class="autodq-structured-card">'
                    f'<div class="autodq-structured-card__title">Item {index}</div>'
                    f"{_structured_html(item, depth=depth + 1)}"
                    "</article>"
                )

            content = '<div class="autodq-structured-grid">' + "".join(cards) + "</div>"

        if preview_message:
            content = _structured_preview_note(preview_message) + content

        return content

    return _structured_scalar(str(value))


def _structured_records_table(
    records: list[dict],
    *,
    depth: int,
    first_label: str | None = None,
) -> str:
    if not records:
        return '<p class="autodq-empty">No records.</p>'

    keys = []

    for record in records:
        for key in record:
            if key not in keys:
                keys.append(key)

    simple_keys = [
        key
        for key in keys
        if key not in _STRUCTURED_LONG_FIELDS
        and all(
            _is_scalar(record.get(key))
            and len(str(record.get(key) or "")) <= 100
            for record in records
        )
    ]
    order = {key: index for index, key in enumerate(_STRUCTURED_FIELD_ORDER)}
    simple_keys.sort(key=lambda key: (order.get(key, len(order)), keys.index(key)))

    if "item" in simple_keys:
        simple_keys.remove("item")
        simple_keys.insert(0, "item")

    selected_keys = simple_keys[:8]

    if not selected_keys:
        selected_keys = keys[:1]

    detail_keys = [key for key in keys if key not in selected_keys]
    headers = []

    for key in selected_keys:
        label = first_label if key == "item" and first_label else _humanize(key)
        headers.append(f"<th>{html.escape(label)}</th>")

    if detail_keys:
        headers.append("<th>Details</th>")

    rows = []

    for record in records:
        cells = [
            f"<td>{_structured_scalar(record.get(key), key=key)}</td>"
            for key in selected_keys
        ]

        if detail_keys:
            details = {
                key: record.get(key)
                for key in detail_keys
                if record.get(key) not in (None, "", [], {})
            }

            if details:
                cells.append(
                    '<td><details class="autodq-row-details">'
                    f"<summary>{len(details):,} field(s)</summary>"
                    '<div class="autodq-row-details__body">'
                    f"{_structured_html(details, depth=depth + 1)}"
                    "</div></details></td>"
                )
            else:
                cells.append("<td>—</td>")

        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div class="autodq-structured-table-wrap">'
        '<table class="autodq-structured-table"><thead><tr>'
        + "".join(headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _structured_matrix(matrix: dict) -> str:
    row_names = list(matrix)[:12]
    column_names = []

    for row_name in row_names:
        for column in matrix[row_name]:
            if column not in column_names:
                column_names.append(column)

    column_names = column_names[:12]
    headers = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in column_names
    )
    rows = []

    for row_name in row_names:
        cells = "".join(
            f"<td>{_structured_scalar(matrix[row_name].get(column), key='correlation')}</td>"
            for column in column_names
        )
        rows.append(
            f"<tr><th>{html.escape(str(row_name))}</th>{cells}</tr>"
        )

    note = ""

    if len(matrix) > len(row_names):
        note = _structured_preview_note(
            f"Showing {len(row_names):,} of {len(matrix):,} matrix rows."
        )

    return (
        note
        + '<div class="autodq-structured-table-wrap">'
        '<table class="autodq-structured-table autodq-matrix-table">'
        f"<thead><tr><th>Feature</th>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _structured_scalar(value, *, key: str | None = None) -> str:
    if value is None:
        return '<span class="autodq-null">—</span>'

    normalized_key = str(key or "").lower()

    if isinstance(value, bool):
        status = "good" if value else "neutral"
        label = "Yes" if value else "No"
        return f'<span class="autodq-data-badge autodq-data-badge--{status}">{label}</span>'

    if isinstance(value, float):
        if "confidence" in normalized_key:
            numeric = value * 100 if abs(value) <= 1 else value
            rendered = f"{numeric:.1f}%"
        elif "percent" in normalized_key:
            rendered = f"{value:,.2f}%"
        elif value != value:
            rendered = "—"
        else:
            rendered = f"{value:,.4f}".rstrip("0").rstrip(".")
    elif isinstance(value, int):
        rendered = f"{value:,}"
    else:
        rendered = str(value)

    normalized_value = rendered.lower().strip().replace(" ", "_")
    badge_keys = {
        "direction",
        "priority",
        "severity",
        "status",
        "strength",
    }

    if normalized_key in badge_keys:
        badge_class = _structured_badge_class(normalized_value)
        return (
            f'<span class="autodq-data-badge autodq-data-badge--{badge_class}">'
            f"{html.escape(_humanize(rendered))}</span>"
        )

    if normalized_key in {"algorithm", "method", "strategy", "problem_type"}:
        return f'<code class="autodq-inline-code">{html.escape(rendered)}</code>'

    return html.escape(rendered)


def _structured_badge_class(value: str) -> str:
    if value in {"passed", "good", "approved", "positive", "low", "strong", "very_strong"}:
        return "good"
    if value in {"failed", "bad", "rejected", "negative", "critical", "high"}:
        return "bad"
    if value in {"warning", "pending", "medium", "moderate"}:
        return "warning"
    return "neutral"


def _is_scalar(value) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _is_numeric_matrix(value: dict) -> bool:
    if len(value) < 2 or not all(isinstance(item, dict) for item in value.values()):
        return False

    cells = [cell for row in value.values() for cell in row.values()]
    return bool(cells) and all(
        isinstance(cell, (int, float, bool)) or cell is None
        for cell in cells
    )


def _is_record_mapping(value: dict) -> bool:
    return bool(value) and any(isinstance(item, dict) for item in value.values()) and all(
        isinstance(item, dict) or item is None
        for item in value.values()
    )


def _is_section_mapping(value: dict) -> bool:
    return any(str(key).lower() in _STRUCTURED_SECTION_KEYS for key in value)


def _is_preview_marker(value) -> bool:
    text = str(value)
    return text.startswith("Showing ") and "omitted" in text


def _structured_count(value) -> int | None:
    if isinstance(value, (dict, list, tuple)):
        count = len(value)

        if isinstance(value, dict) and "__preview__" in value:
            count -= 1
        elif isinstance(value, (list, tuple)) and value and _is_preview_marker(value[0]):
            count -= 1

        return max(0, count)

    return None


def _structured_preview_note(message: str) -> str:
    return (
        '<p class="autodq-structured-note">'
        f"{html.escape(message)}"
        "</p>"
    )


def _humanize(value) -> str:
    return str(value).replace("_", " ").strip().title()


def _notebook_limit(
    value,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(parsed, maximum))


def _truncate_text(value: str, limit: int) -> tuple[str, bool]:
    text = str(value)

    if len(text) <= limit:
        return text, False

    omitted = len(text) - limit
    suffix = f"\n… {omitted:,} additional character(s) omitted"
    prefix_limit = max(0, limit - len(suffix))
    return text[:prefix_limit].rstrip() + suffix, True


def _truncate_notebook_value(
    value,
    *,
    item_limit: int,
    string_limit: int,
    depth: int = 0,
    max_depth: int = 5,
) -> tuple[object, bool]:
    if isinstance(value, str):
        return _truncate_text(value, string_limit)

    if depth >= max_depth and isinstance(value, (dict, list, tuple)):
        count = len(value)
        return f"… {count:,} nested item(s) omitted", True

    if isinstance(value, dict):
        items = list(value.items())
        truncated = len(items) > item_limit
        preview = {}

        if len(items) > item_limit:
            preview["__preview__"] = (
                f"Showing {item_limit:,} of {len(items):,} fields; "
                f"{len(items) - item_limit:,} additional field(s) omitted"
            )

        for key, item in items[:item_limit]:
            rendered, child_truncated = _truncate_notebook_value(
                item,
                item_limit=item_limit,
                string_limit=string_limit,
                depth=depth + 1,
                max_depth=max_depth,
            )
            preview[str(key)] = rendered
            truncated = truncated or child_truncated

        return preview, truncated

    if isinstance(value, (list, tuple)):
        items = list(value)
        truncated = len(items) > item_limit
        preview = []

        if len(items) > item_limit:
            preview.append(
                f"Showing {item_limit:,} of {len(items):,} items; "
                f"{len(items) - item_limit:,} additional item(s) omitted"
            )

        for item in items[:item_limit]:
            rendered, child_truncated = _truncate_notebook_value(
                item,
                item_limit=item_limit,
                string_limit=string_limit,
                depth=depth + 1,
                max_depth=max_depth,
            )
            preview.append(rendered)
            truncated = truncated or child_truncated

        return preview, truncated

    return value, False


def _truncation_note(message: str) -> str:
    return (
        '<p class="autodq-truncation-note">'
        f"<strong>Output truncated.</strong> {html.escape(message)}"
        "</p>"
    )


def _limit_notebook_outputs(
    outputs: list[dict],
    *,
    character_limit: int,
) -> list[dict]:
    limited = []

    for output in outputs[:_NOTEBOOK_MAX_OUTPUTS]:
        item = dict(output)

        if item.get("mime") == "text/plain":
            item["data"], _ = _truncate_text(
                item.get("data", ""),
                character_limit,
            )

        limited.append(item)

    if len(outputs) > _NOTEBOOK_MAX_OUTPUTS:
        limited.append(
            {
                "mime": "text/plain",
                "data": (
                    "Output truncated: "
                    f"{len(outputs) - _NOTEBOOK_MAX_OUTPUTS:,} additional "
                    "notebook output item(s) were omitted."
                ),
            }
        )

    return limited


_REPORT_CSS = """
.autodq-report{font-family:var(--vscode-font-family);color:var(--vscode-foreground);line-height:1.45;padding:4px 0 12px}
.autodq-report h2{font-size:18px;margin:8px 0 2px}
.autodq-report-heading{align-items:flex-start;display:flex;justify-content:space-between;margin-bottom:12px}
.autodq-muted{color:var(--vscode-descriptionForeground);font-size:12px}
.autodq-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:9px;margin:14px 0}
.autodq-metric{border:1px solid var(--vscode-panel-border);border-radius:8px;padding:10px 12px}
.autodq-metric span{display:block;color:var(--vscode-descriptionForeground);font-size:11px;text-transform:uppercase}
.autodq-metric strong{display:block;font-size:19px;margin-top:3px}
.autodq-groups{border:1px solid var(--vscode-panel-border);border-radius:8px;padding:5px 12px;margin-bottom:12px}
.autodq-table-wrap{max-height:440px;overflow:auto}
.autodq-report-table{border-collapse:collapse;font-size:12px;width:100%}
.autodq-report-table th,.autodq-report-table td{border-bottom:1px solid var(--vscode-panel-border);padding:7px 9px;text-align:left}
.autodq-report-table th{background:var(--vscode-editor-background);position:sticky;top:0}
.autodq-issues{display:grid;gap:10px;margin-top:12px}
.autodq-issue{border:1px solid var(--vscode-panel-border);border-radius:8px;padding:12px}
.autodq-issue p{margin:7px 0}
.autodq-severity{border-radius:999px;display:inline-block;font-size:10px;font-weight:700;margin-right:8px;padding:3px 7px}
.autodq-high,.autodq-critical{background:#7f1d1d;color:#fee2e2}
.autodq-medium{background:#78350f;color:#fef3c7}
.autodq-low,.autodq-none{background:#064e3b;color:#d1fae5}
.autodq-empty{border:1px dashed var(--vscode-panel-border);border-radius:8px;padding:16px}
.autodq-recommendations{display:grid;gap:10px}
.autodq-recommendation{background:var(--vscode-editor-background);border:1px solid var(--vscode-panel-border);border-radius:10px;padding:13px 14px}
.autodq-recommendation h3{font-size:14px;line-height:1.4;margin:10px 0 7px}
.autodq-recommendation__header{align-items:center;display:flex;flex-wrap:wrap;gap:7px}
.autodq-recommendation__number{align-items:center;background:var(--vscode-badge-background);border-radius:999px;color:var(--vscode-badge-foreground);display:inline-flex;font-size:11px;font-weight:700;height:24px;justify-content:center;width:24px}
.autodq-priority,.autodq-strategy{border-radius:999px;font-size:10px;font-weight:700;padding:3px 7px}
.autodq-priority--critical,.autodq-priority--high{background:#7f1d1d;color:#fee2e2}
.autodq-priority--medium{background:#78350f;color:#fef3c7}
.autodq-priority--low{background:#064e3b;color:#d1fae5}
.autodq-priority--normal{background:var(--vscode-badge-background);color:var(--vscode-badge-foreground)}
.autodq-strategy{background:var(--vscode-textBlockQuote-background);color:var(--vscode-foreground)}
.autodq-recommendation__meta{color:var(--vscode-descriptionForeground);display:flex;flex-wrap:wrap;font-size:11px;gap:6px 16px;margin-bottom:9px}
.autodq-column-list{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0}
.autodq-column-chip{background:var(--vscode-textCodeBlock-background);border:1px solid var(--vscode-panel-border);border-radius:5px;font-family:var(--vscode-editor-font-family);font-size:11px;padding:2px 6px}
.autodq-recommendation__details{border-top:1px solid var(--vscode-panel-border);margin-top:11px;padding-top:9px}
.autodq-recommendation__details summary{color:var(--vscode-textLink-foreground);cursor:pointer;font-size:12px;font-weight:600}
.autodq-recommendation__details p{font-size:12px;margin:8px 0 0}
.autodq-key-values{border-collapse:collapse;width:100%;font-size:12px}
.autodq-key-values th,.autodq-key-values td{border-bottom:1px solid var(--vscode-panel-border);padding:7px 9px;text-align:left;vertical-align:top}
.autodq-key-values th{width:28%;color:var(--vscode-descriptionForeground)}
.autodq-structured-table-wrap{max-width:100%;overflow:auto}
.autodq-structured-table{border-collapse:collapse;font-size:12px;min-width:100%;width:max-content}
.autodq-structured-table th,.autodq-structured-table td{border-bottom:1px solid var(--vscode-panel-border);max-width:280px;padding:7px 9px;text-align:left;vertical-align:top}
.autodq-structured-table thead th{background:var(--vscode-editor-background);color:var(--vscode-descriptionForeground);font-size:10px;letter-spacing:.04em;position:sticky;text-transform:uppercase;top:0;z-index:1}
.autodq-structured-table tbody th{background:var(--vscode-editor-background);font-weight:600;position:sticky;left:0}
.autodq-matrix-table td{font-variant-numeric:tabular-nums;text-align:right}
.autodq-structured-section{border-bottom:1px solid var(--vscode-panel-border);padding:0}
.autodq-structured-section>summary{align-items:center;cursor:pointer;display:flex;font-size:12px;font-weight:600;gap:8px;padding:9px 0}
.autodq-structured-section__body{padding:2px 0 11px 10px}
.autodq-section-count{background:var(--vscode-badge-background);border-radius:999px;color:var(--vscode-badge-foreground);font-size:10px;font-weight:600;padding:1px 6px}
.autodq-chip-list{display:flex;flex-wrap:wrap;gap:5px;padding:7px 0}
.autodq-data-chip{background:var(--vscode-textCodeBlock-background);border:1px solid var(--vscode-panel-border);border-radius:5px;font-family:var(--vscode-editor-font-family);font-size:11px;padding:3px 7px}
.autodq-data-badge{border-radius:999px;display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;white-space:nowrap}
.autodq-data-badge--good{background:#064e3b;color:#d1fae5}
.autodq-data-badge--warning{background:#78350f;color:#fef3c7}
.autodq-data-badge--bad{background:#7f1d1d;color:#fee2e2}
.autodq-data-badge--neutral{background:var(--vscode-badge-background);color:var(--vscode-badge-foreground)}
.autodq-inline-code{background:var(--vscode-textCodeBlock-background);border-radius:4px;font-family:var(--vscode-editor-font-family);font-size:11px;padding:2px 5px}
.autodq-null{color:var(--vscode-descriptionForeground)}
.autodq-row-details>summary{color:var(--vscode-textLink-foreground);cursor:pointer;font-size:11px;white-space:nowrap}
.autodq-row-details__body{min-width:300px;padding:7px 0}
.autodq-structured-grid{display:grid;gap:9px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.autodq-structured-card{border:1px solid var(--vscode-panel-border);border-radius:8px;padding:10px}
.autodq-structured-card__title{font-size:11px;font-weight:700;margin-bottom:6px}
.autodq-structured-note{border-left:3px solid var(--vscode-textLink-foreground);color:var(--vscode-descriptionForeground);font-size:11px;margin:7px 0;padding:5px 9px}
.autodq-value-report details{border-bottom:1px solid var(--vscode-panel-border);padding:9px 0}
.autodq-value-report summary{cursor:pointer;font-weight:600}
.autodq-value-report pre{max-height:420px;white-space:pre-wrap;overflow:auto}
.autodq-bounded-output{max-height:620px;overflow:auto;padding-right:6px}
.autodq-truncation-note{border-left:3px solid var(--vscode-editorWarning-foreground);color:var(--vscode-descriptionForeground);font-size:12px;padding:7px 10px}
"""


def _visualization_outputs(report) -> list[dict]:
    matplotlib_cache = Path(
        os.environ.get(
            "MPLCONFIGDIR",
            Path.home() / ".cache" / "autodq" / "matplotlib",
        )
    ).expanduser()
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))

    import matplotlib

    matplotlib.use("Agg")

    from autodq.visualization.renderers.matplotlib_renderer import (
        MatplotlibVisualizationRenderer,
    )

    renderer = MatplotlibVisualizationRenderer()
    outputs = []

    charts = getattr(report, "charts", None)

    if charts is None and hasattr(report, "chart_id"):
        charts = [report]

    for chart in charts or []:
        try:
            image = renderer.render_bytes(chart, format="png")
        except Exception as error:
            outputs.append(
                {
                    "mime": "text/plain",
                    "data": (
                        f"Could not render {getattr(chart, 'title', 'chart')}: "
                        f"{error}"
                    ),
                }
            )
            continue

        outputs.append(
            {
                "mime": "image/png",
                "data": base64.b64encode(image).decode("ascii"),
                "metadata": {
                    "title": getattr(chart, "title", "AutoDQ chart"),
                    "chart_id": getattr(chart, "chart_id", None),
                },
            }
        )

    return outputs


def _figure_output(figure, *, title: str) -> dict:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=144, bbox_inches="tight")
    return {
        "mime": "image/png",
        "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
        "metadata": {"title": title},
    }


def _run_kernel(path: str) -> int:
    """Serve JSON-line notebook requests while retaining one AutoDQ project."""
    runner = ADQLFileRunner()
    project = None
    executed_cells: set[int] = set()

    for line in sys.stdin:
        line = line.strip()

        if not line:
            continue

        request_id = None

        try:
            request = json.loads(line)
            request_id = request.get("id")
            action = request.get("action", "execute")

            if action == "shutdown":
                break

            if action == "reset":
                project = None
                executed_cells.clear()
                payload = {
                    "protocol": "autodq-notebook-v1",
                    "success": True,
                    "outputs": [
                        {"mime": "text/plain", "data": "ADQL session restarted."}
                    ],
                }
            else:
                cell = int(request["cell"])

                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    if project is None:
                        result = runner.run(
                            path,
                            through_cell=cell,
                            raise_on_error=False,
                            auto_display=False,
                        )
                        project = result.project
                        executed_cells.update(
                            item.cell.number for item in result.cell_runs
                        )
                    else:
                        result = runner.run_with_project(
                            project,
                            path,
                            cell=cell,
                            raise_on_error=False,
                            auto_display=False,
                        )
                        executed_cells.add(cell)

                payload = _notebook_payload(
                    result,
                    max_output_rows=request.get("max_output_rows"),
                    max_output_characters=request.get(
                        "max_output_characters"
                    ),
                )
                payload["session"] = {
                    "persistent": True,
                    "executed_cells": sorted(executed_cells),
                }
        except Exception as error:
            payload = {
                "protocol": "autodq-notebook-v1",
                "success": False,
                "outputs": [
                    {
                        "mime": "text/plain",
                        "data": f"{type(error).__name__}: {error}",
                    }
                ],
            }

        payload["id"] = request_id
        print(json.dumps(payload), flush=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = _normalise_argv(
        list(sys.argv[1:] if argv is None else argv)
    )
    parser = _build_parser()
    options = parser.parse_args(arguments)
    runner = ADQLFileRunner()

    try:
        if options.command == "kernel":
            return _run_kernel(options.path)

        if options.command == "run":
            run_options = {
                "dataset": options.dataset,
                "target": options.target,
                "cell": options.cell,
                "through_cell": options.through_cell,
                "continue_on_error": options.continue_on_error,
                "raise_on_error": False,
                "auto_display": False,
            }

            if options.notebook_json:
                with redirect_stdout(io.StringIO()):
                    result = runner.run(options.path, **run_options)

                print(json.dumps(_notebook_payload(result)))
                return 0 if result.success else 1

            result = runner.run(options.path, **run_options)
            _render_run(result)

            if options.json_path:
                output = _save_json(
                    result,
                    options.json_path,
                    overwrite=options.overwrite,
                )
                print(f"Result JSON: {output}")

            return 0 if result.success else 1

        if options.command == "validate":
            document = runner.validate(
                options.path,
                dataset=options.dataset,
            )
            print(
                f"Valid ADQL: {document.path} "
                f"({document.cell_count} cell(s))"
            )
            return 0

        if options.command == "cells":
            document = runner.inspect(options.path)

            for cell in document.cells:
                print(
                    f"{cell.number}\t{cell.title}\t"
                    f"lines {cell.start_line}-{cell.end_line}"
                )

            return 0

        if options.command == "vscode":
            if options.vscode_command == "path":
                print(extension_path())
                return 0

            installed = install_extension(
                destination=options.destination,
                overwrite=options.overwrite,
            )
            print(f"Installed AutoDQ ADQL extension: {installed}")
            print("Restart VS Code, then open any .adql file.")
            return 0
    except (ADQLError, FileNotFoundError, FileExistsError, ValueError) as error:
        print(f"autodq: {error}", file=sys.stderr)
        return 2

    parser.error("Unknown command.")
    return 2
