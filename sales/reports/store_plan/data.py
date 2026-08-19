# sales/reports/store_plan/data.py
"""
Данные для печати плана продаж на месяц.

Модель ``StoreSalesPlan`` (sales/models.py) не меняется — здесь только
чтение уже занесённых в неё планов и подготовка к печати: без модели
не считаем ничего нового (ни прогнозов, ни аналитики), просто показываем
план по месяцу либо по одному магазину, либо по всем сразу.
"""

from __future__ import annotations

import calendar
from decimal import Decimal

from sales.models import StoreSalesPlan
from sales.reports.sales_plan_report.utils import fmt_money

from .config import _MONTHS_RU


def get_store_plan_payload(plan_month, store_ids=None) -> dict:
    """
    plan_month — дата первого числа месяца (как хранится в StoreSalesPlan).
    store_ids — если задано, печатаем план только по этим магазинам
    (используется для печати по одному магазину); если None — печатаем
    план по всем магазинам, у которых есть план на этот месяц.
    """
    qs = (
        StoreSalesPlan.objects
        .filter(plan_month=plan_month)
        .select_related("store", "store__gr")
        .order_by("-amount")
    )
    if store_ids:
        qs = qs.filter(store_id__in=store_ids)

    rows = []
    total = Decimal("0")
    for plan in qs:
        store = plan.store
        amount = plan.amount or Decimal("0")
        group_name = store.gr.name if store and store.gr_id else "—"
        rows.append({
            "store_name": store.name if store else "—",
            "group_name": group_name,
            "amount": amount,
            "amount_fmt": fmt_money(amount),
        })
        total += amount

    stores_count = len(rows)

    # Доля магазина от общего плана (по выбранной выборке магазинов) — при
    # печати одного магазина доля всегда 100%, это ожидаемо.
    for row in rows:
        share_pct = (row["amount"] / total * 100) if total else Decimal("0")
        row["share_pct_fmt"] = f"{share_pct:.0f}%"

    # Средний дневной план — общий план сети (или выбранных магазинов),
    # разложенный на календарные дни месяца. Не "план на магазин" — тот
    # мало что говорит при разных по размеру магазинах, а дневной план
    # напрямую сравним с фактом сбора кэша день в день.
    days_in_month = calendar.monthrange(plan_month.year, plan_month.month)[1]
    average_daily = (total / days_in_month) if days_in_month else Decimal("0")

    return {
        "plan_month": plan_month,
        "month_year_fmt": f"{_MONTHS_RU[plan_month.month - 1]}, {plan_month.year}",
        "rows": rows,
        "stores_count": stores_count,
        "total": total,
        "total_fmt": fmt_money(total),
        "days_in_month": days_in_month,
        "average_daily_fmt": fmt_money(average_daily),
        "is_single": stores_count == 1,
    }
