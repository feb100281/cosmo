



# # sales/reports/sales_plan_report/calendar.py

# import calendar
# from decimal import Decimal, ROUND_HALF_UP

# from django.db import connection
# from .utils import to_decimal, safe_div, fmt_money_short, fmt_pct


# WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# def get_daily_cash_map(month_start, report_date, store_name=None):
#     """
#     Возвращает поступления по дням.
#     Если store_name указан - только для конкретного магазина
#     """
#     with connection.cursor() as cursor:
#         if store_name:
#             cursor.execute(
#                 """
#                 SELECT 
#                     date,
#                     COALESCE(SUM(amount), 0) AS amount
#                 FROM orders_orderscf
#                 WHERE date >= %s
#                   AND date <= %s
#                   AND LOWER(TRIM(store)) = %s
#                   AND (
#                         oper_type = 'Поступление оплаты от клиента'
#                         OR register LIKE 'Отчет о розничных продажах%%'
#                   )
#                 GROUP BY date
#                 ORDER BY date
#                 """,
#                 [month_start, report_date, store_name.lower().strip()],
#             )
#         else:
#             cursor.execute(
#                 """
#                 SELECT 
#                     date,
#                     COALESCE(SUM(amount), 0) AS amount
#                 FROM orders_orderscf
#                 WHERE date >= %s
#                   AND date <= %s
#                   AND (
#                         oper_type = 'Поступление оплаты от клиента'
#                         OR register LIKE 'Отчет о розничных продажах%%'
#                   )
#                 GROUP BY date
#                 ORDER BY date
#                 """,
#                 [month_start, report_date],
#             )
#         return {
#             row[0]: to_decimal(row[1])
#             for row in cursor.fetchall()
#         }


# def get_daily_returns_map(month_start, report_date, store_name=None):
#     """
#     Возвращает возвраты по дням (сумма по модулю)
#     Если store_name указан - только для конкретного магазина
#     """
#     with connection.cursor() as cursor:
#         if store_name:
#             cursor.execute(
#                 """
#                 SELECT 
#                     date,
#                     COALESCE(SUM(ABS(amount)), 0) AS returns_amount
#                 FROM orders_orderscf
#                 WHERE date >= %s
#                   AND date <= %s
#                   AND LOWER(TRIM(store)) = %s
#                   AND (
#                         oper_type = 'Возврат или иная оплата клиенту'
#                         OR register LIKE 'Отчет о розничных возвратах%%'
#                   )
#                 GROUP BY date
#                 ORDER BY date
#                 """,
#                 [month_start, report_date, store_name.lower().strip()],
#             )
#         else:
#             cursor.execute(
#                 """
#                 SELECT 
#                     date,
#                     COALESCE(SUM(ABS(amount)), 0) AS returns_amount
#                 FROM orders_orderscf
#                 WHERE date >= %s
#                   AND date <= %s
#                   AND (
#                         oper_type = 'Возврат или иная оплата клиенту'
#                         OR register LIKE 'Отчет о розничных возвратах%%'
#                   )
#                 GROUP BY date
#                 ORDER BY date
#                 """,
#                 [month_start, report_date],
#             )
#         return {
#             row[0]: to_decimal(row[1])
#             for row in cursor.fetchall()
#         }


# def get_calendar_level(amount, daily_plan):
#     """
#     Класс дня для раскраски календаря (по поступлениям)
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


# def build_week_summary(week_cells, daily_plan):
#     """
#     Формирует боковую аналитику по неделе
#     """
#     daily_plan = to_decimal(daily_plan)

#     current_days = [day for day in week_cells if day["is_current_month"]]
#     fact_days = [day for day in current_days if not day["is_future"]]
#     future_days = [day for day in current_days if day["is_future"]]

#     week_fact = sum((day["amount"] for day in fact_days), Decimal("0"))
#     week_plan = daily_plan * Decimal(len(current_days))
#     week_plan_to_date = daily_plan * Decimal(len(fact_days))
#     week_exec_pct = safe_div(week_fact, week_plan_to_date) * Decimal("100")

#     week_progress_width = min(week_exec_pct, Decimal("100")).quantize(
#         Decimal("0.1"), rounding=ROUND_HALF_UP
#     )

