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
                COALESCE(SUM(ABS(amount)), 0) AS returns_amount,  -- <-- ABS()
                COUNT(*) AS returns_count
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND (
                    oper_type = 'Возврат или иная оплата клиенту'
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
                "amount": Decimal(str(row[1] or 0)),
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
                COALESCE(SUM(ABS(amount)), 0) AS returns_amount  -- <-- ABS()
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
        
        
def build_returns_analytics(report_date, income_rows):
    """
    Формирует аналитику по возвратам для отчёта
    
    income_rows — это sales_plan.rows из основного отчёта (с приходами)
    """
    month_start = report_date.replace(day=1)
    
    returns_map = get_returns_by_store(month_start, report_date)
    daily_returns = get_daily_returns_map(month_start, report_date)
    
    # Обогащаем строки магазинов данными по возвратам
    enriched_rows = []
    total_returns = Decimal("0")
    total_income = Decimal("0")
    
    for row in income_rows:
        store_key = row["store_name"].lower().strip()
        returns_data = returns_map.get(store_key, {"amount": Decimal("0"), "count": 0})
        
        returns_amount = returns_data["amount"]
        income = row["fact"]
        
        total_returns += returns_amount
        total_income += income
        
        return_pct_of_income = safe_div(returns_amount, income) * Decimal("100") if income > 0 else Decimal("0")
        
        enriched_rows.append({
            "store_name": row["store_name"],
            "income": income,
            "income_fmt": row["fact_fmt"],
            "returns_amount": returns_amount,
            "returns_amount_fmt": fmt_money(returns_amount),
            "returns_count": returns_data["count"],
            "return_pct_of_income": return_pct_of_income,
            "return_pct_fmt": fmt_pct(return_pct_of_income),
            "net_income": income - returns_amount,
            "net_income_fmt": fmt_money(income - returns_amount),
        })
    
    # Сортируем по сумме возвратов
    enriched_rows.sort(key=lambda x: x["returns_amount"], reverse=True)
    
    total_return_pct = safe_div(total_returns, total_income) * Decimal("100") if total_income > 0 else Decimal("0")
    
    return {
        "rows": enriched_rows,
        "total_returns": total_returns,
        "total_returns_fmt": fmt_money(total_returns),
        "total_income": total_income,
        "total_income_fmt": fmt_money(total_income),
        "total_return_pct": total_return_pct,
        "total_return_pct_fmt": fmt_pct(total_return_pct),
        "daily_returns": daily_returns,
        "has_returns": total_returns > 0,
    }