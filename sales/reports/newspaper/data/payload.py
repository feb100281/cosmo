# sales/reports/newspaper/data/payload.py
"""
Собирает единый payload отчёта из данных + аналитики + графиков.

Это единственная точка, которую вызывает render-слой. Шаблон (report.html)
не делает расчётов — он только показывает то, что уже подготовлено здесь.

    payload = {
        "meta": {...},
        "company": {...},
        "cash": {...},
        "stocks": {...},
        "stores": [...],
        "insights": [...],
        "charts": {...},
    }
"""

from __future__ import annotations

from ..analytics.cash import analyze_cash
from ..analytics.cash_ytd import analyze_cash_ytd
from ..analytics.insights import build_insights
from ..analytics.narrative import (
    build_cash_lead,
    build_cash_ytd_lead,
    build_returns_lead,
    build_stocks_lead,
)
from ..analytics.stocks import analyze_stocks
from ..analytics.stores import build_store_sections
from ..charts.cash import build_cash_pace_chart, build_cash_share_donut, build_store_pace_chart
from ..charts.cash_ytd import build_cash_ytd_monthly_chart, build_cash_ytd_pace_chart
from ..charts.stocks import build_stock_distribution_chart
from ..config import (
    COMPANY_BRAND_NAME,
    COMPANY_LEGAL_NAME,
    COMPANY_WEBSITE,
    MAX_INSIGHTS_ON_COVER,
    REPORT_SUBTITLE,
    REPORT_TITLE,
)
from ..render.helpers import (
    fmt_money,
    fmt_money_mln_or_rub,
    fmt_money_short,
    fmt_pct,
    fmt_qty,
    nbsp,
)
from .cash import get_cash_data, get_cash_ytd_data
from .stocks import UNASSIGNED_LABEL, get_stocks_data


def _nbsp_calendar(calendar: dict) -> dict:
    """
    Проставляет неразрывные пробелы во всех уже отформатированных денежных
    строках календаря, чтобы разряды числа не переносились на новую строку
    в узкой ячейке дня (напр. "1 629 032" не должно рваться на "1" и
    "629 032"). Считать заново ничего не нужно — только пробел в уже
    готовой строке.
    """
    calendar["daily_plan_fmt"] = nbsp(calendar.get("daily_plan_fmt"))
    for week in calendar.get("weeks", []):
        for day in week.get("days", []):
            day["amount_fmt"] = nbsp(day.get("amount_fmt"))
            day["returns_amount_fmt"] = nbsp(day.get("returns_amount_fmt"))
            day["netto_amount_fmt"] = nbsp(day.get("netto_amount_fmt"))
        summary = week.get("summary")
        if summary:
            summary["week_fact_fmt"] = nbsp(summary.get("week_fact_fmt"))
            summary["week_plan_fmt"] = nbsp(summary.get("week_plan_fmt"))
            summary["week_plan_to_date_fmt"] = nbsp(summary.get("week_plan_to_date_fmt"))
    return calendar


def _nbsp_ytd_rows(rows: list) -> list:
    """
    Неразрывные пробелы в уже готовых денежных строках YTD-таблицы по
    магазинам — та же причина, что и в _nbsp_calendar/cash_data.rows: узкая
    колонка не должна переносить "9 000 000" на "9" и "000 000".
    """
    return [
        {
            **row,
            "plan_to_date_fmt": nbsp(row.get("plan_to_date_fmt")),
            "fact_fmt": nbsp(row.get("fact_fmt")),
            "prev_year_fact_fmt": nbsp(row.get("prev_year_fact_fmt")),
        }
        for row in rows
    ]


def _returns_payload(returns_data: dict) -> dict:
    """
    Оборачивает уже готовую sales_plan_report.returns_analytics (возвраты +
    дизайнерское вознаграждение по магазинам) под шаблон отчёта: только
    неразрывные пробелы в уже отформатированных суммах, никаких новых
    расчётов — сама аналитика полностью переиспользуется как есть.
    """
    rows_fmt = [
        {
            **row,
            "income_fmt": nbsp(row.get("income_fmt")),
            "returns_amount_fmt": nbsp(row.get("returns_amount_fmt")),
            "designer_amount_fmt": nbsp(row.get("designer_amount_fmt")),
            "net_after_all_fmt": nbsp(row.get("net_after_all_fmt")),
        }
        for row in returns_data.get("rows", [])
    ]
    return {
        "rows": rows_fmt,
        "total_income_fmt": nbsp(returns_data.get("total_income_fmt")),
        "total_returns_fmt": nbsp(returns_data.get("total_returns_fmt")),
        "total_return_pct_fmt": returns_data.get("total_return_pct_fmt"),
        "total_designer_fmt": nbsp(returns_data.get("total_designer_fmt")),
        "total_designer_pct_fmt": returns_data.get("total_designer_pct_fmt"),
        "net_after_all_fmt": nbsp(returns_data.get("net_after_all_fmt")),
        "has_returns": bool(returns_data.get("has_returns")),
        "has_designer": bool(returns_data.get("has_designer")),
    }


