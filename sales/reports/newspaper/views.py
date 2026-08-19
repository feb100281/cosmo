# sales/reports/newspaper/views.py
"""
Django view для прямого доступа к отчёту по URL.

Основная точка входа — вторая кнопка в Django Admin (см. INTEGRATION.md),
которая вызывает build_newspaper_pdf_response напрямую, как это уже
устроено для старого sales_plan_report (см. admin.py -> print_plan_report).

Этот view нужен как самостоятельная точка входа: для прямых ссылок,
тестирования вне админки и потенциальной интеграции в другие места
(email-рассылка PDF, дашборд руководителя и т.д.).
"""

from __future__ import annotations

from datetime import date

from django.http import Http404

from .render.pdf import build_newspaper_pdf_response


def newspaper_pdf_view(request, pk: str):
    """
    pk — дата отчёта в формате YYYY-MM-DD (как в существующем print_plan_report).
    """
    try:
        report_date = date.fromisoformat(pk)
    except ValueError:
        raise Http404("Invalid date format. Expected YYYY-MM-DD")

    return build_newspaper_pdf_response(report_date, request=request)
