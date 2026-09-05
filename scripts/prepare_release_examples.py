#!/usr/bin/env python3
"""Remove persisted notebook outputs from distributable ADQL examples."""

from __future__ import annotations

import argparse
from pathlib import Path


OUTPUT_CACHE_START = '# <autodq-output-cache version="1">'
OUTPUT_CACHE_END = "# </autodq-output-cache>"
EXCLUDED_EXAMPLES = {"sales_analysis.adql"}


def strip_output_caches(source: str) -> tuple[str, int]:
    """Return ADQL source without complete persisted-output blocks."""
    lines = source.splitlines(keepends=True)
    removed = 0

    while True:
        start = next(
            (
                index
                for index in range(len(lines) - 1, -1, -1)
                if lines[index].strip() == OUTPUT_CACHE_START
            ),
            None,
        )
        if start is None:
            break

        end = next(
            (
                index
                for index in range(start + 1, len(lines))
                if lines[index].strip() == OUTPUT_CACHE_END
            ),
            None,
        )
        if end is None:
            raise ValueError(
                "Found an ADQL output-cache start marker without an end marker."
            )

        del lines[start : end + 1]
        removed += 1

    cleaned = "".join(lines).rstrip() + "\n"
    return cleaned, removed


def distributable_examples(root: Path) -> list[Path]:
    return [
        path
        for path in sorted((root / "examples").glob("*.adql"))
        if path.name not in EXCLUDED_EXAMPLES
    ]


def prepare(paths: list[Path]) -> int:
    removed = 0

    for path in paths:
        source = path.read_text(encoding="utf-8")
        cleaned, count = strip_output_caches(source)
        if count:
            path.write_text(cleaned, encoding="utf-8")
            print(f"Removed {count} output cache(s) from {path}.")
            removed += count

    print(
        f"Prepared {len(paths)} distributable ADQL example(s); "
        f"removed {removed} output cache(s)."
    )
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    paths = [path.expanduser().resolve() for path in args.paths]
    if not paths:
        paths = distributable_examples(root)

    prepare(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
