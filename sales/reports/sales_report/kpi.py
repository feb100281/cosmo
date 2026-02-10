from datetime import date
from django.db.models import Sum
from sales.models import MV_Daily_Sales

def build_kpi_for_range(start: date, end: date) -> dict:
    """
    KPI как ИТОГ за период.
    ave_check = amount / orders
    rtr_ratio = cr / dt
    """
    agg = MV_Daily_Sales.objects.filter(date__range=(start, end)).aggregate(
        amount=Sum("amount"),
        dt=Sum("dt"),
        cr=Sum("cr"),
        orders=Sum("orders"),
        quant=Sum("quant"),
    )

    amount = agg["amount"] or 0
    dt = agg["dt"] or 0
    cr = agg["cr"] or 0
    orders = agg["orders"] or 0
    quant = agg["quant"] or 0

    ave_check = (amount / orders) if orders else None
    rtr_ratio = (cr / dt) if dt else None  # доля 0..1 (твой fmt_pct это понимает)

    return {
        "amount": amount,
        "dt": dt,
        "cr": cr,
        "orders": orders,
        "quant": quant,
        "ave_check": ave_check,
        "rtr_ratio": rtr_ratio,
    }