#     max_day_amount = max([day["amount"] for day in current_days] + [Decimal("1")])

#     daily_bars = []
#     for day in current_days:
#         bar_height = min(
#             safe_div(day["amount"], max_day_amount) * Decimal("100"),
#             Decimal("100"),
#         ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

#         daily_bars.append({
#             "day": day["day"],
#             "amount": day["amount"],
#             "amount_fmt": day["amount_fmt"],
#             "bar_height": bar_height,
#             "level_class": day["level_class"],
#             "is_future": day["is_future"],
#             "is_report_date": day["is_report_date"],
#         })

#     return {
#         "week_label": f"{current_days[0]['day']}–{current_days[-1]['day']}",
#         "days_count": len(current_days),
#         "fact_days_count": len(fact_days),
#         "future_days_count": len(future_days),
#         "week_fact": week_fact,
#         "week_plan": week_plan,
#         "week_plan_to_date": week_plan_to_date,
#         "week_exec_pct": week_exec_pct,
#         "week_progress_width": week_progress_width,
#         "week_fact_fmt": fmt_money_short(week_fact),
#         "week_plan_fmt": fmt_money_short(week_plan),
#         "week_plan_to_date_fmt": fmt_money_short(week_plan_to_date),
#         "week_exec_pct_fmt": fmt_pct(week_exec_pct),
#         "is_completed_week": len(future_days) == 0,
#         "is_current_week": any(day["is_report_date"] for day in current_days),
#         "daily_bars": daily_bars,
#     }


# def build_cash_calendar(report_date, daily_plan, store_name=None):
#     """
#     Формирует календарную сетку для PDF с поступлениями, возвратами и нетто.
#     Если store_name указан - только для конкретного магазина
#     """
#     month_start = report_date.replace(day=1)
#     _, days_in_month = calendar.monthrange(report_date.year, report_date.month)

#     daily_plan = to_decimal(daily_plan)
#     daily_cash = get_daily_cash_map(month_start, report_date, store_name)
#     daily_returns = get_daily_returns_map(month_start, report_date, store_name)

#     month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(
#         report_date.year, report_date.month
#     )

#     weeks = []
#     week_summaries = []

#     for week in month_calendar:
#         week_cells = []

#         for current_day in week:
#             is_current_month = current_day.month == report_date.month
#             is_future = current_day > report_date and is_current_month

#             amount = daily_cash.get(current_day, Decimal("0")) if is_current_month else Decimal("0")
#             returns_amount = daily_returns.get(current_day, Decimal("0")) if is_current_month else Decimal("0")
#             netto_amount = amount - returns_amount

#             if amount > 0 and daily_plan > 0:
#                 day_ratio = amount / daily_plan * Decimal("100")
#             else:
#                 day_ratio = Decimal("0")

#             if is_current_month and not is_future:
#                 level_class = get_calendar_level(amount, daily_plan)
#             elif is_current_month and is_future:
#                 level_class = "day-future"
#             else:
#                 level_class = "day-outside"

#             week_cells.append({
#                 "date": current_day,
#                 "day": current_day.day,
#                 "weekday": WEEKDAYS_RU[current_day.weekday()],
#                 "is_current_month": is_current_month,
#                 "is_report_date": current_day == report_date,
#                 "is_future": is_future,
#                 "amount": amount,
#                 "amount_fmt": fmt_money_short(amount) if amount else "—",
#                 "returns_amount": returns_amount,
#                 "returns_amount_fmt": fmt_money_short(returns_amount) if returns_amount else "—",
#                 "netto_amount": netto_amount,
#                 "netto_amount_fmt": fmt_money_short(netto_amount) if netto_amount else "—",
#                 "day_ratio": day_ratio,
#                 "day_ratio_fmt": fmt_pct(day_ratio) if amount > 0 and not is_future else "",
#                 "level_class": level_class,
#             })

#         current_month_days = [day for day in week_cells if day["is_current_month"]]

#         week_summary = None
#         if current_month_days:
#             week_summary = build_week_summary(week_cells=week_cells, daily_plan=daily_plan)
#             week_summaries.append(week_summary)

#         weeks.append({
#             "days": week_cells,
#             "summary": week_summary,
#         })

