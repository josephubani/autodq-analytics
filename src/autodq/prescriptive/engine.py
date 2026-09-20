from __future__ import annotations

from autodq.prescriptive.models import (
    OptimizationSummary,
    PrescriptionAuditEntry,
    PrescriptiveAction,
    PrescriptiveConstraint,
    PrescriptivePlan,
    WhatIfScenario,
)


class PrescriptiveAnalyticsEngine:
    """Turn operational evidence into governed, optimizable action plans."""

    OBJECTIVE_ALIASES = {
        "balanced": "balanced",
        "reduce_delay": "reduce_delay",
        "minimize_delay": "reduce_delay",
        "reduce_failures": "reduce_failures",
        "minimize_failures": "reduce_failures",
        "minimize_cost": "minimize_cost",
        "reduce_cost": "minimize_cost",
        "maximize_value": "maximize_value",
        "increase_value": "maximize_value",
        "balance_capacity": "balance_capacity",
        "maximize_capacity": "balance_capacity",
        "minimize_shortage": "minimize_shortage",
        "reduce_shortage": "minimize_shortage",
    }
    RISK_LEVELS = {"low": 1, "medium": 2, "high": 3}
    STATUS_TRANSITIONS = {
        "approve": ({"selected", "proposed"}, "approved"),
        "reject": ({"selected", "proposed", "approved"}, "rejected"),
        "execute": ({"approved"}, "executed"),
    }

    def generate(
        self,
        *,
        dataset_name: str,
        operations_report=None,
        inventory_report=None,
        objective: str = "balanced",
        budget: float | None = None,
        max_actions: int = 5,
        min_confidence: float = 0.5,
        max_risk: str = "high",
        top: int = 20,
    ) -> PrescriptivePlan:
        objective = self.normalize_objective(objective)
        actions: list[PrescriptiveAction] = []
        sources = []
        warnings = [
            "Expected impact and cost are planning estimates, not causal guarantees. Validate assumptions before implementation.",
            "ACTION EXECUTE records an implementation decision only; it does not change source systems or contact external services.",
        ]

        if operations_report is not None and operations_report.detection.is_operational:
            sources.append("operations")
            actions.extend(self._operational_actions(operations_report))
        elif operations_report is not None:
            warnings.append(
                "Operational evidence was omitted because the dataset did not meet the operational-confidence threshold."
            )

        if inventory_report is not None and inventory_report.detection.is_inventory:
            sources.append("inventory")
            actions.extend(self._inventory_actions(inventory_report))
        elif inventory_report is not None:
            warnings.append(
                "Inventory evidence was omitted because required inventory roles were not recognized."
            )

        actions = self._deduplicate(actions)[:top]
        for index, action in enumerate(actions, start=1):
            action.action_id = f"A{index:03d}"

        plan = PrescriptivePlan(
            dataset_name=dataset_name,
            objective=objective,
            actions=actions,
            source_reports=sources,
            warnings=warnings,
        )
        self.optimize(
            plan,
            objective=objective,
            budget=budget,
            max_actions=max_actions,
            min_confidence=min_confidence,
            max_risk=max_risk,
        )
        return plan

    def optimize(
        self,
        plan: PrescriptivePlan,
        *,
        objective: str | None = None,
        budget: float | None = None,
        max_actions: int = 5,
        min_confidence: float = 0.5,
        max_risk: str = "high",
    ) -> OptimizationSummary:
        objective = self.normalize_objective(objective or plan.objective)
        max_risk = str(max_risk).strip().lower()
        constraints = PrescriptiveConstraint(
            budget=budget,
            max_actions=max_actions,
            min_confidence=min_confidence,
            max_risk=max_risk,
        )
        cost_units = {
            action.cost_unit
            for action in plan.actions
            if action.status not in {"rejected", "executed"}
        }
        if budget is not None and len(cost_units) > 1:
            raise ValueError(
                "BUDGET cannot optimize actions with mixed cost units: "
                + ", ".join(sorted(cost_units))
                + ". Use SOURCE operations or SOURCE inventory, or optimize without BUDGET."
            )
        eligible = [
            action for action in plan.actions
            if action.status not in {"rejected", "executed"}
            and action.confidence >= min_confidence
            and self.RISK_LEVELS[action.risk] <= self.RISK_LEVELS[max_risk]
            and (budget is None or action.estimated_cost <= budget)
        ]
        for action in plan.actions:
            if action.status in {"proposed", "selected"}:
                action.status = "proposed"
            action.optimization_score = self._utility(action, objective)

        selected, method, notes = self._select_actions(
            eligible,
            budget=budget,
            max_actions=max_actions,
        )
        selected_ids = {item.action_id for item in selected}
        for action in plan.actions:
            if action.action_id in selected_ids and action.status == "proposed":
                action.status = "selected"

        summary = OptimizationSummary(
            objective=objective,
            method=method,
            status="optimal" if selected or not eligible else "infeasible",
            candidate_count=len(plan.actions),
            eligible_count=len(eligible),
            selected_action_ids=[item.action_id for item in selected],
            total_estimated_cost=round(
                sum(item.estimated_cost for item in selected), 2
            ),
            total_impact_score=round(
                sum(item.impact_score for item in selected), 2
            ),
            constraints=constraints,
            feasible=bool(selected or not eligible),
            notes=notes,
        )
        plan.objective = objective
        plan.optimization = summary
        plan.audit_trail.append(
            PrescriptionAuditEntry(
                event="optimized",
                action_id=None,
                previous_status=None,
                new_status=None,
                actor="autodq",
                reason=(
                    f"Selected {len(selected)} action(s) for {objective} "
                    f"using {method}."
                ),
            )
        )
        return summary

    def scenario(
        self,
        plan: PrescriptivePlan,
        *,
        name: str,
        operations_report=None,
        inventory_report=None,
        duration_change: float = 0.0,
        failure_change: float = 0.0,
        cost_change: float = 0.0,
        capacity_change: float = 0.0,
        value_change: float = 0.0,
        demand_change: float = 0.0,
        lead_time_change: float = 0.0,
    ) -> WhatIfScenario:
        changes = {
            "duration_change": float(duration_change),
            "failure_change": float(failure_change),
            "cost_change": float(cost_change),
            "capacity_change": float(capacity_change),
            "value_change": float(value_change),
            "demand_change": float(demand_change),
            "lead_time_change": float(lead_time_change),
        }
        baseline = self._baseline_metrics(operations_report, inventory_report)
        projected = dict(baseline)
        assumptions = []

        self._scale_metrics(
            projected,
            ("average_cycle_time", "median_cycle_time", "p95_cycle_time"),
            duration_change,
        )
        self._scale_metrics(
            projected,
            ("failure_rate",),
            failure_change,
            lower=0.0,
            upper=100.0,
        )
        self._scale_metrics(projected, ("total_cost",), cost_change)
        self._scale_metrics(projected, ("total_value",), value_change)
        if "capacity_utilization" in projected and capacity_change != 0:
            denominator = 1 + capacity_change / 100
            projected["capacity_utilization"] = round(
                max(0.0, projected["capacity_utilization"] / denominator), 2
            ) if denominator > 0 else projected["capacity_utilization"]
        inventory_multiplier = (
            (1 + demand_change / 100) * (1 + lead_time_change / 100)
        )
        if "shortage_units" in projected and inventory_multiplier >= 0:
            projected["shortage_units"] = round(
                max(0.0, projected["shortage_units"] * inventory_multiplier), 2
            )
        if "service_readiness" in projected:
            pressure = demand_change + lead_time_change
            projected["service_readiness"] = round(
                min(100.0, max(0.0, projected["service_readiness"] - pressure * 0.5)),
                2,
            )
        if "total_value" in projected and "total_cost" in projected:
            projected["operating_margin"] = round(
                projected["total_value"] - projected["total_cost"], 2
            )

        assumptions.append(
            "Percentage changes are applied independently to the latest observed KPI baseline."
        )
        if demand_change or lead_time_change:
            assumptions.append(
                "Inventory shortage uses a directional demand × lead-time approximation; rerun INVENTORY with revised inputs for a policy-grade result."
            )
        deltas = {
            key: round(projected[key] - baseline[key], 2)
            for key in projected
        }
        scenario = WhatIfScenario(
            scenario_id=f"S{len(plan.scenarios) + 1:03d}",
            name=str(name).strip(),
            changes={key: value for key, value in changes.items() if value != 0},
            baseline_metrics=baseline,
            projected_metrics=projected,
            metric_deltas=deltas,
            assumptions=assumptions,
            warnings=(
                [] if baseline else ["No numeric operational or inventory KPI baseline was available."]
            ),
        )
        plan.scenarios.append(scenario)
        plan.audit_trail.append(
            PrescriptionAuditEntry(
                event="scenario_evaluated",
                action_id=None,
                previous_status=None,
                new_status=None,
                actor="autodq",
                reason=scenario.name,
            )
        )
        return scenario

    def approve(
        self,
        plan: PrescriptivePlan,
        action_id: str,
        *,
        actor: str = "user",
        reason: str | None = None,
    ) -> PrescriptiveAction:
        return self._transition(plan, action_id, "approve", actor, reason)

    def approve_all(
        self,
        plan: PrescriptivePlan,
        *,
        actor: str = "user",
        reason: str | None = None,
    ) -> list[PrescriptiveAction]:
        candidates = [item for item in plan.actions if item.status == "selected"]
        if not candidates:
            candidates = [item for item in plan.actions if item.status == "proposed"]
        return [
            self.approve(plan, item.action_id, actor=actor, reason=reason)
            for item in candidates
        ]

    def reject(
        self,
        plan: PrescriptivePlan,
        action_id: str,
        *,
        actor: str = "user",
        reason: str | None = None,
    ) -> PrescriptiveAction:
        return self._transition(plan, action_id, "reject", actor, reason)

    def execute(
        self,
        plan: PrescriptivePlan,
        action_id: str,
        *,
        actor: str = "user",
        reason: str | None = None,
    ) -> PrescriptiveAction:
        action = self._transition(
            plan, action_id, "execute", actor, reason
        )
        action.metadata["execution_mode"] = "record_only"
        action.metadata["external_side_effects"] = False
        return action

    @classmethod
    def normalize_objective(cls, objective: str) -> str:
        normalized = str(objective).strip().lower().replace("-", "_")
        if normalized not in cls.OBJECTIVE_ALIASES:
            supported = ", ".join(sorted(set(cls.OBJECTIVE_ALIASES.values())))
            raise ValueError(
                f"Unsupported prescriptive objective: {objective}. Supported: {supported}."
            )
        return cls.OBJECTIVE_ALIASES[normalized]

    def _operational_actions(self, report) -> list[PrescriptiveAction]:
        actions = []
        detection_confidence = report.detection.confidence
        for item in report.bottlenecks:
            if item.delay_ratio is not None and item.delay_ratio > 1:
                objective = "reduce_delay"
                action_type = "process_improvement"
                description = (
                    f"Reduce cycle time for {item.dimension}={item.segment}; "
                    "validate the local workflow, queues, and handoffs."
                )
                impact_unit = "bottleneck-score points"
            elif (item.failure_rate or 0) > 0:
                objective = "reduce_failures"
                action_type = "failure_reduction"
                description = (
                    f"Reduce adverse outcomes for {item.dimension}={item.segment}."
                )
                impact_unit = "bottleneck-score points"
            else:
                objective = "balance_capacity"
                action_type = "capacity_rebalance"
                description = (
                    f"Rebalance workload concentrated in {item.dimension}={item.segment}."
                )
                impact_unit = "bottleneck-score points"
            actions.append(
                PrescriptiveAction(
                    action_id="",
                    title=f"Address {item.segment} bottleneck",
                    action_type=action_type,
                    objective=objective,
                    source="operations.bottlenecks",
                    target=f"{item.dimension}={item.segment}",
                    description=description,
                    rationale=item.evidence,
                    expected_impact=round(item.score, 2),
                    impact_unit=impact_unit,
                    impact_score=round(item.score, 2),
                    estimated_cost=round(max(1.0, item.records * 0.01), 2),
                    cost_unit="planning units",
                    cost_basis="1 planning unit per 100 affected records, minimum 1.",
                    priority=item.severity,
                    risk="medium" if item.severity == "high" else "low",
                    confidence=round(
                        min(0.99, detection_confidence * (0.75 + item.score / 400)),
                        3,
                    ),
                    metadata=item.to_dict(),
                )
            )

        for item in report.root_causes:
            objective = {
                "cycle_time": "reduce_delay",
                "adverse_outcome": "reduce_failures",
                "operational_value": "maximize_value",
            }.get(item.outcome, "balanced")
            target = item.feature
            if item.segment is not None:
                target += f"={item.segment}"
            score = round(min(100.0, item.strength * 100), 2)
            actions.append(
                PrescriptiveAction(
                    action_id="",
                    title=f"Test intervention for {target}",
                    action_type="driver_intervention",
                    objective=objective,
                    source="operations.root_causes",
                    target=target,
                    description=(
                        f"Design a controlled intervention around {target} and measure its effect on {item.outcome.replace('_', ' ')}."
                    ),
                    rationale=(
                        f"{item.evidence} This is an association and must be validated before causal use."
                    ),
                    expected_impact=score,
                    impact_unit="driver-strength points",
                    impact_score=score,
                    estimated_cost=round(max(1.0, item.records * 0.005), 2),
                    cost_unit="planning units",
                    cost_basis="0.5 planning units per 100 supporting records, minimum 1.",
                    priority="high" if score >= 60 else "medium" if score >= 30 else "low",
                    risk="medium",
                    confidence=round(
                        min(0.95, detection_confidence * (0.6 + min(item.strength, 1) * 0.3)),
                        3,
                    ),
                    metadata=item.to_dict(),
                )
            )
        return actions

    def _inventory_actions(self, report) -> list[PrescriptiveAction]:
        actions = []
        nodes = {(item.item, item.location): item for item in report.nodes}
        total_shortage = max(
            sum(item.shortage_units for item in report.nodes), 1.0
        )
        for item in report.recommendations:
            target = nodes.get((item.item, item.target_location))
            source = (
                nodes.get((item.item, item.source_location))
                if item.source_location is not None else None
            )
            unit_cost = (
                (target.unit_cost if target else None)
                or (source.unit_cost if source else None)
                or 1.0
            )
            if item.action == "transfer":
                estimated_cost = item.quantity * max(unit_cost * 0.05, 0.1)
                cost_basis = "Estimated transfer handling equals 5% of unit value, with a 0.1-unit floor."
                risk = "low"
                action_type = "inventory_transfer"
                title = f"Transfer {item.item} to {item.target_location}"
            else:
                estimated_cost = item.quantity * unit_cost
                cost_basis = "Estimated replenishment spend equals quantity × inferred unit cost."
                risk = "medium"
                action_type = "inventory_replenishment"
                title = f"Replenish {item.item} at {item.target_location}"
            impact_score = min(
                100.0,
                item.expected_shortage_reduction / total_shortage * 100,
            )
            actions.append(
                PrescriptiveAction(
                    action_id="",
                    title=title,
                    action_type=action_type,
                    objective="minimize_shortage",
                    source="inventory.recommendations",
                    target=f"{item.item}@{item.target_location}",
                    description=(
                        f"{item.action.title()} {item.quantity:g} unit(s) of {item.item} "
                        f"from {item.source_location or 'external supply'} to {item.target_location}."
                    ),
                    rationale=item.rationale,
                    expected_impact=round(item.expected_shortage_reduction, 2),
                    impact_unit="shortage units reduced",
                    impact_score=round(impact_score, 2),
                    estimated_cost=round(estimated_cost, 2),
                    cost_unit="estimated value",
                    cost_basis=cost_basis,
                    priority=item.priority,
                    risk=risk,
                    confidence=round(
                        min(0.99, report.detection.confidence * (0.95 if item.priority == "high" else 0.85)),
                        3,
                    ),
                    metadata=item.to_dict(),
                )
            )
        return actions

    def _select_actions(
        self,
        actions: list[PrescriptiveAction],
        *,
        budget: float | None,
        max_actions: int,
    ) -> tuple[list[PrescriptiveAction], str, list[str]]:
        if not actions or max_actions == 0:
            return [], "none", ["No eligible actions matched the constraints."]
        try:
            import numpy as np
            from scipy.optimize import Bounds, LinearConstraint, milp

            utilities = np.array(
                [float(item.optimization_score or 0.0) for item in actions]
            )
            constraints = [
                LinearConstraint(np.ones(len(actions)), -np.inf, max_actions)
            ]
            if budget is not None:
                costs = np.array([item.estimated_cost for item in actions])
                constraints.append(LinearConstraint(costs, -np.inf, budget))
            result = milp(
                c=-utilities,
                integrality=np.ones(len(actions)),
                bounds=Bounds(np.zeros(len(actions)), np.ones(len(actions))),
                constraints=constraints,
                options={"time_limit": 10.0},
            )
            if result.success and result.x is not None:
                selected = [
                    action for action, choice in zip(actions, result.x)
                    if choice >= 0.5
                ]
                return selected, "scipy_milp", [str(result.message)]
        except (ImportError, ValueError, RuntimeError) as error:
            fallback_note = f"MILP unavailable; deterministic greedy fallback used ({error})."
        else:
            fallback_note = "MILP did not return a feasible solution; deterministic greedy fallback used."

        ranked = sorted(
            actions,
            key=lambda item: (
                -float(item.optimization_score or 0.0) / max(item.estimated_cost, 0.01),
                -float(item.optimization_score or 0.0),
                item.action_id,
            ),
        )
        selected = []
        spent = 0.0
        for action in ranked:
            if len(selected) >= max_actions:
                break
            if budget is not None and spent + action.estimated_cost > budget:
                continue
            selected.append(action)
            spent += action.estimated_cost
        return selected, "deterministic_greedy", [fallback_note]

    def _utility(self, action: PrescriptiveAction, objective: str) -> float:
        compatibility = 1.0 if objective == "balanced" else (
            1.0 if action.objective == objective else 0.35
        )
        priority = {"low": 1.0, "medium": 1.1, "high": 1.25}[action.priority]
        risk_penalty = {"low": 1.0, "medium": 0.85, "high": 0.65}[action.risk]
        return round(
            action.impact_score * action.confidence * compatibility * priority * risk_penalty,
            4,
        )

    def _transition(
        self,
        plan: PrescriptivePlan,
        action_id: str,
        event: str,
        actor: str,
        reason: str | None,
    ) -> PrescriptiveAction:
        action = plan.get_action(action_id)
        allowed, new_status = self.STATUS_TRANSITIONS[event]
        if action.status not in allowed:
            expected = ", ".join(sorted(allowed))
            raise ValueError(
                f"Cannot {event} {action.action_id} while status is {action.status}; expected {expected}."
            )
        previous = action.status
        action.status = new_status
        plan.audit_trail.append(
            PrescriptionAuditEntry(
                event=event,
                action_id=action.action_id,
                previous_status=previous,
                new_status=new_status,
                actor=str(actor).strip() or "user",
                reason=reason,
            )
        )
        return action

    @staticmethod
    def _deduplicate(actions: list[PrescriptiveAction]) -> list[PrescriptiveAction]:
        output = []
        seen = set()
        for action in sorted(
            actions,
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}[item.priority],
                -item.impact_score,
                item.title.casefold(),
            ),
        ):
            key = (action.action_type, action.target.casefold())
            if key in seen:
                continue
            seen.add(key)
            output.append(action)
        return output

    @staticmethod
    def _baseline_metrics(operations_report, inventory_report) -> dict[str, float]:
        metrics = {}
        for report in (operations_report, inventory_report):
            if report is None:
                continue
            for item in report.kpis:
                if isinstance(item.value, bool) or not isinstance(item.value, (int, float)):
                    continue
                metrics[item.key] = round(float(item.value), 2)
        return metrics

    @staticmethod
    def _scale_metrics(
        metrics: dict[str, float],
        keys: tuple[str, ...],
        change: float,
        *,
        lower: float | None = None,
        upper: float | None = None,
    ) -> None:
        factor = 1 + float(change) / 100
        for key in keys:
            if key not in metrics:
                continue
            value = metrics[key] * factor
            if lower is not None:
                value = max(lower, value)
            if upper is not None:
                value = min(upper, value)
            metrics[key] = round(value, 2)
