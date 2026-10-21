"""ConsolidateReq.sql: physical, zero-Norm, direct virtual and top-node targets."""
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from mta.domain.validation import ZERO, ceiling, floor, number


def average_positive_norm(norms: tuple[Decimal, ...]) -> Decimal:
    values = [number(n, "peer Norm", integer=True) for n in norms]
    positive = [n for n in values if n > 0]
    with localcontext() as ctx:
        ctx.prec = 50
        return ceiling(sum(positive, ZERO) / len(positive)) if positive else ZERO


@dataclass(frozen=True)
class _PeerNormGroup:
    """Local derived average, bound by identity to its immutable source tuple."""
    norms: tuple[Decimal, ...]
    _average: Decimal | None = field(default=None, init=False, repr=False, compare=False)

    def average(self, norms):
        if self.norms is not norms:
            raise ValueError('Peer average does not belong to these Norms')
        if self._average is None:
            object.__setattr__(self, '_average', average_positive_norm(norms))
        return self._average


@dataclass(frozen=True)
class VirtualNorm:
    value: Decimal
    additional_demand: Decimal
    blue_requirement: Decimal
    dispatch_blue_band: Decimal
    kind: str


def resolve_virtual_norm(norm: Decimal, additional: Decimal, *, kind: str,
                         peer_norms: tuple[Decimal, ...] = (),
                         parent_pack_size: Decimal = Decimal(1),
                         _peer_group=None) -> VirtualNorm:
    n = number(norm, "Effective Norm", integer=True)
    additional = number(additional, "eligible additional demand", integer=True)
    pack = number(parent_pack_size, "parent pack", integer=True, positive=True)
    if kind not in {"CHILD", "TOP", "DIRECT"}:
        raise ValueError("Unknown Virtual Norm topology")
    with localcontext() as ctx:
        ctx.prec = 50
        if kind == "DIRECT" or (kind == "CHILD" and n == 0):
            if kind == "DIRECT" and n != 0:
                raise ValueError("Direct virtual node has zero base Norm")
            if _peer_group is None:
                average = average_positive_norm(peer_norms)
            elif type(_peer_group) is _PeerNormGroup:
                average = _peer_group.average(peer_norms)
            else:
                raise ValueError('Owned peer Norm group required')
            value = min(average, additional) if average > 0 else additional
        else:
            value = n + additional if kind == "TOP" else min(2 * n, n + additional)
        # Legacy expands BlueReq for the last case pack, separately from Virtual Norm.
        # SQL's literal 2/3.0 has scale 6: .666666 (not exact 2/3).
        # Direct virtual nodes are created AFTER this physical-node adjustment.
        pack_blue = max(floor(Decimal('.666666') * value) + pack - (n + additional), ZERO) if value > 0 and kind != 'DIRECT' else ZERO
        blue = additional + pack_blue
        band = blue - (value - n)
    number(value, "Virtual Norm", integer=True); number(blue, "Blue requirement", integer=True)
    return VirtualNorm(value, additional, blue, band, kind)
