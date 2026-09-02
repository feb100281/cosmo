# sales/reports/newspaper/analytics/cash_ytd.py
"""
Аналитический слой над данными YTD-кэша (data/cash.py:get_cash_ytd_data).

Тот же принцип, что и в analytics/cash.py для месяца: ничего не
пересчитывает из бизнес-логики sales_plan_report, только строит поверх
готовых накопительных цифр управленческие метрики — лидера/аутсайдера
года и статус "опережаем/отстаём от плана на сегодня".
"""

from __future__ import annotations

from decimal import Decimal

from ..config import CASH_STORE_LAG_ALERT_PCT


def _to_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def analyze_cash_ytd(ytd_data: dict) -> dict:
    totals = ytd_data["totals"]
    rows = ytd_data["rows"]

    exec_pct = _to_float(totals["exec_pct"])
    is_behind = totals["plan_to_date"] > 0 and exec_pct < 100
    is_ahead = totals["plan_to_date"] > 0 and exec_pct >= 100

    plan_rows = [r for r in rows if r["has_plan"] and r["plan_to_date"] > 0]

    worst_store = None
    best_store = None
    if plan_rows:
        worst_store = min(plan_rows, key=lambda r: _to_float(r["exec_pct"]))
        best_store = max(plan_rows, key=lambda r: _to_float(r["exec_pct"]))

    lagging_stores = [
        r for r in plan_rows
        if _to_float(r["exec_pct"]) < exec_pct - CASH_STORE_LAG_ALERT_PCT
    ]
    lagging_stores.sort(key=lambda r: _to_float(r["exec_pct"]))

    yoy_pct = _to_float(totals["yoy_pct"])
    has_yoy_base = totals["prev_year_fact"] > 0

    return {
        "is_behind_pace": is_behind,
        "is_ahead_pace": is_ahead,
        "worst_store": worst_store,
        "best_store": best_store,
        "lagging_stores": lagging_stores,
        "is_on_track": totals["is_on_track"],
        "has_yoy_base": has_yoy_base,
        "is_yoy_positive": has_yoy_base and yoy_pct >= 0,
    }
