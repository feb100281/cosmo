# # sales/reports/sales_report/kpi/kpi_block.py
# from __future__ import annotations

# from datetime import date
# from decimal import Decimal
# from typing import Any, Dict, List

# from .kpi_data import build_kpi_for_range
# from .kpi_compare import build_compare
# from ..store_logos import attach_store_logos
# from ..formatters import fmt_money, fmt_int, fmt_pct

# from ..trends.trend_block import build_trends_context
# from .categories_period_data import get_categories_for_period
# from .categories_period_chart import build_categories_pareto_svg
# from .manufacturers_period_data import get_manufacturers_for_period
# from .manufacturers_period_chart import build_manufacturers_pareto_svg


# def _to_decimal(x) -> Decimal:
#     try:
#         return Decimal(str(x or 0))
#     except Exception:
#         return Decimal("0")


# def build_kpi_context(
#     report_type: str,
#     report_date: date,
#     period_start: date,
#     period_end: date,
#     trend_points: int = 12,
# ) -> Dict[str, Any]:

#     kpi_raw = build_kpi_for_range(period_start, period_end)
#     # --- категории за период (Pareto + таблица) ---
#     cat_df = get_categories_for_period(period_start, period_end)

#     categories_pareto_svg = build_categories_pareto_svg(
#         cat_df,
#         title=f"Категории: чистая выручка за период ({period_start:%d.%m.%Y}–{period_end:%d.%m.%Y})",
#         top_n=7,
#     )

#     categories_table = []
#     if cat_df is not None and not cat_df.empty:
#         tmp = cat_df.sort_values("amount", ascending=False).copy()
#         total_amount = float(tmp["amount"].sum()) or 0.0
#         top = tmp.head(10).copy()

#         for _, r in top.iterrows():
#             share = (float(r["amount"]) / total_amount) if total_amount else 0.0
#             categories_table.append({
#                 "cat": str(r["cat_name"]),
#                 "amount": fmt_money(r["amount"]),
#                 "share": fmt_pct(share * 100),
#             })
    
    
#     # --- производители за период (Pareto + таблица) ---
#     mf_df = get_manufacturers_for_period(period_start, period_end)

#     manufacturers_pareto_svg = build_manufacturers_pareto_svg(
#         mf_df,
#         title=f"Производители: чистая выручка за период ({period_start:%d.%m.%Y}–{period_end:%d.%m.%Y})",
#         top_n=7,
#     )

#     manufacturers_table = []
#     if mf_df is not None and not mf_df.empty:
#         tmp = mf_df.sort_values("amount", ascending=False).copy()
#         total_amount = float(tmp["amount"].sum()) or 0.0
#         top = tmp.head(10).copy()

#         for _, r in top.iterrows():
#             share = (float(r["amount"]) / total_amount) if total_amount else 0.0
#             manufacturers_table.append({
#                 "manufacturer": str(r["manufacturer_name"] or "Производитель не указан"),
#                 "amount": fmt_money(r["amount"]),
#                 "share": fmt_pct(share * 100),
#             })


#     # --- карточки ---
#     cards = {
#         "dt": fmt_money(kpi_raw.get("dt")),
#         "cr": fmt_money(kpi_raw.get("cr")),
#         "amount": fmt_money(kpi_raw.get("amount")),
#         "amount_services": fmt_money(kpi_raw.get("amount_services")),
#         "rtr_ratio": fmt_pct(kpi_raw.get("rtr_ratio")),
#     }

#     # --- магазины (форматируем + доля + логотипы) ---
#     total_amount_dec = _to_decimal(kpi_raw.get("amount"))
 

#     shops_tmp: List[Dict[str, Any]] = []
#     for r in (kpi_raw.get("sales_by_shop") or []):
#         shop_name = (r.get("shop") or "—").strip() or "—"
#         amount_dec = _to_decimal(r.get("amount"))
#         cr_dec = _to_decimal(r.get("cr"))
#         dt_dec = _to_decimal(r.get("dt"))


#         share = (amount_dec / total_amount_dec) if total_amount_dec else None

#         shops_tmp.append({
#             "shop": shop_name,
#             "amount_raw": amount_dec,  # для сортировки (не выводим)
#             "turnover": fmt_money(dt_dec), 
#             "amount": fmt_money(amount_dec),
#             "cr": fmt_money(cr_dec),
#             "share": fmt_pct(share) if share is not None else "—",
            
#         })

#     # сортировка по выручке
#     shops_tmp.sort(key=lambda x: x["amount_raw"], reverse=True)

#     # логотипы 
#     sales_by_shop = attach_store_logos(shops_tmp)

#     # чистим служебное поле
#     for s in sales_by_shop:
#         s.pop("amount_raw", None)

