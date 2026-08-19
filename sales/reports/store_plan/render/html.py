# sales/reports/store_plan/render/html.py
"""
Строит HTML-разметку документа "План продаж на месяц" из уже готовых
данных (см. ../data.py). Как и в Newspaper — этот файл ничего не считает,
только собирает context и рендерит шаблон.
"""

from __future__ import annotations

from datetime import date

from django.template.loader import render_to_string

from ..charts import build_plan_chart
from ..config import (
    CHART_MAX_ROWS,
    COMPANY_BRAND_NAME,
    COMPANY_LEGAL_NAME,
    COMPANY_WEBSITE,
    REPORT_TITLE,
)
from ..data import get_store_plan_payload

TEMPLATE_NAME = "reports/store_plan/report.html"


def build_store_plan_context(plan_month, store_ids=None, request=None) -> dict:
    payload = get_store_plan_payload(plan_month, store_ids=store_ids)

    # Страница всегда двухколоночная: график слева, таблица справа (см.
    # .plan-columns в report.css). Таблица показывает всех магазинов без
    # ограничений и при необходимости продолжается на следующей странице;
    # график ограничен CHART_MAX_ROWS — это только про читаемость самих
    # баров, не про вёрстку страницы.
    chart_rows = payload["rows"]
    chart_truncated = len(chart_rows) > CHART_MAX_ROWS
    if chart_truncated:
        chart_rows = chart_rows[:CHART_MAX_ROWS]
    payload["chart_truncated"] = chart_truncated
    payload["chart"] = build_plan_chart(chart_rows)
    payload["company"] = {
        "brand_name": COMPANY_BRAND_NAME,
        "legal_name": COMPANY_LEGAL_NAME,
        "website": COMPANY_WEBSITE,
    }
    payload["meta"] = {
        "title": REPORT_TITLE,
        "generated_at_fmt": date.today().strftime("%d.%m.%Y"),
    }
    return {"payload": payload}


def render_store_plan_html(plan_month, store_ids=None, request=None) -> str:
    context = build_store_plan_context(plan_month, store_ids=store_ids, request=request)
    return render_to_string(TEMPLATE_NAME, context, request=request)
