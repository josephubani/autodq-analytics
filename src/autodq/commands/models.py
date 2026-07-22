from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def serializable_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, (datetime, date, pd.Timestamp, Path)):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): serializable_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serializable_value(item) for item in value]

    if hasattr(value, "to_dict"):
        return serializable_value(value.to_dict())

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


@dataclass(slots=True)
class ADQLStatement:
    kind: str
    raw: str
    parameters: dict[str, Any] = field(default_factory=dict)
    statement_number: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "raw": self.raw,
            "parameters": serializable_value(self.parameters),
            "statement_number": self.statement_number,
        }


@dataclass(slots=True)
class ADQLScript:
    source: str
    statements: list[ADQLStatement] = field(default_factory=list)

    @property
    def statement_count(self) -> int:
        return len(self.statements)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_count": self.statement_count,
            "statements": [item.to_dict() for item in self.statements],
        }


@dataclass(slots=True)
class ADQLResult:
    statement: ADQLStatement
    status: str
    message: str
    data: pd.DataFrame | None = field(default=None, repr=False)
    value: Any = field(default=None, repr=False)
    total_rows: int | None = None
    duration_seconds: float = 0.0
    error_type: str | None = None
    error_message: str | None = None

    @property
    def row_count(self) -> int:
        return len(self.data) if self.data is not None else 0

    @property
    def success(self) -> bool:
        return self.status == "completed"

    def to_dict(self, preview_rows: int = 100) -> dict[str, Any]:
        data_summary = None

        if self.data is not None:
            data_summary = {
                "rows": self.row_count,
                "total_rows": self.total_rows,
                "columns": [str(column) for column in self.data.columns],
                "preview": serializable_value(
                    self.data.head(preview_rows).to_dict(orient="records")
                ),
            }

        return {
            "statement": self.statement.to_dict(),
            "status": self.status,
            "success": self.success,
            "message": self.message,
            "data": data_summary,
            "value": serializable_value(self.value),
            "duration_seconds": self.duration_seconds,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


@dataclass(slots=True)
class ADQLRunResult:
    script: ADQLScript
    results: list[ADQLResult] = field(default_factory=list)
    source_name: str = "notebook"
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    auto_display: bool = field(default=True, repr=False)

    @property
    def statement_count(self) -> int:
        return self.script.statement_count

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self.results if item.success)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.results if not item.success)

    @property
    def success(self) -> bool:
        return self.failed_count == 0 and len(self.results) == self.statement_count

    @property
    def latest(self) -> ADQLResult | None:
        return self.results[-1] if self.results else None

    @property
    def data(self) -> pd.DataFrame | None:
        return self.latest.data if self.latest is not None else None

    @property
    def value(self) -> Any:
        return self.latest.value if self.latest is not None else None

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0

        return round(
            (self.finished_at - self.started_at).total_seconds(),
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "success": self.success,
            "statement_count": self.statement_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at is not None
                else None
            ),
            "results": [item.to_dict() for item in self.results],
        }

    def to_html(self) -> str:
        status = "Completed" if self.success else "Failed"
        cards = []

        for result in self.results:
            query = html.escape(result.statement.raw)
            message = html.escape(result.message)
            content = ""

            if result.data is not None:
                content = result.data.head(100).to_html(
                    index=False,
                    escape=True,
                    border=0,
                    classes="adql-table",
                )
            elif result.value is not None:
                rendered = json.dumps(
                    serializable_value(result.value),
                    indent=2,
                    ensure_ascii=False,
                )
                content = f"<pre>{html.escape(rendered)}</pre>"

            error = ""

            if result.error_message:
                error = (
                    '<div class="adql-error">'
                    f"{html.escape(result.error_message)}</div>"
                )

            cards.append(
                f"""<section class="adql-result">
<div class="adql-command"><code>{query}</code></div>
<div class="adql-message">{message}</div>{error}
<div class="adql-output">{content}</div>
</section>"""
            )

        return f"""<div class="adql-run">
<style>
.adql-run{{font-family:ui-sans-serif,system-ui;color:#172033;line-height:1.45}}
.adql-summary{{padding:12px 14px;background:#eef3fa;border-radius:10px;margin-bottom:10px}}
.adql-result{{border:1px solid #d9e2ef;border-radius:10px;padding:12px;margin:10px 0;overflow:auto}}
.adql-command{{margin-bottom:6px;white-space:pre-wrap}}
.adql-message{{color:#64748b;font-size:.9em;margin-bottom:8px}}
.adql-error{{color:#b42318;background:#fee4e2;padding:8px;border-radius:7px}}
.adql-table{{border-collapse:collapse;width:100%;font-size:.88em}}
.adql-table th,.adql-table td{{padding:7px 9px;border-bottom:1px solid #d9e2ef;text-align:left}}
.adql-table th{{background:#f6f8fb}}
.adql-output pre{{white-space:pre-wrap}}
</style>
<div class="adql-summary"><strong>ADQL {status}</strong> · {self.completed_count}/{self.statement_count} statements · {self.duration_seconds:.4f}s</div>
{''.join(cards)}
</div>"""

    def show(self) -> "ADQLRunResult":
        try:
            from IPython.display import HTML, display
        except ImportError:
            print(self.to_dict())
        else:
            display(HTML(self.to_html()))

        return self

    def _repr_html_(self) -> str | None:
        if not self.auto_display:
            return None

        return self.to_html()