#     return {
#         "weekdays": WEEKDAYS_RU,
#         "weeks": weeks,
#         "week_summaries": week_summaries,
#         "month_start": month_start,
#         "month_end": report_date.replace(day=days_in_month),
#         "daily_plan": daily_plan,
#         "daily_plan_fmt": fmt_money_short(daily_plan),
#     }


# def build_calendars_for_all_stores(report_date, sales_plan_rows):
#     """
#     Строит календари для всех магазинов, у которых есть план или факт
#     """
#     month_start = report_date.replace(day=1)
#     _, days_in_month = calendar.monthrange(report_date.year, report_date.month)
    
#     stores_calendars = []
    
#     for row in sales_plan_rows:
#         store_name = row["store_name"]
#         store_plan = row["plan"]
        
#         # Пропускаем магазины без плана и с нулевыми поступлениями
#         if store_plan == 0 and row["fact"] == 0:
#             continue
            
#         daily_plan = store_plan / days_in_month if store_plan > 0 else Decimal("0")
        
#         calendar_data = build_cash_calendar(
#             report_date=report_date,
#             daily_plan=daily_plan,
#             store_name=store_name,
#         )
        
#         stores_calendars.append({
#             "store_name": store_name,
#             "store_plan": store_plan,
#             "store_plan_fmt": row["plan_fmt"],
#             "store_fact": row["fact"],
#             "store_fact_fmt": row["fact_fmt"],
#             "store_exec_pct": row["exec_pct"],
#             "store_exec_pct_fmt": row["exec_pct_fmt"],
#             "has_plan": row["has_plan"],
#             "calendar": calendar_data,
#         })
    
#     return stores_calendars



# sales/reports/sales_plan_report/calendar.py

import calendar
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection
from .utils import to_decimal, safe_div, fmt_money_short, fmt_pct


WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_daily_cash_map(month_start, report_date, store_name=None):
    """
    Возвращает поступления по дням.
    Если store_name указан - только для конкретного магазина
    """
    with connection.cursor() as cursor:
        if store_name:
            cursor.execute(
                """
                SELECT 
                    date,
                    COALESCE(SUM(amount), 0) AS amount
                FROM orders_orderscf
                WHERE date >= %s
                  AND date <= %s
                  AND LOWER(TRIM(store)) = %s
                  AND (
                        oper_type = 'Поступление оплаты от клиента'
                        OR register LIKE 'Отчет о розничных продажах%%'
                  )
                GROUP BY date
                ORDER BY date
                """,
                [month_start, report_date, store_name.lower().strip()],
            )
        else:
            cursor.execute(
                """
                SELECT 
                    date,
                    COALESCE(SUM(amount), 0) AS amount
                FROM orders_orderscf
                WHERE date >= %s
                  AND date <= %s
                  AND (
                        oper_type = 'Поступление оплаты от клиента'
                        OR register LIKE 'Отчет о розничных продажах%%'
                  )
                GROUP BY date
                ORDER BY date
                """,
                [month_start, report_date],
            )
        return {
            row[0]: to_decimal(row[1])
            for row in cursor.fetchall()
        }


