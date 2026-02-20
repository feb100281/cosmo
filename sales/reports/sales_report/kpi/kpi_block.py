# sales/reports/sales_report/kpi/kpi_block.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from .kpi_data import build_kpi_for_range
from .kpi_compare import build_compare
from ..store_logos import attach_store_logos
from ..formatters import fmt_money, fmt_int, fmt_pct

from ..trends.trend_block import build_trends_context
from .categories_period_data import get_categories_for_period
from .categories_period_chart import build_categories_pareto_svg


def _to_decimal(x) -> Decimal:
    try:
        return Decimal(str(x or 0))
    except Exception:
        return Decimal("0")


def build_kpi_context(
    report_type: str,
    report_date: date,
    period_start: date,
    period_end: date,
    trend_points: int = 12,
) -> Dict[str, Any]:

    kpi_raw = build_kpi_for_range(period_start, period_end)
    # --- категории за период (Pareto + таблица) ---
    cat_df = get_categories_for_period(period_start, period_end)

    categories_pareto_svg = build_categories_pareto_svg(
        cat_df,
        title=f"Категории: чистая выручка за период ({period_start:%d.%m.%Y}–{period_end:%d.%m.%Y})",
        top_n=10,
    )

    categories_table = []
    if cat_df is not None and not cat_df.empty:
        tmp = cat_df.sort_values("amount", ascending=False).copy()
        total_amount = float(tmp["amount"].sum()) or 0.0
        top = tmp.head(10).copy()

        for _, r in top.iterrows():
            share = (float(r["amount"]) / total_amount) if total_amount else 0.0
            categories_table.append({
                "cat": str(r["cat_name"]),
                "amount": fmt_money(r["amount"]),
                "share": fmt_pct(share * 100),
            })


    # --- карточки ---
    cards = {
        "dt": fmt_money(kpi_raw.get("dt")),
        "cr": fmt_money(kpi_raw.get("cr")),
        "amount": fmt_money(kpi_raw.get("amount")),
        "amount_services": fmt_money(kpi_raw.get("amount_services")),
        "rtr_ratio": fmt_pct(kpi_raw.get("rtr_ratio")),
    }

    # --- магазины (форматируем + доля + логотипы) ---
    total_amount_dec = _to_decimal(kpi_raw.get("amount"))
 

    shops_tmp: List[Dict[str, Any]] = []
    for r in (kpi_raw.get("sales_by_shop") or []):
        shop_name = (r.get("shop") or "—").strip() or "—"
        amount_dec = _to_decimal(r.get("amount"))
        cr_dec = _to_decimal(r.get("cr"))
        dt_dec = _to_decimal(r.get("dt"))


        share = (amount_dec / total_amount_dec) if total_amount_dec else None

        shops_tmp.append({
            "shop": shop_name,
            "amount_raw": amount_dec,  # для сортировки (не выводим)
            "turnover": fmt_money(dt_dec), 
            "amount": fmt_money(amount_dec),
            "cr": fmt_money(cr_dec),
            "share": fmt_pct(share) if share is not None else "—",
            
        })

    # сортировка по выручке
    shops_tmp.sort(key=lambda x: x["amount_raw"], reverse=True)

    # логотипы 
    sales_by_shop = attach_store_logos(shops_tmp)

    # чистим служебное поле
    for s in sales_by_shop:
        s.pop("amount_raw", None)

    # --- типы заказов (форматируем) ---
    # ВАЖНО: этот блок отработает только если kpi_raw реально возвращает sales_by_type
    # sales_by_type: List[Dict[str, Any]] = []
    # for r in (kpi_raw.get("sales_by_type") or []):
    #     sales_by_type.append({
    #         "type": r.get("type"),
    #         "orders": fmt_int(r.get("orders")),
    #         "dt": fmt_money(r.get("dt")),
    #         "cr": fmt_money(r.get("cr")),
    #         "amount": fmt_money(r.get("amount")),
    #     })

    # --- контрольные точки ---
    # max_order = kpi_raw.get("max_order")
    # if max_order:
    #     max_order = {
    #         "amount": fmt_money(max_order.get("amount")),
    #         "date": max_order.get("date"),
    #         "client_order_number": max_order.get("client_order_number"),
    #     }

    # медиана по net заказов
    # orders_net = kpi_raw.get("orders_net") or []
    # median_check = None
    # if orders_net:
    #     srt = sorted([float(x) for x in orders_net])
    #     n = len(srt)
    #     if n % 2 == 1:
    #         median = srt[n // 2]
    #     else:
    #         median = (srt[n // 2 - 1] + srt[n // 2]) / 2
    #     median_check = fmt_money(median)

    # --- compare ---
    compare = build_compare(report_type, period_start, period_end)

    trends_ctx = build_trends_context(report_type, report_date, points=trend_points)


    return {
        "period_start": period_start,
        "period_end": period_end,

        "kpi_raw": kpi_raw,

        "cards": cards,
        "sales_by_shop": sales_by_shop,
        # "sales_by_type": sales_by_type,

        # "max_order": max_order,
        # "median_check": median_check,
        
        "categories_pareto_svg": categories_pareto_svg,
        "categories_table": categories_table,

        "compare": compare,
        **trends_ctx,
    }
