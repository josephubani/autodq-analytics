from pathlib import Path

import pandas as pd

from autodq.auto.engine import AutoEngine
from autodq.auto.models import AutoRunConfig
from autodq.cleaning.engine import CleaningEngine
from autodq.commands.errors import ADQLExecutionError
from autodq.commands.executor import ADQLExecutor
from autodq.commands.parser import ADQLParser
from autodq.commands.runner import ADQLFileRunner
from autodq.commands.validator import ADQLValidator
from autodq.dashboard.engine import DashboardEngine
from autodq.core.session import AutoDQSession
from autodq.core.state import AutoDQState
from autodq.decision.engine import DecisionEngine
from autodq.diagnosis.engine import run_diagnosis
from autodq.interpretation.engine import InterpretationEngine
from autodq.io.loaders import load_dataset
from autodq.knowledge.engine import KnowledgeEngine
from autodq.preview.engine import PreviewEngine
from autodq.profiling.profiler import generate_profile
from autodq.recommendations.engine import RecommendationEngine
from autodq.renderers.console.cleaning import ConsoleCleaningRenderer
from autodq.renderers.console.diagnosis import ConsoleDiagnosisRenderer
from autodq.renderers.console.interpretation import ConsoleInterpretationRenderer
from autodq.renderers.console.preview import ConsolePreviewRenderer
from autodq.renderers.console.profile import ConsoleProfileRenderer
from autodq.renderers.console.recommendations import ConsoleRecommendationRenderer
from autodq.renderers.console.statistics import ConsoleStatisticsRenderer
from autodq.renderers.console.validation import ConsoleValidationRenderer
from autodq.reporting.engine import ReportingEngine
from autodq.statistics.engine import StatisticsEngine
from autodq.validation.engine import ValidationEngine
from autodq.visualization.engine import VisualizationEngine
from autodq.renderers.console.visualization import ConsoleVisualizationRenderer
from autodq.io.loaders import export_dataset, load_dataset
from autodq.correlation.engine import CorrelationEngine
from autodq.renderers.console.correlation import ConsoleCorrelationRenderer
from autodq.ml_readiness.engine import MLReadinessEngine
from autodq.renderers.console.ml_readiness import ConsoleMLReadinessRenderer
from autodq.features.engine import FeatureEngineeringEngine
from autodq.renderers.console.features import ConsoleFeatureRenderer
from autodq.ml.engine import MLEngine
from autodq.renderers.console.model import ConsoleModelRenderer
from autodq.prediction.engine import PredictionEngine
from autodq.renderers.console.prediction import ConsolePredictionRenderer
from autodq.explainability.engine import ExplainabilityEngine
from autodq.datasets.manager import DatasetManager
from autodq.datasets.merger import DatasetMerger
from autodq.renderers.console.datasets import ConsoleDatasetRenderer
from autodq.blue.engine import BLUEEngine
from autodq.renderers.console.blue import ConsoleBLUERenderer
from autodq.visualization.gallery import VisualizationGallery
from autodq.visualization.notebook_renderer import (NotebookVisualizationRenderer,)
from autodq.visualization.models import VisualizationReport
from autodq.blue.visualizer import (BLUEVisualizationReport,BLUEVisualizer,)
from autodq.blue.visual_interpreter import (BLUEVisualInterpreter,)
from autodq.blue.prescriptions import BLUEPrescriptionEngine
from autodq.explainability.shap_visualizer import SHAPVisualizer
from autodq.persistence.engine import ModelPersistenceEngine
from autodq.review.engine import CleaningReviewEngine
from autodq.workspaces.manager import WorkspaceManager
from autodq.workspaces.models import WorkspaceContext


