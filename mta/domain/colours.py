"""CalculatePenetrationAndColor.sql uses decimal(22,2) BEFORE band comparisons."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext
from mta.domain.validation import ZERO, number
from mta.domain.virtual_norm import VirtualNorm


@dataclass(frozen=True)
class Colour:
    penetration: Decimal
    band: str


def colour(norm: Decimal, inventory: Decimal, blue_requirement: Decimal) -> Colour:
    n = number(norm, "colour Norm", integer=True)
    stock = number(inventory, "colour inventory", integer=True)
    blue = number(blue_requirement, "colour Blue requirement", integer=True)
    with localcontext() as ctx:
        ctx.prec = 50
        penetration = (100 * (n-stock)/n).quantize(Decimal(".01"), rounding=ROUND_HALF_UP) if n else Decimal("-99999999.00")
        penetration = max(penetration, Decimal("-99999999.00"))
    if penetration >= 100:
        band = "BLACK"
    elif penetration >= Decimal("66.67"):
        band = "RED"
    elif penetration >= Decimal("33.33"):
        band = "YELLOW"
    elif penetration >= 0:
        band = "GREEN"
    else:
        band = "BLUE" if blue > 0 and stock <= n + blue else "WHITE"
        if n == 0 and stock == 0:
            band = "GREY"
    return Colour(penetration, band)


def all_colours(norm: Decimal, stock: Decimal, git: Decimal, virtual: VirtualNorm) -> dict[str, Colour]:
    stock = number(stock, "physical stock", integer=True)
    git = number(git, "physical GIT", integer=True)
    # A direct virtual node has no physical inventory of its own.
    if virtual.kind == "DIRECT" and (stock != ZERO or git != ZERO):
        raise ValueError("Direct virtual node inventory must be zero")
    return {"technical": colour(norm, stock, virtual.blue_requirement),
            "economic": colour(norm, stock + git, virtual.blue_requirement),
            "dispatch": colour(virtual.value, stock + git, virtual.dispatch_blue_band)}
