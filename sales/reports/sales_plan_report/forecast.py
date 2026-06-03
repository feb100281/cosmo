# sales/reports/sales_plan_report/forecast.py
from decimal import Decimal, ROUND_HALF_UP


def to_decimal(value):
    return Decimal(str(value or 0))


def safe_div(a, b):
    a = to_decimal(a)
    b = to_decimal(b)
    if b == 0:
        return Decimal("0")
    return a / b


def fmt_money_mln(value):
    value = to_decimal(value)
    return f"{float(value / Decimal('1000000')):.1f} млн ₽"


def build_forecast_vs_plan_chart(total_plan, total_fact, projected_month_fact):
    total_plan = to_decimal(total_plan)
    total_fact = to_decimal(total_fact)
    projected_month_fact = to_decimal(projected_month_fact)

    max_value = max(total_plan, projected_month_fact, total_fact, Decimal("1"))

    fact_width = min(safe_div(total_fact, max_value) * 100, Decimal("100"))
    forecast_width = min(safe_div(projected_month_fact, max_value) * 100, Decimal("100"))
    plan_marker_left = min(safe_div(total_plan, max_value) * 100, Decimal("100"))

    forecast_gap = projected_month_fact - total_plan

    return {
        "plan": total_plan,
        "fact": total_fact,
        "forecast": projected_month_fact,
        "gap": forecast_gap,

        "plan_fmt": fmt_money_mln(total_plan),
        "fact_fmt": fmt_money_mln(total_fact),
        "forecast_fmt": fmt_money_mln(projected_month_fact),
        "gap_fmt": fmt_money_mln(abs(forecast_gap)),

        "fact_width": fact_width.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
        "forecast_width": forecast_width.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
        "plan_marker_left": plan_marker_left.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),

        "is_on_track": projected_month_fact >= total_plan,
    }