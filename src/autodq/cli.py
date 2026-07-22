from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

from autodq.commands.errors import ADQLError
from autodq.commands.runner import ADQLFileRunner
from autodq.vscode import extension_path, install_extension


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


def _notebook_payload(result) -> dict:
    """Build the rich-output protocol consumed by the VS Code notebook."""
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
                    {
                        "mime": "text/html",
                        "data": _dataframe_html(statement_result.data),
                    }
                )

            if (
                statement_result.statement.kind == "PROFILE"
                and isinstance(statement_result.value, dict)
            ):
                outputs.append(
                    {
                        "mime": "text/html",
                        "data": _profile_html(statement_result.value),
                    }
                )

            if (
                statement_result.statement.kind == "DIAGNOSE"
                and statement_result.value is not None
            ):
                outputs.append(
                    {
                        "mime": "text/html",
                        "data": _diagnosis_html(statement_result.value),
                    }
                )

            if (
                statement_result.statement.kind == "VISUALIZE"
                and statement_result.value is not None
            ):
                outputs.extend(
                    _visualization_outputs(statement_result.value)
                )

            if statement_result.error_message:
                outputs.append(
                    {
                        "mime": "text/plain",
                        "data": statement_result.error_message,
                    }
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


def _dataframe_html(frame: pd.DataFrame, limit: int = 100) -> str:
    table = frame.head(limit).to_html(
        index=False,
        escape=True,
        border=0,
        classes="autodq-dataframe",
    )
    remainder = ""

    if len(frame) > limit:
        remainder = (
            f"<p class='autodq-table-note'>"
            f"Showing {limit:,} of {len(frame):,} rows.</p>"
        )

    return f"""<style>
.autodq-dataframe{{border-collapse:collapse;font-family:var(--vscode-font-family);font-size:12px;width:100%}}
.autodq-dataframe th,.autodq-dataframe td{{border-bottom:1px solid var(--vscode-panel-border);padding:6px 9px;text-align:left}}
.autodq-dataframe th{{font-weight:600;position:sticky;top:0}}
.autodq-table-note{{opacity:.75;font-size:12px}}
</style>{table}{remainder}"""


def _profile_html(profile: dict) -> str:
    columns = []

    for column in profile.get("column_names", []):
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
</section>"""


def _diagnosis_html(report) -> str:
    issue_cards = []

    for issue in getattr(report, "issues", []):
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
    return f"""<style>{_REPORT_CSS}</style>
<section class="autodq-report">
  <h2>Data Quality Diagnosis</h2>
  <div class="autodq-metrics">
    {_metric_card('Quality score', score_text)}
    {_metric_card('Issues found', f"{int(getattr(report, 'issue_count', 0)):,}")}
  </div>
  <p>{summary}</p>
  <div class="autodq-issues">{''.join(issue_cards)}</div>
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


_REPORT_CSS = """
.autodq-report{font-family:var(--vscode-font-family);color:var(--vscode-foreground);line-height:1.45;padding:4px 0 12px}
.autodq-report h2{font-size:18px;margin:8px 0 2px}
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

    for chart in getattr(report, "charts", []):
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


def main(argv: list[str] | None = None) -> int:
    arguments = _normalise_argv(
        list(sys.argv[1:] if argv is None else argv)
    )
    parser = _build_parser()
    options = parser.parse_args(arguments)
    runner = ADQLFileRunner()

    try:
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
