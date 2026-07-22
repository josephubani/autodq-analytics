from __future__ import annotations

import shutil
from importlib.resources import as_file, files
from pathlib import Path


EXTENSION_VERSION = "0.2.1"


def extension_path() -> Path:
    """Return the bundled VS Code extension directory."""
    resource = files("autodq.vscode").joinpath("extension")

    with as_file(resource) as path:
        return Path(path)


def install_extension(
    destination: str | Path | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Copy the bundled extension into VS Code's extension directory."""
    target = (
        Path(destination).expanduser()
        if destination is not None
        else Path.home()
        / ".vscode"
        / "extensions"
        / f"autodq.adql-{EXTENSION_VERSION}"
    )

    if target.exists():
        if not overwrite:
            raise FileExistsError(
                f"VS Code extension already exists: {target}. "
                "Use --overwrite to replace it."
            )

        shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(extension_path(), target)
    return target.resolve()
