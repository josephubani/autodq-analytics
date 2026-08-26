from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname


@runtime_checkable
class PipelineSourceResolver(Protocol):
    """Resolve a platform reference into a local path for AutoDQ."""

    def resolve(
        self,
        reference: str | Path,
        *,
        base_path: str | Path | None = None,
        must_exist: bool = True,
    ) -> Path: ...


@runtime_checkable
class PipelineArtifactStore(Protocol):
    """Persist structured pipeline results to an artifact destination."""

    def location(
        self,
        reference: str | Path,
        *,
        base_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> str: ...

    def write_json(
        self,
        reference: str | Path,
        payload: dict[str, Any],
        *,
        base_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> str: ...


class LocalSourceResolver:
    """Resolve local paths and file:// URIs."""

    def resolve(
        self,
        reference: str | Path,
        *,
        base_path: str | Path | None = None,
        must_exist: bool = True,
    ) -> Path:
        path = self._path(reference)

        if not path.is_absolute():
            base = (
                Path(base_path).expanduser()
                if base_path is not None
                else Path.cwd()
            )
            path = base / path

        path = path.expanduser().resolve()

        if must_exist and not path.exists():
            raise FileNotFoundError(f"Pipeline input not found: {path}")

        return path

    @staticmethod
    def _path(reference: str | Path) -> Path:
        if isinstance(reference, Path):
            return reference

        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Pipeline path reference cannot be empty.")

        value = reference.strip()
        parsed = urlparse(value)
        windows_drive = len(parsed.scheme) == 1 and value[1:3] in {":/", ":\\"}

        if parsed.scheme and not windows_drive:
            if parsed.scheme.lower() != "file":
                raise ValueError(
                    f"LocalSourceResolver does not support {parsed.scheme}:// "
                    "references. Register a platform-specific source resolver."
                )

            if parsed.netloc not in {"", "localhost"}:
                raise ValueError("Remote file:// hosts are not supported.")

            return Path(url2pathname(unquote(parsed.path)))

        return Path(value)


class LocalArtifactStore:
    """Atomically persist JSON results on the local filesystem."""

    def __init__(self, resolver: PipelineSourceResolver | None = None):
        self.resolver = resolver or LocalSourceResolver()

    def location(
        self,
        reference: str | Path,
        *,
        base_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> str:
        path = self.resolver.resolve(
            reference,
            base_path=base_path,
            must_exist=False,
        )

        if path.suffix.lower() != ".json":
            raise ValueError("Pipeline result path must end with .json.")

        if path.parent.exists() and not path.parent.is_dir():
            raise ValueError(
                f"Pipeline result parent is not a directory: {path.parent}"
            )

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Pipeline result already exists: {path}. "
                "Set overwrite_result to true to replace it."
            )

        return path.as_uri()

    def write_json(
        self,
        reference: str | Path,
        payload: dict[str, Any],
        *,
        base_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> str:
        uri = self.location(
            reference,
            base_path=base_path,
            overwrite=overwrite,
        )
        path = Path(url2pathname(unquote(urlparse(uri).path)))
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )

        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            os.replace(temporary_name, path)
        except Exception:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            finally:
                raise

        return uri


__all__ = [
    "LocalArtifactStore",
    "LocalSourceResolver",
    "PipelineArtifactStore",
    "PipelineSourceResolver",
]