def build_report_payload(report_date) -> dict:
    cash_data = get_cash_data(report_date)
    # Важно: берём ВСЕ магазины из cash-отчёта, включая те, у которых нет
    # плана по кэшу (has_plan=False) — например, недавно открытые точки.
    # Если отфильтровать только магазины с планом, их остатки не найдут
    # соответствия в _build_store_matcher и покажутся под сырым названием
    # склада вместо привычного имени магазина — план по кэшу и наличие
    # остатков никак не связаны.
    store_names = [r["store_name"] for r in cash_data["rows"]]

    stocks_data = get_stocks_data(report_date, store_names)

    # Короткие форматы для узких колонок таблицы по магазинам (Осталось /
    # Нужно в день / Прогноз) — сама Decimal-величина не меняется, меняется
    # только форма записи (напр. "1,2 млн" вместо "1 200 000"), чтобы строка
    # помещалась по ширине даже при длинных названиях магазинов.
    for row in cash_data["rows"]:
        row["remaining_fmt_short"] = nbsp(fmt_money_short(row["remaining"]))
        row["required_daily_fmt_short"] = nbsp(fmt_money_short(row["required_daily"]))
        row["projected_month_fact_fmt_short"] = nbsp(fmt_money_short(row["projected_month_fact"]))
        row["plan_fmt"] = nbsp(row.get("plan_fmt"))
        row["fact_fmt"] = nbsp(row.get("fact_fmt"))

    cash_data["cash_calendar"] = _nbsp_calendar(cash_data["cash_calendar"])

    cash_analytics = analyze_cash(cash_data)
    stocks_analytics = analyze_stocks(stocks_data)
    store_sections = build_store_sections(cash_data, stocks_data)

    ytd_data = get_cash_ytd_data(report_date)
    ytd_analytics = analyze_cash_ytd(ytd_data)

    insights = build_insights(
        cash_data, cash_analytics, stocks_data, stocks_analytics, store_sections,
        ytd_data=ytd_data, ytd_analytics=ytd_analytics,
    )

    charts = {
        "cash_pace": build_cash_pace_chart(cash_data),
        "store_pace": build_store_pace_chart(cash_data),
        "cash_share": build_cash_share_donut(cash_data),
        "stock_distribution": build_stock_distribution_chart(stocks_data, UNASSIGNED_LABEL),
        "cash_ytd_pace": build_cash_ytd_pace_chart(ytd_data),
        "cash_ytd_monthly": build_cash_ytd_monthly_chart(ytd_data),
    }

    cash_lead = build_cash_lead(cash_data, cash_analytics)
    cash_ytd_lead = build_cash_ytd_lead(ytd_data, ytd_analytics)
    stocks_lead = build_stocks_lead(stocks_data, stocks_analytics)

    # Возвраты и дизайнерское вознаграждение — это уже готовая аналитика из
    # sales_plan_report (build_returns_analytics), просто раньше она не
    # выводилась в Newspaper. Ничего не пересчитываем, только оборачиваем.
    returns_data = cash_data.get("returns_analytics") or {}
    has_returns_section = bool(returns_data.get("rows"))
    returns_payload = _returns_payload(returns_data) if has_returns_section else None
    returns_lead = build_returns_lead(returns_data) if has_returns_section else ""

    totals = cash_data["totals"]
    company_stock = stocks_data["company"]

    top_categories_fmt = [
        {
            **cat,
            "qty_available_fmt": fmt_qty(cat["qty_available"]),
        }
        for cat in stocks_data["top_categories"]
    ]

    unassigned_bucket = stocks_data["unassigned_bucket"]
    unassigned_bucket_fmt = {
        **unassigned_bucket,
        "qty_available_fmt": fmt_qty(unassigned_bucket["qty_available"]),
        "qty_ordered_fmt": fmt_qty(unassigned_bucket["qty_ordered"]),
    }

    # Полный список подразделений (магазины + физические склады) — без
    # группировки в общий бакет, каждое под своим названием, как оно
    # записано в warehouse_stocks. "is_overstocked" проставлен только для
    # магазинов, которые есть и в cash-отчёте (для них есть с чем сравнить
    # долю остатков и долю кэша); для чисто складских позиций флага нет.
    overstock_by_name = {s["store_name"]: s["is_overstocked"] for s in store_sections}
    known_store_names = set(store_names)
    stock_locations = sorted(
        (
            {
                "name": name,
                "qty_available": vals["qty_available"],
                "qty_available_fmt": fmt_qty(vals["qty_available"]),
                "is_known_store": name in known_store_names,
                "is_overstocked": overstock_by_name.get(name, False),
            }
            for name, vals in stocks_data["by_store"].items()
        ),
        key=lambda x: x["qty_available"],
        reverse=True,
    )

    return {
        "meta": {
            "report_date": report_date,
            "report_date_fmt": report_date.strftime("%d.%m.%Y"),
            "report_date_iso": report_date.strftime("%Y-%m-%d"),
            "weekday_ru": _weekday_ru(report_date),
            "month_year_fmt": f"{_MONTHS_RU[report_date.month - 1]}, {report_date.year}",
            "title": REPORT_TITLE,
            "subtitle": REPORT_SUBTITLE,
            "generated_at_fmt": report_date.strftime("%d.%m.%Y"),
        },
        "company": {
            "brand_name": COMPANY_BRAND_NAME,
            "legal_name": COMPANY_LEGAL_NAME,
            "website": COMPANY_WEBSITE,
        },
        "cash": {
            "totals": totals,
            "rows": cash_data["rows"],
            "days_in_month": cash_data["days_in_month"],
            "days_passed": cash_data["days_passed"],
            "days_left": cash_data["days_left"],
            "analytics": cash_analytics,
            "plan_fmt": fmt_money_short(totals["plan"]),
            "fact_fmt": fmt_money_short(totals["fact"]),
            "forecast_fmt": fmt_money_short(totals["projected_month_fact"]),
            "exec_pct_fmt": fmt_pct(totals["exec_pct"]),
            "lead": cash_lead,
            "calendar": cash_data["cash_calendar"],
        },
        "cash_ytd": {
            "totals": ytd_data["totals"],
            "rows": _nbsp_ytd_rows([r for r in ytd_data["rows"] if r["has_plan"]]),
            "monthly": ytd_data["monthly"],
            "days_passed_year": ytd_data["days_passed_year"],
            "days_in_year": ytd_data["days_in_year"],
            "analytics": ytd_analytics,
            "plan_to_date_fmt": fmt_money_short(ytd_data["totals"]["plan_to_date"]),
            "plan_year_full_fmt": fmt_money_short(ytd_data["totals"]["plan_year_full"]),
            "fact_fmt": fmt_money_short(ytd_data["totals"]["fact"]),
            "forecast_fmt": fmt_money_short(ytd_data["totals"]["projected_year_fact"]),
            "exec_pct_fmt": fmt_pct(ytd_data["totals"]["exec_pct"]),
            "year_pct_fmt": fmt_pct(ytd_data["totals"]["year_pct"]),
            "lead": cash_ytd_lead,
            # План на год заведён не на все 12 месяцев (см. data.cash /
            # sales_plan_report.get_cash_ytd_data) — годовые метрики прячем
            # в шаблоне, пока флаг не станет True.
            "plan_year_complete": ytd_analytics["plan_year_complete"],
            "has_plan_to_date": ytd_analytics["has_plan_to_date"],
            "is_behind_amount": ytd_analytics["is_behind_amount"],
            "diff_to_date_fmt": fmt_money_short(abs(ytd_analytics["diff_to_date"])),
        },
        "stocks": {
            "company": company_stock,
            "qty_total_fmt": fmt_qty(company_stock["qty_total"]),
            "qty_available_fmt": fmt_qty(company_stock["qty_available"]),
            "qty_ordered_fmt": fmt_qty(company_stock["qty_ordered"]),
            "sku_count_with_stock": stocks_data["sku_count_with_stock"],
            "top_categories": top_categories_fmt,
            "locations": stock_locations,
            "unassigned_bucket": unassigned_bucket_fmt,
            "unassigned_label": UNASSIGNED_LABEL,
            "analytics": stocks_analytics,
            "lead": stocks_lead,
        },
        "returns": returns_payload,
        "returns_lead": returns_lead,
        "stores": store_sections,
        "insights": insights,
        "insights_cover": insights[:MAX_INSIGHTS_ON_COVER],
        "charts": charts,
    }


_WEEKDAYS_RU = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]

_MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def _weekday_ru(report_date) -> str:
    return _WEEKDAYS_RU[report_date.weekday()]
