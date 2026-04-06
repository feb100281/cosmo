from __future__ import annotations

from datetime import date
import pandas as pd
from dateutil.relativedelta import relativedelta

from django.db.models import Sum, F, Value, DecimalField, Count, Q
from django.db.models.functions import Coalesce, TruncMonth

from sales.models import SalesData


def _store_sales_qs(start: date, end: date):
    return (
        SalesData.objects
        .filter(date__range=(start, end), store__isnull=False)
        .values("store_id", "store__name")
        .annotate(
            dt=Coalesce(Sum("dt"), Value(0), output_field=DecimalField()),
            cr=Coalesce(Sum("cr"), Value(0), output_field=DecimalField()),
            quant_dt=Coalesce(Sum("quant_dt"), Value(0), output_field=DecimalField()),
            quant_cr=Coalesce(Sum("quant_cr"), Value(0), output_field=DecimalField()),
            orders=Count(
                "client_order_number",
                distinct=True,
                filter=Q(client_order_number__isnull=False) & ~Q(client_order_number="")
            ),
        )
        .annotate(
            amount=F("dt") - F("cr"),
            quant=F("quant_dt") - F("quant_cr"),
        )
        .order_by("-amount")
    )


def get_store_sales_df(start: date, end: date) -> pd.DataFrame:
    qs = _store_sales_qs(start, end)
    rows = list(qs)
    if not rows:
        return pd.DataFrame(columns=[
            "store_id", "store", "dt", "cr", "amount", "quant", "orders", "ave_check", "rtr_ratio"
        ])

    out = []
    for r in rows:
        dt = float(r["dt"] or 0)
        cr = float(r["cr"] or 0)
        amount = float(r["amount"] or 0)
        quant = float(r["quant"] or 0)
        orders = int(r["orders"] or 0)

        ave_check = (amount / orders) if orders else None
        rtr_ratio = (cr / dt) if dt else None

        out.append({
            "store_id": r["store_id"],
            "store": r["store__name"] or "Без магазина",
            "dt": dt,
            "cr": cr,
            "amount": amount,
            "quant": quant,
            "orders": orders,
            "ave_check": ave_check,
            "rtr_ratio": rtr_ratio,
        })

    return pd.DataFrame(out)


def get_store_monthly_sales_df(start: date, end: date) -> pd.DataFrame:
    qs = (
        SalesData.objects
        .filter(date__range=(start, end), store__isnull=False)
        .annotate(month=TruncMonth("date"))
        .values("store_id", "store__name", "month")
        .annotate(
            dt=Coalesce(Sum("dt"), Value(0), output_field=DecimalField()),
            cr=Coalesce(Sum("cr"), Value(0), output_field=DecimalField()),
            quant_dt=Coalesce(Sum("quant_dt"), Value(0), output_field=DecimalField()),
            quant_cr=Coalesce(Sum("quant_cr"), Value(0), output_field=DecimalField()),
            orders=Count(
                "client_order_number",
                distinct=True,
                filter=Q(client_order_number__isnull=False) & ~Q(client_order_number="")
            ),
        )
        .annotate(
            amount=F("dt") - F("cr"),
            quant=F("quant_dt") - F("quant_cr"),
        )
        .order_by("month", "store__name")
    )

    rows = list(qs)
    if not rows:
        return pd.DataFrame(columns=[
            "store_id", "store", "month", "dt", "cr", "amount", "quant", "orders"
        ])

    df = pd.DataFrame([{
        "store_id": r["store_id"],
        "store": r["store__name"] or "Без магазина",
        "month": pd.to_datetime(r["month"]),
        "dt": float(r["dt"] or 0),
        "cr": float(r["cr"] or 0),
        "amount": float(r["amount"] or 0),
        "quant": float(r["quant"] or 0),
        "orders": int(r["orders"] or 0),
    } for r in rows])

    return df


def get_store_yoy_raw(d: date) -> dict:
    ytd_start = d.replace(month=1, day=1)
    ytd_prev_end = d - relativedelta(years=1)
    ytd_prev_start = ytd_prev_end.replace(month=1, day=1)

    mtd_start = d.replace(day=1)
    mtd_prev_start = (d - relativedelta(years=1)).replace(day=1)

    curr_ytd = get_store_sales_df(ytd_start, d)
    prev_ytd = get_store_sales_df(ytd_prev_start, ytd_prev_end)

    curr_mtd = get_store_sales_df(mtd_start, d)
    prev_mtd = get_store_sales_df(mtd_prev_start, ytd_prev_end)

    monthly_curr = get_store_monthly_sales_df(ytd_start, d)
    monthly_prev = get_store_monthly_sales_df(ytd_prev_start, ytd_prev_end)

    return {
        "date": d,
        "y_curr": d.year,
        "y_prev": d.year - 1,
        "curr_ytd": curr_ytd,
        "prev_ytd": prev_ytd,
        "curr_mtd": curr_mtd,
        "prev_mtd": prev_mtd,
        "monthly_curr": monthly_curr,
        "monthly_prev": monthly_prev,
    }