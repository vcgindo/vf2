from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Mapping
from uuid import UUID


class MtaRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class MtaStageName(StrEnum):
    VALIDATE_INPUT = "validate_input"
    PREPARE_MASTER_STATE = "prepare_master_state"
    RESOLVE_EFFECTIVE_NORM = "resolve_effective_norm"
    CALCULATE_REQUIREMENT = "calculate_requirement"
    RESOLVE_VIRTUAL_NORM_AND_DISPATCH = "resolve_virtual_norm_and_dispatch"
    RATION = "ration"
    PACK_AND_RESIDUAL_ALLOCATION = "pack_and_residual_allocation"
    PUBLISH_RRR = "publish_rrr"
    CALCULATE_BOR = "calculate_bor"
    CALCULATE_BOR_OA = "calculate_bor_oa"
    EVALUATE_DBM = "evaluate_dbm"
    BUILD_BUFFER_TREND = "build_buffer_trend"
    BUILD_PICK_LIST = "build_pick_list"
    OUTPUT_FINALIZATION = "output_finalization"
    BUILD_REPORTS = "build_reports"
    AUDIT_AND_COMMIT = "audit_and_commit"


@dataclass(frozen=True, slots=True)
class MtaRun:
    run_id: UUID
    business_date: date
    site_code: str
    configuration_version: str
    input_snapshot_id: str
    status: MtaRunStatus = MtaRunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_stage: MtaStageName | None = None


@dataclass(frozen=True, slots=True)
class Sku:
    sku_code: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class Location:
    location_code: str
    location_type: str | None = None


@dataclass(frozen=True, slots=True)
class SkuLocation:
    sku_code: str
    location_code: str
    base_norm: Decimal
    replenishment_lead_time_days: int | None = None
    pack_size: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ParentChildRelationship:
    sku_code: str
    child_location_code: str
    parent_location_code: str
    effective_from: date
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class InventoryPosition:
    sku_code: str
    location_code: str
    business_date: date
    stock: Decimal
    goods_in_transit: Decimal


@dataclass(frozen=True, slots=True)
class NormControlEvent:
    control_type: str
    effective_from: date
    value: Decimal
    source_event_id: str


@dataclass(frozen=True, slots=True)
class EffectiveNormInput:
    sku_location: SkuLocation
    business_date: date
    controls: tuple[NormControlEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class EffectiveNorm:
    sku_code: str
    location_code: str
    business_date: date
    value: Decimal
    basis: str
    applied_control_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RequirementInput:
    effective_norm: EffectiveNorm
    inventory_position: InventoryPosition


@dataclass(frozen=True, slots=True)
class Requirement:
    sku_code: str
    location_code: str
    business_date: date
    effective_norm: Decimal
    stock: Decimal
    goods_in_transit: Decimal
    available_inventory: Decimal
    requirement_quantity: Decimal
    rule_ids: tuple[str, ...]
    metadata: Mapping[str, str] = field(default_factory=dict)
