from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection

from sales.models import StoreSalesPlan
from .calendar import build_cash_calendar


def to_decimal(value):
    return Decimal(str(value or 0))


def fmt_money(value):
    value = to_decimal(value)
    return f"{float(value):,.0f}".replace(",", " ")


def fmt_pct(value):
    value = to_decimal(value)
    return f"{float(value):.1f}"


def normalize_store_name(value):
    return (value or "").strip().lower()


def safe_div(a, b):
    a = to_decimal(a)
    b = to_decimal(b)
    if b == 0:
        return Decimal("0")
    return a / b


def get_month_bounds(report_date):
    start = report_date.replace(day=1)
    end = report_date.replace(
        day=monthrange(report_date.year, report_date.month)[1]
    )
    return start, end


def get_sales_plan_data(report_date):
    month_start, month_end = get_month_bounds(report_date)

    days_in_month = month_end.day
    days_passed = report_date.day
    days_left = max(days_in_month - days_passed, 0)

    plans_qs = (
        StoreSalesPlan.objects
        .filter(
            plan_month__year=report_date.year,
            plan_month__month=report_date.month,
        )
        .select_related("store", "store__gr")
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                LOWER(TRIM(store)) AS store_name,
                COALESCE(SUM(amount), 0) AS fact
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
            GROUP BY LOWER(TRIM(store))
            """,
            [month_start, report_date],
        )

        facts_map = {
            row[0]: to_decimal(row[1])
            for row in cursor.fetchall()
        }

    rows = []
    total_plan = Decimal("0")
    total_fact = Decimal("0")

    for plan in plans_qs:
        store_name = str(plan.store).strip()
        store_key = normalize_store_name(store_name)

        fact = facts_map.get(store_key, Decimal("0"))
        plan_amount = to_decimal(plan.amount)

        exec_pct = safe_div(fact, plan_amount) * Decimal("100")
        diff = fact - plan_amount
        remaining = max(plan_amount - fact, Decimal("0"))

        avg_daily_fact = safe_div(fact, days_passed)
        required_daily = safe_div(remaining, days_left) if days_left > 0 else remaining
        projected_month_fact = avg_daily_fact * Decimal(days_in_month)
        projected_diff = projected_month_fact - plan_amount

        progress_width = min(exec_pct, Decimal("100"))
        progress_width = progress_width.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

        rows.append({
            "store": plan.store,
            "store_name": store_name,
            "group_name": str(plan.store.gr) if getattr(plan.store, "gr", None) else "—",

            "plan": plan_amount,
            "fact": fact,
            "diff": diff,
            "remaining": remaining,
            "exec_pct": exec_pct,

            "avg_daily_fact": avg_daily_fact,
            "required_daily": required_daily,
            "projected_month_fact": projected_month_fact,
            "projected_diff": projected_diff,

            "plan_fmt": fmt_money(plan_amount),
            "fact_fmt": fmt_money(fact),
            "diff_fmt": fmt_money(abs(diff)),
            "remaining_fmt": fmt_money(remaining),
            "avg_daily_fact_fmt": fmt_money(avg_daily_fact),
            "required_daily_fmt": fmt_money(required_daily),
            "projected_month_fact_fmt": fmt_money(projected_month_fact),
            "projected_diff_fmt": fmt_money(abs(projected_diff)),

            "exec_pct_fmt": fmt_pct(exec_pct),
            "progress_width": progress_width,

            "is_done": exec_pct >= 100,
            "is_on_track": projected_month_fact >= plan_amount,
        })

        total_plan += plan_amount
        total_fact += fact

    rows = sorted(rows, key=lambda x: x["exec_pct"], reverse=True)

    total_exec_pct = safe_div(total_fact, total_plan) * Decimal("100")
    total_diff = total_fact - total_plan
    total_remaining = max(total_plan - total_fact, Decimal("0"))

    total_avg_daily_fact = safe_div(total_fact, days_passed)
    total_required_daily = (
        safe_div(total_remaining, days_left) if days_left > 0 else total_remaining
    )
    total_projected_month_fact = total_avg_daily_fact * Decimal(days_in_month)
    total_projected_diff = total_projected_month_fact - total_plan

    total_progress_width = min(total_exec_pct, Decimal("100"))
    total_progress_width = total_progress_width.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
    cash_calendar = build_cash_calendar(
            report_date=report_date,
            required_daily=total_required_daily,
        )

    return {
        "report_date": report_date,
        "month_start": month_start,
        "month_end": month_end,
        "days_in_month": days_in_month,
        "days_passed": days_passed,
        "days_left": days_left,
        "cash_calendar": cash_calendar,
        "rows": rows,
        "totals": {
            "plan": total_plan,
            "fact": total_fact,
            "diff": total_diff,
            "remaining": total_remaining,
            "exec_pct": total_exec_pct,

            "avg_daily_fact": total_avg_daily_fact,
            "required_daily": total_required_daily,
            "projected_month_fact": total_projected_month_fact,
            "projected_diff": total_projected_diff,

            "plan_fmt": fmt_money(total_plan),
            "fact_fmt": fmt_money(total_fact),
            "diff_fmt": fmt_money(abs(total_diff)),
            "remaining_fmt": fmt_money(total_remaining),
            "avg_daily_fact_fmt": fmt_money(total_avg_daily_fact),
            "required_daily_fmt": fmt_money(total_required_daily),
            "projected_month_fact_fmt": fmt_money(total_projected_month_fact),
            "projected_diff_fmt": fmt_money(abs(total_projected_diff)),

            "exec_pct_fmt": fmt_pct(total_exec_pct),
            "progress_width": total_progress_width,

            "is_done": total_exec_pct >= 100,
            "is_on_track": total_projected_month_fact >= total_plan,
            "stores_count": len(rows),
        },
    }