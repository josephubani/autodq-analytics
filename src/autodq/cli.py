from __future__ import annotations

import argparse
import json
import sys
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


def main(argv: list[str] | None = None) -> int:
    arguments = _normalise_argv(
        list(sys.argv[1:] if argv is None else argv)
    )
    parser = _build_parser()
    options = parser.parse_args(arguments)
    runner = ADQLFileRunner()

    try:
        if options.command == "run":
            result = runner.run(
                options.path,
                dataset=options.dataset,
                target=options.target,
                cell=options.cell,
                through_cell=options.through_cell,
                continue_on_error=options.continue_on_error,
                raise_on_error=False,
                auto_display=False,
            )
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
