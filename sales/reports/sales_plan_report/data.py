# sales/reports/sales_plan_report/data.py

from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from django.db import connection

from sales.models import StoreSalesPlan

from .calendar import build_cash_calendar
from .charts import build_cash_share_chart


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


def get_cash_fact_by_store(date_start, date_end):
    """
    Возвращает cash-in по магазинам за период:
    {
        normalized_store_name: Decimal(fact)
    }
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                LOWER(TRIM(store)) AS store_name,
                COALESCE(SUM(amount), 0) AS fact
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND (
                    oper_type = 'Поступление оплаты от клиента'
                    OR oper_type = 'Возврат или иная оплата клиенту'
                    OR register LIKE 'Отчет о розничных продажах%%'
                    OR register LIKE 'Отчет о розничных возвратах%%'
              )
            GROUP BY LOWER(TRIM(store))
            """,
            [date_start, date_end],
        )

        return {
            row[0]: Decimal(str(row[1] or 0))
            for row in cursor.fetchall()
        }


def get_sales_plan_data(report_date):
    month_start, month_end = get_month_bounds(report_date)

    prev_month_report_date = report_date - relativedelta(months=1)
    prev_year_report_date = report_date - relativedelta(years=1)

    prev_month_start = prev_month_report_date.replace(day=1)
    prev_year_start = prev_year_report_date.replace(day=1)

    prev_month_fact_map = get_cash_fact_by_store(
        prev_month_start,
        prev_month_report_date,
    )

    prev_year_fact_map = get_cash_fact_by_store(
        prev_year_start,
        prev_year_report_date,
    )

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

    facts_map = get_cash_fact_by_store(month_start, report_date)

    rows = []
    total_plan = Decimal("0")
    total_fact = Decimal("0")

    for plan in plans_qs:
        store_name = str(plan.store).strip()
        store_key = normalize_store_name(store_name)

        fact = facts_map.get(store_key, Decimal("0"))
        plan_amount = to_decimal(plan.amount)

        prev_month_fact = prev_month_fact_map.get(store_key, Decimal("0"))
        prev_year_fact = prev_year_fact_map.get(store_key, Decimal("0"))

        mom_diff = fact - prev_month_fact
        mom_pct = safe_div(mom_diff, prev_month_fact) * Decimal("100")

        yoy_diff = fact - prev_year_fact
        yoy_pct = safe_div(yoy_diff, prev_year_fact) * Decimal("100")

        exec_pct = safe_div(fact, plan_amount) * Decimal("100")
        diff = fact - plan_amount
        remaining = max(plan_amount - fact, Decimal("0"))

        avg_daily_fact = safe_div(fact, days_passed)
        required_daily = safe_div(remaining, days_left) if days_left > 0 else remaining

        projected_month_fact = avg_daily_fact * Decimal(days_in_month)
        projected_diff = projected_month_fact - plan_amount

        progress_width = min(exec_pct, Decimal("100")).quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )

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

            "prev_month_fact": prev_month_fact,
            "prev_year_fact": prev_year_fact,
            "mom_diff": mom_diff,
            "mom_pct": mom_pct,
            "yoy_diff": yoy_diff,
            "yoy_pct": yoy_pct,

            "plan_fmt": fmt_money(plan_amount),
            "fact_fmt": fmt_money(fact),
            "diff_fmt": fmt_money(abs(diff)),
            "remaining_fmt": fmt_money(remaining),
            "avg_daily_fact_fmt": fmt_money(avg_daily_fact),
            "required_daily_fmt": fmt_money(required_daily),
            "projected_month_fact_fmt": fmt_money(projected_month_fact),
            "projected_diff_fmt": fmt_money(abs(projected_diff)),

            "prev_month_fact_fmt": fmt_money(prev_month_fact),
            "prev_year_fact_fmt": fmt_money(prev_year_fact),
            "mom_diff_fmt": fmt_money(abs(mom_diff)),
            "mom_pct_fmt": fmt_pct(abs(mom_pct)),
            "yoy_diff_fmt": fmt_money(abs(yoy_diff)),
            "yoy_pct_fmt": fmt_pct(abs(yoy_pct)),

            "exec_pct_fmt": fmt_pct(exec_pct),
            "progress_width": progress_width,

            "is_done": exec_pct >= 100,
            "is_on_track": projected_month_fact >= plan_amount,
        })

        total_plan += plan_amount
        total_fact += fact

    rows = sorted(rows, key=lambda x: x["exec_pct"], reverse=True)

    for row in rows:
        share_pct = safe_div(row["fact"], total_fact) * Decimal("100")
        row["share_pct"] = share_pct
        row["share_pct_fmt"] = fmt_pct(share_pct)

    total_exec_pct = safe_div(total_fact, total_plan) * Decimal("100")
    total_diff = total_fact - total_plan
    total_remaining = max(total_plan - total_fact, Decimal("0"))

    total_avg_daily_fact = safe_div(total_fact, days_passed)
    total_required_daily = (
        safe_div(total_remaining, days_left) if days_left > 0 else total_remaining
    )

    total_projected_month_fact = total_avg_daily_fact * Decimal(days_in_month)
    total_projected_diff = total_projected_month_fact - total_plan

    total_progress_width = min(total_exec_pct, Decimal("100")).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )

    calendar_daily_plan = safe_div(total_plan, days_in_month)

    cash_calendar = build_cash_calendar(
        report_date=report_date,
        daily_plan=calendar_daily_plan,
    )

    cash_share_chart = build_cash_share_chart(
        rows=rows,
        total_fact=total_fact,
    )

    return {
        "report_date": report_date,
        "month_start": month_start,
        "month_end": month_end,
        "days_in_month": days_in_month,
        "days_passed": days_passed,
        "days_left": days_left,

        "cash_calendar": cash_calendar,
        "cash_share_chart": cash_share_chart,

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