@dataclass(slots=True)
class ADQLCell:
    number: int
    title: str
    source: str
    start_line: int
    end_line: int
    kind: str = "code"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "kind": self.kind,
            "source": self.source,
        }


@dataclass(slots=True)
class ADQLDocument:
    path: Path
    source: str
    cells: list[ADQLCell] = field(default_factory=list)

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    def cell(self, number: int) -> ADQLCell:
        for item in self.cells:
            if item.number == number:
                return item

        raise IndexError(
            f"ADQL cell {number} was not found. "
            f"The document has {self.cell_count} cell(s)."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "cell_count": self.cell_count,
            "cells": [item.to_dict() for item in self.cells],
        }


@dataclass(slots=True)
class ADQLCellRun:
    cell: ADQLCell
    result: ADQLRunResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell": self.cell.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(slots=True)
class ADQLFileResult:
    document: ADQLDocument
    project: Any = field(repr=False)
    cell_runs: list[ADQLCellRun] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    auto_display: bool = field(default=True, repr=False)

    @property
    def source_name(self) -> str:
        """Compatibility name matching an inline ADQL run result."""
        return str(self.document.path)

    @property
    def success(self) -> bool:
        return bool(self.cell_runs) and all(
            item.result.success for item in self.cell_runs
        )

    @property
    def completed_cell_count(self) -> int:
        return sum(1 for item in self.cell_runs if item.result.success)

    @property
    def failed_cell_count(self) -> int:
        return sum(1 for item in self.cell_runs if not item.result.success)

    @property
    def latest(self) -> ADQLRunResult | None:
        return self.cell_runs[-1].result if self.cell_runs else None

    @property
    def data(self) -> pd.DataFrame | None:
        return self.latest.data if self.latest is not None else None

    @property
    def value(self) -> Any:
        return self.latest.value if self.latest is not None else None

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0

        return round(
            (self.finished_at - self.started_at).total_seconds(),
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.document.path),
            "success": self.success,
            "cell_count": len(self.cell_runs),
            "completed_cell_count": self.completed_cell_count,
            "failed_cell_count": self.failed_cell_count,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at is not None
                else None
            ),
            "cells": [item.to_dict() for item in self.cell_runs],
        }

    def to_html(self) -> str:
        sections = []

        for item in self.cell_runs:
            sections.append(
                f"""<section class="adql-file-cell">
<h3>Cell {item.cell.number}: {html.escape(item.cell.title)}</h3>
{item.result.to_html()}
</section>"""
            )

        status = "Completed" if self.success else "Failed"
        return f"""<div class="adql-file-result">
<div><strong>{html.escape(self.document.path.name)} — {status}</strong> ·
{self.completed_cell_count}/{len(self.cell_runs)} cells ·
{self.duration_seconds:.4f}s</div>
{''.join(sections)}
</div>"""

    def show(self) -> "ADQLFileResult":
        try:
            from IPython.display import HTML, display
        except ImportError:
            print(self.to_dict())
        else:
            display(HTML(self.to_html()))

        return self

    def _repr_html_(self) -> str | None:
        if not self.auto_display:
            return None

        return self.to_html()
