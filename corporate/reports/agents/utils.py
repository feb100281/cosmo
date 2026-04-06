# corporate/reports/agents/utils.py
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

NBSP = "\u00A0"


def _d(x: Any) -> Decimal:
    try:
        return Decimal(str(x or "0"))
    except Exception:
        return Decimal("0")


def _quant0(v: Decimal) -> Decimal:
    return v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def fmt_money_ru(v: Decimal) -> str:
    """
    12,3 млн ₽
    450 тыс ₽
    12 345 ₽
    """
    vq = _quant0(v)
    a = abs(vq)

    if a >= Decimal("1000000"):
        s = (vq / Decimal("1000000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{str(s).replace('.', ',')}{NBSP}млн{NBSP}₽"

    if a >= Decimal("1000"):
        s = (vq / Decimal("1000")).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP)
        txt = f"{int(s):,}".replace(",", " ")
        return f"{txt}{NBSP}тыс{NBSP}₽"

    txt = f"{int(vq):,}".replace(",", " ")
    return f"{txt}{NBSP}₽"


def fmt_int(v: int) -> str:
    return f"{int(v):,}".replace(",", " ")