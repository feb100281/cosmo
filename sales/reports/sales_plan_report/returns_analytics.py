# # sales/reports/sales_plan_report/returns_analytics.py

# from decimal import Decimal
# from django.db import connection

# from .utils import safe_div, fmt_money, fmt_pct, to_decimal 


# def get_returns_by_store(date_start, date_end):
#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT 
#                 COALESCE(LOWER(TRIM(store)), '') AS store_name,
#                 COALESCE(SUM(amount), 0) AS returns_amount,
#                 COUNT(*) AS returns_count
#             FROM orders_orderscf
#             WHERE date >= %s
#               AND date <= %s
#               AND (
#                     oper_type = 'Возврат оплаты клиенту (продажа товаров, работ, услуг)'
#                     OR register LIKE 'Отчет о розничных возвратах%%'
#               )
#               AND store IS NOT NULL
#               AND TRIM(store) != ''
#             GROUP BY COALESCE(LOWER(TRIM(store)), '')
#             """,
#             [date_start, date_end],
#         )
#         return {
#             row[0]: {
#                 "amount": Decimal(str(row[1] or 0)),
#                 "count": row[2],
#             }
#             for row in cursor.fetchall()
#             if row[0]
#         }


# def get_designer_rewards_by_store(date_start, date_end):
#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT 
#                 COALESCE(LOWER(TRIM(store)), '') AS store_name,
#                 COALESCE(SUM(amount), 0) AS designer_amount,
#                 COUNT(*) AS designer_count
#             FROM orders_orderscf
#             WHERE date >= %s
#               AND date <= %s
#               AND oper_type IN ('Дизайнерское вознаграждение из УТ10', 'Дизайнерское вознаграждение')
#               AND store IS NOT NULL
#               AND TRIM(store) != ''
#             GROUP BY COALESCE(LOWER(TRIM(store)), '')
#             """,
#             [date_start, date_end],
#         )
#         return {
#             row[0]: {
#                 "amount": Decimal(str(row[1] or 0)),
#                 "count": row[2],
#             }
#             for row in cursor.fetchall()
#             if row[0]
#         }


# def get_daily_returns_map(month_start, report_date):
#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT 
#                 date,
#                 COALESCE(SUM(amount), 0) AS returns_amount
#             FROM orders_orderscf
#             WHERE date >= %s
#               AND date <= %s
#               AND (
#                     oper_type = 'Возврат оплаты клиенту (продажа товаров, работ, услуг)'
#                     OR register LIKE 'Отчет о розничных возвратах%%'
#               )
#             GROUP BY date
#             ORDER BY date
#             """,
#             [month_start, report_date],
#         )
#         return {
#             row[0]: to_decimal(row[1])
#             for row in cursor.fetchall()
#         }


# def get_daily_designer_map(month_start, report_date):
#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT 
#                 date,
#                 COALESCE(SUM(amount), 0) AS designer_amount
#             FROM orders_orderscf
#             WHERE date >= %s
#               AND date <= %s
#               AND oper_type IN ('Дизайнерское вознаграждение из УТ10', 'Дизайнерское вознаграждение')
#             GROUP BY date
#             ORDER BY date
#             """,
#             [month_start, report_date],
#         )
#         return {
#             row[0]: to_decimal(row[1])
#             for row in cursor.fetchall()
#         }


# def build_returns_analytics(report_date, income_rows):
#     month_start = report_date.replace(day=1)
    
#     returns_map = get_returns_by_store(month_start, report_date)
#     daily_returns = get_daily_returns_map(month_start, report_date)
    
#     designer_map = get_designer_rewards_by_store(month_start, report_date)
#     daily_designer = get_daily_designer_map(month_start, report_date)
    
#     enriched_rows = []
#     total_returns_abs = Decimal("0")
#     total_income = Decimal("0")
#     total_designer_abs = Decimal("0")
    
#     for row in income_rows:
#         store_key = row["store_name"].lower().strip()
#         returns_data = returns_map.get(store_key, {"amount": Decimal("0"), "count": 0})
#         designer_data = designer_map.get(store_key, {"amount": Decimal("0"), "count": 0})
        
#         returns_amount = abs(returns_data["amount"])  # для отображения берём модуль
#         designer_amount = designer_data["amount"]  # оставляем как есть (может быть + или -)
#         income = row["fact"]
        
#         total_returns_abs += returns_amount
#         total_designer_abs += abs(designer_amount)
#         total_income += income
        