#     # --- типы заказов (форматируем) ---
#     # ВАЖНО: этот блок отработает только если kpi_raw реально возвращает sales_by_type
#     # sales_by_type: List[Dict[str, Any]] = []
#     # for r in (kpi_raw.get("sales_by_type") or []):
#     #     sales_by_type.append({
#     #         "type": r.get("type"),
#     #         "orders": fmt_int(r.get("orders")),
#     #         "dt": fmt_money(r.get("dt")),
#     #         "cr": fmt_money(r.get("cr")),
#     #         "amount": fmt_money(r.get("amount")),
#     #     })

#     # --- контрольные точки ---
#     # max_order = kpi_raw.get("max_order")
#     # if max_order:
#     #     max_order = {
#     #         "amount": fmt_money(max_order.get("amount")),
#     #         "date": max_order.get("date"),
#     #         "client_order_number": max_order.get("client_order_number"),
#     #     }

#     # медиана по net заказов
#     # orders_net = kpi_raw.get("orders_net") or []
#     # median_check = None
#     # if orders_net:
#     #     srt = sorted([float(x) for x in orders_net])
#     #     n = len(srt)
#     #     if n % 2 == 1:
#     #         median = srt[n // 2]
#     #     else:
#     #         median = (srt[n // 2 - 1] + srt[n // 2]) / 2
#     #     median_check = fmt_money(median)

#     # --- compare ---
#     compare = build_compare(report_type, period_start, period_end)

#     trends_ctx = build_trends_context(report_type, report_date, points=trend_points)


#     return {
#         "period_start": period_start,
#         "period_end": period_end,

#         "kpi_raw": kpi_raw,

#         "cards": cards,
#         "sales_by_shop": sales_by_shop,
#         # "sales_by_type": sales_by_type,

#         # "max_order": max_order,
#         # "median_check": median_check,
        
#         "categories_pareto_svg": categories_pareto_svg,
#         "categories_table": categories_table,
#         "manufacturers_pareto_svg": manufacturers_pareto_svg,
#         "manufacturers_table": manufacturers_table,

#         "compare": compare,
#         **trends_ctx,
#     }




# sales/reports/sales_report/kpi/kpi_block.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from dateutil.relativedelta import relativedelta  # ✅ add

from .kpi_data import build_kpi_for_range
from .kpi_compare import build_compare
from ..store_logos import attach_store_logos
from ..formatters import fmt_money, fmt_int, fmt_pct

from ..trends.trend_block import build_trends_context
from .categories_period_data import get_categories_for_period
from .categories_period_chart import build_categories_pareto_svg
from .manufacturers_period_data import get_manufacturers_for_period
from .manufacturers_period_chart import build_manufacturers_pareto_svg


def _to_decimal(x) -> Decimal:
    try:
        return Decimal(str(x or 0))
    except Exception:
        return Decimal("0")


def _safe_ratio(num: Decimal, den: Decimal) -> Decimal | None:
    if den is None:
        return None
    try:
        den_d = _to_decimal(den)
        if den_d == 0:
            return None
        return _to_decimal(num) / den_d
    except Exception:
        return None


def _pct_delta(curr: Decimal, base: Decimal) -> Decimal | None:
    """
    Возвращает долю (0..1), а форматирование делает fmt_pct.
    """
    try:
        c = _to_decimal(curr)
        b = _to_decimal(base)
        if b == 0:
            return None
        return (c - b) / b
    except Exception:
        return None


