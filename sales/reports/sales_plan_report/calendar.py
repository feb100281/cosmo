# # sales/reports/sales_plan_report/calendar.py

# import calendar
# from decimal import Decimal

# from django.db import connection


# WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# def to_decimal(value):
#     return Decimal(str(value or 0))


# def fmt_money_short(value):
#     value = to_decimal(value)

#     if abs(value) >= Decimal("1000000"):
#         return f"{float(value / Decimal('1000000')):.1f} млн"

#     if abs(value) >= Decimal("1000"):
#         return f"{float(value / Decimal('1000')):.0f} тыс."

#     return f"{float(value):,.0f}".replace(",", " ")


# def fmt_pct(value):
#     value = to_decimal(value)
#     return f"{float(value):.0f}%"


# def get_daily_cash_map(month_start, report_date):
#     """
#     Возвращает поступления по дням:
#     {
#         date: Decimal(amount)
#     }
#     """
#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT 
#                 date,
#                 COALESCE(SUM(amount), 0) AS amount
#             FROM orders_orderscf
#             WHERE date >= %s
#               AND date <= %s
#             GROUP BY date
#             ORDER BY date
#             """,
#             [month_start, report_date],
#         )

#         return {
#             row[0]: to_decimal(row[1])
#             for row in cursor.fetchall()
#         }


# def get_calendar_level(amount, daily_plan):
#     """
#     Класс дня для раскраски календаря.

#     Важно:
#     daily_plan — это плановая дневная норма месяца,
#     а не догоняющий required_daily до конца месяца.
#     """
#     amount = to_decimal(amount)
#     daily_plan = to_decimal(daily_plan)

#     if amount <= 0:
#         return "day-empty"

#     if daily_plan <= 0:
#         return "day-good"

#     ratio = amount / daily_plan

#     if ratio >= Decimal("1.2"):
#         return "day-excellent"

#     if ratio >= Decimal("0.8"):
#         return "day-good"

#     if ratio >= Decimal("0.4"):
#         return "day-warning"

#     return "day-bad"


# def build_cash_calendar(report_date, daily_plan):
#     """
#     Формирует календарную сетку для PDF.

#     Цвет дня считается относительно плановой дневной нормы месяца:
#     total_plan / days_in_month.
#     """
#     month_start = report_date.replace(day=1)
#     _, days_in_month = calendar.monthrange(report_date.year, report_date.month)
#     month_end = report_date.replace(day=days_in_month)

#     daily_plan = to_decimal(daily_plan)

#     daily_cash = get_daily_cash_map(month_start, report_date)

#     month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(
#         report_date.year,
#         report_date.month,
#     )

#     weeks = []

#     for week in month_calendar:
#         week_cells = []

#         for current_day in week:
#             is_current_month = current_day.month == report_date.month
#             is_future = current_day > report_date and is_current_month

#             amount = (
#                 daily_cash.get(current_day, Decimal("0"))
#                 if is_current_month
#                 else Decimal("0")
#             )

#             if amount > 0 and daily_plan > 0:
#                 day_ratio = amount / daily_plan * Decimal("100")
#             else:
#                 day_ratio = Decimal("0")

#             if is_current_month and not is_future:
#                 level_class = get_calendar_level(amount, daily_plan)
#             else:
#                 level_class = "day-future"

#             week_cells.append({
#                 "date": current_day,
#                 "day": current_day.day,
#                 "weekday": WEEKDAYS_RU[current_day.weekday()],
#                 "is_current_month": is_current_month,
#                 "is_report_date": current_day == report_date,
#                 "is_future": is_future,

#                 "amount": amount,
#                 "amount_fmt": fmt_money_short(amount) if amount else "—",

#                 "day_ratio": day_ratio,
#                 "day_ratio_fmt": fmt_pct(day_ratio) if amount > 0 and not is_future else "",

#                 "level_class": level_class,
#             })

#         weeks.append(week_cells)

#     return {
#         "weekdays": WEEKDAYS_RU,
#         "weeks": weeks,
#         "month_start": month_start,
#         "month_end": month_end,
#         "daily_plan": daily_plan,
#         "daily_plan_fmt": fmt_money_short(daily_plan),
#     }



# sales/reports/sales_plan_report/calendar.py

import calendar
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection


WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def to_decimal(value):
    return Decimal(str(value or 0))


def safe_div(a, b):
    a = to_decimal(a)
    b = to_decimal(b)

    if b == 0:
        return Decimal("0")

    return a / b


def fmt_money_short(value):
    value = to_decimal(value)

    if abs(value) >= Decimal("1000000"):
        return f"{float(value / Decimal('1000000')):.1f} млн"

    if abs(value) >= Decimal("1000"):
        return f"{float(value / Decimal('1000')):.0f} тыс."

    return f"{float(value):,.0f}".replace(",", " ")


def fmt_pct(value):
    value = to_decimal(value)
    return f"{float(value):.0f}%"


def get_daily_cash_map(month_start, report_date):
    """
    Возвращает поступления по дням:
    {
        date: Decimal(amount)
    }
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                date,
                COALESCE(SUM(amount), 0) AS amount
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
            GROUP BY date
            ORDER BY date
            """,
            [month_start, report_date],
        )

        return {
            row[0]: to_decimal(row[1])
            for row in cursor.fetchall()
        }


