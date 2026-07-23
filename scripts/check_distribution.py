#!/usr/bin/env python3
"""Validate AutoDQ wheel and source-distribution release artifacts."""

from __future__ import annotations

import argparse
import email
import re
import tarfile
import zipfile
from pathlib import Path


PROJECT_NAME = "autodq"
REQUIRED_DEPENDENCIES = {
    "joblib",
    "matplotlib",
    "numpy",
    "openpyxl",
    "pandas",
    "scikit-learn",
    "scipy",
    "shap",
    "statsmodels",
    "xlrd",
}
REQUIRED_WHEEL_FILES = {
    "autodq/__init__.py",
    "autodq/__main__.py",
    "autodq/_version.py",
    "autodq/cli.py",
    "autodq/vscode/extension/package.json",
    "autodq/vscode/extension/icons/adql-light.svg",
    "autodq/vscode/extension/icons/adql-dark.svg",
    "autodq/vscode/extension/syntaxes/adql.tmLanguage.json",
}
REQUIRED_SDIST_SUFFIXES = {
    "/.github/workflows/tests.yml",
    "/.github/workflows/publish-pypi.yml",
    "/.github/workflows/publish-testpypi.yml",
    "/CHANGELOG.md",
    "/LICENSE",
    "/MANIFEST.in",
    "/README.md",
    "/docs/RELEASING.md",
    "/docs/RELEASE_NOTES_0.1.0.md",
    "/examples/sales_auto.adql",
    "/examples/sales_analysis.adql",
    "/pyproject.toml",
    "/scripts/check_distribution.py",
    "/tests/test_packaging.py",
}
FORBIDDEN_PARTS = {"__pycache__", ".DS_Store"}


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def dependency_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)

    if match is None:
        raise ValueError(f"Invalid dependency metadata: {requirement}")

    return normalized_name(match.group(0))


def forbidden_members(
    names: set[str],
    *,
    allow_egg_info: bool = False,
) -> list[str]:
    forbidden = []

    for name in names:
        parts = set(Path(name).parts)

        if parts & FORBIDDEN_PARTS or name.endswith((".pyc", ".pyo")):
            forbidden.append(name)

        if not allow_egg_info and any(
            part.endswith(".egg-info") for part in parts
        ):
            forbidden.append(name)

    return sorted(set(forbidden))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def inspect_wheel(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = REQUIRED_WHEEL_FILES - names
        require(not missing, f"Wheel is missing: {', '.join(sorted(missing))}")

        forbidden = forbidden_members(names)
        require(not forbidden, f"Wheel contains forbidden files: {forbidden}")

        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        entry_point_names = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        license_names = [
            name for name in names if ".dist-info/licenses/LICENSE" in name
        ]

        require(len(metadata_names) == 1, "Wheel must contain one METADATA file.")
        require(
            len(entry_point_names) == 1,
            "Wheel must contain one entry_points.txt file.",
        )
        require(license_names, "Wheel does not contain the MIT license file.")

        metadata = email.message_from_bytes(archive.read(metadata_names[0]))
        require(
            normalized_name(metadata["Name"]) == PROJECT_NAME,
            f"Unexpected project name: {metadata['Name']}",
        )
        require(metadata["Version"], "Wheel metadata does not contain a version.")
        require(
            metadata["Requires-Python"] == ">=3.10",
            f"Unexpected Python requirement: {metadata['Requires-Python']}",
        )

        dependencies = {
            dependency_name(value)
            for value in metadata.get_all("Requires-Dist", [])
            if "extra ==" not in value
        }
        missing_dependencies = REQUIRED_DEPENDENCIES - dependencies
        require(
            not missing_dependencies,
            "Wheel metadata is missing runtime dependencies: "
            + ", ".join(sorted(missing_dependencies)),
        )

        entry_points = archive.read(entry_point_names[0]).decode("utf-8")
        require("[console_scripts]" in entry_points, "Console scripts are missing.")
        require(
            "autodq = autodq.cli:main" in entry_points,
            "The autodq console entry point is missing or incorrect.",
        )

        return metadata["Version"]


def inspect_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = {member.name for member in archive.getmembers()}

    missing = {
        suffix
        for suffix in REQUIRED_SDIST_SUFFIXES
        if not any(name.endswith(suffix) for name in names)
    }
    require(not missing, f"Source archive is missing: {', '.join(sorted(missing))}")

    forbidden = forbidden_members(names, allow_egg_info=True)
    require(not forbidden, f"Source archive contains forbidden files: {forbidden}")


def find_one(directory: Path, pattern: str, label: str) -> Path:
    matches = sorted(directory.glob(pattern))
    require(
        len(matches) == 1,
        f"Expected exactly one {label} in {directory}, found {len(matches)}.",
    )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        default="dist",
        type=Path,
        help="Directory containing one AutoDQ wheel and one source archive.",
    )
    options = parser.parse_args()
    directory = options.directory.expanduser().resolve()

    require(directory.is_dir(), f"Distribution directory not found: {directory}")
    wheel = find_one(directory, "autodq-*.whl", "wheel")
    sdist = find_one(directory, "autodq-*.tar.gz", "source archive")
    version = inspect_wheel(wheel)
    inspect_sdist(sdist)

    print(f"AutoDQ {version} distributions passed inspection.")
    print(f"Wheel: {wheel.name}")
    print(f"Source: {sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
