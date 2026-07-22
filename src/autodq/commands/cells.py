from __future__ import annotations

import re
from pathlib import Path

from autodq.commands.models import ADQLCell, ADQLDocument


class ADQLCellParser:
    """Split a plain-text ADQL document into notebook-style cells."""

    CELL_MARKER = re.compile(
        r"^\s*(?:#|--)\s*%%(?:\s*\[(.*?)\])?(?:\s+(.*?))?\s*$"
    )

    def read(self, path: str | Path) -> ADQLDocument:
        document_path = Path(path).expanduser().resolve()

        if document_path.suffix.lower() != ".adql":
            raise ValueError("ADQL documents must end with .adql.")

        if not document_path.is_file():
            raise FileNotFoundError(
                f"ADQL document was not found: {document_path}"
            )

        source = document_path.read_text(encoding="utf-8")
        return ADQLDocument(
            path=document_path,
            source=source,
            cells=self.split(source),
        )

    def split(self, source: str) -> list[ADQLCell]:
        if not isinstance(source, str):
            raise TypeError("ADQL document source must be a string.")

        lines = source.splitlines(keepends=True)

        if not lines:
            return [
                ADQLCell(
                    number=1,
                    title="Script",
                    source="",
                    start_line=1,
                    end_line=1,
                )
            ]

        markers = []

        for index, line in enumerate(lines):
            match = self.CELL_MARKER.match(line.rstrip("\r\n"))

            if match is not None:
                tag = (match.group(1) or "").strip()
                trailing = (match.group(2) or "").strip()
                kind = "markdown" if tag.casefold() == "markdown" else "code"
                title = (
                    trailing
                    if tag.casefold() in {"markdown", "code"}
                    else tag or trailing
                )
                markers.append((index, title, kind))

        if not markers:
            return [
                ADQLCell(
                    number=1,
                    title="Script",
                    source=source,
                    start_line=1,
                    end_line=max(1, len(lines)),
                )
            ]

        cells = []
        first_marker = markers[0][0]
        preamble = "".join(lines[:first_marker])

        if self._has_executable_source(preamble):
            cells.append(
                ADQLCell(
                    number=1,
                    title="Preamble",
                    source=preamble,
                    start_line=1,
                    end_line=max(1, first_marker),
                )
            )

        for marker_index, (line_index, title, kind) in enumerate(markers):
            next_line = (
                markers[marker_index + 1][0]
                if marker_index + 1 < len(markers)
                else len(lines)
            )
            cell_number = len(cells) + 1
            cells.append(
                ADQLCell(
                    number=cell_number,
                    title=title or f"Cell {cell_number}",
                    source="".join(lines[line_index + 1 : next_line]),
                    start_line=line_index + 1,
                    end_line=max(line_index + 1, next_line),
                    kind=kind,
                )
            )

        return cells

    @staticmethod
    def _has_executable_source(source: str) -> bool:
        for line in source.splitlines():
            stripped = line.strip()

            if stripped and not stripped.startswith(("#", "--")):
                return True

        return False