def build_kpi_context(
    report_type: str,
    report_date: date,
    period_start: date,
    period_end: date,
    trend_points: int = 12,
) -> Dict[str, Any]:

    # --- KPI за период (обычно день) ---
    kpi_raw = build_kpi_for_range(period_start, period_end)

    # --- MTD / YTD (накопленные итоги) ---
    # MTD: с 1-го числа месяца до даты отчета (включительно)
    mtd_start = report_date.replace(day=1)
    mtd_end = report_date

    # YTD: с 1 января до даты отчета (включительно)
    ytd_start = report_date.replace(month=1, day=1)
    ytd_end = report_date

    # LY периоды (аналогичные)
    mtd_start_ly = mtd_start - relativedelta(years=1)
    mtd_end_ly = mtd_end - relativedelta(years=1)

    ytd_start_ly = ytd_start - relativedelta(years=1)
    ytd_end_ly = ytd_end - relativedelta(years=1)

    mtd = build_kpi_for_range(mtd_start, mtd_end)
    ytd = build_kpi_for_range(ytd_start, ytd_end)

    mtd_ly = build_kpi_for_range(mtd_start_ly, mtd_end_ly)
    ytd_ly = build_kpi_for_range(ytd_start_ly, ytd_end_ly)

    # ВАЖНО: показываем на карточках именно ЧИСТУЮ ВЫРУЧКУ (amount),
    # потому что возвраты уже "внутри" net-логики.
    mtd_amount = _to_decimal(mtd.get("amount"))
    ytd_amount = _to_decimal(ytd.get("amount"))
    mtd_amount_ly = _to_decimal(mtd_ly.get("amount"))
    ytd_amount_ly = _to_decimal(ytd_ly.get("amount"))

    mtd_delta = _pct_delta(mtd_amount, mtd_amount_ly)  # доля (0..1)
    ytd_delta = _pct_delta(ytd_amount, ytd_amount_ly)  # доля (0..1)

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
            share = (float(r["amount"]) / total_amount) if total_amount else 0.0  # 0..1
            categories_table.append({
                "cat": str(r["cat_name"]),
                "amount": fmt_money(r["amount"]),
                "share": fmt_pct(share),  # ✅ доля 0..1
            })

    # --- производители за период (Pareto + таблица) ---
    mf_df = get_manufacturers_for_period(period_start, period_end)
    manufacturers_pareto_svg = build_manufacturers_pareto_svg(
        mf_df,
        title=f"Производители: чистая выручка за период ({period_start:%d.%m.%Y}–{period_end:%d.%m.%Y})",
        top_n=10,
    )

    manufacturers_table = []
    if mf_df is not None and not mf_df.empty:
        tmp = mf_df.sort_values("amount", ascending=False).copy()
        total_amount = float(tmp["amount"].sum()) or 0.0
        top = tmp.head(10).copy()
        for _, r in top.iterrows():
            share = (float(r["amount"]) / total_amount) if total_amount else 0.0  # 0..1
            manufacturers_table.append({
                "manufacturer": str(r["manufacturer_name"] or "Производитель не указан"),
                "amount": fmt_money(r["amount"]),
                "share": fmt_pct(share),  # ✅ доля 0..1
            })

    # --- карточки ДНЯ ---
    dt_d = _to_decimal(kpi_raw.get("dt"))
    cr_d = _to_decimal(kpi_raw.get("cr"))
    amount_d = _to_decimal(kpi_raw.get("amount"))
    services_d = _to_decimal(kpi_raw.get("amount_services"))

    rtr_ratio = _safe_ratio(cr_d, dt_d)  # возвраты / оборот
    services_share = _safe_ratio(services_d, amount_d)  # услуги / чистая выручка

    cards = {
        "dt": fmt_money(dt_d),
        "cr": fmt_money(cr_d),
        "amount": fmt_money(amount_d),
        "amount_services": fmt_money(services_d),
        "services_share": fmt_pct(services_share) if services_share is not None else "—",
        "rtr_ratio": fmt_pct(rtr_ratio) if rtr_ratio is not None else "—",
        "rtr_caption": "от оборота",  # 👈 подпись под 6,2%
    }

    # --- накопленные итоги (2 карточки) ---
    accum_cards = {
        "mtd": {
            "title": "MTD",
            "subtitle": f"{mtd_start:%d.%m.%Y}–{mtd_end:%d.%m.%Y}",
            "amount": fmt_money(mtd_amount),
            "delta_ly": fmt_pct(mtd_delta) if mtd_delta is not None else "—",
            "delta_is_positive": (mtd_delta is not None and mtd_delta >= 0),
        },
        "ytd": {
            "title": "YTD",
            "subtitle": f"{ytd_start:%d.%m.%Y}–{ytd_end:%d.%m.%Y}",
            "amount": fmt_money(ytd_amount),
            "delta_ly": fmt_pct(ytd_delta) if ytd_delta is not None else "—",
            "delta_is_positive": (ytd_delta is not None and ytd_delta >= 0),
        },
    }

    # --- магазины (форматируем + доля + логотипы) ---
    total_amount_dec = amount_d
    shops_tmp: List[Dict[str, Any]] = []
    for r in (kpi_raw.get("sales_by_shop") or []):
        shop_name = (r.get("shop") or "—").strip() or "—"
        amount_dec = _to_decimal(r.get("amount"))
        cr_dec = _to_decimal(r.get("cr"))
        dt_dec = _to_decimal(r.get("dt"))
        share = _safe_ratio(amount_dec, total_amount_dec)  # 0..1

        shops_tmp.append({
            "shop": shop_name,
            "amount_raw": amount_dec,
            "turnover": fmt_money(dt_dec),
            "amount": fmt_money(amount_dec),
            "cr": fmt_money(cr_dec),
            "share": fmt_pct(share) if share is not None else "—",
        })

    shops_tmp.sort(key=lambda x: x["amount_raw"], reverse=True)
    sales_by_shop = attach_store_logos(shops_tmp)
    for s in sales_by_shop:
        s.pop("amount_raw", None)

    compare = build_compare(report_type, period_start, period_end)
    trends_ctx = build_trends_context(report_type, report_date, points=trend_points)

    return {
        "period_start": period_start,
        "period_end": period_end,

        "kpi_raw": kpi_raw,
        "cards": cards,
        "accum_cards": accum_cards,  # ✅ new

        "sales_by_shop": sales_by_shop,

        "categories_pareto_svg": categories_pareto_svg,
        "categories_table": categories_table,
        "manufacturers_pareto_svg": manufacturers_pareto_svg,
        "manufacturers_table": manufacturers_table,

        "compare": compare,
        **trends_ctx,
    }