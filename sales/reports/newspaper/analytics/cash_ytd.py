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


def _build_monthly_rows(monthly: list) -> list:
    """
    Отклонение план/факт по каждому месяцу с начала года — для таблицы под
    помесячным графиком (charts.cash_ytd.build_cash_ytd_monthly_chart).
    Текущий (ещё не закончившийся) месяц не судим: сравнивать факт за
    неполный месяц с планом на весь месяц несправедливо, поэтому для него
    diff/diff_pct не считаем вовсе (is_judged=False).
    """
    rows = []
    for m in monthly:
        plan_v = m.get("plan") or Decimal("0")
        fact_v = m.get("fact") or Decimal("0")
        has_plan = plan_v > 0
        is_judged = has_plan and not m["is_current"]

        diff = (fact_v - plan_v) if is_judged else None
        diff_pct = (safe_div_pct(fact_v, plan_v) - Decimal("100")) if is_judged else None

        rows.append({
            "month_name": m["month_name"],
            "is_current": m["is_current"],
            "has_plan": has_plan,
            "is_judged": is_judged,
            "plan": plan_v,
            "fact": fact_v,
            "diff": diff,
            "diff_pct": diff_pct,
            "is_ahead": bool(is_judged and diff is not None and diff >= 0),
        })
    return rows


def safe_div_pct(fact, plan) -> Decimal:
    if not plan:
        return Decimal("0")
    return (fact / plan) * Decimal("100")


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

    # Разница факта и плана на сегодня в рублях (сколько не довыполнили —
    # или на сколько опередили план). Считается всегда от "плана на
    # сегодня" (plan_to_date), а не от годового плана — это то же
    # накопительное сравнение, что и exec_pct, просто в рублях, а не в %.
    has_plan_to_date = totals["plan_to_date"] > 0
    diff_to_date = (totals["fact"] - totals["plan_to_date"]) if has_plan_to_date else Decimal("0")

    return {
        "is_behind_pace": is_behind,
        "is_ahead_pace": is_ahead,
        "worst_store": worst_store,
        "best_store": best_store,
        "lagging_stores": lagging_stores,
        "is_on_track": totals["is_on_track"],
        "has_yoy_base": has_yoy_base,
        "is_yoy_positive": has_yoy_base and yoy_pct >= 0,
        "has_plan_to_date": has_plan_to_date,
        "diff_to_date": diff_to_date,
        "is_behind_amount": diff_to_date < 0,
        # План на год может быть неполным (заведён не на весь год) — см.
        # data.get_cash_ytd_data. Пока это так, годовые метрики (% от
        # годового плана, прогноз-vs-годовой план) показывать нельзя.
        "plan_year_complete": bool(totals.get("plan_year_complete", False)),
        "monthly_rows": _build_monthly_rows(ytd_data["monthly"]),
    }
