"""Legacy-code-derived daily Norm controls, not the importer/approval workflow.

Source: ProcessSeasonality.sql; CollectPhaseOutData.sql; CollectPhaseInData.sql.
Mixed control precedence and unsupported lifecycle state fail closed.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext
from mta.domain.models import EffectiveNorm, SkuLocation
from mta.domain.validation import RuleBlocked, ZERO, ceiling, day, floor, identity, number, percent


@dataclass(frozen=True)
class ManualNorm:
    event_id: str
    effective_from: date
    value: Decimal
    kind: str  # ACCEPTED or FORCED: already approved, selected event, not a suggestion


@dataclass(frozen=True)
class Seasonality:
    event_id: str
    start: date
    end: date
    original_norm: Decimal
    target_norm: Decimal
    buildup_days: int
    rlt_days: int
    direction: str
    # Explicitly validated target. Out-of-cap input is blocked, never guessed/clamped.
    cap: Decimal
    # Exact EndDate is an update hole in recovered SQL and retains this row state.
    previous_new_norm: Decimal | None = None


@dataclass(frozen=True)
class PhaseOut:
    event_id: str
    started_on: date
    stock: Decimal
    git: Decimal
    pack_size: Decimal
    original_norm: Decimal
    previous_new_norm: Decimal
    # EXISTING/DIRECT_NEW rows precede the completion scan; CASCADE_NEW follows it.
    activation_kind: str = "EXISTING"
    parent_completed_on: date | None = None
    is_top_node: bool = True


@dataclass(frozen=True)
class OldSkuNorm:
    sku_code: str
    original_norm: Decimal
    effective_norm: EffectiveNorm  # resolved phase-out or explicit unchanged master


@dataclass(frozen=True)
class PhaseIn:
    event_id: str
    started_on: date
    old_skus: tuple[OldSkuNorm, ...]
    target_norm: Decimal | None
    start_percent: Decimal
    # Legacy gate retains prior NewNorm when no new candidate qualifies.
    previous_new_norm: Decimal


def seasonal_norm(control: Seasonality, business_date: date) -> tuple[Decimal, str]:
    day(business_date); day(control.start); day(control.end); identity(control.event_id)
    original = number(control.original_norm, "original Norm", integer=True)
    target = number(control.target_norm, "target Norm", integer=True)
    cap = number(control.cap, "season cap", integer=True)
    if type(control.buildup_days) is not int or type(control.rlt_days) is not int:
        raise ValueError("Integral buildup/RLT days required")
    if control.buildup_days < 0 or control.rlt_days < 0 or control.end <= control.start:
        raise ValueError("Invalid seasonal date/duration")
    higher = control.direction == "HIGHER"
    if control.direction not in {"HIGHER", "LOWER"}:
        raise ValueError("Season direction must be HIGHER or LOWER")
    if (higher and target < original) or (not higher and target > original):
        raise ValueError("Target disagrees with season direction")
    if (higher and max(original, target) > cap) or (not higher and min(original, target) < cap):
        raise RuleBlocked("DIV-008", "Out-of-cap explicit seasonal target needs validation-path decision")
    if not higher and (control.rlt_days > control.buildup_days or (control.end-control.start).days < control.buildup_days):
        raise ValueError("Legacy lower-season duration/RLT validation failed")
    if higher and control.rlt_days > control.buildup_days:
        raise RuleBlocked("DIV-009", "Higher-season RLT exceeds buildup; validation entry-path decision required")
    if business_date == control.end:
        if control.previous_new_norm is None:
            raise RuleBlocked("SEA-END-DATE", "Legacy exact EndDate retains prior row state; coherent prior-state replay required")
        return number(control.previous_new_norm, "previous seasonal Norm", integer=True), "END_DATE_RETAINED"
    if business_date > control.end:
        return original, "SEASON_END"
    with localcontext() as ctx:
        ctx.prec = 50
        duration = Decimal(max(control.buildup_days - control.rlt_days, 1))
        if higher:
            begins = control.start - timedelta(days=control.buildup_days)
            target_day = control.start - timedelta(days=control.rlt_days)
            if business_date < begins:
                return original, "NOT_STARTED"
            if business_date <= target_day:
                elapsed = Decimal((business_date - begins).days)
                return original + ceiling(elapsed * (target-original) / duration), "NORM_SETTING"
            if business_date < control.start:
                return target, "NORM_SET_PRE_SEASON"
            if business_date <= max(control.end-timedelta(days=control.rlt_days), control.start):
                return target, "SEASON"
            return original, "NORM_RESET_PRE_SEASON_END"
        if business_date < control.start-timedelta(days=control.rlt_days):
            return original, "NOT_STARTED"
        if business_date < control.start:
            return target, "NORM_SET_PRE_SEASON"  # legacy step, not spec's gradual decline
        if business_date <= control.end-timedelta(days=control.buildup_days):
            return target, "SEASON"
        if business_date <= control.end-timedelta(days=control.rlt_days):
            elapsed = Decimal(control.buildup_days - (control.end-business_date).days)
            return target + ceiling(elapsed*(original-target)/duration), "NORM_RESET"
        return original, "NORM_RESET_PRE_SEASON_END"


def resolve_effective_norm(sku_location: SkuLocation, business_date: date,
                           controls: tuple[ManualNorm | Seasonality | PhaseOut | PhaseIn, ...] = ()) -> EffectiveNorm:
    day(business_date); identity(sku_location.sku_code); identity(sku_location.location_code)
    base = number(sku_location.base_norm, "base Norm", integer=True)
    active = []
    for control in controls:
        identity(control.event_id)
        if isinstance(control, Seasonality):
            # Keep the same source control through reset; future season not active yet.
            seasonal_norm(control, business_date)  # validate even a future record
            begins = control.start-timedelta(days=control.buildup_days if control.direction == "HIGHER" else control.rlt_days)
            if begins <= business_date:
                active.append(control)
        elif isinstance(control, (ManualNorm, PhaseOut, PhaseIn)):
            starts = control.effective_from if isinstance(control, ManualNorm) else control.started_on
            day(starts)
            if starts <= business_date:
                active.append(control)
        else:
            raise RuleBlocked("UNKNOWN_NORM_CONTROL", "Unsupported control input")
    if len({c.event_id for c in controls}) != len(controls):
        raise ValueError("Duplicate Norm control event")
    if len(active) > 1:
        if any(isinstance(c, Seasonality) for c in active) and any(isinstance(c, (PhaseIn, PhaseOut)) for c in active):
            # CollectPhaseOutData.sql removes Phase-In/Phase-Out candidates while
            # Seasonality is active.  The seasonal row therefore owns today's
            # effective Norm; phase processing remains excluded for that day.
            active = [c for c in active if isinstance(c, Seasonality)]
        if len(active) > 1:
            raise RuleBlocked("NORM_PRECEDENCE", "Multiple active controls require explicit source-state/precedence evidence")
    value, basis, event_ids = base, "BASE_NORM", ()
    if active:
        control = active[0]
        event_ids = (control.event_id,)
        if isinstance(control, ManualNorm):
            if control.kind not in {"ACCEPTED", "FORCED"}:
                raise RuleBlocked("MANUAL_NORM_KIND", "Only approved accepted/forced Norm changes are mapped")
            value, basis = number(control.value, "manual Norm", integer=True), control.kind
        elif isinstance(control, Seasonality):
            value, status = seasonal_norm(control, business_date)
            basis = "SEASONALITY_" + status
        elif isinstance(control, PhaseOut):
            number(control.original_norm, "phase original", integer=True)
            previous = number(control.previous_new_norm, "previous phase-out Norm", integer=True)
            if control.activation_kind not in {'EXISTING','DIRECT_NEW','CASCADE_NEW'}:
                raise RuleBlocked('PHASE_ACTIVATION', 'Mapped phase-out activation state required')
            if control.activation_kind != 'EXISTING' and control.started_on != business_date:
                raise ValueError('New phase activation must match business date')
            if type(control.is_top_node) is not bool:
                raise ValueError("Explicit phase topology required")
            if control.activation_kind == 'CASCADE_NEW':
                if control.is_top_node or control.parent_completed_on is None or day(control.parent_completed_on) != business_date:
                    raise RuleBlocked("PHASE_PARENT_NOT_COMPLETE", "Child cannot begin before immediate parent completion")
            economic = number(control.stock, "phase stock", integer=True) + number(control.git, "phase GIT", integer=True)
            pack = number(control.pack_size, "phase pack", integer=True, positive=True)
            finished = economic < pack and control.activation_kind != 'CASCADE_NEW'
            value = ZERO if finished else min(previous,economic)
            basis = "PHASE_OUT_FINISHED" if finished else "PHASE_OUT"
        else:
            if not control.old_skus or len({o.sku_code for o in control.old_skus}) != len(control.old_skus):
                raise ValueError("Unique, nonempty old-SKU closure required")
            total_original = total_current = ZERO
            for old in control.old_skus:
                identity(old.sku_code)
                resolved = old.effective_norm
                if (resolved.sku_code, resolved.location_code, resolved.business_date) != (old.sku_code, sku_location.location_code, business_date):
                    raise ValueError("Phase old-SKU state must match SKU/location/business date")
                total_original += number(old.original_norm, "phase original", integer=True)
                total_current += number(resolved.value, "phase current", integer=True)
            target = total_original if control.target_norm is None else number(control.target_norm, "phase target", integer=True)
            previous = number(control.previous_new_norm, "previous phase Norm", integer=True)
            with localcontext() as ctx:
                ctx.prec = 50
                gate = floor(total_original * (100-percent(control.start_percent)) / 100)
            if total_current > gate:
                value, basis = previous, "PHASE_IN_HELD_BY_GATE"
            else:
                value, basis = max(target-total_current, ZERO), "PHASE_IN"
    return EffectiveNorm(sku_location.sku_code, sku_location.location_code, business_date,
                         number(value, "resolved Norm", integer=True), basis, event_ids)