class AutoDQ:
    """
    Main project controller for AutoDQ Analytics.
    """

    def __init__(self, dataset_path: str, target: str | None = None):
        self.state = AutoDQState(
            dataset_path=Path(dataset_path),
            target=target,
        )

        self.knowledge_engine = KnowledgeEngine()
        self.statistics_engine = StatisticsEngine()
        self.interpretation_engine = InterpretationEngine()
        self.cleaning_engine = CleaningEngine()
        self.validation_engine = ValidationEngine()
        self.reporting_engine = ReportingEngine()
        self.visualization_engine = VisualizationEngine()
        self.visualization_gallery = VisualizationGallery()
        self.notebook_visualization_renderer = (NotebookVisualizationRenderer())
        self.correlation_engine = CorrelationEngine()
        self.ml_readiness_engine = MLReadinessEngine()
        self.feature_engine = FeatureEngineeringEngine()
        self.ml_engine = MLEngine()
        self.prediction_engine = PredictionEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.dataset_manager = DatasetManager()
        self.dataset_merger = DatasetMerger()
        self.blue_engine = BLUEEngine()
        self.blue_visualizer = BLUEVisualizer()
        self.blue_visual_interpreter = BLUEVisualInterpreter()
        self.blue_prescription_engine = BLUEPrescriptionEngine()
        self.model_persistence_engine = ModelPersistenceEngine()
        self.cleaning_review_engine = CleaningReviewEngine()
        self.auto_engine = AutoEngine()
        self.dashboard_engine = DashboardEngine()
        self.adql_parser = ADQLParser()
        self.adql_validator = ADQLValidator()
        self.adql_executor = ADQLExecutor()
        self.adql_file_runner = ADQLFileRunner(
            parser=self.adql_parser,
            validator=self.adql_validator,
            executor=self.adql_executor,
        )
        self.workspace_manager: WorkspaceManager | None = None
        self.workspace: WorkspaceContext | None = None

        self.session = AutoDQSession(dataset_path=str(self.state.dataset_path))
        self.dataset_manager.add(
          name="main",
          dataset_path=self.state.dataset_path,
        is_primary=True,
      )

    @property
    def dataset_path(self):
        return self.state.dataset_path

    @property
    def target(self):
        return self.state.target

    @property
    def data(self):
        return self.state.data

    @property
    def workspace_name(self) -> str | None:
        if self.workspace is None:
            return None

        return self.workspace.manifest.name

    @classmethod
    def create_workspace(
        cls,
        name: str,
        dataset_path: str,
        target: str | None = None,
        workspace_root: str = ".autodq/workspaces",
    ) -> "AutoDQ":
        """Create an isolated workspace and return its AutoDQ project."""
        manager = WorkspaceManager(workspace_root)
        context = manager.create(
            name=name,
            dataset_path=dataset_path,
            target=target,
        )
        active_dataset = next(
            item
            for item in context.manifest.datasets
            if item.name == context.manifest.active_dataset
        )
        project = cls(
            str(manager.dataset_path(context, active_dataset)),
            target=target,
        )
        project.workspace_manager = manager
        project.workspace = context
        project.session.log(
            step="create_workspace",
            message="AutoDQ workspace created.",
            metadata={
                "workspace": context.manifest.workspace_id,
                "path": str(context.path),
            },
        )
        project.save_workspace(include_model=False)
        return project

    @classmethod
    def open_workspace(
        cls,
        name_or_path: str,
        workspace_root: str = ".autodq/workspaces",
        load_model: bool = True,
    ) -> "AutoDQ":
        """Restore datasets, session history, and a saved model."""
        manager = WorkspaceManager(workspace_root)
        context = manager.open(name_or_path)
        active_dataset = next(
            item
            for item in context.manifest.datasets
            if item.name == context.manifest.active_dataset
        )
        active_path = manager.dataset_path(context, active_dataset)
        project = cls(
            str(active_path),
            target=context.manifest.target,
        )
        project.workspace_manager = manager
        project.workspace = context
        project.dataset_manager.clear()

        for dataset in context.manifest.datasets:
            dataset_path = manager.dataset_path(context, dataset)
            project.dataset_manager.add(
                name=dataset.name,
                dataset_path=dataset_path,
                data=manager.load_dataset(context, dataset),
                is_primary=(
                    dataset.name == context.manifest.active_dataset
                ),
            )

        primary = project.dataset_manager.primary()

        if primary is None:
            raise ValueError("Workspace has no active dataset.")

        project.state.dataset_path = Path(primary.path)
        project.state.data = primary.data.copy()
        session_data = manager.load_session(context)

        if session_data is not None:
            project.session = AutoDQSession.from_dict(session_data)

        model_path = manager.model_path(context)

        if load_model and model_path is not None:
            project.load_model(str(model_path))

        project.session.log(
            step="open_workspace",
            message="AutoDQ workspace restored.",
            metadata={
                "workspace": context.manifest.workspace_id,
                "datasets": len(context.manifest.datasets),
                "model_loaded": bool(load_model and model_path),
            },
        )
        return project

    @classmethod
    def list_workspaces(
        cls,
        workspace_root: str = ".autodq/workspaces",
    ):
        """List valid AutoDQ workspaces under a workspace root."""
        return WorkspaceManager(workspace_root).list()

    def save_workspace(
        self,
        model_name: str = "active_model",
        include_model: bool = True,
    ) -> dict:
        """Persist all datasets, session history, and the active model."""
        if self.workspace_manager is None or self.workspace is None:
            raise RuntimeError(
                "This project is not attached to a workspace. Create it "
                "with AutoDQ.create_workspace() first."
            )

        primary = self.dataset_manager.primary()

        if primary is None:
            raise ValueError("Workspace has no primary dataset to save.")

        if self.state.data is not None:
            primary.data = self.state.data.copy()

        active_model = self.workspace_manager.model_path(self.workspace)

        if include_model and self.state.model_report is not None:
            if self.state.model_bundle is None:
                destination = self.workspace_manager.model_destination(
                    self.workspace,
                    model_name,
                )
                bundle = self.save_model(
                    str(destination),
                    overwrite=True,
                )
                active_model = bundle.path
            else:
                bundle_path = self.state.model_bundle.path.resolve()
                models_dir = self.workspace.models_dir.resolve()

                if bundle_path.is_relative_to(models_dir):
                    active_model = bundle_path
                else:
                    destination = (
                        self.workspace_manager.model_destination(
                            self.workspace,
                            model_name,
                        )
                    )
                    bundle = self.save_model(
                        str(destination),
                        overwrite=True,
                    )
                    active_model = bundle.path

        audit_entries = 0

        if self.state.cleaning_review is not None:
            audit_path = (
                self.workspace.logs_dir / "cleaning_audit.json"
            )
            self.state.cleaning_review.export_audit(audit_path)
            audit_entries = self.state.cleaning_review.audit_count
            self.workspace.manifest.metadata["cleaning_audit"] = (
                "logs/cleaning_audit.json"
            )

        self.session.log(
            step="save_workspace",
            message="AutoDQ workspace saved.",
            metadata={
                "workspace": self.workspace.manifest.workspace_id,
                "datasets": len(self.dataset_manager.entries()),
                "model_saved": active_model is not None,
                "cleaning_audit_entries": audit_entries,
            },
        )
        self.workspace = self.workspace_manager.save(
            context=self.workspace,
            dataset_entries=self.dataset_manager.entries(),
            target=self.state.target,
            session=self.session.to_dict(),
            active_model=active_model,
        )
        return self.workspace_info()

    def workspace_info(self) -> dict:
        """Return the active workspace manifest and local path."""
        if self.workspace is None:
            raise RuntimeError("This project is not attached to a workspace.")

        info = self.workspace.manifest.to_dict()
        info["path"] = str(self.workspace.path)
        return info

    def load(self) -> pd.DataFrame:
        primary = self.dataset_manager.primary()

        if primary is not None:
            self.state.data = primary.data.copy()

            if primary.path is not None:
                self.state.dataset_path = Path(primary.path)
        else:
            self.state.data = load_dataset(
                self.state.dataset_path
            )
            self.dataset_manager.add(
                name="main",
                dataset_path=self.state.dataset_path,
                data=self.state.data,
                is_primary=True,
            )

        self.session.log(
            step="load",
            message="Dataset loaded successfully.",
            metadata={
                "rows": len(self.state.data),
                "columns": len(self.state.data.columns),
            },
        )

        return self.state.data

    def auto(
        self,
        mode: str = "review",
        *,
        approve_all: bool | None = None,
        apply_cleaning: bool | None = None,
        visualize: bool = True,
        apply_features: bool = False,
        train_model: bool | None = None,
        generate_predictions: bool | None = None,
        explain_model: bool | None = None,
        algorithm: str = "auto",
        test_size: float = 0.2,
        random_state: int = 42,
        report_output: str | None = None,
        report_style: str = "executive",
        save_workspace: bool = False,
        refresh: bool = False,
        continue_on_error: bool = False,
        raise_on_error: bool = False,
        auto_display: bool = True,
    ):
        """Run the AutoDQ workflow with safe, traceable presets.

        ``mode='review'`` prepares analysis and cleaning decisions without
        changing data. ``mode='clean'`` approves and applies executable
        cleaning actions. ``mode='full'`` also models, predicts, and
        explains when a target is available.
        """
        config = AutoRunConfig.from_options(
            mode=mode,
            approve_all=approve_all,
            apply_cleaning=apply_cleaning,
            visualize=visualize,
            apply_features=apply_features,
            train_model=train_model,
            generate_predictions=generate_predictions,
            explain_model=explain_model,
            algorithm=algorithm,
            test_size=test_size,
            random_state=random_state,
            report_output=report_output,
            report_style=report_style,
            save_workspace=save_workspace,
            refresh=refresh,
            continue_on_error=continue_on_error,
            raise_on_error=raise_on_error,
            auto_display=auto_display,
        )
        return self.auto_engine.run(self, config)

    def change_dataset(self, dataset_path: str) -> pd.DataFrame:
        self.state.reset_all(dataset_path)
        self.dataset_manager.add(
            name="main",
            dataset_path=self.state.dataset_path,
            is_primary=True,
            overwrite=True,
        )

        self.session = AutoDQSession(dataset_path=str(self.state.dataset_path))
        self.session.log(
            step="change_dataset",
            message="Dataset path changed and project state reset.",
            metadata={"dataset_path": str(self.state.dataset_path)},
        )

        return self.load()

    def set_target(self, target: str) -> None:
        self.state.target = target

        self.session.log(
            step="set_target",
            message="Target column updated.",
            metadata={"target": target},
        )

    def set_type(self, column: str, dtype: str) -> None:
        if self.state.data is None:
            self.load()

        if column not in self.state.data.columns:
            raise ValueError(f"Column not found: {column}")

        dtype_normalized = dtype.lower().strip()

        if dtype_normalized == "datetime":
            self.state.data[column] = pd.to_datetime(
                self.state.data[column],
                errors="coerce",
            )
        elif dtype_normalized in ["str", "string", "text"]:
            self.state.data[column] = self.state.data[column].astype(str)
        elif dtype_normalized in ["int", "integer"]:
            self.state.data[column] = pd.to_numeric(
                self.state.data[column],
                errors="coerce",
            ).astype("Int64")
        elif dtype_normalized in ["float", "numeric", "number"]:
            self.state.data[column] = pd.to_numeric(
                self.state.data[column],
                errors="coerce",
            )
        elif dtype_normalized in ["category", "categorical"]:
            self.state.data[column] = self.state.data[column].astype("category")
        else:
            raise ValueError(
                f"Unsupported dtype: {dtype}. "
                "Supported: datetime, string, int, float, category"
            )

        self.state.reset_outputs()

        self.session.log(
            step="set_type",
            message="Column data type manually updated.",
            metadata={"column": column, "dtype": dtype_normalized},
        )

    def apply_knowledge(self):
        if self.state.data is None:
            self.load()

        self.state.knowledge_rules = self.knowledge_engine.get_rules_for_columns(
            list(self.state.data.columns)
        )

        matched_rules = {
            column: rule.to_dict()
            for column, rule in self.state.knowledge_rules.items()
            if rule is not None
        }

        self.session.log(
            step="knowledge",
            message="Knowledge rules applied to dataset columns.",
            metadata={"matched_columns": list(matched_rules.keys())},
        )

        return self.state.knowledge_rules
    
    
    

    def profile(self) -> dict:
        if self.state.data is None:
            self.load()

        self.state.profile_report = generate_profile(
            self.state.data,
            dataset_path=str(self.state.dataset_path),
        )

        self.session.log(
            step="profile",
            message="Dataset profile generated.",
            metadata={
                "rows": self.state.profile_report["rows"],
                "columns": self.state.profile_report["columns"],
            },
        )

        return self.state.profile_report

    def statistics(self):
        if self.state.data is None:
            self.load()

        self.state.statistics_report = self.statistics_engine.analyze(
            self.state.data
        )

        self.session.log(
            step="statistics",
            message="Statistics generated.",
            metadata={
                "columns": len(self.state.statistics_report.descriptive)
            },
        )

        return self.state.statistics_report

    def interpret(self):
        if self.state.statistics_report is None:
            self.statistics()

        self.state.interpretation_report = (
            self.interpretation_engine.interpret_statistics(
                self.state.statistics_report
            )
        )

        self.session.log(
            step="interpret",
            message="Statistical interpretations generated.",
            metadata={
                "insights": self.state.interpretation_report.insight_count
            },
        )

        return self.state.interpretation_report

    def diagnose(self):
        if self.state.data is None:
            self.load()

        self.state.diagnosis_report = run_diagnosis(self.state.data)

        self.session.log(
            step="diagnose",
            message="Data quality diagnosis completed.",
            metadata={
                "issue_count": self.state.diagnosis_report.issue_count,
                "quality_score": self.state.diagnosis_report.quality_score,
            },
        )

        return self.state.diagnosis_report

    def recommend(self):
        if self.state.diagnosis_report is None:
            self.diagnose()

        if self.state.statistics_report is None:
            self.statistics()

        if self.state.interpretation_report is None:
            self.interpret()

        engine = RecommendationEngine(self.knowledge_engine)

        self.state.recommendations = engine.recommend(
            diagnosis_report=self.state.diagnosis_report,
            statistics_report=self.state.statistics_report,
            interpretation_report=self.state.interpretation_report,
        )

        self.session.log(
            step="recommend",
            message="Evidence-aware cleaning recommendations generated.",
            metadata={"recommendation_count": len(self.state.recommendations)},
        )

        return self.state.recommendations

    def decide(self):
        if self.state.recommendations is None:
            self.recommend()

        engine = DecisionEngine()
        self.state.decision_plan = engine.build_plan(self.state.recommendations)
        self.state.cleaning_review = None
        self.state.domain_validation_report = None

        self.session.log(
            step="decide",
            message="Decision plan created.",
            metadata={"action_count": self.state.decision_plan.action_count},
        )

        return self.state.decision_plan

    def preview(self):
        if self.state.data is None:
            self.load()

        if self.state.decision_plan is None:
            self.decide()

        engine = PreviewEngine()
        self.state.preview_report = engine.preview(
            self.state.data,
            self.state.decision_plan,
        )

        self.session.log(
            step="preview",
            message="Cleaning preview generated.",
            metadata={"preview_actions": self.state.preview_report.action_count},
        )

        return self.state.preview_report

    def review_cleaning(
        self,
        use_knowledge: bool = True,
        refresh: bool = False,
        auto_display: bool = True,
    ):
        """Start or return the interactive cleaning review session."""
        if self.state.cleaning_review is not None and not refresh:
            self.state.cleaning_review.auto_display = auto_display
            return self.state.cleaning_review

        if self.state.data is None:
            self.load()

        if self.state.decision_plan is None:
            self.decide()

        if self.state.preview_report is None:
            self.preview()

        knowledge_rules = {}

        if use_knowledge:
            if self.state.knowledge_rules is None:
                self.apply_knowledge()

            knowledge_rules = self.state.knowledge_rules or {}

        review = self.cleaning_review_engine.create_review(
            df=self.state.data,
            decision_plan=self.state.decision_plan,
            preview_report=self.state.preview_report,
            knowledge_rules=knowledge_rules,
            auto_display=auto_display,
        )
        self.state.cleaning_review = review
        self.state.domain_validation_report = review.domain_report

        self.session.log(
            step="review_cleaning",
            message="Interactive cleaning review started.",
            metadata={
                "actions": review.action_count,
                "domain_rules": len(review.domain_rules),
                "outliers": (
                    review.outlier_report.outlier_count
                    if review.outlier_report is not None
                    else 0
                ),
            },
        )
        return review

    def approve(self, action_ids):
        """Approve one action ID or a collection of action IDs."""
        review = self.review_cleaning(auto_display=False)
        review.approve(action_ids)
        self.session.log(
            step="approve",
            message="Selected cleaning actions approved.",
            metadata={"action_ids": action_ids},
        )
        return review

    def reject(self, action_ids, reason: str | None = None):
        """Reject one action ID or a collection of action IDs."""
        review = self.review_cleaning(auto_display=False)
        review.reject(action_ids, reason=reason)
        self.session.log(
            step="reject",
            message="Selected cleaning actions rejected.",
            metadata={"action_ids": action_ids, "reason": reason},
        )
        return review

    def approve_all(self):
        review = self.review_cleaning(auto_display=False)
        review.approve_all()
        self.session.log(
            step="approve",
            message="All decision actions approved.",
            metadata={"approved_actions": review.action_count},
        )
        return review

    def cleaning_preview(self, action_ids=None, max_rows: int = 5):
        """Preview selected actions without modifying review data."""
        review = self.review_cleaning(auto_display=False)
        return review.preview(action_ids=action_ids, max_rows=max_rows)

    def edit_row(
        self,
        row_index,
        changes: dict,
        reason: str | None = None,
    ):
        """Edit one review row and record every changed cell."""
        review = self.review_cleaning(auto_display=False)
        row = review.edit_row(row_index, changes, reason=reason)
        self.session.log(
            step="manual_row_edit",
            message="A row was manually edited during cleaning review.",
            metadata={
                "row_index": row_index,
                "columns": list(changes),
                "reason": reason,
            },
        )
        return row

    def add_domain_rule(self, column: str, **constraints):
        """Add a range, allowed-value, pattern, null, or uniqueness rule."""
        review = self.review_cleaning(auto_display=False)
        rule = review.add_domain_rule(column, **constraints)
        self.state.domain_validation_report = None
        self.session.log(
            step="domain_rule",
            message="A custom domain rule was added.",
            metadata={"rule_id": rule.rule_id, "column": column},
        )
        return rule

    def validate_domain(self):
        """Validate the review data against all active domain rules."""
        review = self.review_cleaning(auto_display=False)
        report = review.validate_domain()
        self.state.domain_validation_report = report
        self.session.log(
            step="validate_domain",
            message="Domain validation completed.",
            metadata={
                "rules": report.rule_count,
                "violations": report.violation_count,
                "invalid_rows": report.invalid_row_count,
            },
        )
        return report

    def review_outliers(
        self,
        columns: list[str] | str | None = None,
        iqr_multiplier: float = 1.5,
    ):
        """Return row-level IQR outliers for interactive review."""
        review = self.review_cleaning(auto_display=False)
        report = review.review_outliers(
            columns=columns,
            iqr_multiplier=iqr_multiplier,
        )
        self.session.log(
            step="review_outliers",
            message="Outliers prepared for manual review.",
            metadata={
                "outliers": report.outlier_count,
                "columns": report.columns,
            },
        )
        return report

    def treat_outliers(
        self,
        column: str,
        strategy: str = "clip",
        **options,
    ) -> int:
        """Treat reviewed outliers while preserving cell-level audit data."""
        review = self.review_cleaning(auto_display=False)
        changed = review.treat_outliers(
            column=column,
            strategy=strategy,
            **options,
        )
        self.session.log(
            step="treat_outliers",
            message="Reviewed outliers were treated.",
            metadata={
                "column": column,
                "strategy": strategy,
                "changes": changed,
            },
        )
        return changed

    def export_cleaning_audit(self, output: str | None = None):
        """Export the cleaning audit trail as JSON or CSV."""
        review = self.review_cleaning(auto_display=False)

        if output is None:
            if self.workspace is None:
                raise ValueError(
                    "output is required for projects outside a workspace."
                )

            output = str(
                self.workspace.logs_dir / "cleaning_audit.json"
            )

        path = review.export_audit(output)
        self.session.log(
            step="export_cleaning_audit",
            message="Cleaning audit trail exported.",
            metadata={"output": str(path), "entries": review.audit_count},
        )
        return path

    def clean(self):
        if self.state.data is None:
            self.load()

        if self.state.decision_plan is None:
            self.decide()

        review = self.state.cleaning_review
        source_data = (
            review.working_data
            if review is not None
            else self.state.data
        )
        decision_plan = (
            review.decision_plan
            if review is not None
            else self.state.decision_plan
        )
        cleaned_data, cleaning_report = self.cleaning_engine.clean(
            df=source_data,
            decision_plan=decision_plan,
        )

        self.state.cleaned_data = cleaned_data
        self.state.cleaning_report = cleaning_report

        if review is not None:
            self.cleaning_review_engine.finalize_cleaning(
                review,
                cleaned_data=cleaned_data,
                cleaning_report=cleaning_report,
            )
            self.state.domain_validation_report = review.domain_report

        self.session.log(
            step="clean",
            message="Approved cleaning actions executed.",
            metadata={
                "actions": cleaning_report.action_count,
                "successful_actions": cleaning_report.successful_actions,
                "rows_before": len(self.state.data),
                "rows_after": len(self.state.cleaned_data),
            },
        )

        return self.state.cleaned_data

    def apply_cleaning_review(self):
        """Apply reviewed manual changes and approved cleaning actions."""
        return self.clean()

    def validate_cleaning(self):
        if self.state.data is None:
            self.load()

        if self.state.cleaned_data is None:
            print("\nNo cleaned dataset available. Run project.clean() first.")
            return None

        self.state.validation_report = self.validation_engine.validate(
            before_df=self.state.data,
            after_df=self.state.cleaned_data,
        )

        self.session.log(
            step="validate_cleaning",
            message="Post-cleaning validation completed.",
            metadata={
                "quality_score_before": self.state.validation_report.quality_score_before,
                "quality_score_after": self.state.validation_report.quality_score_after,
                "quality_score_change": self.state.validation_report.quality_score_change,
            },
        )

        return self.state.validation_report

    def generate_report(
        self,
        output: str,
        style: str = "executive",
    ) -> None:
        if self.state.visualization_report is None:
            self.visualize(chart="auto")

        output_path = Path(output)

        report = self.reporting_engine.build_report(
            self.state,
            self.session,
            output_dir=output_path.parent,
        )

        self.reporting_engine.export(
            report,
            output,
            style=style,
        )

        self.session.log(
            step="report",
            message="Report exported.",
            metadata={
                "output": output,
                "style": style,
            },
        )

        print(f"\nReport exported to {output}")
        
    
        
    def visualize(
        self,
        chart: str | None = None,
        x: str | None = None,
        y: str | None = None,
        column: str | None = None,
        stage: str = "current",
        append: bool = True,
        display: bool = True,
        allow_duplicates: bool = False,
        title: str | None = None,
        subtitle: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        theme: str | None = None,
        color: str | None = None,
        palette: str | list[str] | tuple[str, ...] | None = None,
        figsize: tuple[float, float] | None = None,
        dpi: int | None = None,
        grid: bool | None = None,
        legend: bool | None = None,
        legend_position: str | None = None,
        template: str | None = None,
        transparent: bool | None = None,
        save: str | None = None,
        save_format: str | None = None,
    ):
        if self.state.data is None:
            self.load()

        stage_normalized = stage.lower().strip()

        if stage_normalized in {"after", "cleaned"}:
            if self.state.cleaned_data is None:
                print(
                    "\nNo cleaned dataset available. "
                    "Run project.clean() first."
                )
                return None

            active_df = self.state.cleaned_data

        elif stage_normalized in {"engineered", "features"}:
            if self.state.engineered_data is None:
                print(
                    "\nNo engineered dataset available. "
                    "Run project.apply_features() first."
                )
                return None

            active_df = self.state.engineered_data

        else:
            active_df = self.state.data

        new_report = self.visualization_engine.visualize(
            df=active_df,
            chart=chart,
            x=x,
            y=y,
            column=column,
            stage=stage_normalized,
            cleaned_df=self.state.cleaned_data,
            diagnosis_report=self.state.diagnosis_report,
            cleaning_report=self.state.cleaning_report,
            validation_report=self.state.validation_report,
        )

        if title is not None and new_report.chart_count != 1:
            raise ValueError(
                "A custom title can only be applied when one chart is "
                "generated. Customize gallery charts by chart_id instead."
            )

        for generated_chart in new_report.charts:
            generated_chart.customize(
                title=title,
                subtitle=subtitle,
                x_label=x_label,
                y_label=y_label,
                theme=theme,
                color=color,
                palette=palette,
                figsize=figsize,
                dpi=dpi,
                grid=grid,
                legend=legend,
                legend_position=legend_position,
                template=template,
                transparent=transparent,
            )

        if not append:
            self.visualization_gallery.clear()

        added_charts = self.visualization_gallery.add_report(
            new_report,
            allow_duplicates=allow_duplicates,
            replace_existing=True,
        )

        self.state.visualization_report = (
            self.visualization_gallery.to_report()
        )

        if display and added_charts:
            display_report = self._build_visualization_subset(
                original_report=new_report,
                charts=added_charts,
            )

            self.notebook_visualization_renderer.render(
                display_report
            )

        saved_paths = []

        if save is not None and added_charts:
            if len(added_charts) == 1 and Path(save).suffix:
                saved_paths = [
                    added_charts[0].save(
                        save,
                        format=save_format,
                    )
                ]
            else:
                saved_paths = VisualizationReport(
                    charts=added_charts
                ).save(save, format=save_format or "png")

        self.state.visualization_report.auto_display = False
        new_report.auto_display = False

        self.session.log(
            step="visualize",
            message="Visualization generated and added to gallery.",
            metadata={
                "requested_chart": chart or "auto",
                "stage": stage_normalized,
                "new_charts": len(added_charts),
                "gallery_size": (
                    self.visualization_gallery.chart_count
                ),
                "displayed_in_notebook": display,
                "saved_paths": [str(path) for path in saved_paths],
            },
        )

        return new_report

    def dashboard(
        self,
        output: str | None = None,
        *,
        title: str = "AutoDQ Analytics Dashboard",
        subtitle: str | None = None,
        theme: str = "light",
        stage: str = "best",
        chart_ids: list[str] | tuple[str, ...] | None = None,
        max_charts: int | None = 12,
        max_preview_rows: int = 20,
        include_charts: bool = True,
        include_data_preview: bool = True,
        refresh: bool = False,
        overwrite: bool = False,
        auto_display: bool = True,
    ):
        """Build a notebook-ready dashboard and optionally export HTML.

        The dashboard reuses every available project artifact, including
        cleaning review, automation, model, prediction, and uncertainty
        results. Missing profile, diagnosis, and automatic visualizations are
        prepared on demand.
        """
        if chart_ids is not None and not include_charts:
            raise ValueError(
                "chart_ids cannot be used when include_charts is False."
            )

        self.dashboard_engine.validate_options(
            theme=theme,
            stage=stage,
            max_charts=max_charts if include_charts else 0,
            max_preview_rows=max_preview_rows,
        )

        output_path = Path(output).expanduser() if output is not None else None

        if output_path is not None and output_path.suffix.lower() != ".html":
            raise ValueError("Dashboard output must end with .html.")

        if self.state.data is None:
            self.load()

        if refresh or self.state.profile_report is None:
            self.profile()

        if refresh or self.state.diagnosis_report is None:
            self.diagnose()

        if include_charts and (
            refresh or self.state.visualization_report is None
        ):
            visualization_stage = str(stage).lower().strip()

            if visualization_stage == "best":
                if self.state.engineered_data is not None:
                    visualization_stage = "engineered"
                elif self.state.cleaned_data is not None:
                    visualization_stage = "cleaned"
                else:
                    visualization_stage = "current"

            self.visualize(
                chart="auto",
                stage=visualization_stage,
                append=not refresh,
                display=False,
            )

        dashboard = self.dashboard_engine.build(
            state=self.state,
            session=self.session,
            title=title,
            subtitle=subtitle,
            theme=theme,
            stage=stage,
            chart_ids=chart_ids,
            max_charts=max_charts if include_charts else 0,
            max_preview_rows=max_preview_rows,
            include_data_preview=include_data_preview,
            auto_display=auto_display,
        )

        if output_path is not None:
            if not output_path.is_absolute() and self.workspace is not None:
                output_path = self.workspace.reports_dir / output_path

            dashboard.save(output_path, overwrite=overwrite)

        self.state.dashboard_report = dashboard
        self.session.log(
            step="dashboard",
            message="Interactive analytics dashboard generated.",
            metadata={
                "stage": dashboard.stage,
                "metrics": dashboard.metric_count,
                "charts": dashboard.chart_count,
                "preview_rows": dashboard.preview_row_count,
                "theme": dashboard.theme,
                "output": (
                    str(dashboard.path)
                    if dashboard.path is not None
                    else None
                ),
            },
        )
        return dashboard

    def query(
        self,
        source: str,
        *,
        continue_on_error: bool = False,
        auto_display: bool = True,
        source_name: str = "notebook",
        base_path: str | Path | None = None,
    ):
        """Parse, validate, and execute an ADQL statement or script."""
        script = self.adql_parser.parse(source)
        self.adql_validator.validate(script)

        try:
            result = self.adql_executor.execute(
                self,
                script,
                continue_on_error=continue_on_error,
                auto_display=auto_display,
                source_name=source_name,
                base_path=base_path,
            )
        except ADQLExecutionError as error:
            if error.result is not None:
                self._record_adql_run(error.result)

            raise

        self._record_adql_run(result)
        return result

    def adql(self, source: str, **options):
        """Alias for :meth:`query` using ADQL syntax."""
        return self.query(source, **options)

    def run_adql(
        self,
        path: str | Path,
        *,
        continue_on_error: bool = False,
        auto_display: bool = True,
        cell: int | None = None,
        through_cell: int | None = None,
    ):
        """Execute a UTF-8 ``.adql`` script file."""
        return self.adql_file_runner.run_with_project(
            self,
            path,
            continue_on_error=continue_on_error,
            auto_display=auto_display,
            cell=cell,
            through_cell=through_cell,
            raise_on_error=True,
        )

    @property
    def adql_history(self) -> list:
        """Return a copy of the recent ADQL run history."""
        return list(self.state.adql_history)

    def _record_adql_run(self, result) -> None:
        self.state.adql_history.append(result)

        if len(self.state.adql_history) > self.adql_executor.MAX_HISTORY:
            del self.state.adql_history[
                : -self.adql_executor.MAX_HISTORY
            ]

        self.session.log(
            step="adql",
            message=(
                "ADQL script completed."
                if result.success
                else "ADQL script completed with failures."
            ),
            metadata={
                "source": result.source_name,
                "statements": result.statement_count,
                "completed": result.completed_count,
                "failed": result.failed_count,
                "duration_seconds": result.duration_seconds,
            },
        )

    def head(self, n: int = 5) -> pd.DataFrame:
        if self.state.data is None:
            self.load()

        return self.state.data.head(n)

    def tail(self, n: int = 5) -> pd.DataFrame:
        if self.state.data is None:
            self.load()

        return self.state.data.tail(n)

    def sample(self, n: int = 5, random_state: int | None = 42) -> pd.DataFrame:
        if self.state.data is None:
            self.load()

        return self.state.data.sample(n=n, random_state=random_state)

    def view(self, n: int = 10) -> pd.DataFrame:
        if self.state.data is None:
            self.load()

        return self.state.data.head(n)

    def info(self) -> None:
        if self.state.data is None:
            self.load()

        self.state.data.info()

    def export_cleaned(self, output: str) -> None:
        if self.state.cleaned_data is None:
            print("\nNo cleaned dataset available. Run project.clean() first.")
            return

        export_dataset(self.state.cleaned_data, output)

        self.session.log(
            step="export_cleaned",
            message="Cleaned dataset exported.",
            metadata={
                "output": output,
                "rows": len(self.state.cleaned_data),
                "columns": len(self.state.cleaned_data.columns),
            },
        )

        print(f"\nCleaned dataset exported to {output}")

    def export_current(self, output: str) -> None:
        if self.state.data is None:
            self.load()

        export_dataset(self.state.data, output)

        self.session.log(
            step="export_current",
            message="Current dataset exported.",
            metadata={
                "output": output,
                "rows": len(self.state.data),
                "columns": len(self.state.data.columns),
            },
        )

        print(f"\nCurrent dataset exported to {output}")
        
        
    def correlation(self, min_abs_correlation: float = 0.3):
        if self.state.data is None:
            self.load()

        self.state.correlation_report = self.correlation_engine.analyze(
            df=self.state.data,
            target=self.state.target,
            min_abs_correlation=min_abs_correlation,
        )

        self.session.log(
            step="correlation",
            message="Correlation intelligence generated.",
            metadata={
                "relationships": self.state.correlation_report.relationship_count,
                "target_relationships": self.state.correlation_report.target_relationship_count,
            },
        )

        return self.state.correlation_report

    def show_correlation(self) -> None:
        if self.state.correlation_report is None:
            self.correlation()

        ConsoleCorrelationRenderer.render(self.state.correlation_report)
        
        
    def ml_readiness(self):
        if self.state.data is None:
            self.load()

        if self.state.diagnosis_report is None:
            self.diagnose()

        if self.state.statistics_report is None:
            self.statistics()

        if self.state.interpretation_report is None:
            self.interpret()

        if self.state.correlation_report is None:
            self.correlation()

        self.state.ml_readiness_report = self.ml_readiness_engine.analyze(
            df=self.state.data,
            target=self.state.target,
            diagnosis_report=self.state.diagnosis_report,
            statistics_report=self.state.statistics_report,
            interpretation_report=self.state.interpretation_report,
            correlation_report=self.state.correlation_report,
        )

        self.session.log(
            step="ml_readiness",
            message="Machine learning readiness evaluated.",
            metadata={
                "score": self.state.ml_readiness_report.score,
                "target": self.state.ml_readiness_report.target,
                "recommended_task": self.state.ml_readiness_report.recommended_task,
                "issues": self.state.ml_readiness_report.issue_count,
            },
        )

        return self.state.ml_readiness_report

    def show_ml_readiness(self) -> None:
        if self.state.ml_readiness_report is None:
            self.ml_readiness()

        ConsoleMLReadinessRenderer.render(self.state.ml_readiness_report)
        
        
    def features(self):
        if self.state.data is None:
            self.load()

        if self.state.statistics_report is None:
            self.statistics()

        if self.state.interpretation_report is None:
            self.interpret()

        self.state.feature_report = self.feature_engine.recommend(
            df=self.state.data,
            target=self.state.target,
            statistics_report=self.state.statistics_report,
            interpretation_report=self.state.interpretation_report,
        )

        self.session.log(
            step="features",
            message="Feature engineering recommendations generated.",
            metadata={
                "recommendations": self.state.feature_report.recommendation_count,
            },
        )

        return self.state.feature_report

    def show_features(self) -> None:
        if self.state.feature_report is None:
            self.features()

        ConsoleFeatureRenderer.render(self.state.feature_report)
        
    def create_feature(
        self,
        name: str,
        method: str,
        column: str | None = None,
        columns: list[str] | None = None,
        expression: str | None = None,
        bins: list[float] | None = None,
        labels: list[str] | None = None,
        use_engineered: bool = True,
    ) -> pd.DataFrame:
        if self.state.data is None:
            self.load()

        if use_engineered and self.state.engineered_data is not None:
            active_df = self.state.engineered_data
        elif self.state.cleaned_data is not None:
            active_df = self.state.cleaned_data
        else:
            active_df = self.state.data

        self.state.engineered_data = self.feature_engine.create_manual_feature(
            df=active_df,
            name=name,
            method=method,
            column=column,
            columns=columns,
            expression=expression,
            bins=bins,
            labels=labels,
        )

        self.session.log(
            step="create_feature",
            message="Manual feature created.",
            metadata={
                "feature": name,
                "method": method,
                "column": column,
                "columns": columns,
                "rows": len(self.state.engineered_data),
                "columns_after": len(self.state.engineered_data.columns),
            },
        )

        print(f"\nManual feature created: {name}")

        return self.state.engineered_data
        
    def apply_features(self, features: list[str] | None = None) -> pd.DataFrame:
        if self.state.data is None:
            self.load()

        if self.state.feature_report is None:
            self.features()

        active_df = (
            self.state.cleaned_data
            if self.state.cleaned_data is not None
            else self.state.data
        )
        self.state.engineered_data = self.feature_engine.apply(
            df=active_df,
            feature_report=self.state.feature_report,
            selected_features=features,
        )

        added_columns = [
            column
            for column in self.state.engineered_data.columns
            if column not in active_df.columns
        ]

        self.session.log(
            step="apply_features",
            message="Feature engineering recommendations applied.",
            metadata={
                "features_added": len(added_columns),
                "added_columns": added_columns,
                "rows": len(self.state.engineered_data),
                "columns": len(self.state.engineered_data.columns),
            },
        )

        print(f"\nFeature engineering completed. Added {len(added_columns)} feature(s).")

        return self.state.engineered_data

    def export_engineered(self, output: str) -> None:
        if self.state.engineered_data is None:
            print("\nNo engineered dataset available. Run project.apply_features() first.")
            return

        export_dataset(self.state.engineered_data, output)

        self.session.log(
            step="export_engineered",
            message="Engineered dataset exported.",
            metadata={
                "output": output,
                "rows": len(self.state.engineered_data),
                "columns": len(self.state.engineered_data.columns),
            },
        )

        print(f"\nEngineered dataset exported to {output}")
        
        
    def model(
        self,
        algorithm: str | None = "auto",
        use_engineered: bool = True,
        test_size: float = 0.2,
        random_state: int = 42,
        exclude_features: list[str] | None = None,
        exclude_leakage: bool = False,
    ):
        if self.state.target is None:
            raise ValueError("Set a target first using project.set_target('column_name').")

        if use_engineered and self.state.engineered_data is not None:
            active_df = self.state.engineered_data
        elif self.state.cleaned_data is not None:
            active_df = self.state.cleaned_data
        else:
            if self.state.data is None:
                self.load()
            active_df = self.state.data
            
        final_exclusions = list(exclude_features or [])

        if exclude_leakage:
            leakage_candidates = self._detect_leakage_candidates(
                df=active_df,
                target=self.state.target,
            )

            final_exclusions.extend(leakage_candidates)
            final_exclusions = sorted(set(final_exclusions))

        self.state.model_report = self.ml_engine.train(
            df=active_df,
            target=self.state.target,
            algorithm=algorithm,
            test_size=test_size,
            random_state=random_state,
            exclude_features=final_exclusions,
        )
        self.state.model_bundle = None
        self.state.prediction_report = None
        self.state.prediction_data = None
        self.state.explainability_report = None

        self.session.log(
            step="model",
            message="Machine learning model trained.",
            metadata={
                "target": self.state.model_report.target,
                "problem_type": self.state.model_report.problem_type,
                "algorithm": self.state.model_report.algorithm,
                "features": self.state.model_report.feature_count,
                "excluded_features": final_exclusions,
            },
        )

        return self.state.model_report
    
    def _detect_leakage_candidates(
        self,
        df: pd.DataFrame,
        target: str,
        threshold: float = 0.95,
    ) -> list[str]:
        if target not in df.columns:
            return []

        numeric_df = df.select_dtypes(include="number")

        if target not in numeric_df.columns:
            return []

        correlations = numeric_df.corr(numeric_only=True)[target].dropna()

        leakage_candidates = []

        for column, value in correlations.items():
            if column == target:
                continue

            if abs(value) >= threshold:
                leakage_candidates.append(column)

        name_based_candidates = []

        target_lower = target.lower()

        leakage_keywords = [
            "gross",
            "net",
            "total",
            "amount",
            "profit",
            "cost",
            "margin",
        ]

        for column in df.columns:
            column_lower = column.lower()

            if column == target:
              continue

    # Any feature containing the target name is suspicious
            if target_lower in column_lower:
                name_based_candidates.append(column)

    # Business-derived columns are also suspicious
            if any(keyword in column_lower for keyword in leakage_keywords):
               if target_lower in ["revenue", "sales", "profit"]:
                   name_based_candidates.append(column)

        return sorted(set(leakage_candidates + name_based_candidates))

    def show_model(self) -> None:
        if self.state.model_report is None:
            self.model()

        ConsoleModelRenderer.render(self.state.model_report) 

    def save_model(
        self,
        output: str,
        overwrite: bool = False,
    ):
        """Save the trained model and its metadata as a model bundle."""
        if self.state.model_report is None:
            raise ValueError(
                "No trained model available. Run project.model() first."
            )

        bundle = self.model_persistence_engine.save(
            model_report=self.state.model_report,
            destination=output,
            overwrite=overwrite,
        )
        self.state.model_bundle = bundle

        self.session.log(
            step="save_model",
            message="Trained model bundle saved.",
            metadata={
                "output": str(bundle.path),
                "algorithm": bundle.manifest.algorithm,
                "format_version": bundle.manifest.format_version,
            },
        )

        return bundle

    def load_model(self, source: str):
        """Load a trusted AutoDQ model bundle into this project."""
        bundle = self.model_persistence_engine.load(source)
        report = bundle.model_report

        self.state.target = report.target
        self.state.model_report = report
        self.state.model_bundle = bundle
        self.state.prediction_report = None
        self.state.prediction_data = None
        self.state.explainability_report = None

        self.session.log(
            step="load_model",
            message="Trained model bundle loaded.",
            metadata={
                "source": str(bundle.path),
                "target": report.target,
                "algorithm": report.algorithm,
                "format_version": bundle.manifest.format_version,
            },
        )

        return report
        
        
    def predict(
        self,
        data=None,
        strict_schema: bool = False,
        uncertainty: bool = True,
        confidence_level: float = 0.9,
        low_confidence_threshold: float = 0.6,
    ):
        """Generate predictions with optional calibrated uncertainty.

        Regression models return conformal prediction intervals.
        Classification models return class probabilities, probability
        confidence, margin, entropy, and a low-confidence flag.
        """
        if self.state.model_report is None:
            self.model()

        if data is None:
            if self.state.engineered_data is not None:
                active_df = self.state.engineered_data
            elif self.state.cleaned_data is not None:
                active_df = self.state.cleaned_data
            else:
                if self.state.data is None:
                    self.load()
                active_df = self.state.data
        else:
            active_df = data

        prediction_data, prediction_report = self.prediction_engine.predict(
            model_report=self.state.model_report,
            data=active_df,
            target=self.state.target,
            strict_schema=strict_schema,
            uncertainty=uncertainty,
            confidence_level=confidence_level,
            low_confidence_threshold=low_confidence_threshold,
        )

        self.state.prediction_data = prediction_data
        self.state.prediction_report = prediction_report

        self.session.log(
            step="predict",
            message="Predictions generated.",
            metadata={
                "prediction_count": prediction_report.prediction_count,
                "algorithm": prediction_report.algorithm,
                "target": prediction_report.target,
                "uncertainty_available": (
                    prediction_report.uncertainty_available
                ),
                "uncertainty_method": (
                    prediction_report.uncertainty_method
                ),
                "confidence_level": (
                    prediction_report.confidence_level
                ),
            },
        )

        return prediction_data

    def show_predictions(self) -> None:
        if self.state.prediction_report is None:
            self.predict()

        ConsolePredictionRenderer.render(self.state.prediction_report)

    def export_predictions(self, output: str) -> None:
        if self.state.prediction_data is None:
            print("\nNo prediction data available. Run project.predict() first.")
            return

        export_dataset(self.state.prediction_data, output)

        self.session.log(
            step="export_predictions",
            message="Prediction dataset exported.",
            metadata={
                "output": output,
                "rows": len(self.state.prediction_data),
                "columns": len(self.state.prediction_data.columns),
            },
        )

        print(f"\nPredictions exported to {output}") 
        
    def explain(
        self,
        max_rows: int = 20,
        use_engineered: bool = True,
    ):
        if self.state.model_report is None:
            self.model()

        if self.state.prediction_report is None:
            self.predict()

        if use_engineered and self.state.engineered_data is not None:
            active_df = self.state.engineered_data

        elif self.state.cleaned_data is not None:
            active_df = self.state.cleaned_data

        else:
            if self.state.data is None:
                self.load()

            active_df = self.state.data

        self.state.explainability_report = (
            self.explainability_engine.explain(
                model_report=self.state.model_report,
                data=active_df,
                prediction_report=self.state.prediction_report,
                max_rows=max_rows,
            )
        )

        self.session.log(
            step="explain",
            message="Model explainability report generated.",
            metadata={
                "method": self.state.explainability_report.method,
                "explanations": (
                    self.state.explainability_report.explanation_count
                ),
                "global_features": (
                    self.state.explainability_report.global_feature_count
                ),
            },
        )

        return self.state.explainability_report

    def show_explanations(self) -> None:
        if self.state.explainability_report is None:
            self.explain()

        report = self.state.explainability_report

        print("\n=== AutoDQ Explainability Report ===\n")
        print(f"Algorithm: {report.algorithm}")
        print(f"Method: {report.method}")
        print(f"Explanations: {report.explanation_count}")

        if report.warnings:
            print("\nWarnings:")

            for warning in report.warnings:
                print(f"- {warning}")

        if report.global_features:
            print("\nGlobal SHAP Feature Contributions:")

            for item in report.global_features[:10]:
                percent = (
                    item.contribution_percent
                    if item.contribution_percent is not None
                    else 0
                )

                print(
                    f"  {item.rank}. {item.feature}: "
                    f"{percent}%"
                )

        if report.row_explanations:
            print("\nSample Row Explanations:")

            for row in report.row_explanations[:5]:
                print(
                    f"\nRow {row.row_id}"
                    f" | Prediction: {row.prediction}"
                    f" | Base Value: {row.base_value}"
                )

                for contribution in row.top_contributions:
                    sign = (
                        "+"
                        if contribution.direction == "positive"
                        else "-"
                    )

                    print(
                        f"  {sign} {contribution.feature}"
                        f" = {contribution.feature_value}"
                        f" | SHAP: {contribution.contribution}"
                        f" | Share: "
                        f"{contribution.contribution_percent}%"
                    )

                print(
                    f"  Explanation: {row.explanation}"
                )
                
                
    def visualize_shap(
        self,
        chart: str = "summary",
        row: int = 0,
        feature: str | None = None,
        save: str | None = None,
        display: bool = True,
    ):
        """
        Generate a SHAP visualization from the latest explainability report.

        Supported chart types:
        - summary
        - beeswarm
        - bar
        - waterfall
        - dependence

        Parameters
        ----------
        chart:
            Type of SHAP visualization to generate.

        row:
            Row position used for waterfall plots.

        feature:
            Feature name used for dependence plots.

        save:
            Optional file path for saving the visualization.

        display:
            Whether to display the visualization immediately.

        Returns
        -------
        Any
            The generated matplotlib figure or plot result.
        """
        if self.state.explainability_report is None:
            self.explain()

        report = self.state.explainability_report

        if report is None:
            raise RuntimeError(
                "Explainability report could not be generated."
            )

        visualizer = SHAPVisualizer(report)

        chart_normalized = chart.lower().strip()
        result = visualizer.plot(
            chart=chart_normalized,
            row=row,
            feature=feature,
            save=save,
            show=display,
        )

        self.session.log(
            step="visualize_shap",
            message="SHAP visualization generated.",
            metadata={
                "chart": chart_normalized,
                "row": (
                    row
                    if chart_normalized == "waterfall"
                    else None
                ),
                "feature": (
                    feature
                    if chart_normalized == "dependence"
                    else None
                ),
                "saved_to": save,
                "displayed_in_notebook": display,
            },
        )

        return result
                    

    def add_dataset(
        self,
        name: str,
        dataset_path: str | None = None,
        data: pd.DataFrame | None = None,
        overwrite: bool = False,
    ) -> pd.DataFrame:
        entry = self.dataset_manager.add(
            name=name,
            dataset_path=dataset_path,
            data=data,
            overwrite=overwrite,
        )

        self.session.log(
            step="add_dataset",
            message="Additional dataset registered.",
            metadata=entry.to_dict(),
        )

        return entry.data

    def list_datasets(self) -> None:
        ConsoleDatasetRenderer.render_datasets(
            self.dataset_manager.entries()
        )

    def use_dataset(
        self,
        name: str,
        reset_outputs: bool = True,
    ) -> pd.DataFrame:
        entry = self.dataset_manager.set_primary(name)

        self.state.dataset_path = (
            Path(entry.path)
            if entry.path is not None
            else Path(f"{entry.name}.in_memory")
        )

        if reset_outputs:
            self.state.reset_outputs()

        self.state.data = entry.data.copy()

        self.session.log(
            step="use_dataset",
            message="Active dataset changed.",
            metadata={
                "dataset": entry.name,
                "rows": entry.rows,
                "columns": entry.columns,
            },
        )

        return self.state.data

    def merge_datasets(
        self,
        left: str,
        right: str,
        output_name: str | None = None,
        how: str = "left",
        on: str | list[str] | None = None,
        left_on: str | list[str] | None = None,
        right_on: str | list[str] | None = None,
        validate: str | None = None,
        suffixes: tuple[str, str] = ("_left", "_right"),
        make_active: bool = True,
    ) -> pd.DataFrame:
        left_df = self.dataset_manager.get_data(left)
        right_df = self.dataset_manager.get_data(right)

        merged_df, merge_report = self.dataset_merger.merge(
            left_df=left_df,
            right_df=right_df,
            left_name=left,
            right_name=right,
            how=how,
            on=on,
            left_on=left_on,
            right_on=right_on,
            validate=validate,
            suffixes=suffixes,
        )

        final_name = output_name or f"{left}_{right}_merged"

        self.dataset_manager.add(
            name=final_name,
            data=merged_df,
            overwrite=True,
        )

        self.state.merge_report = merge_report

        if make_active:
            self.use_dataset(
                final_name,
                reset_outputs=True,
            )
            self.state.merge_report = merge_report

        self.session.log(
            step="merge_datasets",
            message="Datasets merged successfully.",
            metadata=merge_report.to_dict(),
        )

        return merged_df

    def concat_datasets(
        self,
        datasets: list[str],
        output_name: str = "concatenated",
        axis: int = 0,
        ignore_index: bool = True,
        join: str = "outer",
        make_active: bool = True,
    ) -> pd.DataFrame:
        frames = [
            self.dataset_manager.get_data(name)
            for name in datasets
        ]

        combined_df, concat_report = self.dataset_merger.concat(
            datasets=frames,
            dataset_names=datasets,
            axis=axis,
            ignore_index=ignore_index,
            join=join,
        )

        self.dataset_manager.add(
            name=output_name,
            data=combined_df,
            overwrite=True,
        )

        self.state.concat_report = concat_report

        if make_active:
            self.use_dataset(
                output_name,
                reset_outputs=True,
            )
            self.state.concat_report = concat_report

        self.session.log(
            step="concat_datasets",
            message="Datasets concatenated successfully.",
            metadata=concat_report.to_dict(),
        )

        return combined_df

    def show_merge_report(self) -> None:
        if self.state.merge_report is None:
            print("\nNo merge report available.")
            return

        ConsoleDatasetRenderer.render_merge(
            self.state.merge_report
        )

    def show_concat_report(self) -> None:
        if self.state.concat_report is None:
            print("\nNo concatenation report available.")
            return

        ConsoleDatasetRenderer.render_concat(
            self.state.concat_report
        )  
        
    def blue(
        self,
        source: str = "data",
        use_engineered: bool = True,
        exclude_leakage: bool = True,
        max_features: int = 20,
        significance_level: float = 0.05,
        leakage_threshold: float = 0.98,
        exclude_features: list[str] | None = None,
    ):
        source_normalized = source.lower().strip()

        if self.state.target is None:
            raise ValueError(
                "Set a target before running BLUE diagnostics."
            )

        if (
            use_engineered
            and self.state.engineered_data is not None
        ):
            active_df = self.state.engineered_data

        elif self.state.cleaned_data is not None:
            active_df = self.state.cleaned_data

        else:
            if self.state.data is None:
                self.load()

            active_df = self.state.data

        if source_normalized == "data":
            self.state.blue_report = self.blue_engine.analyze(
                df=active_df,
                target=self.state.target,
                max_features=max_features,
                significance_level=significance_level,
                exclude_leakage=exclude_leakage,
                leakage_threshold=leakage_threshold,
                exclude_features=exclude_features,
            )

        elif source_normalized == "trained_model":
            if self.state.model_report is None:
                raise ValueError(
                    "Train a linear model before using "
                    "source='trained_model'."
                )

            self.state.blue_report = (
                self.blue_engine.analyze_trained_model(
                    model_report=self.state.model_report,
                    df=active_df,
                    target=self.state.target,
                    significance_level=significance_level,
                )
            )

        else:
            raise ValueError(
                "source must be either 'data' or 'trained_model'."
            )

        self.session.log(
            step="blue",
            message="BLUE regression diagnostics completed.",
            metadata={
                "target": self.state.blue_report.target,
                "source": source_normalized,
                "score": self.state.blue_report.suitability_score,
                "status": self.state.blue_report.overall_status,
                "features_used": self.state.blue_report.features_used,
                "excluded_features": (
                    self.state.blue_report.excluded_features
                ),
                "rows": self.state.blue_report.rows_analyzed,
            },
        )

        return self.state.blue_report  

    def show_blue(self) -> None:
        if self.state.blue_report is None:
            self.blue()

        ConsoleBLUERenderer.render(
            self.state.blue_report
        )
        
    def _build_visualization_subset(
        self,
        original_report,
        charts: list,
    ):
        report_class = type(original_report)

        try:
            return report_class(charts=charts)

        except TypeError:
            subset = original_report

            if hasattr(subset, "charts"):
                subset.charts = charts

            return subset
        
        
    def list_visualizations(self) -> list:
        print("\n=== AutoDQ Visualization Gallery ===\n")

        charts = self.visualization_gallery.charts

        if not charts:
            print("No visualizations stored.")
            return []

        for index, chart in enumerate(
            charts,
            start=1,
        ):
            print(
                f"{index}. "
                f"{getattr(chart, 'title', 'Untitled Chart')}"
            )
            print(
                f"   ID: "
                f"{getattr(chart, 'chart_id', 'N/A')}"
            )
            print(
                f"   Type: "
                f"{getattr(chart, 'chart_type', 'N/A')}"
            )
            print(
                f"   Stage: "
                f"{getattr(chart, 'stage', 'N/A')}"
            )

        return charts

    def get_visualization(self, chart_id: str):
        """Return a reusable chart from the visualization gallery."""
        return self.visualization_gallery.get(chart_id)

    def filter_visualizations(
        self,
        *,
        chart_type: str | None = None,
        stage: str | None = None,
        recommended: bool | None = None,
    ) -> list:
        """Filter gallery charts without changing the gallery."""
        return self.visualization_gallery.filter(
            chart_type=chart_type,
            stage=stage,
            recommended=recommended,
        )

    def customize_visualization(
        self,
        chart_id: str,
        **options,
    ):
        """Customize a retained chart and return the reusable object."""
        chart = self.visualization_gallery.customize(
            chart_id,
            **options,
        )
        self.session.log(
            step="customize_visualization",
            message="Visualization styling updated.",
            metadata={
                "chart_id": chart_id,
                "options": sorted(options),
            },
        )
        return chart

    def save_visualizations(
        self,
        output_dir: str | None = None,
        *,
        format: str = "png",
    ) -> list[Path]:
        """Export the visualization gallery, using workspace storage."""
        if not self.visualization_gallery.charts:
            raise ValueError("Visualization gallery is empty.")

        if output_dir is None:
            if self.workspace is not None:
                destination = self.workspace.visualizations_dir
            else:
                destination = Path(".autodq/visualizations")
        else:
            destination = Path(output_dir)

        paths = self.visualization_gallery.save(
            destination,
            format=format,
        )
        self.session.log(
            step="save_visualizations",
            message="Visualization gallery exported.",
            metadata={
                "output_dir": str(destination),
                "format": format,
                "charts": len(paths),
            },
        )
        return paths

    def remove_visualization(
        self,
        chart_id: str,
    ):
        removed = self.visualization_gallery.remove(
            chart_id
        )

        if self.state.visualization_report is not None:
            self.state.visualization_report.charts = (
                self.visualization_gallery.charts
            )

        self.session.log(
            step="remove_visualization",
            message="Visualization removed from gallery.",
            metadata={
                "chart_id": chart_id,
                "gallery_size": (
                    self.visualization_gallery.chart_count
                ),
            },
        )

        return removed

    def clear_visualizations(self) -> None:
        self.visualization_gallery.clear()

        if self.state.visualization_report is not None:
            self.state.visualization_report.charts = []

        self.session.log(
            step="clear_visualizations",
            message="Visualization gallery cleared.",
            metadata={"gallery_size": 0},
        )

        print("\nVisualization gallery cleared.")

    def show_visualizations(self):
        if self.state.visualization_report is None:
            print("\nNo visualizations available.")
            return None

        if not self.visualization_gallery.charts:
            print("\nVisualization gallery is empty.")
            return None

        self.state.visualization_report.charts = (
            self.visualization_gallery.charts
        )
        self.state.visualization_report.auto_display = False

        if self.notebook_visualization_renderer.is_notebook():
            self.notebook_visualization_renderer.render(
                self.state.visualization_report
            )
        else:
            ConsoleVisualizationRenderer.render(
                self.state.visualization_report
            )

        return self.state.visualization_report
    def visualize_blue(
        self,
        display: bool = True,
        append: bool = True,
        allow_duplicates: bool = False,
    ):
        if self.state.blue_report is None:
            self.blue()

        if self.state.engineered_data is not None:
            active_df = self.state.engineered_data

        elif self.state.cleaned_data is not None:
            active_df = self.state.cleaned_data

        else:
            if self.state.data is None:
                self.load()

            active_df = self.state.data

        blue_visualization_report = self.blue_visualizer.build(
            df=active_df,
            target=self.state.target,
            blue_report=self.state.blue_report,
        )

        if not append:
            self.visualization_gallery.clear()

        added_charts = self.visualization_gallery.add_report(
            blue_visualization_report,
            allow_duplicates=allow_duplicates,
            replace_existing=True,
        )

        self.state.visualization_report = (
            self.visualization_gallery.to_report()
        )

        if display and added_charts:
            display_report = BLUEVisualizationReport(
                charts=added_charts,
            )

            self.notebook_visualization_renderer.render(
                display_report
            )

        self.state.visualization_report.auto_display = False
        blue_visualization_report.auto_display = False

        self.session.log(
            step="visualize_blue",
            message="BLUE diagnostic visualizations generated.",
            metadata={
                "new_charts": len(added_charts),
                "gallery_size": (
                    self.visualization_gallery.chart_count
                ),
                "displayed_in_notebook": display,
            },
        )

        return blue_visualization_report
    def interpret_blue_visuals(self):
        if self.state.blue_report is None:
            self.blue()

        self.state.blue_report.visual_insights = (
            self.blue_visual_interpreter.interpret(
                blue_report=self.state.blue_report,
            )
        )

        self.session.log(
            step="interpret_blue_visuals",
            message="BLUE visual diagnostics interpreted.",
            metadata={
                "insight_count": len(
                    self.state.blue_report.visual_insights
                ),
            },
        )

        return self.state.blue_report.visual_insights
    
    def show_blue_visual_insights(self) -> None:
        if self.state.blue_report is None:
            self.blue()

        if not self.state.blue_report.visual_insights:
            self.interpret_blue_visuals()

        print("\n=== AutoDQ BLUE Visual Insights ===\n")

        for insight in self.state.blue_report.visual_insights:
            print(f"{insight.title}")
            print(f"  Status: {insight.status}")
            print(f"  Interpretation: {insight.interpretation}")
            print(f"  Recommendation: {insight.recommendation}")
            print(
                f"  Confidence: "
                f"{round(insight.confidence * 100, 2)}%"
            )
            print()
            
                
    def prescribe_blue(self):
        if self.state.blue_report is None:
            self.blue()

        self.state.blue_report.prescriptions = (
            self.blue_prescription_engine.prescribe(
                self.state.blue_report
            )
        )

        self.session.log(
            step="prescribe_blue",
            message="BLUE diagnostic prescriptions generated.",
            metadata={
                "prescription_count": len(
                    self.state.blue_report.prescriptions
                ),
            },
        )

        return self.state.blue_report.prescriptions


    def show_blue_prescriptions(self) -> None:
        if self.state.blue_report is None:
            self.blue()

        if not self.state.blue_report.prescriptions:
            self.prescribe_blue()

        print("\n=== AutoDQ BLUE Prescriptions ===\n")

        for index, item in enumerate(
            self.state.blue_report.prescriptions,
            start=1,
        ):
            print(f"{index}. {item.action}")
            print(f"   Category: {item.category}")
            print(f"   Priority: {item.priority}")
            print(f"   Reason: {item.reason}")
            print(f"   Recommendation: {item.recommendation}")
            print(
                f"   Confidence: "
                f"{round(item.confidence * 100, 2)}%"
            )
            print()    
    

    def show_knowledge(self) -> None:
        if not self.state.knowledge_rules:
            self.apply_knowledge()

        print("\n=== AutoDQ Knowledge Layer ===")

        matched = False

        for column, rule in self.state.knowledge_rules.items():
            if rule is None:
                continue

            matched = True
            print(f"\n{column}")
            print(f"  Semantic Type: {rule.semantic_type}")
            print(f"  Preferred Imputation: {rule.preferred_imputation}")
            print(f"  Preferred Outlier Strategy: {rule.preferred_outlier_strategy}")

            if rule.expected_min is not None:
                print(f"  Expected Min: {rule.expected_min}")

            if rule.expected_max is not None:
                print(f"  Expected Max: {rule.expected_max}")

            if rule.allow_negative is not None:
                print(f"  Allow Negative: {rule.allow_negative}")

            if rule.notes:
                print(f"  Notes: {' '.join(rule.notes)}")

        if not matched:
            print("No knowledge rules matched this dataset yet.")

    def show_profile(self) -> None:
        if self.state.profile_report is None:
            self.profile()

        ConsoleProfileRenderer.render(self.state.profile_report)

    def show_statistics(self) -> None:
        if self.state.statistics_report is None:
            self.statistics()

        ConsoleStatisticsRenderer.render(self.state.statistics_report)

    def show_interpretations(self) -> None:
        if self.state.interpretation_report is None:
            self.interpret()

        ConsoleInterpretationRenderer.render(
            self.state.interpretation_report
        )

    def show_diagnosis(self) -> None:
        if self.state.diagnosis_report is None:
            self.diagnose()

        ConsoleDiagnosisRenderer.render(self.state.diagnosis_report)

    def show_recommendations(self) -> None:
        if self.state.recommendations is None:
            self.recommend()

        ConsoleRecommendationRenderer.render(self.state.recommendations)

    def show_preview(self) -> None:
        if self.state.preview_report is None:
            self.preview()

        ConsolePreviewRenderer.render(self.state.preview_report)

    def show_cleaning_report(self) -> None:
        if self.state.cleaning_report is None:
            print("\nNo cleaning report available. Run project.clean() first.")
            return

        ConsoleCleaningRenderer.render(self.state.cleaning_report)

    def show_validation(self) -> None:
        if self.state.validation_report is None:
            self.validate_cleaning()

        if self.state.validation_report is not None:
            ConsoleValidationRenderer.render(self.state.validation_report)

    def show_session(self) -> None:
        self.session.summary()
