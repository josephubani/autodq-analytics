from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from autodq.auto.models import (
    AutoRunConfig,
    AutoRunError,
    AutoRunResult,
    AutoStageResult,
)


class AutoEngine:
    """Run the public AutoDQ workflow as a traceable orchestration."""

    def run(
        self,
        project,
        config: AutoRunConfig,
    ) -> AutoRunResult:
        result = AutoRunResult(
            config=config,
            auto_display=config.auto_display,
        )
        project.state.auto_run_report = result

        if config.refresh:
            project.state.reset_outputs()
            project.state.auto_run_report = result

        stages = [
            (
                "load",
                project.load,
                project.state.data is not None,
                self._dataset_summary,
                "Dataset loaded.",
            ),
            (
                "knowledge",
                project.apply_knowledge,
                project.state.knowledge_rules is not None,
                self._knowledge_summary,
                "Knowledge rules matched.",
            ),
            (
                "profile",
                project.profile,
                project.state.profile_report is not None,
                self._profile_summary,
                "Dataset profile generated.",
            ),
            (
                "statistics",
                project.statistics,
                project.state.statistics_report is not None,
                self._statistics_summary,
                "Descriptive statistics generated.",
            ),
            (
                "interpret",
                project.interpret,
                project.state.interpretation_report is not None,
                self._interpretation_summary,
                "Statistical interpretations generated.",
            ),
            (
                "diagnose",
                project.diagnose,
                project.state.diagnosis_report is not None,
                self._diagnosis_summary,
                "Data quality diagnosis completed.",
            ),
            (
                "recommend",
                project.recommend,
                project.state.recommendations is not None,
                lambda output: {"recommendations": len(output)},
                "Cleaning recommendations generated.",
            ),
            (
                "decide",
                project.decide,
                project.state.decision_plan is not None,
                lambda output: {"actions": output.action_count},
                "Decision plan generated.",
            ),
            (
                "preview",
                project.preview,
                project.state.preview_report is not None,
                lambda output: {"actions": output.action_count},
                "Safe cleaning previews generated.",
            ),
        ]

        for name, function, reuse, summary, message in stages:
            if not self._stage(
                project,
                result,
                name=name,
                function=function,
                reuse=reuse and not config.refresh,
                summary=summary,
                message=message,
            ):
                return self._finish(project, result)

        if not self._stage(
            project,
            result,
            name="review",
            function=lambda: project.review_cleaning(
                refresh=config.refresh,
                auto_display=False,
            ),
            reuse=(
                project.state.cleaning_review is not None
                and not config.refresh
            ),
            summary=self._review_summary,
            message="Interactive cleaning review prepared.",
        ):
            return self._finish(project, result)

        result.review = project.state.cleaning_review

        if result.review is not None and result.review.domain_rules:
            if not self._stage(
                project,
                result,
                name="domain_validation",
                function=project.validate_domain,
                summary=self._domain_summary,
                message="Domain rules validated.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "domain_validation",
                "No domain rules matched the dataset.",
            )

        analysis_stages = [
            (
                "correlation",
                project.correlation,
                project.state.correlation_report is not None,
                self._correlation_summary,
                "Correlation analysis completed.",
            ),
            (
                "ml_readiness",
                project.ml_readiness,
                project.state.ml_readiness_report is not None,
                self._ml_readiness_summary,
                "Machine-learning readiness evaluated.",
            ),
            (
                "features",
                project.features,
                project.state.feature_report is not None,
                lambda output: {
                    "recommendations": output.recommendation_count
                },
                "Feature recommendations generated.",
            ),
        ]

        for name, function, reuse, summary, message in analysis_stages:
            if not self._stage(
                project,
                result,
                name=name,
                function=function,
                reuse=reuse and not config.refresh,
                summary=summary,
                message=message,
            ):
                return self._finish(project, result)

        if config.approve_all:
            if not self._stage(
                project,
                result,
                name="approve_all",
                function=project.approve_all,
                summary=self._review_summary,
                message="All cleaning actions approved.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "approve_all",
                "Automatic approval is disabled.",
            )

        if config.apply_cleaning:
            if not self._stage(
                project,
                result,
                name="clean",
                function=project.apply_cleaning_review,
                summary=self._dataset_summary,
                message="Reviewed cleaning changes applied.",
            ):
                return self._finish(project, result)

            if not self._stage(
                project,
                result,
                name="validate_cleaning",
                function=project.validate_cleaning,
                summary=self._validation_summary,
                message="Post-cleaning validation completed.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "clean",
                "Cleaning is review-only in this run.",
            )
            self._skip(
                result,
                "validate_cleaning",
                "Cleaning was not applied.",
            )

        if config.apply_features:
            if not self._stage(
                project,
                result,
                name="apply_features",
                function=project.apply_features,
                summary=self._dataset_summary,
                message="Recommended executable features applied.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "apply_features",
                "Automatic feature creation is disabled.",
            )

        if config.visualize:
            stage = (
                "cleaned"
                if project.state.cleaned_data is not None
                else "current"
            )

            if not self._stage(
                project,
                result,
                name="visualize",
                function=lambda: project.visualize(
                    chart="auto",
                    stage=stage,
                    append=False,
                    display=False,
                ),
                summary=lambda output: {"charts": output.chart_count},
                message="Automatic visualizations generated.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "visualize",
                "Automatic visualization is disabled.",
            )

        if config.train_model and project.state.target is not None:
            if not self._stage(
                project,
                result,
                name="model",
                function=lambda: project.model(
                    algorithm=config.algorithm,
                    use_engineered=config.apply_features,
                    test_size=config.test_size,
                    random_state=config.random_state,
                ),
                summary=self._model_summary,
                message="Machine-learning model trained.",
            ):
                return self._finish(project, result)
        elif config.train_model:
            self._skip(
                result,
                "model",
                "No target is set, so model training was skipped.",
            )
        else:
            self._skip(
                result,
                "model",
                "Automatic model training is disabled.",
            )

        if config.generate_predictions:
            if project.state.model_report is None:
                self._skip(
                    result,
                    "predict",
                    "No trained model is available.",
                )
            elif not self._stage(
                project,
                result,
                name="predict",
                function=project.predict,
                summary=lambda output: {"predictions": len(output)},
                message="Predictions generated.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "predict",
                "Automatic prediction is disabled.",
            )

        if config.explain_model:
            if project.state.model_report is None:
                self._skip(
                    result,
                    "explain",
                    "No trained model is available.",
                )
            elif not self._stage(
                project,
                result,
                name="explain",
                function=project.explain,
                summary=self._explanation_summary,
                message="Model explanations generated.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "explain",
                "Automatic model explanation is disabled.",
            )

        result.next_actions = self._next_actions(project, result)

        if config.report_output is not None:
            if not self._stage(
                project,
                result,
                name="report",
                function=lambda: project.generate_report(
                    config.report_output,
                    style=config.report_style,
                ),
                summary=lambda _: {"output": config.report_output},
                message="Project report exported.",
            ):
                return self._finish(project, result)

            result.report_path = Path(config.report_output).resolve()
        else:
            self._skip(
                result,
                "report",
                "No report output path was requested.",
            )

        if config.save_workspace:
            if project.workspace is None:
                self._skip(
                    result,
                    "save_workspace",
                    "The project is not attached to a workspace.",
                )
            elif not self._stage(
                project,
                result,
                name="save_workspace",
                function=project.save_workspace,
                summary=lambda output: {
                    "workspace": output["workspace_id"]
                },
                message="Workspace saved.",
            ):
                return self._finish(project, result)
        else:
            self._skip(
                result,
                "save_workspace",
                "Automatic workspace saving is disabled.",
            )

        return self._finish(project, result)

    def _stage(
        self,
        project,
        result: AutoRunResult,
        *,
        name: str,
        function: Callable[[], Any],
        summary: Callable[[Any], dict[str, Any]],
        message: str,
        reuse: bool = False,
    ) -> bool:
        if reuse:
            result.stages.append(
                AutoStageResult(
                    name=name,
                    status="reused",
                    message="Existing project output reused.",
                )
            )
            return True

        started = perf_counter()

        try:
            output = function()
            stage_summary = summary(output)
        except Exception as error:
            duration = round(perf_counter() - started, 4)
            result.stages.append(
                AutoStageResult(
                    name=name,
                    status="failed",
                    message=f"{type(error).__name__}: {error}",
                    duration_seconds=duration,
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
            )

            if result.config.raise_on_error:
                self._finish(project, result)
                raise AutoRunError(name, str(error), result) from error

            return result.config.continue_on_error

        duration = round(perf_counter() - started, 4)
        result.stages.append(
            AutoStageResult(
                name=name,
                status="completed",
                message=message,
                duration_seconds=duration,
                summary=stage_summary,
            )
        )
        return True

    @staticmethod
    def _skip(result: AutoRunResult, name: str, message: str) -> None:
        result.stages.append(
            AutoStageResult(
                name=name,
                status="skipped",
                message=message,
            )
        )

    def _finish(self, project, result: AutoRunResult) -> AutoRunResult:
        if result.finished_at is None:
            result.finished_at = datetime.now()
            result.review = project.state.cleaning_review
            result.next_actions = self._next_actions(project, result)
            project.state.auto_run_report = result
            project.session.log(
                step="auto",
                message=(
                    "Automatic workflow completed."
                    if result.success
                    else "Automatic workflow needs attention."
                ),
                metadata={
                    "mode": result.config.mode,
                    "completed": result.completed_count,
                    "reused": result.reused_count,
                    "skipped": result.skipped_count,
                    "failed": result.failed_count,
                    "duration_seconds": result.duration_seconds,
                },
            )

        return result

    @staticmethod
    def _next_actions(project, result: AutoRunResult) -> list[str]:
        actions = []
        review = project.state.cleaning_review

        if result.failed_count:
            failed = [
                item.name
                for item in result.stages
                if item.status == "failed"
            ]
            actions.append(
                "Review failed automatic stages: " + ", ".join(failed) + "."
            )

        if review is not None and review.pending_count:
            actions.append(
                f"Review {review.pending_count} pending cleaning action(s) "
                "with result.review."
            )

        domain_report = project.state.domain_validation_report

        if domain_report is not None and domain_report.violation_count:
            actions.append(
                f"Resolve {domain_report.violation_count} domain "
                "violation(s) before finalizing the dataset."
            )

        if project.state.target is None:
            actions.append(
                "Set a target column to enable automatic modeling."
            )
        elif not result.config.train_model:
            actions.append(
                "Run project.auto(train_model=True) when modeling is ready."
            )

        return actions

    @staticmethod
    def _dataset_summary(output) -> dict[str, Any]:
        return {"rows": len(output), "columns": len(output.columns)}

    @staticmethod
    def _knowledge_summary(output) -> dict[str, Any]:
        return {
            "matched_rules": sum(
                1 for item in output.values() if item is not None
            )
        }

    @staticmethod
    def _profile_summary(output) -> dict[str, Any]:
        return {
            "rows": output.get("rows", output.get("row_count", 0)),
            "columns": output.get(
                "columns",
                output.get("column_count", 0),
            ),
        }

    @staticmethod
    def _statistics_summary(output) -> dict[str, Any]:
        return {"columns": len(output.descriptive)}

    @staticmethod
    def _interpretation_summary(output) -> dict[str, Any]:
        return {"insights": output.insight_count}

    @staticmethod
    def _diagnosis_summary(output) -> dict[str, Any]:
        return {
            "issues": output.issue_count,
            "quality_score": output.quality_score,
        }

    @staticmethod
    def _review_summary(output) -> dict[str, Any]:
        return {
            "actions": output.action_count,
            "pending": output.pending_count,
            "approved": output.approved_count,
            "rejected": output.rejected_count,
        }

    @staticmethod
    def _domain_summary(output) -> dict[str, Any]:
        return {
            "rules": output.rule_count,
            "violations": output.violation_count,
            "invalid_rows": output.invalid_row_count,
        }

    @staticmethod
    def _correlation_summary(output) -> dict[str, Any]:
        return {
            "relationships": output.relationship_count,
            "target_relationships": output.target_relationship_count,
        }

    @staticmethod
    def _ml_readiness_summary(output) -> dict[str, Any]:
        return {
            "score": output.score,
            "issues": output.issue_count,
            "task": output.recommended_task,
        }

    @staticmethod
    def _validation_summary(output) -> dict[str, Any]:
        return {
            "quality_before": output.quality_score_before,
            "quality_after": output.quality_score_after,
            "quality_change": output.quality_score_change,
        }

    @staticmethod
    def _model_summary(output) -> dict[str, Any]:
        return {
            "algorithm": output.algorithm,
            "problem_type": output.problem_type,
            "features": output.feature_count,
        }

    @staticmethod
    def _explanation_summary(output) -> dict[str, Any]:
        return {
            "method": output.method,
            "explanations": output.explanation_count,
            "global_features": output.global_feature_count,
        }
