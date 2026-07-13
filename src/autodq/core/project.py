from pathlib import Path

import pandas as pd

from autodq.cleaning.engine import CleaningEngine
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
        self.correlation_engine = CorrelationEngine()
        self.ml_readiness_engine = MLReadinessEngine()
        self.feature_engine = FeatureEngineeringEngine()
        self.ml_engine = MLEngine()
        self.prediction_engine = PredictionEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.dataset_manager = DatasetManager()
        self.dataset_merger = DatasetMerger()
        self.blue_engine = BLUEEngine()

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

    def load(self) -> pd.DataFrame:
        if self.dataset_manager.exists("main"):
            self.state.data = (
            self.dataset_manager.get_data("main").copy()
        )
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

    def change_dataset(self, dataset_path: str) -> pd.DataFrame:
        self.state.reset_all(dataset_path)

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

    def approve_all(self) -> None:
        if self.state.decision_plan is None:
            self.decide()

        for action in self.state.decision_plan.actions:
            action.status = "approved"

        self.session.log(
            step="approve",
            message="All decision actions approved.",
            metadata={"approved_actions": self.state.decision_plan.action_count},
        )

    def clean(self):
        if self.state.data is None:
            self.load()

        if self.state.decision_plan is None:
            self.decide()

        cleaned_data, cleaning_report = self.cleaning_engine.clean(
            df=self.state.data,
            decision_plan=self.state.decision_plan,
        )

        self.state.cleaned_data = cleaned_data
        self.state.cleaning_report = cleaning_report

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
    ):
        if self.state.data is None:
            self.load()

        if stage == "after":
            if self.state.cleaned_data is None:
                print("\nNo cleaned dataset available. Run project.clean() first.")
                return None

            active_df = self.state.cleaned_data

        else:
            active_df = self.state.data

        self.state.visualization_report = self.visualization_engine.visualize(
            df=active_df,
            chart=chart,
            x=x,
            y=y,
            column=column,
            stage=stage,
            cleaned_df=self.state.cleaned_data,
            diagnosis_report=self.state.diagnosis_report,
            cleaning_report=self.state.cleaning_report,
            validation_report=self.state.validation_report,
        )

        self.session.log(
            step="visualize",
            message="Visualization specifications generated.",
            metadata={
                "chart_count": self.state.visualization_report.chart_count,
                "chart": chart or "auto",
                "stage": stage,
            },
        )

        return self.state.visualization_report

    def show_visualizations(self) -> None:
        if self.state.visualization_report is None:
            self.visualize()

        if self.state.visualization_report is not None:
            ConsoleVisualizationRenderer.render(self.state.visualization_report)
            
            
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

        self.state.engineered_data = self.feature_engine.apply(
            df=self.state.data,
            feature_report=self.state.feature_report,
            selected_features=features,
        )

        added_columns = [
            column
            for column in self.state.engineered_data.columns
            if column not in self.state.data.columns
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
        
        
    def predict(self, data=None):
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
        use_engineered: bool = True,
        max_features: int = 20,
        significance_level: float = 0.05,
    ):
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

        self.state.blue_report = self.blue_engine.analyze(
            df=active_df,
            target=self.state.target,
            max_features=max_features,
            significance_level=significance_level,
        )

        self.session.log(
            step="blue",
            message="BLUE regression diagnostics completed.",
            metadata={
                "target": self.state.blue_report.target,
                "score": self.state.blue_report.suitability_score,
                "status": self.state.blue_report.overall_status,
                "features": self.state.blue_report.features_analyzed,
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