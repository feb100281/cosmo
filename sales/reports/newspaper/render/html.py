# sales/reports/newspaper/render/html.py
"""
Строит HTML-разметку отчёта из готового payload.

HTML здесь — исключительно внутренний механизм вёрстки документа для
WeasyPrint (см. render/pdf.py). Ничего не считает: весь payload уже готов
к моменту вызова render_to_string.
"""

from __future__ import annotations

from django.template.loader import render_to_string

from ..data.payload import build_report_payload

TEMPLATE_NAME = "reports/newspaper/report.html"


def build_newspaper_context(report_date, request=None) -> dict:
    payload = build_report_payload(report_date)
    return {"payload": payload}


def render_newspaper_html(report_date, request=None) -> str:
    context = build_newspaper_context(report_date, request=request)
    return render_to_string(TEMPLATE_NAME, context, request=request)
