# sales/reports/sales_report/stores/store_sales.py
from __future__ import annotations

from datetime import date

from django.db.models import Sum, F, Value, DecimalField, Count, Q
from django.db.models.functions import Coalesce

from sales.models import SalesData


def get_store_sales_for_range(start: date, end: date) -> list[dict]:
    """
    Возвращает список строк по магазинам за период:
    - оборот (dt)
    - возвраты (cr)
    - чистая выручка (amount = dt - cr)
    - кол-во товаров (quant = quant_dt - quant_cr)
    - заказы (orders = distinct client_order_number)
    - средний чек (ave_check = amount / orders)
    - доля возвратов (rtr_ratio = cr / dt)
    """
    qs = (
        SalesData.objects
        .filter(date__range=(start, end), store__isnull=False)
        .values("store_id", "store__name")
        .annotate(
            dt=Coalesce(Sum("dt"), Value(0), output_field=DecimalField()),
            cr=Coalesce(Sum("cr"), Value(0), output_field=DecimalField()),
            quant_dt=Coalesce(Sum("quant_dt"), Value(0), output_field=DecimalField()),
            quant_cr=Coalesce(Sum("quant_cr"), Value(0), output_field=DecimalField()),
            # ✅ заказы: уникальные номера заказов (игнорируем пустые)
            orders=Count("client_order_number", distinct=True, filter=Q(client_order_number__isnull=False) & ~Q(client_order_number="")),
        )
        .annotate(
            amount=F("dt") - F("cr"),
            quant=F("quant_dt") - F("quant_cr"),
        )
        .order_by("-amount")
    )

    rows: list[dict] = []
    for r in qs:
        dt = r["dt"] or 0
        cr = r["cr"] or 0
        amount = r["amount"] or 0
        orders = r["orders"] or 0

        rtr_ratio = (cr / dt) if dt else None
        ave_check = (amount / orders) if orders else None

        rows.append({
            "store_id": r["store_id"],
            "store": r["store__name"],
            "dt": r["dt"],
            "cr": r["cr"],
            "amount": r["amount"],
            "quant": r["quant"],
            "orders": orders,
            "ave_check": ave_check,
            "rtr_ratio": rtr_ratio,
        })

    return rows
