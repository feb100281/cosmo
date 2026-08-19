# sales/reports/newspaper/analytics/cash.py
"""
Аналитический слой над данными кэша.

Ничего не пересчитывает из бизнес-логики sales_plan_report — берёт уже
готовые план/факт/прогноз по компании и магазинам и строит поверх них
управленческие метрики: темп выполнения плана относительно календаря месяца,
отстающие магазины, лидеры.
"""

from __future__ import annotations

from decimal import Decimal

from ..config import CASH_PACE_LAG_ALERT_PCT, CASH_STORE_LAG_ALERT_PCT


def _to_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def analyze_cash(cash_data: dict) -> dict:
    totals = cash_data["totals"]
    rows = cash_data["rows"]

    days_in_month = cash_data["days_in_month"]
    days_passed = cash_data["days_passed"]

    expected_pace_pct = (
        (days_passed / days_in_month) * 100.0 if days_in_month else 0.0
    )

    exec_pct = _to_float(totals["exec_pct"])
    pace_gap_pp = exec_pct - expected_pace_pct
    is_behind_pace = pace_gap_pp < -CASH_PACE_LAG_ALERT_PCT

    plan_rows = [r for r in rows if r["has_plan"]]

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

    return {
        "expected_pace_pct": expected_pace_pct,
        "expected_pace_pct_fmt": f"{expected_pace_pct:.0f}%",
        "pace_gap_pp": pace_gap_pp,
        "is_behind_pace": is_behind_pace,
        "is_ahead_pace": pace_gap_pp > CASH_PACE_LAG_ALERT_PCT,
        "worst_store": worst_store,
        "best_store": best_store,
        "lagging_stores": lagging_stores,
        "is_on_track": totals["is_on_track"],
    }