#         return_pct_of_income = safe_div(returns_amount, income) * Decimal("100") if income > 0 else Decimal("0")
#         designer_pct_of_income = safe_div(abs(designer_amount), income) * Decimal("100") if income > 0 else Decimal("0")
        
#         # Итого расходы с учётом знака дизайнеров
#         total_costs = returns_amount + designer_amount
#         net_after_all = income - total_costs
        
#         enriched_rows.append({
#             "store_name": row["store_name"],
#             "income": income,
#             "income_fmt": row["fact_fmt"],
#             "returns_amount": returns_amount,
#             "returns_amount_fmt": fmt_money(returns_amount),
#             "returns_count": returns_data["count"],
#             "return_pct_of_income": return_pct_of_income,
#             "return_pct_fmt": fmt_pct(return_pct_of_income),
#             "net_income": income - returns_amount,
#             "net_income_fmt": fmt_money(income - returns_amount),
#             "designer_amount": designer_amount,
#             "designer_amount_fmt": fmt_money(abs(designer_amount)),
#             "designer_count": designer_data["count"],
#             "designer_pct_of_income": designer_pct_of_income,
#             "designer_pct_fmt": fmt_pct(designer_pct_of_income),
#             "total_costs": total_costs,
#             "total_costs_fmt": fmt_money(total_costs),
#             "net_after_all": net_after_all,
#             "net_after_all_fmt": fmt_money(net_after_all),
#         })
    
#     enriched_rows.sort(key=lambda x: x["returns_amount"], reverse=True)
    
#     total_return_pct = safe_div(total_returns_abs, total_income) * Decimal("100") if total_income > 0 else Decimal("0")
#     total_designer_pct = safe_div(total_designer_abs, total_income) * Decimal("100") if total_income > 0 else Decimal("0")
#     net_after_all = total_income - total_returns_abs - total_designer_abs
    
#     return {
#         "rows": enriched_rows,
#         "total_returns": total_returns_abs,
#         "total_returns_fmt": fmt_money(total_returns_abs),
#         "total_income": total_income,
#         "total_income_fmt": fmt_money(total_income),
#         "total_return_pct": total_return_pct,
#         "total_return_pct_fmt": fmt_pct(total_return_pct),
#         "daily_returns": daily_returns,
#         "has_returns": total_returns_abs > 0,
#         "total_designer": total_designer_abs,
#         "total_designer_fmt": fmt_money(total_designer_abs),
#         "total_designer_pct": total_designer_pct,
#         "total_designer_pct_fmt": fmt_pct(total_designer_pct),
#         "daily_designer": daily_designer,
#         "has_designer": total_designer_abs > 0,
#         "net_after_all": net_after_all,
#         "net_after_all_fmt": fmt_money(net_after_all),
#     }




# sales/reports/sales_plan_report/returns_analytics.py

from decimal import Decimal
from django.db import connection

from .utils import safe_div, fmt_money, fmt_pct, to_decimal


def get_returns_by_store(date_start, date_end):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                COALESCE(LOWER(TRIM(store)), '') AS store_name,
                COALESCE(SUM(amount), 0) AS returns_amount,
                COUNT(*) AS returns_count
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND (
                    oper_type = 'Возврат оплаты клиенту (продажа товаров, работ, услуг)'
                    OR register LIKE 'Отчет о розничных возвратах%%'
              )
              AND store IS NOT NULL
              AND TRIM(store) != ''
            GROUP BY COALESCE(LOWER(TRIM(store)), '')
            """,
            [date_start, date_end],
        )
        return {
            row[0]: {
                "amount": to_decimal(row[1]),
                "count": row[2],
            }
            for row in cursor.fetchall()
            if row[0]
        }


def get_designer_rewards_by_store(date_start, date_end):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                COALESCE(LOWER(TRIM(store)), '') AS store_name,
                COALESCE(SUM(amount), 0) AS designer_amount,
                COUNT(*) AS designer_count
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND oper_type IN (
                    'Дизайнерское вознаграждение из УТ10',
                    'Дизайнерское вознаграждение'
              )
              AND store IS NOT NULL
              AND TRIM(store) != ''
            GROUP BY COALESCE(LOWER(TRIM(store)), '')
            """,
            [date_start, date_end],
        )
        return {
            row[0]: {
                "amount": to_decimal(row[1]),
                "count": row[2],
            }
            for row in cursor.fetchall()
            if row[0]
        }