def get_daily_returns_map(month_start, report_date, store_name=None):
    """
    Возвращает возвраты по дням (сумма по модулю)
    Если store_name указан - только для конкретного магазина
    """
    with connection.cursor() as cursor:
        if store_name:
            cursor.execute(
                """
                SELECT 
                    date,
                    COALESCE(SUM(ABS(amount)), 0) AS returns_amount
                FROM orders_orderscf
                WHERE date >= %s
                  AND date <= %s
                  AND LOWER(TRIM(store)) = %s
                  AND (
                        oper_type = 'Возврат или иная оплата клиенту'
                        OR register LIKE 'Отчет о розничных возвратах%%'
                  )
                GROUP BY date
                ORDER BY date
                """,
                [month_start, report_date, store_name.lower().strip()],
            )
        else:
            cursor.execute(
                """
                SELECT 
                    date,
                    COALESCE(SUM(ABS(amount)), 0) AS returns_amount
                FROM orders_orderscf
                WHERE date >= %s
                  AND date <= %s
                  AND (
                        oper_type = 'Возврат или иная оплата клиенту'
                        OR register LIKE 'Отчет о розничных возвратах%%'
                  )
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
    Класс дня для раскраски календаря (по поступлениям)
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
    Формирует боковую аналитику по неделе
    """
    daily_plan = to_decimal(daily_plan)

    current_days = [day for day in week_cells if day["is_current_month"]]
    fact_days = [day for day in current_days if not day["is_future"]]
    future_days = [day for day in current_days if day["is_future"]]

    week_fact = sum((day["amount"] for day in fact_days), Decimal("0"))
    week_plan = daily_plan * Decimal(len(current_days))
    week_plan_to_date = daily_plan * Decimal(len(fact_days))
    week_exec_pct = safe_div(week_fact, week_plan_to_date) * Decimal("100")

    week_progress_width = min(week_exec_pct, Decimal("100")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )

    max_day_amount = max([day["amount"] for day in current_days] + [Decimal("1")])

    daily_bars = []
    for day in current_days:
        bar_height = min(
            safe_div(day["amount"], max_day_amount) * Decimal("100"),
            Decimal("100"),
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

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


def build_cash_calendar(report_date, daily_plan, store_name=None):
    """
    Формирует календарную сетку для PDF с поступлениями, возвратами и нетто.
    Если store_name указан - только для конкретного магазина
    """
    month_start = report_date.replace(day=1)
    _, days_in_month = calendar.monthrange(report_date.year, report_date.month)

    daily_plan = to_decimal(daily_plan)
    daily_cash = get_daily_cash_map(month_start, report_date, store_name)
    daily_returns = get_daily_returns_map(month_start, report_date, store_name)

    month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(
        report_date.year, report_date.month
    )

    weeks = []
    week_summaries = []

    for week in month_calendar:
        week_cells = []

        for current_day in week:
            is_current_month = current_day.month == report_date.month
            is_future = current_day > report_date and is_current_month

            amount = daily_cash.get(current_day, Decimal("0")) if is_current_month else Decimal("0")
            returns_amount = daily_returns.get(current_day, Decimal("0")) if is_current_month else Decimal("0")
            netto_amount = amount - returns_amount

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
                "returns_amount": returns_amount,
                "returns_amount_fmt": fmt_money_short(returns_amount) if returns_amount else "—",
                "netto_amount": netto_amount,
                "netto_amount_fmt": fmt_money_short(netto_amount) if netto_amount else "—",
                "day_ratio": day_ratio,
                "day_ratio_fmt": fmt_pct(day_ratio) if amount > 0 and not is_future else "",
                "level_class": level_class,
            })

        current_month_days = [day for day in week_cells if day["is_current_month"]]

        week_summary = None
        if current_month_days:
            week_summary = build_week_summary(week_cells=week_cells, daily_plan=daily_plan)
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
        "month_end": report_date.replace(day=days_in_month),
        "daily_plan": daily_plan,
        "daily_plan_fmt": fmt_money_short(daily_plan),
    }


def build_calendars_for_all_stores(report_date, sales_plan_rows):
    """
    Строит календари для всех магазинов (полные, с возвратами и нетто)
    """
    _, days_in_month = calendar.monthrange(report_date.year, report_date.month)
    
    stores_calendars = []
    
    for row in sales_plan_rows:
        store_name = row["store_name"]
        store_plan = row["plan"]
        
        # Пропускаем магазины без плана и с нулевыми поступлениями
        if store_plan == 0 and row["fact"] == 0:
            continue
            
        daily_plan = store_plan / days_in_month if store_plan > 0 else Decimal("0")
        
        calendar_data = build_cash_calendar(
            report_date=report_date,
            daily_plan=daily_plan,
            store_name=store_name,
        )
        
        stores_calendars.append({
            "store_name": store_name,
            "store_plan": store_plan,
            "store_plan_fmt": row["plan_fmt"],
            "store_fact": row["fact"],
            "store_fact_fmt": row["fact_fmt"],
            "store_exec_pct": row["exec_pct"],
            "store_exec_pct_fmt": row["exec_pct_fmt"],
            "has_plan": row["has_plan"],
            "calendar": calendar_data,
        })
    
    return stores_calendars