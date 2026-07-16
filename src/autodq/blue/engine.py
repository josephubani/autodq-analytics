from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from autodq.blue.models import (
    BLUEAssumptionResult,
    BLUEReport,
    VIFResult,
)


class BLUEEngine:
    """
    Evaluates assumptions associated with linear regression and BLUE.

    Current diagnostics:
    - linearity
    - residual normality
    - homoscedasticity
    - independence of errors
    - multicollinearity
    - influential observations
    """

    def analyze(
        self,
        df: pd.DataFrame,
        target: str,
        max_features: int = 20,
        significance_level: float = 0.05,
        exclude_leakage: bool = True,
        leakage_threshold: float = 0.98,
        exclude_features: list[str] | None = None,
    ) -> BLUEReport:
        if target is None:
            raise ValueError(
                "A target column must be set before BLUE analysis."
            )

        if target not in df.columns:
            raise ValueError(
                f"Target column not found: {target}"
            )

        working_df = df.copy()

        numeric_df = working_df.select_dtypes(
            include="number"
        ).copy()

        if target not in numeric_df.columns:
            raise ValueError(
                "BLUE analysis currently requires a numeric target."
            )

        candidate_features = [
            column
            for column in numeric_df.columns
            if column != target
        ]

        excluded_features: list[str] = []

        identifier_features = [
            column
            for column in candidate_features
            if self._is_identifier_column(column)
        ]

        excluded_features.extend(identifier_features)

        feature_columns = [
            column
            for column in candidate_features
            if column not in identifier_features
        ]

        manual_exclusions = [
            column
            for column in (exclude_features or [])
            if column in feature_columns
        ]

        excluded_features.extend(manual_exclusions)

        feature_columns = [
            column
            for column in feature_columns
            if column not in manual_exclusions
        ]

        if exclude_leakage:
            leakage_candidates = self._detect_leakage_candidates(
                df=numeric_df,
                target=target,
                feature_columns=feature_columns,
                threshold=leakage_threshold,
            )

            excluded_features.extend(leakage_candidates)

            feature_columns = [
                column
                for column in feature_columns
                if column not in leakage_candidates
            ]

        feature_columns = self._remove_duplicate_predictors(
            df=numeric_df,
            feature_columns=feature_columns,
            excluded_features=excluded_features,
        )

        if not feature_columns:
            raise ValueError(
                "No suitable numeric predictor columns remained after "
                "identifier and leakage filtering."
            )

        feature_columns = self._rank_predictors(
            df=numeric_df,
            target=target,
            feature_columns=feature_columns,
        )[:max_features]

        excluded_features = list(dict.fromkeys(excluded_features))

        model_df = numeric_df[
            feature_columns + [target]
        ].replace(
            [np.inf, -np.inf],
            np.nan,
        ).dropna()

        if len(model_df) < 30:
            raise ValueError(
                "BLUE analysis requires at least 30 complete rows."
            )

        X = model_df[feature_columns].astype(float)
        y = model_df[target].astype(float)

        X_constant = sm.add_constant(
            X,
            has_constant="add",
        )

        fitted_model = sm.OLS(
            y,
            X_constant,
        ).fit()

        residuals = fitted_model.resid
        fitted_values = fitted_model.fittedvalues

        assumption_results = [
            self._test_linearity(
                residuals=residuals,
                fitted_values=fitted_values,
            ),
            self._test_normality(
                residuals=residuals,
                significance_level=significance_level,
            ),
            self._test_homoscedasticity(
                residuals=residuals,
                design_matrix=X_constant,
                significance_level=significance_level,
            ),
            self._test_independence(
                residuals=residuals,
            ),
            self._test_influential_observations(
                fitted_model=fitted_model,
            ),
        ]

        vif_results = self._calculate_vif(X)

        multicollinearity_result = (
            self._build_multicollinearity_result(
                vif_results
            )
        )

        assumption_results.append(
            multicollinearity_result
        )

        suitability_score = self._calculate_score(
            assumption_results
        )

        overall_status = self._overall_status(
            suitability_score=suitability_score,
            assumptions=assumption_results,
        )

        recommendations = self._build_recommendations(
            assumption_results=assumption_results,
            vif_results=vif_results,
        )

        warnings = []

        if fitted_model.rsquared >= 0.98:
            warnings.append(
                "The fitted linear model has an unusually high R². "
                "Review predictors for target leakage."
            )

        if excluded_features:
            warnings.append(
                f"{len(excluded_features)} feature(s) were excluded from "
                "BLUE analysis because they appeared to be identifiers, "
                "duplicates, manually excluded fields, or leakage candidates."
            )

        return BLUEReport(
            target=target,
            rows_analyzed=len(model_df),
            features_analyzed=len(feature_columns),
            overall_status=overall_status,
            suitability_score=suitability_score,
            features_used=feature_columns,
            excluded_features=excluded_features,
            assumptions=assumption_results,
            vif_results=vif_results,
            recommendations=recommendations,
            warnings=warnings,
        )

        
    def analyze_trained_model(
        self,
        model_report,
        df: pd.DataFrame,
        target: str,
        significance_level: float = 0.05,
    ) -> BLUEReport:
        if model_report is None:
            raise ValueError(
                "No trained model report is available."
            )

        algorithm = str(
            getattr(model_report, "algorithm", "")
        ).lower()

        supported_linear_models = {
            "linear_regression",
            "ridge_regression",
            "lasso_regression",
            "elastic_net_regression",
        }

        if algorithm not in supported_linear_models:
            raise ValueError(
                "BLUE diagnostics only apply to trained linear regression "
                f"models. Current model: {algorithm or 'unknown'}"
            )

        pipeline = getattr(
            model_report,
            "model_object",
            None,
        )

        if pipeline is None:
            raise ValueError(
                "The fitted model pipeline is unavailable."
            )

        if target not in df.columns:
            raise ValueError(
                f"Target column not found: {target}"
            )

        feature_columns = list(
            getattr(
                model_report,
                "feature_columns",
                [],
            )
        )

        if not feature_columns:
            feature_columns = [
                column
                for column in df.columns
                if column != target
            ]

        missing_features = [
            column
            for column in feature_columns
            if column not in df.columns
        ]

        if missing_features:
            raise ValueError(
                "The active dataset is missing trained model features: "
                f"{missing_features}"
            )

        model_df = (
            df[feature_columns + [target]]
            .replace([np.inf, -np.inf], np.nan)
            .dropna(subset=[target])
            .copy()
        )

        if len(model_df) < 30:
            raise ValueError(
                "At least 30 rows are required for trained-model "
                "BLUE diagnostics."
            )

        X = model_df[feature_columns]
        y = pd.to_numeric(
            model_df[target],
            errors="coerce",
        )

        valid_rows = y.notna()

        X = X.loc[valid_rows]
        y = y.loc[valid_rows]

        predictions = np.asarray(
            pipeline.predict(X),
            dtype=float,
        )

        actual_values = np.asarray(
            y,
            dtype=float,
        )

        residuals = actual_values - predictions

        transformed_X, transformed_feature_names = (
            self._extract_transformed_features(
                pipeline=pipeline,
                X=X,
            )
        )

        if transformed_X.shape[1] == 0:
            raise ValueError(
                "No transformed model features were available."
            )

        diagnostic_design = sm.add_constant(
            transformed_X,
            has_constant="add",
        )

        diagnostic_model = sm.OLS(
            actual_values,
            diagnostic_design,
        ).fit()

        fitted_values = predictions

        assumption_results = [
            self._test_linearity(
                residuals=pd.Series(residuals),
                fitted_values=pd.Series(fitted_values),
            ),
            self._test_normality(
                residuals=pd.Series(residuals),
                significance_level=significance_level,
            ),
            self._test_homoscedasticity(
                residuals=pd.Series(residuals),
                design_matrix=pd.DataFrame(
                    diagnostic_design
                ),
                significance_level=significance_level,
            ),
            self._test_independence(
                residuals=pd.Series(residuals),
            ),
            self._test_influential_observations(
                fitted_model=diagnostic_model,
            ),
        ]

        vif_frame = pd.DataFrame(
            transformed_X,
            columns=transformed_feature_names,
        )

        vif_frame = self._remove_constant_transformed_columns(
            vif_frame
        )

        vif_results = self._calculate_vif(
            vif_frame
        )

        assumption_results.append(
            self._build_multicollinearity_result(
                vif_results
            )
        )

        suitability_score = self._calculate_score(
            assumption_results
        )

        overall_status = self._overall_status(
            suitability_score=suitability_score,
            assumptions=assumption_results,
        )

        recommendations = self._build_recommendations(
            assumption_results=assumption_results,
            vif_results=vif_results,
        )

        warnings = [
            "BLUE diagnostics were calculated from the exact trained "
            f"{algorithm.replace('_', ' ')} model."
        ]

        if diagnostic_model.rsquared >= 0.98:
            warnings.append(
                "The trained linear model has an unusually high R². "
                "Review the retained predictors for possible target leakage."
            )

        return BLUEReport(
            target=target,
            rows_analyzed=len(X),
            features_analyzed=vif_frame.shape[1],
            overall_status=overall_status,
            suitability_score=suitability_score,
            features_used=feature_columns,
            excluded_features=[],
            assumptions=assumption_results,
            vif_results=vif_results,
            recommendations=recommendations,
            warnings=warnings,
        )

    def _extract_transformed_features(
        self,
        pipeline,
        X: pd.DataFrame,
    ) -> tuple[np.ndarray, list[str]]:
        if hasattr(pipeline, "steps") and len(pipeline.steps) > 1:
            transformer = pipeline[:-1]
            transformed = transformer.transform(X)

            if hasattr(transformed, "toarray"):
                transformed = transformed.toarray()

            transformed_array = np.asarray(
                transformed,
                dtype=float,
            )

            feature_names = []

            if hasattr(
                transformer,
                "get_feature_names_out",
            ):
                try:
                    feature_names = list(
                        transformer.get_feature_names_out()
                    )
                except Exception:
                    feature_names = []

        else:
            transformed_array = np.asarray(
                X,
                dtype=float,
            )
            feature_names = list(X.columns)

        if not feature_names:
            feature_names = [
                f"feature_{index}"
                for index in range(
                    transformed_array.shape[1]
                )
            ]

        feature_names = [
            self._clean_transformed_feature_name(
                feature
            )
            for feature in feature_names
        ]

        return transformed_array, feature_names


    def _clean_transformed_feature_name(
        self,
        feature: str,
    ) -> str:
        feature = str(feature)

        prefixes = (
            "numeric__",
            "categorical__",
            "num__",
            "cat__",
            "remainder__",
        )

        for prefix in prefixes:
            if feature.startswith(prefix):
                return feature[len(prefix):]

        return feature


    def _remove_constant_transformed_columns(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        retained = [
            column
            for column in frame.columns
            if frame[column].nunique(dropna=True) > 1
        ]

        return frame[retained].copy()
    def _test_linearity(
        self,
        residuals: pd.Series,
        fitted_values: pd.Series,
    ) -> BLUEAssumptionResult:
        correlation = stats.pearsonr(
            fitted_values,
            residuals,
        )

        absolute_correlation = abs(
            float(correlation.statistic)
        )

        if absolute_correlation < 0.1:
            status = "passed"
            severity = "low"
            interpretation = (
                "Residuals show little linear association with fitted "
                "values, supporting the linearity assumption."
            )
            recommendation = (
                "No major linearity correction is currently required."
            )

        elif absolute_correlation < 0.3:
            status = "warning"
            severity = "medium"
            interpretation = (
                "Residuals show some association with fitted values. "
                "Possible nonlinear structure may remain."
            )
            recommendation = (
                "Review residual plots and consider polynomial terms, "
                "interactions, or transformations."
            )

        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "Residuals are strongly associated with fitted values, "
                "suggesting the relationship may not be adequately linear."
            )
            recommendation = (
                "Consider nonlinear models, transformations, splines, "
                "or interaction features."
            )

        return BLUEAssumptionResult(
            assumption="linearity",
            status=status,
            statistic=round(
                float(correlation.statistic),
                6,
            ),
            p_value=round(
                float(correlation.pvalue),
                6,
            ),
            threshold=0.1,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.85,
        )

    def _test_normality(
        self,
        residuals: pd.Series,
        significance_level: float,
    ) -> BLUEAssumptionResult:
        sample = residuals

        if len(sample) > 5000:
            sample = sample.sample(
                5000,
                random_state=42,
            )

        statistic, p_value = stats.jarque_bera(
            sample
        )

        if p_value >= significance_level:
            status = "passed"
            severity = "low"
            interpretation = (
                "Residual normality was not rejected."
            )
            recommendation = (
                "Residual distribution appears acceptable for standard "
                "linear inference."
            )
        else:
            status = "failed"
            severity = "medium"
            interpretation = (
                "Residuals significantly deviate from normality."
            )
            recommendation = (
                "Review outliers, transform skewed variables, or use "
                "robust standard errors."
            )

        return BLUEAssumptionResult(
            assumption="residual_normality",
            status=status,
            statistic=round(float(statistic), 6),
            p_value=round(float(p_value), 6),
            threshold=significance_level,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.9,
        )

    def _test_homoscedasticity(
        self,
        residuals: pd.Series,
        design_matrix: pd.DataFrame,
        significance_level: float,
    ) -> BLUEAssumptionResult:
        lm_statistic, lm_p_value, _, _ = (
            het_breuschpagan(
                residuals,
                design_matrix,
            )
        )

        if lm_p_value >= significance_level:
            status = "passed"
            severity = "low"
            interpretation = (
                "The Breusch-Pagan test did not detect significant "
                "heteroscedasticity."
            )
            recommendation = (
                "Standard linear regression variance assumptions appear "
                "reasonable."
            )
        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "The Breusch-Pagan test detected non-constant residual "
                "variance."
            )
            recommendation = (
                "Use heteroscedasticity-robust standard errors, transform "
                "the target, or consider weighted least squares."
            )

        return BLUEAssumptionResult(
            assumption="homoscedasticity",
            status=status,
            statistic=round(
                float(lm_statistic),
                6,
            ),
            p_value=round(
                float(lm_p_value),
                6,
            ),
            threshold=significance_level,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.95,
        )

    def _test_independence(
        self,
        residuals: pd.Series,
    ) -> BLUEAssumptionResult:
        statistic = float(
            durbin_watson(residuals)
        )

        if 1.5 <= statistic <= 2.5:
            status = "passed"
            severity = "low"
            interpretation = (
                "The Durbin-Watson statistic suggests limited residual "
                "autocorrelation."
            )
            recommendation = (
                "No major autocorrelation correction is currently required."
            )

        elif 1.0 <= statistic <= 3.0:
            status = "warning"
            severity = "medium"
            interpretation = (
                "Some residual autocorrelation may be present."
            )
            recommendation = (
                "Review observation order, time effects, lagged variables, "
                "or clustered errors."
            )

        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "The Durbin-Watson statistic indicates substantial "
                "residual autocorrelation."
            )
            recommendation = (
                "Consider time-series regression, generalized least "
                "squares, or lag features."
            )

        return BLUEAssumptionResult(
            assumption="independence",
            status=status,
            statistic=round(statistic, 6),
            threshold=2.0,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.9,
        )

    def _test_influential_observations(
        self,
        fitted_model,
    ) -> BLUEAssumptionResult:
        influence = fitted_model.get_influence()

        cooks_distance = influence.cooks_distance[0]

        threshold = 4 / len(cooks_distance)

        influential_count = int(
            (cooks_distance > threshold).sum()
        )

        influential_percentage = (
            influential_count
            / len(cooks_distance)
            * 100
        )

        if influential_percentage <= 1:
            status = "passed"
            severity = "low"
            interpretation = (
                "Very few observations exceed the Cook's distance "
                "threshold."
            )
            recommendation = (
                "No major influential-observation issue was detected."
            )

        elif influential_percentage <= 5:
            status = "warning"
            severity = "medium"
            interpretation = (
                "Several potentially influential observations were found."
            )
            recommendation = (
                "Review high Cook's distance records and compare models "
                "with and without them."
            )

        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "A notable portion of observations may strongly influence "
                "the regression estimates."
            )
            recommendation = (
                "Investigate influential rows, possible data errors, "
                "segmentation, or robust regression."
            )

        return BLUEAssumptionResult(
            assumption="influential_observations",
            status=status,
            statistic=round(
                influential_percentage,
                4,
            ),
            threshold=1.0,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.88,
            details={
                "influential_rows": influential_count,
                "influential_percentage": round(
                    influential_percentage,
                    4,
                ),
                "cooks_distance_threshold": round(
                    threshold,
                    6,
                ),
            },
        )

    def _calculate_vif(
        self,
        X: pd.DataFrame,
    ) -> list[VIFResult]:
        if X.shape[1] < 2:
            return []

        vif_frame = sm.add_constant(
            X,
            has_constant="add",
        )

        results = []

        for index, column in enumerate(
            vif_frame.columns
        ):
            if column == "const":
                continue

            try:
                vif = float(
                    variance_inflation_factor(
                        vif_frame.values,
                        index,
                    )
                )
            except Exception:
                vif = float("inf")

            if vif < 5:
                severity = "low"
                interpretation = (
                    "No major multicollinearity concern."
                )
                recommendation = (
                    "The feature can generally remain in the model."
                )

            elif vif < 10:
                severity = "medium"
                interpretation = (
                    "Moderate multicollinearity detected."
                )
                recommendation = (
                    "Review correlated predictors and coefficient stability."
                )

            else:
                severity = "high"
                interpretation = (
                    "Severe multicollinearity detected."
                )
                recommendation = (
                    "Remove, combine, transform, or regularize correlated "
                    "predictors."
                )

            results.append(
                VIFResult(
                    feature=column,
                    vif=round(vif, 4),
                    severity=severity,
                    interpretation=interpretation,
                    recommendation=recommendation,
                )
            )

        return sorted(
            results,
            key=lambda item: item.vif,
            reverse=True,
        )

    def _build_multicollinearity_result(
        self,
        vif_results: list[VIFResult],
    ) -> BLUEAssumptionResult:
        if not vif_results:
            return BLUEAssumptionResult(
                assumption="multicollinearity",
                status="warning",
                interpretation=(
                    "VIF could not be calculated because fewer than two "
                    "predictors were available."
                ),
                recommendation=(
                    "Use at least two predictors for multicollinearity "
                    "assessment."
                ),
                severity="low",
                confidence=0.7,
            )

        maximum_vif = max(
            result.vif
            for result in vif_results
        )

        severe_count = sum(
            result.vif >= 10
            for result in vif_results
        )

        moderate_count = sum(
            5 <= result.vif < 10
            for result in vif_results
        )

        if severe_count > 0:
            status = "failed"
            severity = "high"
            interpretation = (
                f"{severe_count} predictor(s) have VIF values of at least "
                "10, indicating severe multicollinearity."
            )
            recommendation = (
                "Review highly correlated predictors, derived variables, "
                "and target-leakage-like features."
            )

        elif moderate_count > 0:
            status = "warning"
            severity = "medium"
            interpretation = (
                f"{moderate_count} predictor(s) have moderate VIF values."
            )
            recommendation = (
                "Review coefficient stability and consider regularization."
            )

        else:
            status = "passed"
            severity = "low"
            interpretation = (
                "No major multicollinearity was detected."
            )
            recommendation = (
                "Predictor collinearity appears acceptable."
            )

        return BLUEAssumptionResult(
            assumption="multicollinearity",
            status=status,
            statistic=round(
                maximum_vif,
                4,
            ),
            threshold=5.0,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.95,
            details={
                "maximum_vif": round(
                    maximum_vif,
                    4,
                ),
                "moderate_vif_features": moderate_count,
                "severe_vif_features": severe_count,
            },
        )

    def _calculate_score(
        self,
        assumptions: list[BLUEAssumptionResult],
    ) -> float:
        scores = {
            "passed": 100,
            "warning": 65,
            "failed": 25,
        }

        if not assumptions:
            return 0.0

        total = sum(
            scores.get(result.status, 0)
            for result in assumptions
        )

        return round(
            total / len(assumptions),
            2,
        )

    def _overall_status(
        self,
        suitability_score: float,
        assumptions: list[BLUEAssumptionResult],
    ) -> str:
        severe_failures = sum(
            result.status == "failed"
            and result.severity == "high"
            for result in assumptions
        )

        if suitability_score >= 85 and severe_failures == 0:
            return "suitable"

        if suitability_score >= 60:
            return "suitable_with_caution"

        return "not_suitable"

    def _build_recommendations(
        self,
        assumption_results: list[BLUEAssumptionResult],
        vif_results: list[VIFResult],
    ) -> list[str]:
        recommendations = []

        for result in assumption_results:
            if result.status != "passed":
                recommendations.append(
                    result.recommendation
                )

        high_vif_features = [
            result.feature
            for result in vif_results
            if result.vif >= 10
        ]

        if high_vif_features:
            recommendations.append(
                "High-VIF predictors requiring review: "
                + ", ".join(high_vif_features[:10])
            )

        if not recommendations:
            recommendations.append(
                "The tested linear regression assumptions appear "
                "acceptable."
            )

        return list(dict.fromkeys(recommendations))

    def _detect_leakage_candidates(
        self,
        df: pd.DataFrame,
        target: str,
        feature_columns: list[str],
        threshold: float,
    ) -> list[str]:
        leakage_candidates: list[str] = []

        target_series = pd.to_numeric(
            df[target],
            errors="coerce",
        )

        target_name = target.lower().strip()

        for column in feature_columns:
            column_name = column.lower().strip()

            if self._is_target_derived_name(
                column_name=column_name,
                target_name=target_name,
            ):
                leakage_candidates.append(column)
                continue

            feature_series = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            pair = pd.concat(
                [target_series, feature_series],
                axis=1,
            ).replace(
                [np.inf, -np.inf],
                np.nan,
            ).dropna()

            if len(pair) < 3:
                continue

            if pair.iloc[:, 1].nunique() <= 1:
                continue

            correlation = pair.iloc[:, 0].corr(
                pair.iloc[:, 1]
            )

            if (
                correlation is not None
                and not pd.isna(correlation)
                and abs(float(correlation)) >= threshold
            ):
                leakage_candidates.append(column)

        return list(dict.fromkeys(leakage_candidates))

    def _is_target_derived_name(
        self,
        column_name: str,
        target_name: str,
    ) -> bool:
        normalized_column = column_name.replace(" ", "_")
        normalized_target = target_name.replace(" ", "_")

        target_tokens = {
            normalized_target,
            f"log_{normalized_target}",
            f"{normalized_target}_log",
            f"{normalized_target}_scaled",
            f"{normalized_target}_normalized",
            f"{normalized_target}_per_unit",
            f"{normalized_target}_ratio",
            f"{normalized_target}_margin",
        }

        if normalized_column in target_tokens:
            return True

        if normalized_target in normalized_column:
            derived_tokens = (
                "ratio",
                "margin",
                "per_",
                "_per",
                "scaled",
                "normalized",
                "log",
                "average",
                "mean",
                "total",
            )

            return any(
                token in normalized_column
                for token in derived_tokens
            )

        return False

    def _remove_duplicate_predictors(
        self,
        df: pd.DataFrame,
        feature_columns: list[str],
        excluded_features: list[str],
    ) -> list[str]:
        retained: list[str] = []

        for column in feature_columns:
            duplicate_found = False

            for existing_column in retained:
                left = df[column]
                right = df[existing_column]

                comparable = pd.concat(
                    [left, right],
                    axis=1,
                ).dropna()

                if comparable.empty:
                    continue

                if comparable.iloc[:, 0].equals(
                    comparable.iloc[:, 1]
                ):
                    excluded_features.append(column)
                    duplicate_found = True
                    break

            if not duplicate_found:
                retained.append(column)

        return retained

    def _rank_predictors(
        self,
        df: pd.DataFrame,
        target: str,
        feature_columns: list[str],
    ) -> list[str]:
        target_series = pd.to_numeric(
            df[target],
            errors="coerce",
        )

        ranked: list[tuple[str, float]] = []

        for column in feature_columns:
            feature_series = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            pair = pd.concat(
                [target_series, feature_series],
                axis=1,
            ).replace(
                [np.inf, -np.inf],
                np.nan,
            ).dropna()

            if len(pair) < 3:
                score = 0.0
            else:
                correlation = pair.iloc[:, 0].corr(
                    pair.iloc[:, 1]
                )

                score = (
                    abs(float(correlation))
                    if correlation is not None
                    and not pd.isna(correlation)
                    else 0.0
                )

            ranked.append((column, score))

        ranked.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            column
            for column, _ in ranked
        ]

    def _is_identifier_column(
        self,
        column: str,
    ) -> bool:
        name = column.lower().strip()

        exact_tokens = {
            "id",
            "uuid",
            "guid",
            "transaction",
            "transaction_id",
            "customer_id",
            "order_id",
            "invoice_id",
            "receipt_id",
        }

        if name in exact_tokens:
            return True

        if name.endswith("_id"):
            return True

        return any(
            token in name
            for token in (
                "transaction_id",
                "customer_id",
                "order_id",
                "invoice_id",
                "receipt_id",
                "uuid",
                "guid",
            )
        )