def get_daily_returns_map(month_start, report_date):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                date,
                COALESCE(SUM(amount), 0) AS returns_amount
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND (
                    oper_type = 'Возврат оплаты клиенту (продажа товаров, работ, услуг)'
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


def get_daily_designer_map(month_start, report_date):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                date,
                COALESCE(SUM(amount), 0) AS designer_amount
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND oper_type IN (
                    'Дизайнерское вознаграждение из УТ10',
                    'Дизайнерское вознаграждение'
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


def build_returns_analytics(report_date, income_rows):
    month_start = report_date.replace(day=1)

    returns_map = get_returns_by_store(month_start, report_date)
    designer_map = get_designer_rewards_by_store(month_start, report_date)

    daily_returns = get_daily_returns_map(month_start, report_date)
    daily_designer = get_daily_designer_map(month_start, report_date)

    enriched_rows = []

    total_income = Decimal("0")
    total_returns = Decimal("0")
    total_designer = Decimal("0")
    total_costs = Decimal("0")
    total_net_after_all = Decimal("0")

    for row in income_rows:
        store_key = row["store_name"].lower().strip()

        returns_data = returns_map.get(
            store_key,
            {"amount": Decimal("0"), "count": 0},
        )
        designer_data = designer_map.get(
            store_key,
            {"amount": Decimal("0"), "count": 0},
        )

        income = to_decimal(row["fact"])

        # ВАЖНО:
        # returns_amount и designer_amount оставляем со знаком из базы.
        # Если в базе возврат = отрицательная сумма, он останется отрицательным.
        # Если дизайнеры = отрицательная сумма, это расход.
        # Если дизайнеры = положительная сумма, это возврат/экономия.
        returns_amount = to_decimal(returns_data["amount"])
        designer_amount = to_decimal(designer_data["amount"])

        row_costs = returns_amount + designer_amount
        row_net_after_all = income + row_costs

        return_pct_of_income = (
            safe_div(returns_amount, income) * Decimal("100")
            if income > 0 else Decimal("0")
        )
        designer_pct_of_income = (
            safe_div(designer_amount, income) * Decimal("100")
            if income > 0 else Decimal("0")
        )

        total_income += income
        total_returns += returns_amount
        total_designer += designer_amount
        total_costs += row_costs
        total_net_after_all += row_net_after_all

        enriched_rows.append({
            "store_name": row["store_name"],

            "income": income,
            "income_fmt": row["fact_fmt"],

            "returns_amount": returns_amount,
            "returns_amount_fmt": fmt_money(returns_amount),
            "returns_count": returns_data["count"],
            "return_pct_of_income": return_pct_of_income,
            "return_pct_fmt": fmt_pct(return_pct_of_income),

            "net_income": income + returns_amount,
            "net_income_fmt": fmt_money(income + returns_amount),

            "designer_amount": designer_amount,
            "designer_amount_fmt": fmt_money(designer_amount),
            "designer_count": designer_data["count"],
            "designer_pct_of_income": designer_pct_of_income,
            "designer_pct_fmt": fmt_pct(designer_pct_of_income),

            "total_costs": row_costs,
            "total_costs_fmt": fmt_money(row_costs),

            "net_after_all": row_net_after_all,
            "net_after_all_fmt": fmt_money(row_net_after_all),
        })

    enriched_rows.sort(
        key=lambda x: abs(x["returns_amount"]),
        reverse=True,
    )

    total_return_pct = (
        safe_div(total_returns, total_income) * Decimal("100")
        if total_income > 0 else Decimal("0")
    )
    total_designer_pct = (
        safe_div(total_designer, total_income) * Decimal("100")
        if total_income > 0 else Decimal("0")
    )

    return {
        "rows": enriched_rows,

        "total_income": total_income,
        "total_income_fmt": fmt_money(total_income),

        "total_returns": total_returns,
        "total_returns_fmt": fmt_money(total_returns),
        "total_return_pct": total_return_pct,
        "total_return_pct_fmt": fmt_pct(total_return_pct),
        "daily_returns": daily_returns,
        "has_returns": total_returns != 0,

        "total_designer": total_designer,
        "total_designer_fmt": fmt_money(total_designer),
        "total_designer_pct": total_designer_pct,
        "total_designer_pct_fmt": fmt_pct(total_designer_pct),
        "daily_designer": daily_designer,
        "has_designer": total_designer != 0,

        "total_costs": total_costs,
        "total_costs_fmt": fmt_money(total_costs),

        "net_after_all": total_net_after_all,
        "net_after_all_fmt": fmt_money(total_net_after_all),
    }