def get_calendar_level(amount, daily_plan):
    """
    Класс дня для раскраски календаря.

    Важно:
    daily_plan — это плановая дневная норма месяца,
    а не догоняющий required_daily до конца месяца.
    """
    amount = to_decimal(amount)
    daily_plan = to_decimal(daily_plan)

    if amount <= 0:
        return "day-empty"

    if daily_plan <= 0:
        return "day-good"

    ratio = amount / daily_plan

    if ratio >= Decimal("1.2"):
        return "day-excellent"

    if ratio >= Decimal("0.8"):
        return "day-good"

    if ratio >= Decimal("0.4"):
        return "day-warning"

    return "day-bad"


def build_week_summary(week_cells, daily_plan):
    """
    Формирует боковую аналитику по неделе:
    - факт недели;
    - план на дату внутри недели;
    - выполнение недели;
    - мини-спарклайн по дням.
    """
    daily_plan = to_decimal(daily_plan)

    current_days = [
        day for day in week_cells
        if day["is_current_month"]
    ]

    fact_days = [
        day for day in current_days
        if not day["is_future"]
    ]

    future_days = [
        day for day in current_days
        if day["is_future"]
    ]

    week_fact = sum(
        (day["amount"] for day in fact_days),
        Decimal("0"),
    )

    week_plan = daily_plan * Decimal(len(current_days))
    week_plan_to_date = daily_plan * Decimal(len(fact_days))

    week_exec_pct = safe_div(week_fact, week_plan_to_date) * Decimal("100")

    week_progress_width = min(
        week_exec_pct,
        Decimal("100"),
    ).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )

    max_day_amount = max(
        [day["amount"] for day in current_days] + [Decimal("1")]
    )

    daily_bars = []

    for day in current_days:
        bar_height = min(
            safe_div(day["amount"], max_day_amount) * Decimal("100"),
            Decimal("100"),
        ).quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )

        daily_bars.append({
            "day": day["day"],
            "amount": day["amount"],
            "amount_fmt": day["amount_fmt"],
            "bar_height": bar_height,
            "level_class": day["level_class"],
            "is_future": day["is_future"],
            "is_report_date": day["is_report_date"],
        })

    return {
        "week_label": f"{current_days[0]['day']}–{current_days[-1]['day']}",

        "days_count": len(current_days),
        "fact_days_count": len(fact_days),
        "future_days_count": len(future_days),

        "week_fact": week_fact,
        "week_plan": week_plan,
        "week_plan_to_date": week_plan_to_date,
        "week_exec_pct": week_exec_pct,
        "week_progress_width": week_progress_width,

        "week_fact_fmt": fmt_money_short(week_fact),
        "week_plan_fmt": fmt_money_short(week_plan),
        "week_plan_to_date_fmt": fmt_money_short(week_plan_to_date),
        "week_exec_pct_fmt": fmt_pct(week_exec_pct),

        "is_completed_week": len(future_days) == 0,
        "is_current_week": any(day["is_report_date"] for day in current_days),

        "daily_bars": daily_bars,
    }


def build_cash_calendar(report_date, daily_plan):
    """
    Формирует календарную сетку для PDF.

    Цвет дня считается относительно плановой дневной нормы месяца:
    total_plan / days_in_month.

    Дополнительно формирует week_summaries для правой панели:
    итоги по неделям + мини-спарклайны.
    """
    month_start = report_date.replace(day=1)
    _, days_in_month = calendar.monthrange(report_date.year, report_date.month)
    month_end = report_date.replace(day=days_in_month)

    daily_plan = to_decimal(daily_plan)

    daily_cash = get_daily_cash_map(month_start, report_date)

    month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(
        report_date.year,
        report_date.month,
    )

    weeks = []
    week_summaries = []

    for week in month_calendar:
        week_cells = []

        for current_day in week:
            is_current_month = current_day.month == report_date.month
            is_future = current_day > report_date and is_current_month

            amount = (
                daily_cash.get(current_day, Decimal("0"))
                if is_current_month
                else Decimal("0")
            )

            if amount > 0 and daily_plan > 0:
                day_ratio = amount / daily_plan * Decimal("100")
            else:
                day_ratio = Decimal("0")

            if is_current_month and not is_future:
                level_class = get_calendar_level(amount, daily_plan)
            elif is_current_month and is_future:
                level_class = "day-future"
            else:
                level_class = "day-outside"

            week_cells.append({
                "date": current_day,
                "day": current_day.day,
                "weekday": WEEKDAYS_RU[current_day.weekday()],

                "is_current_month": is_current_month,
                "is_report_date": current_day == report_date,
                "is_future": is_future,

                "amount": amount,
                "amount_fmt": fmt_money_short(amount) if amount else "—",

                "day_ratio": day_ratio,
                "day_ratio_fmt": (
                    fmt_pct(day_ratio)
                    if amount > 0 and not is_future
                    else ""
                ),

                "level_class": level_class,
            })

        current_month_days = [
            day for day in week_cells
            if day["is_current_month"]
        ]

        week_summary = None

        if current_month_days:
            week_summary = build_week_summary(
                week_cells=week_cells,
                daily_plan=daily_plan,
            )
            week_summaries.append(week_summary)

        weeks.append({
            "days": week_cells,
            "summary": week_summary,
        })

    return {
        "weekdays": WEEKDAYS_RU,
        "weeks": weeks,
        "week_summaries": week_summaries,

        "month_start": month_start,
        "month_end": month_end,

        "daily_plan": daily_plan,
        "daily_plan_fmt": fmt_money_short(daily_plan),
    }