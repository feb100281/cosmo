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


# def get_calendar_level(amount, avg_daily_required):
#     """
#     Класс дня для раскраски календаря.
#     """
#     amount = to_decimal(amount)
#     avg_daily_required = to_decimal(avg_daily_required)

#     if amount <= 0:
#         return "day-empty"

#     if avg_daily_required <= 0:
#         return "day-good"

#     ratio = amount / avg_daily_required

#     if ratio >= Decimal("1.2"):
#         return "day-excellent"
#     if ratio >= Decimal("0.8"):
#         return "day-good"
#     if ratio >= Decimal("0.4"):
#         return "day-warning"

#     return "day-bad"


# def build_cash_calendar(report_date, required_daily):
#     """
#     Формирует календарную сетку для PDF.
#     """
#     month_start = report_date.replace(day=1)
#     _, days_in_month = calendar.monthrange(report_date.year, report_date.month)
#     month_end = report_date.replace(day=days_in_month)

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
#             amount = daily_cash.get(current_day, Decimal("0")) if is_current_month else Decimal("0")

#             week_cells.append({
#                 "date": current_day,
#                 "day": current_day.day,
#                 "weekday": WEEKDAYS_RU[current_day.weekday()],
#                 "is_current_month": is_current_month,
#                 "is_report_date": current_day == report_date,
#                 "is_future": is_future,
#                 "amount": amount,
#                 "amount_fmt": fmt_money_short(amount) if amount else "—",
#                 "level_class": get_calendar_level(amount, required_daily) if is_current_month and not is_future else "day-future",
#             })

#         weeks.append(week_cells)

#     return {
#         "weekdays": WEEKDAYS_RU,
#         "weeks": weeks,
#         "month_start": month_start,
#         "month_end": month_end,
#     }



# sales/reports/sales_plan_report/calendar.py

import calendar
from decimal import Decimal

from django.db import connection


WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def to_decimal(value):
    return Decimal(str(value or 0))


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


def build_cash_calendar(report_date, daily_plan):
    """
    Формирует календарную сетку для PDF.

    Цвет дня считается относительно плановой дневной нормы месяца:
    total_plan / days_in_month.
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
            else:
                level_class = "day-future"

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
                "day_ratio_fmt": fmt_pct(day_ratio) if amount > 0 and not is_future else "",

                "level_class": level_class,
            })

        weeks.append(week_cells)

    return {
        "weekdays": WEEKDAYS_RU,
        "weeks": weeks,
        "month_start": month_start,
        "month_end": month_end,
        "daily_plan": daily_plan,
        "daily_plan_fmt": fmt_money_short(daily_plan),
    }