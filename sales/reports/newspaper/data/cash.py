# sales/reports/newspaper/data/cash.py
"""
Слой данных "Кэш" для Newspaper.

Важно: вся методология план/факта (откуда берётся факт, как считается
план, отклонение, прогноз до конца месяца, MoM/YoY) уже реализована и
проверена в ``sales.reports.sales_plan_report``. Newspaper не переизобретает
эту логику — он переиспользует её напрямую, чтобы цифры двух отчётов
никогда не расходились.

Этот файл — тонкий адаптер: он вызывает существующую функцию
``get_sales_plan_data`` и не делает никаких собственных расчётов кэша.
"""

from __future__ import annotations

from sales.reports.sales_plan_report.data import get_sales_plan_data


def get_cash_data(report_date):
    """
    Возвращает "сырой" результат существующего расчёта план/факта по кэшу.

    Структура — как в sales_plan_report.data.get_sales_plan_data:
    словарь с ключами ``rows`` (по магазинам) и ``totals`` (по компании),
    плюс служебные поля периода (report_date/month_start/...).

    Newspaper использует эти данные напрямую в data/payload.py, добавляя
    поверх только форматирование и аналитику — без изменения бизнес-логики.
    """
    return get_sales_plan_data(report_date)
