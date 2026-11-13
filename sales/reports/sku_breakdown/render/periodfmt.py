# sales/reports/sku_breakdown/render/periodfmt.py
"""Короткая запись периода для заголовков и текста."""
from __future__ import annotations

from datetime import date


def rng(s: date, e: date) -> str:
    if s == e:
        return f"{s:%d.%m.%Y}"
    if s.year == e.year:
        return f"{s:%d.%m}–{e:%d.%m.%Y}"
    return f"{s:%d.%m.%Y}–{e:%d.%m.%Y}"
