#!/usr/bin/env python3
"""Install an AutoDQ wheel in isolation and exercise its public interfaces."""

from __future__ import annotations

import argparse
import csv
import email
import json
import os
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path


def find_wheel(source: Path) -> Path:
    source = source.expanduser().resolve()

    if source.is_file():
        if source.suffix != ".whl":
            raise ValueError(f"Expected a wheel file, received: {source}")
        return source

    matches = sorted(source.glob("autodq-*.whl"))

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one AutoDQ wheel in {source}, found {len(matches)}."
        )

    return matches[0]


def wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]

        if len(metadata_names) != 1:
            raise RuntimeError("The wheel must contain exactly one METADATA file.")

        metadata = email.message_from_bytes(archive.read(metadata_names[0]))
        version = metadata.get("Version")

    if not version:
        raise RuntimeError("The wheel metadata does not contain a version.")

    return version


def environment_executable(root: Path, name: str) -> Path:
    directory = root / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return directory / f"{name}{suffix}"


def run(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = completed.stdout.strip()

    if output:
        print(output)

    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: "
            + " ".join(command)
        )

    return output


def write_dataset(path: Path) -> int:
    rows = []
    regions = ("North", "South", "East", "West")

    for index in range(60):
        units = 2 + index % 17
        price = 12.5 + (index % 11) * 4.25
        discount = (index % 4) * 0.05
        region = regions[index % len(regions)]
        revenue = round(units * price * (1 - discount), 2)
        rows.append([index + 1, units, price, discount, region, revenue])

    rows[8][4] = ""
    rows[12][1] = ""
    rows.append(rows[0].copy())

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["Transaction_ID", "Units", "Price", "Discount", "Region", "Revenue"]
        )
        writer.writerows(rows)

    return len(rows)


def write_adql(path: Path) -> None:
    path.write_text(
        "# %% [Dataset]\n"
        "DATASET \"acceptance.csv\" TARGET Revenue;\n"
        "# %% [Automatic review]\n"
        "AUTO MODE review VISUALIZE false CONTINUE_ON_ERROR false;\n"
        "# %% [Regional totals]\n"
        "SELECT Region, SUM(Revenue) AS total_revenue, COUNT(*) AS transactions\n"
        "FROM CURRENT WHERE Region IS NOT NULL GROUP BY Region\n"
        "ORDER BY total_revenue DESC;\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "wheel",
        nargs="?",
        default="dist",
        type=Path,
        help="AutoDQ wheel or directory containing exactly one wheel.",
    )
    options = parser.parse_args()
    wheel = find_wheel(options.wheel)
    version = wheel_version(wheel)

    with tempfile.TemporaryDirectory(prefix="autodq-wheel-smoke-") as directory:
        root = Path(directory)
        environment = root / "venv"
        workspace = root / "workspace"
        workspace.mkdir()
        venv.EnvBuilder(with_pip=True).create(environment)

        python = environment_executable(environment, "python")
        autodq = environment_executable(environment, "autodq")
        dataset = workspace / "acceptance.csv"
        workflow = workspace / "acceptance.adql"
        result_path = workspace / "result.json"
        row_count = write_dataset(dataset)
        write_adql(workflow)

        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(wheel),
            ],
            cwd=workspace,
        )
        run([str(python), "-m", "pip", "check"], cwd=workspace)

        cli_version = run([str(autodq), "--version"], cwd=workspace)
        module_version = run(
            [str(python), "-m", "autodq", "--version"],
            cwd=workspace,
        )
        expected = f"AutoDQ {version}"

        if cli_version != expected or module_version != expected:
            raise RuntimeError(
                f"Version mismatch: expected {expected!r}, received "
                f"{cli_version!r} and {module_version!r}."
            )

        run([str(autodq), "validate", str(workflow)], cwd=workspace)
        run(
            [
                str(autodq),
                "run",
                str(workflow),
                "--json",
                str(result_path),
            ],
            cwd=workspace,
        )

        payload = json.loads(result_path.read_text(encoding="utf-8"))

        if not payload.get("success"):
            raise RuntimeError("The installed wheel failed the ADQL acceptance workflow.")

        if payload.get("completed_cell_count") != 3:
            raise RuntimeError("The ADQL acceptance workflow did not complete all cells.")

        api_check = (
            "import sys; from autodq import AutoDQ; "
            "project = AutoDQ(sys.argv[1], target='Revenue'); "
            "profile = project.profile(); diagnosis = project.diagnose(); "
            f"assert profile['rows'] == {row_count}; "
            "assert 0 <= diagnosis.quality_score <= 100; "
            "result = project.auto(mode='review', visualize=False, "
            "auto_display=False); assert result.success; print('Python API OK')"
        )
        run([str(python), "-c", api_check, str(dataset)], cwd=workspace)

        extension_output = run(
            [str(autodq), "vscode", "path"],
            cwd=workspace,
        )
        extension = Path(extension_output.splitlines()[-1])

        for relative in (
            "package.json",
            "icons/adql-light.svg",
            "icons/adql-dark.svg",
            "syntaxes/adql.tmLanguage.json",
        ):
            if not (extension / relative).is_file():
                raise RuntimeError(f"Bundled VS Code asset is missing: {relative}")

    print(f"AutoDQ {version} wheel smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
