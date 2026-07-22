from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import warnings
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any
from uuid import uuid4

import joblib
import numpy as np

from autodq.ml.models import (
    FeatureImportance,
    ModelComparisonResult,
    ModelMetrics,
    ModelPrediction,
    ModelReport,
)
from autodq.persistence.models import ModelBundle, ModelManifest


class ModelPersistenceEngine:
    """Saves and restores versioned AutoDQ model bundles."""

    MODEL_FILENAME = "model.joblib"
    MANIFEST_FILENAME = "manifest.json"

    def save(
        self,
        model_report: ModelReport,
        destination: str | Path,
        overwrite: bool = False,
    ) -> ModelBundle:
        if model_report is None or model_report.model_object is None:
            raise ValueError(
                "No trained model is available. Run project.model() first."
            )

        destination_path = Path(destination).expanduser().resolve()

        if destination_path.exists() and not overwrite:
            raise FileExistsError(
                f"Model bundle already exists: {destination_path}. "
                "Use overwrite=True to replace it."
            )

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = destination_path.parent / (
            f".{destination_path.name}.tmp-{uuid4().hex}"
        )
        temporary_path.mkdir(parents=False)

        try:
            model_path = temporary_path / self.MODEL_FILENAME
            joblib.dump(model_report.model_object, model_path)
            model_sha256 = self._sha256(model_path)

            manifest = self._build_manifest(
                model_report=model_report,
                model_sha256=model_sha256,
            )
            manifest_path = temporary_path / self.MANIFEST_FILENAME

            with manifest_path.open("w", encoding="utf-8") as stream:
                json.dump(
                    manifest.to_dict(),
                    stream,
                    indent=2,
                    sort_keys=True,
                    default=self._json_default,
                )
                stream.write("\n")

            self._commit_bundle(
                temporary_path=temporary_path,
                destination_path=destination_path,
                overwrite=overwrite,
            )

        except Exception:
            self._remove_path(temporary_path)
            raise

        return ModelBundle(
            path=destination_path,
            manifest=manifest,
            model_report=model_report,
        )

    def load(self, source: str | Path) -> ModelBundle:
        source_path = Path(source).expanduser().resolve()

        if not source_path.is_dir():
            raise FileNotFoundError(
                f"Model bundle directory was not found: {source_path}"
            )

        manifest_path = source_path / self.MANIFEST_FILENAME

        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Model manifest was not found: {manifest_path}"
            )

        try:
            with manifest_path.open("r", encoding="utf-8") as stream:
                manifest_data = json.load(stream)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Model manifest is not valid JSON: {manifest_path}"
            ) from error

        manifest = ModelManifest.from_dict(manifest_data)
        self._validate_manifest(manifest)

        model_path = source_path / manifest.model_file

        if not model_path.is_file():
            raise FileNotFoundError(
                f"Serialized model was not found: {model_path}"
            )

        actual_checksum = self._sha256(model_path)

        if actual_checksum != manifest.model_sha256:
            raise ValueError(
                "Model checksum verification failed. The bundle may be "
                "corrupted or may have been modified."
            )

        warnings.warn(
            "AutoDQ model bundles use joblib/pickle internally. "
            "Only load bundles from trusted sources.",
            UserWarning,
            stacklevel=2,
        )
        self._warn_about_runtime(manifest)
        model_object = joblib.load(model_path)
        model_report = self._restore_model_report(
            manifest=manifest,
            model_object=model_object,
        )

        return ModelBundle(
            path=source_path,
            manifest=manifest,
            model_report=model_report,
        )

    def _build_manifest(
        self,
        model_report: ModelReport,
        model_sha256: str,
    ) -> ModelManifest:
        report_data = model_report.to_dict()
        # Validation-row values are unnecessary for inference and may contain
        # sensitive target data, so model bundles retain metrics but not rows.
        report_data["predictions"] = []
        report_data["prediction_count"] = 0

        return ModelManifest(
            format_version=ModelManifest.CURRENT_FORMAT_VERSION,
            autodq_version=self._installed_version("autodq"),
            created_at=datetime.now(timezone.utc).isoformat(),
            algorithm=model_report.algorithm,
            problem_type=model_report.problem_type,
            target=model_report.target,
            feature_columns=list(model_report.feature_columns),
            feature_dtypes=dict(model_report.feature_dtypes),
            metrics=model_report.metrics.to_dict(),
            runtime={
                "python": platform.python_version(),
                "platform": platform.platform(),
                "dependencies": {
                    name: self._installed_version(name)
                    for name in (
                        "pandas",
                        "numpy",
                        "scikit-learn",
                        "joblib",
                    )
                },
            },
            model_file=self.MODEL_FILENAME,
            model_sha256=model_sha256,
            model_report=report_data,
        )

    def _validate_manifest(self, manifest: ModelManifest) -> None:
        if (
            manifest.format_version
            != ModelManifest.CURRENT_FORMAT_VERSION
        ):
            raise ValueError(
                "Unsupported model bundle format version: "
                f"{manifest.format_version}. Supported version: "
                f"{ModelManifest.CURRENT_FORMAT_VERSION}."
            )

        model_file = Path(manifest.model_file)

        if model_file.name != manifest.model_file:
            raise ValueError(
                "Invalid model file path in manifest."
            )

        if not manifest.feature_columns:
            raise ValueError(
                "Invalid model manifest: feature_columns is empty."
            )

    def _restore_model_report(
        self,
        manifest: ModelManifest,
        model_object,
    ) -> ModelReport:
        report_data = manifest.model_report
        metrics = self._restore_metrics(
            report_data.get("metrics", manifest.metrics)
        )
        feature_importance = [
            FeatureImportance(
                feature=str(item["feature"]),
                importance=float(item["importance"]),
                rank=int(item["rank"]),
            )
            for item in report_data.get("feature_importance", [])
        ]
        predictions = [
            ModelPrediction(
                actual=item.get("actual"),
                predicted=item.get("predicted"),
                residual=item.get("residual"),
            )
            for item in report_data.get("predictions", [])
        ]
        comparisons = []

        for item in report_data.get("model_comparison", []):
            comparisons.append(
                ModelComparisonResult(
                    algorithm=str(item["algorithm"]),
                    problem_type=str(item["problem_type"]),
                    primary_metric=str(item["primary_metric"]),
                    primary_score=float(item["primary_score"]),
                    metrics=self._restore_metrics(item["metrics"]),
                    rank=int(item.get("rank", 0)),
                )
            )

        generated_at = datetime.now()
        generated_value = report_data.get("generated_at")

        if generated_value:
            try:
                generated_at = datetime.fromisoformat(generated_value)
            except ValueError:
                pass

        preprocessing_object = None

        if hasattr(model_object, "named_steps"):
            preprocessing_object = model_object.named_steps.get(
                "preprocessor"
            )

        return ModelReport(
            target=manifest.target,
            problem_type=manifest.problem_type,
            algorithm=manifest.algorithm,
            metrics=metrics,
            feature_importance=feature_importance,
            predictions=predictions,
            recommendations=list(
                report_data.get("recommendations", [])
            ),
            model_object=model_object,
            preprocessing_object=preprocessing_object,
            feature_columns=list(manifest.feature_columns),
            feature_dtypes=dict(manifest.feature_dtypes),
            generated_at=generated_at,
            model_comparison=comparisons,
        )

    def _restore_metrics(self, data: dict[str, Any]) -> ModelMetrics:
        return ModelMetrics(
            problem_type=str(data["problem_type"]),
            algorithm=str(data["algorithm"]),
            mae=data.get("mae"),
            rmse=data.get("rmse"),
            r2=data.get("r2"),
            accuracy=data.get("accuracy"),
            precision=data.get("precision"),
            recall=data.get("recall"),
            f1=data.get("f1"),
        )

    def _commit_bundle(
        self,
        temporary_path: Path,
        destination_path: Path,
        overwrite: bool,
    ) -> None:
        if not destination_path.exists():
            os.replace(temporary_path, destination_path)
            return

        if not overwrite:
            raise FileExistsError(
                f"Model bundle already exists: {destination_path}"
            )

        backup_path = destination_path.parent / (
            f".{destination_path.name}.backup-{uuid4().hex}"
        )
        os.replace(destination_path, backup_path)

        try:
            os.replace(temporary_path, destination_path)
        except Exception:
            os.replace(backup_path, destination_path)
            raise
        else:
            self._remove_path(backup_path)

    def _warn_about_runtime(self, manifest: ModelManifest) -> None:
        current_autodq = self._installed_version("autodq")

        if current_autodq != manifest.autodq_version:
            warnings.warn(
                "The model was saved with AutoDQ "
                f"{manifest.autodq_version}, but the current version is "
                f"{current_autodq}.",
                RuntimeWarning,
                stacklevel=2,
            )

        saved_python = str(manifest.runtime.get("python", ""))
        current_python = platform.python_version()

        if saved_python and saved_python.split(".")[:2] != (
            current_python.split(".")[:2]
        ):
            warnings.warn(
                "The model was saved with Python "
                f"{saved_python}, but the current version is "
                f"{current_python}.",
                RuntimeWarning,
                stacklevel=2,
            )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _installed_version(package_name: str) -> str:
        try:
            return metadata.version(package_name)
        except metadata.PackageNotFoundError:
            return "0.1.0" if package_name == "autodq" else "unknown"

    @staticmethod
    def _json_default(value):
        if isinstance(value, np.generic):
            return value.item()

        if isinstance(value, (datetime, Path)):
            return str(value)

        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )

    @staticmethod
    def _remove_path(path: Path) -> None:
        if not path.exists():
            return

        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
