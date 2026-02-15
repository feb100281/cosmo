# sales/reports/sales_report/summary.py

from datetime import date
from decimal import Decimal
from django.utils import timezone

from .formatters import fmt_money, fmt_int, fmt_pct
from .compare import build_compare
from .compare_chart import build_compare_delta_bar_svg
from .store_logos import attach_store_logos


def _to_decimal(x) -> Decimal:
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal("0")


def _median_decimal(values):
    if not values:
        return None

    vals = []
    for v in values:
        try:
            vals.append(_to_decimal(v))
        except Exception:
            continue

    if not vals:
        return None

    vals.sort()
    n = len(vals)
    mid = n // 2
    if n % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / Decimal("2")


def build_summary(
    kpi: dict,
    period_value: str,
    report_type: str,
    report_date: date,
    period_start: date,
    period_end: date,
    generated_dt=None,
) -> dict:
    as_of = generated_dt or timezone.now()

    if report_type == "daily":
        title = f"I. KPI за {period_start:%d.%m.%Y}"
    elif report_type == "weekly":
        title = f"I. KPI за неделю ({period_start:%d.%m.%Y} – {period_end:%d.%m.%Y})"
    else:
        title = f"I. KPI за {period_value}"

    compare = build_compare(report_type, period_start, period_end)
    compare_chart_svg_pct = build_compare_delta_bar_svg(compare)

    note = "Показатели рассчитаны по отгрузкам в периоде."

    # --- Разрез по типам заказов (общий) ---
    sales_by_type_raw = kpi.get("sales_by_type") or []
    sales_by_type = []
    for r in sales_by_type_raw:
        if not isinstance(r, dict):
            continue
        sales_by_type.append({
            "type": r.get("type") or "—",
            "orders": fmt_int(r.get("orders")),
            "amount": fmt_money(r.get("amount")),
        })

    # --- Магазины: ТОЛЬКО деньги (без заказов/типов) ---
    total_amount = _to_decimal(kpi.get("amount"))
    shops_raw = kpi.get("sales_by_shop") or []

    shops = []
    for r in shops_raw:
        if not isinstance(r, dict):
            continue

        shop_name = (r.get("shop") or "—").strip() or "—"
        amount_shop = _to_decimal(r.get("amount"))  # чистая выручка (dt-cr)
        cr_shop = _to_decimal(r.get("cr"))          # возвраты

        shops.append({
            "shop": shop_name,
            "amount": amount_shop,
            "cr": cr_shop,
        })

    shops.sort(key=lambda x: x["amount"], reverse=True)

    TOP_N = 26
    top_shops = shops[:TOP_N]

    sales_by_shop = []
    for s in top_shops:
        share = (s["amount"] / total_amount) if total_amount else None
        sales_by_shop.append({
            "shop": s["shop"],
            "amount": fmt_money(s["amount"]),
            "cr": fmt_money(s["cr"]),
            "share": fmt_pct(share) if share is not None else None,
        })

    sales_by_shop = attach_store_logos(sales_by_shop)

    # --- max_order ---
    max_order_raw = kpi.get("max_order")
    max_order = None
    if isinstance(max_order_raw, dict) and max_order_raw.get("amount") is not None:
        o_date = max_order_raw.get("date")
        max_order = {
            "order_id": str(max_order_raw.get("order_id")),
            "date": o_date.strftime("%d.%m.%Y") if hasattr(o_date, "strftime") else "—",
            "amount": fmt_money(max_order_raw.get("amount")),
        }

    # --- медианная отгрузка ---
    orders_net = kpi.get("orders_net") or []
    median_check_dec = _median_decimal(orders_net)
    median_check = fmt_money(median_check_dec) if median_check_dec is not None else None

    return {
        "title": title,
        "as_of": as_of,
        "report_date": report_date,
        "period_start": period_start,
        "period_end": period_end,

        "values": {
            "dt": fmt_money(kpi.get("dt")),
            "cr": fmt_money(kpi.get("cr")),
            "amount": fmt_money(kpi.get("amount")),
            "rtr_ratio": fmt_pct(kpi.get("rtr_ratio")),

            "orders": fmt_int(kpi.get("orders")),
            "ave_check": fmt_money(kpi.get("ave_check")),
            "median_check": median_check,

            "max_order": max_order,

            "sales_by_type": sales_by_type,
            "sales_by_shop": sales_by_shop,
        },

        "compare": compare,
        "compare_chart_svg_pct": compare_chart_svg_pct,
        "note": note,
    }

