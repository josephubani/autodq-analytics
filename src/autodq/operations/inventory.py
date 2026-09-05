from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from autodq.operations.inventory_models import (
    EchelonSummary,
    InventoryColumnMap,
    InventoryDetection,
    InventoryKPI,
    InventoryNode,
    InventoryRecommendation,
    InventoryReport,
)


class MultiEchelonInventoryEngine:
    """Analyze inventory position across products, locations, and echelons."""

    ROLE_ALIASES = {
        "item": (
            "sku", "item_id", "product_id", "material_id", "part_number",
            "item", "product", "material", "part", "stock_code",
        ),
        "location": (
            "location_id", "warehouse_id", "facility_id", "store_id",
            "site_id", "node_id", "location", "warehouse", "facility",
            "distribution_center", "dc", "store", "site", "plant", "branch",
        ),
        "echelon": (
            "echelon", "echelon_level", "network_level", "supply_tier",
            "tier", "level", "node_type", "facility_type", "location_type",
        ),
        "parent_location": (
            "parent_location", "parent_node", "upstream_location",
            "source_location", "supplying_location", "supplier_node",
            "parent_warehouse", "parent_id",
        ),
        "time": (
            "snapshot_date", "snapshot_time", "as_of_date", "inventory_date",
            "recorded_at", "updated_at", "timestamp", "date",
        ),
        "on_hand": (
            "on_hand", "inventory_on_hand", "stock_on_hand", "qty_on_hand",
            "quantity_on_hand", "current_stock", "available_stock",
            "available_quantity", "inventory", "stock",
        ),
        "on_order": (
            "on_order", "quantity_on_order", "qty_on_order", "open_orders",
            "inbound_quantity", "incoming_stock", "scheduled_receipts",
        ),
        "backorder": (
            "backorders", "backorder", "backordered_quantity",
            "backorder_quantity", "unfulfilled_demand", "short_orders",
        ),
        "demand": (
            "daily_demand", "demand_rate", "average_daily_demand",
            "forecast_daily_demand", "forecast_demand", "demand",
            "consumption_rate", "usage_rate", "sales_rate",
        ),
        "lead_time": (
            "lead_time_days", "replenishment_lead_time", "supplier_lead_time",
            "lead_time", "delivery_lead_time", "transit_days",
        ),
        "safety_stock": (
            "safety_stock", "buffer_stock", "reserve_stock", "minimum_stock",
            "min_stock", "safety_inventory",
        ),
        "unit_cost": (
            "unit_cost", "cost_per_unit", "inventory_unit_cost",
            "purchase_cost", "standard_cost", "item_cost",
        ),
        "capacity": (
            "storage_capacity", "inventory_capacity", "max_inventory",
            "maximum_stock", "capacity", "max_capacity",
        ),
    }
    REQUIRED_ROLES = ("item", "location", "on_hand", "demand")
    NUMERIC_ROLES = {
        "on_hand", "on_order", "backorder", "demand", "lead_time",
        "safety_stock", "unit_cost", "capacity",
    }

    def analyze(
        self,
        df: pd.DataFrame,
        *,
        dataset_name: str = "current",
        item_column: str | None = None,
        location_column: str | None = None,
        echelon_column: str | None = None,
        parent_location_column: str | None = None,
        time_column: str | None = None,
        on_hand_column: str | None = None,
        on_order_column: str | None = None,
        backorder_column: str | None = None,
        demand_column: str | None = None,
        lead_time_column: str | None = None,
        safety_stock_column: str | None = None,
        unit_cost_column: str | None = None,
        capacity_column: str | None = None,
        service_level: float = 0.95,
        horizon_days: int = 30,
        top: int = 10,
    ) -> InventoryReport:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Inventory analytics requires a pandas DataFrame.")
        if df.empty:
            raise ValueError("Inventory analytics requires at least one row.")
        service_level = self._service_level(service_level)
        if not isinstance(horizon_days, int) or isinstance(horizon_days, bool):
            raise ValueError("Inventory horizon must be a whole number of days.")
        if horizon_days < 1 or horizon_days > 3650:
            raise ValueError("Inventory horizon must be between 1 and 3,650 days.")
        if not isinstance(top, int) or isinstance(top, bool) or not 1 <= top <= 100:
            raise ValueError("Inventory TOP must be between 1 and 100.")

        overrides = {
            "item": item_column,
            "location": location_column,
            "echelon": echelon_column,
            "parent_location": parent_location_column,
            "time": time_column,
            "on_hand": on_hand_column,
            "on_order": on_order_column,
            "backorder": backorder_column,
            "demand": demand_column,
            "lead_time": lead_time_column,
            "safety_stock": safety_stock_column,
            "unit_cost": unit_cost_column,
            "capacity": capacity_column,
        }
        columns = self._infer_columns(df, overrides)
        detection = self._detect(df, columns)
        snapshot, snapshot_at = self._latest_snapshot(df, columns)

        if not detection.is_inventory:
            return InventoryReport(
                dataset_name=dataset_name,
                rows_analyzed=len(df),
                snapshot_rows=len(snapshot),
                snapshot_at=snapshot_at,
                detection=detection,
                service_level=service_level,
                horizon_days=horizon_days,
                top=top,
            )

        nodes = self._build_nodes(
            snapshot,
            columns=columns,
            horizon_days=horizon_days,
        )
        echelons = self._build_echelons(nodes)
        recommendations = self._build_recommendations(nodes, top=top)
        kpis = self._build_kpis(
            nodes,
            recommendations,
            service_level=service_level,
        )
        return InventoryReport(
            dataset_name=dataset_name,
            rows_analyzed=len(df),
            snapshot_rows=len(snapshot),
            snapshot_at=snapshot_at,
            detection=detection,
            service_level=service_level,
            horizon_days=horizon_days,
            kpis=kpis,
            nodes=nodes,
            echelons=echelons,
            recommendations=recommendations,
            top=top,
        )

    def _infer_columns(
        self,
        df: pd.DataFrame,
        overrides: dict[str, str | None],
    ) -> InventoryColumnMap:
        resolved: dict[str, str | None] = {}
        used: set[str] = set()
        role_order = (
            "item", "location", "echelon", "parent_location", "time",
            "on_hand", "on_order", "backorder", "demand", "lead_time",
            "safety_stock", "unit_cost", "capacity",
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
        return InventoryColumnMap(**resolved)

    def _detect(
        self,
        df: pd.DataFrame,
        columns: InventoryColumnMap,
    ) -> InventoryDetection:
        mapping = columns.to_dict()
        weights = {
            "item": 0.20,
            "location": 0.15,
            "on_hand": 0.25,
            "demand": 0.20,
            "echelon": 0.08,
            "parent_location": 0.04,
            "time": 0.02,
            "lead_time": 0.03,
            "safety_stock": 0.01,
            "on_order": 0.01,
            "backorder": 0.01,
        }
        confidence = round(sum(weights.get(role, 0) for role, value in mapping.items() if value), 3)
        missing = [role for role in self.REQUIRED_ROLES if not mapping[role]]
        is_inventory = not missing
        echelon_count = (
            int(df[columns.echelon].nunique(dropna=True))
            if columns.echelon else 1
        )
        is_multi = bool(columns.echelon and echelon_count > 1)
        dataset_type = (
            "multi_echelon_inventory"
            if is_multi else "single_echelon_inventory"
            if is_inventory else "inventory_candidate"
        )
        evidence = [
            f"{role.replace('_', ' ').title()} recognized: {value}."
            for role, value in mapping.items()
            if value
        ]
        warnings: list[str] = []
        if missing:
            warnings.append(
                "Inventory management requires ITEM, LOCATION, ON_HAND, and "
                "DEMAND roles. Missing: "
                + ", ".join(role.upper() for role in missing)
                + "."
            )
        if is_inventory and not columns.echelon:
            warnings.append(
                "No ECHELON column was found; the network is treated as one level."
            )
        if is_inventory and not columns.parent_location:
            warnings.append(
                "No PARENT location was found; transfers prefer the same echelon "
                "but network routing must be validated operationally."
            )
        if is_inventory and not columns.lead_time:
            warnings.append(
                "No LEAD_TIME column was found; reorder points use zero lead-time days."
            )
        if is_inventory and not columns.safety_stock:
            warnings.append(
                "No SAFETY_STOCK column was found; supplied safety stock defaults to zero."
            )
        if is_inventory and not columns.time:
            warnings.append(
                "No snapshot TIME was found; all rows are treated as the current snapshot."
            )
        return InventoryDetection(
            dataset_type=dataset_type,
            confidence=min(confidence, 1.0),
            is_inventory=is_inventory,
            is_multi_echelon=is_multi,
            columns=columns,
            evidence=evidence,
            warnings=warnings,
        )

    def _latest_snapshot(
        self,
        df: pd.DataFrame,
        columns: InventoryColumnMap,
    ) -> tuple[pd.DataFrame, str | None]:
        snapshot = df.copy()
        if not columns.time:
            return snapshot, None
        timestamps = pd.to_datetime(snapshot[columns.time], errors="coerce")
        if not timestamps.notna().any():
            return snapshot, None
        if not columns.item or not columns.location:
            return snapshot, timestamps.max().isoformat()
        snapshot = snapshot.assign(_autodq_inventory_time=timestamps)
        keys = [columns.item, columns.location]
        if columns.echelon:
            keys.append(columns.echelon)
        snapshot = (
            snapshot.sort_values("_autodq_inventory_time")
            .drop_duplicates(subset=keys, keep="last")
            .drop(columns="_autodq_inventory_time")
        )
        return snapshot, timestamps.max().isoformat()

    def _build_nodes(
        self,
        df: pd.DataFrame,
        *,
        columns: InventoryColumnMap,
        horizon_days: int,
    ) -> list[InventoryNode]:
        keys = [columns.item, columns.location]
        if columns.echelon:
            keys.append(columns.echelon)
        nodes: list[InventoryNode] = []
        group_key: Any = keys[0] if len(keys) == 1 else keys
        grouped = df.groupby(group_key, dropna=False, sort=False)
        for raw_key, group in grouped:
            values = raw_key if isinstance(raw_key, tuple) else (raw_key,)
            item = self._label(values[0])
            location = self._label(values[1])
            echelon = self._label(values[2]) if columns.echelon else "Network"
            parent = self._mode(group[columns.parent_location]) if columns.parent_location else None
            on_hand = self._sum(group, columns.on_hand)
            on_order = self._sum(group, columns.on_order)
            backorders = self._sum(group, columns.backorder)
            demand = max(self._sum(group, columns.demand), 0.0)
            lead_time = max(self._mean(group, columns.lead_time), 0.0)
            safety_stock = max(self._sum(group, columns.safety_stock), 0.0)
            unit_cost = self._optional_mean(group, columns.unit_cost)
            capacity = self._optional_sum(group, columns.capacity)

            inventory_position = on_hand + on_order - backorders
            reorder_point = demand * lead_time + safety_stock
            target_stock = reorder_point + demand * horizon_days
            shortage = max(target_stock - inventory_position, 0.0)
            excess = max(inventory_position - target_stock, 0.0)
            coverage = max(inventory_position, 0.0) / demand if demand > 0 else None
            risk = (
                max(0.0, min(100.0, (reorder_point - max(inventory_position, 0.0)) / reorder_point * 100))
                if reorder_point > 0 else 0.0
            )
            value = on_hand * unit_cost if unit_cost is not None else None
            utilization = (
                on_hand / capacity * 100 if capacity is not None and capacity > 0 else None
            )
            if demand > 0 and (inventory_position <= 0 or risk >= 50):
                status = "critical"
            elif risk > 0 or shortage > 0:
                status = "warning"
            elif excess > 0:
                status = "excess"
            else:
                status = "balanced"
            nodes.append(
                InventoryNode(
                    item=item,
                    location=location,
                    echelon=echelon,
                    parent_location=parent,
                    on_hand=self._round(on_hand),
                    on_order=self._round(on_order),
                    backorders=self._round(backorders),
                    inventory_position=self._round(inventory_position),
                    daily_demand=self._round(demand),
                    lead_time_days=self._round(lead_time),
                    safety_stock=self._round(safety_stock),
                    reorder_point=self._round(reorder_point),
                    target_stock=self._round(target_stock),
                    coverage_days=self._round(coverage) if coverage is not None else None,
                    shortage_units=self._round(shortage),
                    excess_units=self._round(excess),
                    stockout_risk_percent=self._round(risk),
                    unit_cost=self._round(unit_cost) if unit_cost is not None else None,
                    inventory_value=self._round(value) if value is not None else None,
                    capacity=self._round(capacity) if capacity is not None else None,
                    capacity_utilization=self._round(utilization) if utilization is not None else None,
                    status=status,
                )
            )
        status_order = {"critical": 0, "warning": 1, "excess": 2, "balanced": 3}
        return sorted(
            nodes,
            key=lambda item: (
                status_order[item.status],
                -item.stockout_risk_percent,
                -item.shortage_units,
                item.item.casefold(),
                item.location.casefold(),
            ),
        )

    def _build_echelons(self, nodes: list[InventoryNode]) -> list[EchelonSummary]:
        grouped: dict[str, list[InventoryNode]] = defaultdict(list)
        for node in nodes:
            grouped[node.echelon].append(node)
        summaries = []
        for echelon, items in grouped.items():
            values = [item.inventory_value for item in items if item.inventory_value is not None]
            summaries.append(
                EchelonSummary(
                    echelon=echelon,
                    node_count=len(items),
                    item_count=len({item.item for item in items}),
                    location_count=len({item.location for item in items}),
                    on_hand=self._round(sum(item.on_hand for item in items)),
                    inventory_position=self._round(sum(item.inventory_position for item in items)),
                    daily_demand=self._round(sum(item.daily_demand for item in items)),
                    shortage_units=self._round(sum(item.shortage_units for item in items)),
                    excess_units=self._round(sum(item.excess_units for item in items)),
                    at_risk_nodes=sum(item.status in {"critical", "warning"} for item in items),
                    inventory_value=self._round(sum(values)) if values else None,
                )
            )
        return sorted(summaries, key=lambda item: (-item.at_risk_nodes, item.echelon.casefold()))

    def _build_recommendations(
        self,
        nodes: list[InventoryNode],
        *,
        top: int,
    ) -> list[InventoryRecommendation]:
        by_item: dict[str, list[InventoryNode]] = defaultdict(list)
        for node in nodes:
            by_item[node.item].append(node)
        recommendations: list[InventoryRecommendation] = []
        for item, item_nodes in by_item.items():
            donors = [node for node in item_nodes if node.excess_units > 0]
            recipients = [node for node in item_nodes if node.shortage_units > 0]
            available = {id(node): node.excess_units for node in donors}
            recipients.sort(
                key=lambda node: (
                    node.status != "critical",
                    -node.stockout_risk_percent,
                    -node.shortage_units,
                )
            )
            for recipient in recipients:
                remaining = recipient.shortage_units
                ranked_donors = sorted(
                    donors,
                    key=lambda donor: self._transfer_rank(donor, recipient),
                )
                for donor in ranked_donors:
                    quantity = min(available[id(donor)], remaining)
                    if quantity <= 0:
                        continue
                    quantity = self._round(quantity)
                    recommendations.append(
                        InventoryRecommendation(
                            action="transfer",
                            item=item,
                            source_location=donor.location,
                            target_location=recipient.location,
                            source_echelon=donor.echelon,
                            target_echelon=recipient.echelon,
                            quantity=quantity,
                            priority="high" if recipient.status == "critical" else "medium",
                            expected_shortage_reduction=quantity,
                            rationale=self._transfer_rationale(donor, recipient),
                        )
                    )
                    available[id(donor)] = self._round(available[id(donor)] - quantity)
                    remaining = self._round(remaining - quantity)
                    if remaining <= 0:
                        break
                if remaining > 0:
                    recommendations.append(
                        InventoryRecommendation(
                            action="replenish",
                            item=item,
                            source_location=None,
                            target_location=recipient.location,
                            source_echelon=None,
                            target_echelon=recipient.echelon,
                            quantity=remaining,
                            priority="high" if recipient.status == "critical" else "medium",
                            expected_shortage_reduction=remaining,
                            rationale=(
                                f"No same-SKU network excess remains for the {recipient.location} "
                                f"target through the {recipient.lead_time_days:g}-day lead time and "
                                f"planning horizon."
                            ),
                        )
                    )
        priority = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            recommendations,
            key=lambda item: (
                priority[item.priority],
                item.action != "transfer",
                -item.quantity,
                item.item.casefold(),
            ),
        )[:top]

    def _build_kpis(
        self,
        nodes: list[InventoryNode],
        recommendations: list[InventoryRecommendation],
        *,
        service_level: float,
    ) -> list[InventoryKPI]:
        if not nodes:
            return []
        risk_nodes = [item for item in nodes if item.status in {"critical", "warning"}]
        values = [item.inventory_value for item in nodes if item.inventory_value is not None]
        coverage = [item.coverage_days for item in nodes if item.coverage_days is not None]
        reorder_total = sum(item.reorder_point for item in nodes)
        immediate_gap = sum(
            max(item.reorder_point - max(item.inventory_position, 0.0), 0.0)
            for item in nodes
        )
        readiness = 100.0 if reorder_total <= 0 else max(0.0, 100 * (1 - immediate_gap / reorder_total))
        transfer_units = sum(
            item.quantity for item in recommendations if item.action == "transfer"
        )
        replenish_units = sum(
            item.quantity for item in recommendations if item.action == "replenish"
        )
        return [
            self._kpi("network_nodes", "Inventory nodes", len(nodes), "nodes", "neutral", "Distinct SKU-location-echelon positions."),
            self._kpi("total_on_hand", "Total on-hand inventory", self._round(sum(item.on_hand for item in nodes)), "units", "neutral", "Physical units currently on hand."),
            self._kpi("inventory_position", "Network inventory position", self._round(sum(item.inventory_position for item in nodes)), "units", "neutral", "On hand plus on order minus backorders."),
            self._kpi("service_readiness", "Lead-time service readiness", self._round(readiness), "%", "good" if readiness >= service_level * 100 else "warning" if readiness >= max(service_level * 100 - 15, 0) else "critical", f"Share of aggregate reorder-point demand covered, assessed against the {service_level * 100:g}% service target."),
            self._kpi("at_risk_nodes", "At-risk inventory nodes", len(risk_nodes), "nodes", "good" if not risk_nodes else "critical", "Nodes below their planning target or reorder-point requirement."),
            self._kpi("shortage_units", "Planning shortage", self._round(sum(item.shortage_units for item in nodes)), "units", "critical" if any(item.shortage_units > 0 for item in nodes) else "good", "Units required to cover lead time, safety stock, and the planning horizon."),
            self._kpi("excess_units", "Transferable excess", self._round(sum(item.excess_units for item in nodes)), "units", "warning" if any(item.excess_units > 0 for item in nodes) else "good", "Inventory above the calculated planning target."),
            self._kpi("median_coverage", "Median inventory coverage", self._round(float(np.median(coverage))) if coverage else None, "days", "neutral", "Median days of demand covered by network inventory position."),
            self._kpi("recommended_transfers", "Recommended internal transfers", self._round(transfer_units), "units", "neutral", "Same-SKU excess that can be rebalanced inside the network."),
            self._kpi("recommended_replenishment", "Recommended replenishment", self._round(replenish_units), "units", "warning" if replenish_units > 0 else "good", "Residual shortage requiring external or upstream supply."),
            self._kpi("inventory_value", "On-hand inventory value", self._round(sum(values)) if values else None, "value", "neutral", "On-hand quantity multiplied by unit cost where available."),
        ]

    @classmethod
    def _best_column(
        cls,
        df: pd.DataFrame,
        role: str,
        *,
        exclude: set[str],
    ) -> str | None:
        normalized = {column: cls._normalize(column) for column in df.columns}
        aliases = cls.ROLE_ALIASES[role]
        for alias in aliases:
            for column, name in normalized.items():
                if column not in exclude and name == alias:
                    return column
        for alias in aliases:
            for column, name in normalized.items():
                if column not in exclude and re.search(rf"(?:^|_){re.escape(alias)}(?:_|$)", name):
                    return column
        return None

    @staticmethod
    def _resolve_column(df: pd.DataFrame, value: str) -> str:
        lookup = {str(column).casefold(): column for column in df.columns}
        column = lookup.get(str(value).strip().casefold())
        if column is None:
            raise ValueError(f"Inventory column does not exist: {value}")
        return column

    @staticmethod
    def _normalize(value: Any) -> str:
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value).strip())
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

    @staticmethod
    def _service_level(value: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("Inventory SERVICE_LEVEL must be numeric.") from error
        if 1 < parsed <= 100:
            parsed /= 100
        if not 0 < parsed <= 1:
            raise ValueError("Inventory service level must be between 0 and 1, or 1 and 100 percent.")
        return parsed

    @staticmethod
    def _numeric(group: pd.DataFrame, column: str | None) -> pd.Series:
        if not column:
            return pd.Series(dtype=float)
        return pd.to_numeric(group[column], errors="coerce").replace([np.inf, -np.inf], np.nan)

    @classmethod
    def _sum(cls, group: pd.DataFrame, column: str | None) -> float:
        values = cls._numeric(group, column)
        return float(values.fillna(0).sum()) if not values.empty else 0.0

    @classmethod
    def _mean(cls, group: pd.DataFrame, column: str | None) -> float:
        values = cls._numeric(group, column).dropna()
        return float(values.mean()) if not values.empty else 0.0

    @classmethod
    def _optional_sum(cls, group: pd.DataFrame, column: str | None) -> float | None:
        if not column:
            return None
        values = cls._numeric(group, column).dropna()
        return float(values.sum()) if not values.empty else None

    @classmethod
    def _optional_mean(cls, group: pd.DataFrame, column: str | None) -> float | None:
        if not column:
            return None
        values = cls._numeric(group, column).dropna()
        return float(values.mean()) if not values.empty else None

    @staticmethod
    def _mode(values: pd.Series) -> str | None:
        valid = values.dropna().astype(str)
        if valid.empty:
            return None
        mode = valid.mode()
        return str(mode.iloc[0]) if not mode.empty else str(valid.iloc[0])

    @staticmethod
    def _label(value: Any) -> str:
        if pd.isna(value):
            return "(missing)"
        return str(value)

    @staticmethod
    def _round(value: float) -> float:
        return round(float(value), 4)

    @staticmethod
    def _transfer_rank(donor: InventoryNode, recipient: InventoryNode) -> tuple[Any, ...]:
        parent_match = recipient.parent_location is not None and recipient.parent_location.casefold() == donor.location.casefold()
        same_echelon = donor.echelon.casefold() == recipient.echelon.casefold()
        return (not parent_match, not same_echelon, -donor.excess_units, donor.location.casefold())

    @staticmethod
    def _transfer_rationale(donor: InventoryNode, recipient: InventoryNode) -> str:
        if recipient.parent_location and recipient.parent_location.casefold() == donor.location.casefold():
            return "The supplying parent has same-SKU excess while the child location is below target."
        if donor.echelon.casefold() == recipient.echelon.casefold():
            return "A same-echelon location has same-SKU excess available for lateral rebalancing."
        return "Same-SKU excess exists elsewhere in the network; validate cross-echelon routing before execution."

    @staticmethod
    def _kpi(
        key: str,
        name: str,
        value: Any,
        unit: str,
        status: str,
        description: str,
    ) -> InventoryKPI:
        return InventoryKPI(
            key=key,
            name=name,
            value=value,
            unit=unit,
            status=status,
            description=description,
        )
