from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from autodq.operations.models import (
    OperationalBottleneck,
    OperationalColumnMap,
    OperationalDetection,
    OperationalDriver,
    OperationalKPI,
    OperationalReport,
    OperationalTrend,
    ProcessSegment,
)


class OperationalAnalyticsEngine:
    """Infer operational structure and calculate explainable process metrics."""

    ROLE_ALIASES = {
        "entity": (
            "transaction_id", "order_id", "ticket_id", "case_id", "job_id",
            "request_id", "shipment_id", "claim_id", "event_id", "process_id",
            "tracking_number", "work_order", "id",
        ),
        "time": (
            "event_time", "event_date", "timestamp", "transaction_date",
            "order_date", "created_at", "date", "time",
        ),
        "start": (
            "start_time", "started_at", "opened_at", "created_at",
            "arrival_time", "request_time", "start_date",
        ),
        "end": (
            "end_time", "completed_at", "closed_at", "resolved_at",
            "delivered_at", "departure_time", "completion_date", "end_date",
        ),
        "status": (
            "status", "state", "outcome", "result", "disposition", "returned",
            "is_returned", "failed", "is_failed", "completed", "is_completed",
            "cancelled", "canceled", "defect", "late",
        ),
        "stage": (
            "process_stage", "workflow_stage", "stage", "process_step", "step",
            "phase", "queue", "activity",
        ),
        "duration": (
            "cycle_time", "lead_time", "processing_time", "response_time",
            "resolution_time", "wait_time", "waiting_time", "service_time",
            "delivery_days", "duration", "turnaround_time", "downtime",
        ),
        "value": (
            "revenue", "sales", "amount", "order_value", "transaction_value",
            "gross_sales", "value",
        ),
        "cost": (
            "cost", "expense", "operating_cost", "service_cost", "unit_cost",
        ),
        "quantity": (
            "quantity", "units", "volume", "items", "item_count", "demand",
            "output", "production_quantity",
        ),
        "capacity": (
            "capacity", "available_capacity", "maximum_capacity", "limit",
            "slots", "planned_capacity", "resource_capacity",
        ),
    }
    GROUP_ALIASES = (
        "team", "department", "owner", "agent", "assignee", "operator",
        "location", "region", "city", "site", "branch", "warehouse", "plant",
        "channel", "sales_channel", "category", "product_category", "product",
        "priority", "carrier", "route", "machine", "resource", "customer_segment",
    )
    DOMAIN_SIGNALS = {
        "sales_operations": (
            "transaction", "order", "customer", "product", "revenue", "sales",
            "discount", "payment", "channel",
        ),
        "service_operations": (
            "ticket", "case", "request", "agent", "priority", "resolution",
            "response", "sla", "queue",
        ),
        "logistics_operations": (
            "shipment", "tracking", "delivery", "carrier", "route", "warehouse",
            "arrival", "departure", "freight",
        ),
        "manufacturing_operations": (
            "machine", "batch", "plant", "defect", "downtime", "production",
            "work_order", "yield", "shift",
        ),
        "healthcare_operations": (
            "patient", "admission", "discharge", "appointment", "wait",
            "treatment", "ward", "provider",
        ),
        "financial_operations": (
            "account", "payment", "claim", "transaction", "fraud", "settlement",
            "balance", "amount",
        ),
    }
    COMPLETION_WORDS = {
        "complete", "completed", "closed", "resolved", "delivered", "fulfilled",
        "success", "successful", "done", "approved", "finished",
    }
    FAILURE_WORDS = {
        "fail", "failed", "failure", "error", "cancelled", "canceled", "rejected",
        "returned", "return", "late", "breach", "breached", "defect", "defective",
        "lost", "abandoned",
    }
    BACKLOG_WORDS = {
        "open", "pending", "queued", "waiting", "in_progress", "in progress",
        "active", "assigned", "blocked", "on_hold", "on hold",
    }

    def analyze(
        self,
        df: pd.DataFrame,
        *,
        dataset_name: str = "current",
        entity_column: str | None = None,
        time_column: str | None = None,
        start_column: str | None = None,
        end_column: str | None = None,
        status_column: str | None = None,
        stage_column: str | None = None,
        duration_column: str | None = None,
        value_column: str | None = None,
        cost_column: str | None = None,
        quantity_column: str | None = None,
        capacity_column: str | None = None,
        group_by: list[str] | tuple[str, ...] | str | None = None,
        sla_target: float | None = None,
        period: str = "month",
        top: int = 10,
    ) -> OperationalReport:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Operational analytics requires a pandas DataFrame.")
        if df.empty:
            raise ValueError("Operational analytics requires at least one row.")

        period = str(period).lower().strip()
        if period not in {"day", "week", "month"}:
            raise ValueError("Operational period must be day, week, or month.")
        if top < 1:
            raise ValueError("Operational TOP must be positive.")
        if sla_target is not None and sla_target <= 0:
            raise ValueError("Operational SLA must be positive.")

        overrides = {
            "entity": entity_column,
            "time": time_column,
            "start": start_column,
            "end": end_column,
            "status": status_column,
            "stage": stage_column,
            "duration": duration_column,
            "value": value_column,
            "cost": cost_column,
            "quantity": quantity_column,
            "capacity": capacity_column,
        }
        columns = self._infer_columns(df, overrides=overrides, group_by=group_by)
        detection = self._detect(df, columns)
        duration = self._duration_series(df, columns)
        failure, completion = self._status_indicators(df, columns.status)
        event_time = self._datetime_series(df, columns.time)
        if event_time is None:
            event_time = self._datetime_series(df, columns.end or columns.start)
        value = self._numeric_series(df, columns.value)
        cost = self._numeric_series(df, columns.cost)
        quantity = self._numeric_series(df, columns.quantity)
        capacity = self._numeric_series(df, columns.capacity)

        kpis = self._build_kpis(
            df,
            columns=columns,
            duration=duration,
            failure=failure,
            completion=completion,
            event_time=event_time,
            value=value,
            cost=cost,
            quantity=quantity,
            capacity=capacity,
            sla_target=sla_target,
        )
        trends = self._build_trends(
            event_time=event_time,
            duration=duration,
            failure=failure,
            value=value,
            period=period,
        )
        process_segments = self._build_process_segments(
            df,
            columns=columns,
            duration=duration,
            failure=failure,
            value=value,
            sla_target=sla_target,
            top=top,
        )
        bottlenecks = self._build_bottlenecks(
            df,
            columns=columns,
            duration=duration,
            failure=failure,
            sla_target=sla_target,
            top=top,
        )
        root_causes = self._build_root_causes(
            df,
            columns=columns,
            duration=duration,
            failure=failure,
            value=value,
            top=top,
        )
        return OperationalReport(
            dataset_name=dataset_name,
            rows_analyzed=len(df),
            detection=detection,
            kpis=kpis,
            trends=trends,
            process_segments=process_segments,
            bottlenecks=bottlenecks,
            root_causes=root_causes,
            sla_target=sla_target,
            period=period,
        )

    def _infer_columns(
        self,
        df: pd.DataFrame,
        *,
        overrides: dict[str, str | None],
        group_by: list[str] | tuple[str, ...] | str | None,
    ) -> OperationalColumnMap:
        resolved: dict[str, str | None] = {}
        used: set[str] = set()
        role_order = (
            "entity", "start", "end", "time", "status", "stage", "duration",
            "value", "cost", "quantity", "capacity",
        )
        for role in role_order:
            override = overrides[role]
            if override is not None:
                column = self._resolve_column(df, override)
            else:
                column = self._best_column(df, role, exclude=used)
            resolved[role] = column
            if column:
                used.add(column)

        if bool(resolved["start"]) != bool(resolved["end"]):
            # A single timestamp still has value, but cannot create elapsed time.
            if resolved["start"] and not resolved["time"]:
                resolved["time"] = resolved["start"]
            if resolved["end"] and not resolved["time"]:
                resolved["time"] = resolved["end"]
        elif resolved["start"] and resolved["end"] and not resolved["time"]:
            resolved["time"] = resolved["start"]

        if group_by is None:
            groups = self._infer_groups(df, exclude=used)
        else:
            raw_groups = [group_by] if isinstance(group_by, str) else list(group_by)
            groups = [self._resolve_column(df, item) for item in raw_groups]

        unit = self._duration_unit(resolved["duration"], derived=bool(
            resolved["start"] and resolved["end"] and not resolved["duration"]
        ))
        return OperationalColumnMap(
            **resolved,
            group_by=groups,
            duration_unit=unit,
        )

    def _detect(
        self,
        df: pd.DataFrame,
        columns: OperationalColumnMap,
    ) -> OperationalDetection:
        normalized = " ".join(self._normalize(column) for column in df.columns)
        domain_scores = {
            domain: sum(1 for signal in signals if signal in normalized)
            for domain, signals in self.DOMAIN_SIGNALS.items()
        }
        dataset_type, domain_score = max(domain_scores.items(), key=lambda item: item[1])
        if domain_score < 2:
            dataset_type = "generic_operations"

        weights = {
            "entity": 0.14,
            "time": 0.16,
            "status_or_stage": 0.16,
            "elapsed_time": 0.18,
            "quantity": 0.08,
            "commercial": 0.10,
            "capacity": 0.06,
            "groups": 0.06,
            "domain": 0.06,
        }
        present = {
            "entity": bool(columns.entity),
            "time": bool(columns.time or columns.start or columns.end),
            "status_or_stage": bool(columns.status or columns.stage),
            "elapsed_time": bool(columns.duration or (columns.start and columns.end)),
            "quantity": bool(columns.quantity),
            "commercial": bool(columns.value or columns.cost),
            "capacity": bool(columns.capacity),
            "groups": bool(columns.group_by),
            "domain": dataset_type != "generic_operations",
        }
        confidence = round(sum(weights[key] for key, value in present.items() if value), 3)
        evidence = []
        if present["entity"]:
            evidence.append(f"Entity or event key recognized: {columns.entity}.")
        if present["time"]:
            evidence.append(
                f"Operational time recognized: {columns.time or columns.start or columns.end}."
            )
        if present["status_or_stage"]:
            evidence.append(
                f"Process state recognized: {columns.stage or columns.status}."
            )
        if present["elapsed_time"]:
            source = columns.duration or f"{columns.start} to {columns.end}"
            evidence.append(f"Elapsed-time evidence recognized: {source}.")
        if present["quantity"]:
            evidence.append(f"Work volume recognized: {columns.quantity}.")
        if present["commercial"]:
            evidence.append(
                f"Operational value/cost recognized: {columns.value or columns.cost}."
            )
        if dataset_type != "generic_operations":
            evidence.append(
                f"Column vocabulary is consistent with {dataset_type.replace('_', ' ')}."
            )

        warnings = []
        if not present["time"]:
            warnings.append("No operational timestamp was found; time trends are unavailable.")
        if not present["elapsed_time"]:
            warnings.append(
                "No duration or start/end pair was found; cycle-time analysis is limited."
            )
        if not present["status_or_stage"]:
            warnings.append(
                "No status or stage column was found; process-flow analysis is limited."
            )
        if confidence < 0.35:
            warnings.append(
                "Operational confidence is low. Supply explicit column roles to improve it."
            )
        return OperationalDetection(
            dataset_type=dataset_type,
            confidence=confidence,
            is_operational=confidence >= 0.35,
            evidence=evidence,
            columns=columns,
            warnings=warnings,
        )

    def _build_kpis(
        self,
        df: pd.DataFrame,
        *,
        columns: OperationalColumnMap,
        duration: pd.Series | None,
        failure: pd.Series | None,
        completion: pd.Series | None,
        event_time: pd.Series | None,
        value: pd.Series | None,
        cost: pd.Series | None,
        quantity: pd.Series | None,
        capacity: pd.Series | None,
        sla_target: float | None,
    ) -> list[OperationalKPI]:
        kpis = [self._kpi("record_count", "Records processed", len(df), "records", "neutral", "Total operational records analyzed.")]
        if columns.entity:
            unique = int(df[columns.entity].nunique(dropna=True))
            kpis.append(self._kpi("unique_entities", "Unique entities", unique, "entities", "neutral", "Distinct operational entities or events.", [columns.entity]))

        if event_time is not None and event_time.notna().any():
            valid = event_time.dropna()
            elapsed_days = max((valid.max() - valid.min()).total_seconds() / 86400, 0) + 1
            throughput = round(len(valid) / elapsed_days, 2)
            kpis.append(self._kpi("throughput_per_day", "Average throughput", throughput, "records/day", "neutral", "Average records observed per calendar day.", [columns.time or columns.end or columns.start]))

        valid_duration = self._valid_numeric(duration)
        if valid_duration is not None:
            source = [columns.duration] if columns.duration else [columns.start, columns.end]
            source = [item for item in source if item]
            kpis.extend([
                self._kpi("average_cycle_time", "Average cycle time", round(float(valid_duration.mean()), 2), columns.duration_unit, self._duration_status(float(valid_duration.mean()), sla_target), "Mean elapsed time per record.", source),
                self._kpi("median_cycle_time", "Median cycle time", round(float(valid_duration.median()), 2), columns.duration_unit, "neutral", "Typical elapsed time, less sensitive to extremes.", source),
                self._kpi("p95_cycle_time", "95th percentile cycle time", round(float(valid_duration.quantile(0.95)), 2), columns.duration_unit, self._duration_status(float(valid_duration.quantile(0.95)), sla_target), "95% of valid records complete within this time.", source),
            ])
            if sla_target is not None:
                breach_rate = round(float((valid_duration > sla_target).mean() * 100), 2)
                kpis.append(self._kpi("sla_breach_rate", "SLA breach rate", breach_rate, "%", self._rate_status(breach_rate), f"Share of valid records exceeding the {sla_target:g} {columns.duration_unit} SLA.", source))

        if completion is not None and completion.notna().any():
            rate = round(float(completion.dropna().mean() * 100), 2)
            kpis.append(self._kpi("completion_rate", "Completion rate", rate, "%", "good" if rate >= 95 else "warning" if rate >= 80 else "critical", "Share of records carrying a recognized completion outcome.", [columns.status]))
        if failure is not None and failure.notna().any():
            rate = round(float(failure.dropna().mean() * 100), 2)
            label = "Return rate" if columns.status and "return" in self._normalize(columns.status) else "Failure or exception rate"
            kpis.append(self._kpi("failure_rate", label, rate, "%", self._rate_status(rate), "Share of records carrying a recognized adverse outcome.", [columns.status]))

        if value is not None and value.notna().any():
            kpis.append(self._kpi("total_value", "Total operational value", round(float(value.sum()), 2), "value", "neutral", "Sum of the inferred value measure.", [columns.value]))
            kpis.append(self._kpi("average_value", "Average value per record", round(float(value.mean()), 2), "value/record", "neutral", "Mean inferred value across valid records.", [columns.value]))
        if cost is not None and cost.notna().any():
            kpis.append(self._kpi("total_cost", "Total operational cost", round(float(cost.sum()), 2), "cost", "neutral", "Sum of the inferred cost measure.", [columns.cost]))
            if value is not None and value.notna().any():
                margin = float(value.sum() - cost.sum())
                kpis.append(self._kpi("operating_margin", "Operational margin", round(margin, 2), "value", "good" if margin >= 0 else "critical", "Total inferred value minus total inferred cost.", [columns.value, columns.cost]))
        if quantity is not None and quantity.notna().any():
            kpis.append(self._kpi("total_units", "Total units handled", round(float(quantity.sum()), 2), "units", "neutral", "Sum of the inferred quantity or volume measure.", [columns.quantity]))
        if quantity is not None and capacity is not None:
            valid = pd.concat([quantity, capacity], axis=1).dropna()
            valid = valid[valid.iloc[:, 1] > 0]
            if not valid.empty:
                utilization = round(float((valid.iloc[:, 0] / valid.iloc[:, 1]).mean() * 100), 2)
                status = "good" if 70 <= utilization <= 90 else "warning" if utilization <= 100 else "critical"
                kpis.append(self._kpi("capacity_utilization", "Capacity utilization", utilization, "%", status, "Average quantity divided by available capacity.", [columns.quantity, columns.capacity]))

        completeness = round(float((1 - df.isna().sum().sum() / max(df.size, 1)) * 100), 2)
        kpis.append(self._kpi("record_completeness", "Operational data completeness", completeness, "%", "good" if completeness >= 98 else "warning" if completeness >= 90 else "critical", "Non-missing cells as a share of all operational data cells."))
        return kpis

    def _build_trends(
        self,
        *,
        event_time: pd.Series | None,
        duration: pd.Series | None,
        failure: pd.Series | None,
        value: pd.Series | None,
        period: str,
    ) -> list[OperationalTrend]:
        if event_time is None or not event_time.notna().any():
            return []
        frequency = {"day": "D", "week": "W", "month": "M"}[period]
        frame = pd.DataFrame({"event_time": event_time})
        frame["period"] = frame["event_time"].dt.to_period(frequency).astype(str)
        if duration is not None:
            frame["duration"] = duration
        if failure is not None:
            frame["failure"] = failure
        if value is not None:
            frame["value"] = value
        frame = frame.dropna(subset=["event_time"])
        points = []
        for label, group in frame.groupby("period", sort=True):
            points.append(OperationalTrend(
                period=str(label),
                records=len(group),
                average_duration=self._rounded_mean(group.get("duration")),
                failure_rate=self._rounded_rate(group.get("failure")),
                total_value=self._rounded_sum(group.get("value")),
            ))
        return points[-36:]

    def _build_process_segments(
        self,
        df: pd.DataFrame,
        *,
        columns: OperationalColumnMap,
        duration: pd.Series | None,
        failure: pd.Series | None,
        value: pd.Series | None,
        sla_target: float | None,
        top: int,
    ) -> list[ProcessSegment]:
        dimensions = self._unique([columns.stage, columns.status])
        segments = []
        for dimension in dimensions:
            frame = pd.DataFrame({"segment": df[dimension].fillna("(missing)").astype(str)})
            if duration is not None:
                frame["duration"] = duration
            if failure is not None:
                frame["failure"] = failure
            if value is not None:
                frame["value"] = value
            for segment, group in frame.groupby("segment", dropna=False):
                durations = self._valid_numeric(group.get("duration"))
                failures = group.get("failure")
                values = group.get("value")
                breach = None
                if durations is not None and sla_target is not None:
                    breach = round(float((durations > sla_target).mean() * 100), 2)
                segments.append(ProcessSegment(
                    dimension=dimension,
                    segment=str(segment),
                    records=len(group),
                    share_percent=round(len(group) / len(df) * 100, 2),
                    average_duration=self._rounded_mean(durations),
                    median_duration=self._rounded_quantile(durations, 0.5),
                    p95_duration=self._rounded_quantile(durations, 0.95),
                    failure_rate=self._rounded_rate(failures),
                    sla_breach_rate=breach,
                    total_value=self._rounded_sum(values),
                ))
        segments.sort(key=lambda item: item.records, reverse=True)
        return segments[: max(top * max(len(dimensions), 1), top)]

    def _build_bottlenecks(
        self,
        df: pd.DataFrame,
        *,
        columns: OperationalColumnMap,
        duration: pd.Series | None,
        failure: pd.Series | None,
        sla_target: float | None,
        top: int,
    ) -> list[OperationalBottleneck]:
        dimensions = self._unique([columns.stage, columns.status, *columns.group_by])
        overall_duration = self._rounded_mean(self._valid_numeric(duration))
        overall_failure = self._rounded_rate(failure) or 0.0
        bottlenecks = []
        for dimension in dimensions:
            frame = pd.DataFrame({"segment": df[dimension].fillna("(missing)").astype(str)})
            if duration is not None:
                frame["duration"] = duration
            if failure is not None:
                frame["failure"] = failure
            for segment, group in frame.groupby("segment", dropna=False):
                if len(group) < max(3, int(len(df) * 0.005)):
                    continue
                share = len(group) / len(df) * 100
                average = self._rounded_mean(self._valid_numeric(group.get("duration")))
                delay_ratio = (
                    round(average / overall_duration, 3)
                    if average is not None and overall_duration and overall_duration > 0
                    else None
                )
                failure_rate = self._rounded_rate(group.get("failure"))
                delay_risk = min(60.0, max(0.0, (delay_ratio or 1) - 1) * 70)
                failure_risk = min(30.0, max(0.0, (failure_rate or 0) - overall_failure) * 1.5)
                concentration_risk = min(20.0, max(0.0, share - 20) * 0.5)
                backlog_risk = 25.0 if self._normalize(str(segment)) in self.BACKLOG_WORDS else 0.0
                sla_risk = 0.0
                if average is not None and sla_target and average > sla_target:
                    sla_risk = min(30.0, (average / sla_target - 1) * 30)
                score = round(min(100.0, delay_risk + failure_risk + concentration_risk + backlog_risk + sla_risk), 2)
                if score < 15:
                    continue
                severity = "high" if score >= 60 else "medium" if score >= 35 else "low"
                evidence_parts = [f"{share:.1f}% of records"]
                if delay_ratio is not None:
                    evidence_parts.append(f"{delay_ratio:.2f}x overall cycle time")
                if failure_rate is not None:
                    evidence_parts.append(f"{failure_rate:.1f}% adverse outcomes")
                if backlog_risk:
                    evidence_parts.append("status indicates active backlog")
                bottlenecks.append(OperationalBottleneck(
                    dimension=dimension,
                    segment=str(segment),
                    severity=severity,
                    score=score,
                    records=len(group),
                    share_percent=round(share, 2),
                    delay_ratio=delay_ratio,
                    failure_rate=failure_rate,
                    evidence="; ".join(evidence_parts) + ".",
                ))
        bottlenecks.sort(key=lambda item: (item.score, item.records), reverse=True)
        return bottlenecks[:top]

    def _build_root_causes(
        self,
        df: pd.DataFrame,
        *,
        columns: OperationalColumnMap,
        duration: pd.Series | None,
        failure: pd.Series | None,
        value: pd.Series | None,
        top: int,
    ) -> list[OperationalDriver]:
        if duration is not None and duration.notna().sum() >= 3:
            outcome_name, outcome = "cycle_time", duration
        elif failure is not None and failure.notna().sum() >= 3:
            outcome_name, outcome = "adverse_outcome", failure
        elif value is not None and value.notna().sum() >= 3:
            outcome_name, outcome = "operational_value", value
        else:
            return []

        excluded = set(self._unique([
            columns.entity, columns.time, columns.start, columns.end,
            columns.duration, columns.status, columns.stage,
        ]))
        drivers = []
        numeric = df.select_dtypes(include="number")
        for feature in numeric.columns:
            if feature in excluded:
                continue
            pair = pd.concat([
                pd.to_numeric(numeric[feature], errors="coerce").rename("feature"),
                outcome.rename("outcome"),
            ], axis=1).dropna()
            if len(pair) < 3 or pair["feature"].nunique() < 2 or pair["outcome"].nunique() < 2:
                continue
            correlation = pair["feature"].corr(pair["outcome"])
            if pd.isna(correlation) or abs(correlation) < 0.05:
                continue
            direction = "increases" if correlation > 0 else "decreases"
            drivers.append(OperationalDriver(
                outcome=outcome_name,
                feature=str(feature),
                driver_type="numeric_correlation",
                direction=direction,
                strength=round(abs(float(correlation)), 4),
                effect=round(float(correlation), 4),
                segment=None,
                records=len(pair),
                evidence=f"Correlation with {outcome_name} is {correlation:.3f} across {len(pair):,} records.",
            ))

        categorical_candidates = self._unique([
            columns.stage, columns.status, *columns.group_by,
            *self._infer_groups(df, exclude=excluded),
        ])
        outcome_std = float(outcome.std()) if outcome.notna().sum() > 1 else 0.0
        overall = float(outcome.mean())
        for feature in categorical_candidates:
            frame = pd.DataFrame({
                "feature": df[feature].fillna("(missing)").astype(str),
                "outcome": outcome,
            }).dropna(subset=["outcome"])
            if frame.empty or frame["feature"].nunique() < 2 or frame["feature"].nunique() > 100:
                continue
            grouped = frame.groupby("feature")["outcome"].agg(["mean", "count"])
            grouped = grouped[grouped["count"] >= max(3, int(len(frame) * 0.005))]
            if grouped.empty:
                continue
            grouped["difference"] = grouped["mean"] - overall
            segment = str(grouped["difference"].abs().idxmax())
            row = grouped.loc[segment]
            effect = float(row["difference"])
            strength = abs(effect) / outcome_std if outcome_std > 0 else 0.0
            if strength < 0.05:
                continue
            direction = "higher" if effect > 0 else "lower"
            if outcome_name == "adverse_outcome":
                evidence = f"{segment} has an adverse-outcome rate {abs(effect) * 100:.1f} percentage points {direction} than overall."
            else:
                evidence = f"{segment} has average {outcome_name} {abs(effect):.2f} units {direction} than overall."
            drivers.append(OperationalDriver(
                outcome=outcome_name,
                feature=feature,
                driver_type="segment_difference",
                direction=direction,
                strength=round(float(strength), 4),
                effect=round(effect, 4),
                segment=segment,
                records=int(row["count"]),
                evidence=evidence,
            ))
        drivers.sort(key=lambda item: (item.strength, item.records), reverse=True)
        return drivers[:top]

    def _best_column(self, df: pd.DataFrame, role: str, *, exclude: set[str]) -> str | None:
        aliases = self.ROLE_ALIASES[role]
        best: tuple[float, str] | None = None
        for column in df.columns:
            if column in exclude:
                continue
            normalized = self._normalize(column)
            score = 0.0
            for alias in aliases:
                if normalized == alias:
                    score = max(score, 10.0)
                elif alias in normalized or normalized in alias:
                    score = max(score, 6.0)
                else:
                    alias_tokens = set(alias.split("_"))
                    name_tokens = set(normalized.split("_"))
                    score = max(score, len(alias_tokens & name_tokens) * 2.0)
            if role in {"duration", "value", "cost", "quantity", "capacity"} and not pd.api.types.is_numeric_dtype(df[column]):
                score -= 3
            if role in {"time", "start", "end"} and pd.api.types.is_datetime64_any_dtype(df[column]):
                score += 4
            if best is None or score > best[0]:
                best = (score, str(column))
        return best[1] if best and best[0] >= 4 else None

    def _infer_groups(self, df: pd.DataFrame, *, exclude: set[str]) -> list[str]:
        candidates = []
        for column in df.columns:
            if column in exclude:
                continue
            normalized = self._normalize(column)
            score = max((10 if normalized == alias else 6 if alias in normalized else 0) for alias in self.GROUP_ALIASES)
            unique = df[column].nunique(dropna=True)
            if score and 1 < unique <= min(100, max(10, len(df) // 2)):
                candidates.append((score, unique, str(column)))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [item[2] for item in candidates[:3]]

    @staticmethod
    def _resolve_column(df: pd.DataFrame, requested: str) -> str:
        if requested in df.columns:
            return str(requested)
        matches = [str(column) for column in df.columns if str(column).lower() == str(requested).lower()]
        if len(matches) == 1:
            return matches[0]
        raise ValueError(f"Operational column {requested!r} does not exist.")

    def _duration_series(self, df: pd.DataFrame, columns: OperationalColumnMap) -> pd.Series | None:
        if columns.duration:
            return pd.to_numeric(df[columns.duration], errors="coerce").where(lambda item: item >= 0)
        if columns.start and columns.end:
            start = pd.to_datetime(df[columns.start], errors="coerce", utc=True)
            end = pd.to_datetime(df[columns.end], errors="coerce", utc=True)
            return ((end - start).dt.total_seconds() / 3600).where(lambda item: item >= 0)
        return None

    @staticmethod
    def _datetime_series(df: pd.DataFrame, column: str | None) -> pd.Series | None:
        if not column:
            return None
        return pd.to_datetime(df[column], errors="coerce", utc=True).dt.tz_localize(None)

    @staticmethod
    def _numeric_series(df: pd.DataFrame, column: str | None) -> pd.Series | None:
        if not column:
            return None
        return pd.to_numeric(df[column], errors="coerce")

    def _status_indicators(self, df: pd.DataFrame, column: str | None) -> tuple[pd.Series | None, pd.Series | None]:
        if not column:
            return None, None
        series = df[column]
        normalized_name = self._normalize(column)
        if pd.api.types.is_bool_dtype(series) or pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            if any(word in normalized_name for word in ("return", "fail", "error", "defect", "late", "cancel")):
                failure = numeric.where(numeric.isna(), numeric.ne(0).astype(float))
                return failure, 1 - failure
            if any(word in normalized_name for word in ("complete", "success", "resolved", "closed")):
                completion = numeric.where(numeric.isna(), numeric.ne(0).astype(float))
                return 1 - completion, completion
        text = series.astype("string").str.strip().str.lower()
        failure = text.map(lambda value: np.nan if pd.isna(value) else float(any(word in value for word in self.FAILURE_WORDS)))
        completion = text.map(lambda value: np.nan if pd.isna(value) else float(any(word in value for word in self.COMPLETION_WORDS)))
        return failure.astype(float), completion.astype(float)

    @staticmethod
    def _valid_numeric(series: pd.Series | None) -> pd.Series | None:
        if series is None:
            return None
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return valid if not valid.empty else None

    @staticmethod
    def _rounded_mean(series: pd.Series | None) -> float | None:
        if series is None:
            return None
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return round(float(valid.mean()), 2) if not valid.empty else None

    @staticmethod
    def _rounded_sum(series: pd.Series | None) -> float | None:
        if series is None:
            return None
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return round(float(valid.sum()), 2) if not valid.empty else None

    @staticmethod
    def _rounded_quantile(series: pd.Series | None, quantile: float) -> float | None:
        if series is None:
            return None
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return round(float(valid.quantile(quantile)), 2) if not valid.empty else None

    @staticmethod
    def _rounded_rate(series: pd.Series | None) -> float | None:
        if series is None:
            return None
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return round(float(valid.mean() * 100), 2) if not valid.empty else None

    @staticmethod
    def _duration_unit(column: str | None, *, derived: bool) -> str:
        if derived:
            return "hours"
        normalized = OperationalAnalyticsEngine._normalize(column or "")
        if "day" in normalized:
            return "days"
        if "hour" in normalized or normalized.endswith("_hrs"):
            return "hours"
        if "minute" in normalized or normalized.endswith("_mins"):
            return "minutes"
        if "second" in normalized or normalized.endswith("_secs"):
            return "seconds"
        return "units"

    @staticmethod
    def _duration_status(value: float, sla_target: float | None) -> str:
        if sla_target is None:
            return "neutral"
        if value <= sla_target:
            return "good"
        if value <= sla_target * 1.2:
            return "warning"
        return "critical"

    @staticmethod
    def _rate_status(rate: float) -> str:
        if rate <= 2:
            return "good"
        if rate <= 5:
            return "warning"
        return "critical"

    @staticmethod
    def _kpi(key: str, name: str, value: Any, unit: str, status: str, description: str, source_columns: list[str] | None = None) -> OperationalKPI:
        return OperationalKPI(key=key, name=name, value=value, unit=unit, status=status, description=description, source_columns=[item for item in (source_columns or []) if item])

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

    @staticmethod
    def _unique(values: list[str | None]) -> list[str]:
        output = []
        for value in values:
            if value and value not in output:
                output.append(value)
        return output
