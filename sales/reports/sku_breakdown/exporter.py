# sales/reports/sku_breakdown/exporter.py
"""
HTTP-обёртка над отчётом "Разбивка по номенклатуре и штрихкодам".

Принимает дату — так же, как остальные кнопки в MV_Daily_Sales admin
(🖨/📊/📰/📈) — и сама определяет тип периода (день/неделя/месяц) тем же
правилом, что и Newspaper/Sales Digest:
sales.reports.sales_report.period.classify_report (последний день месяца —
месячный отчёт, воскресенье — недельный, иначе — дневной).
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

from django.http import HttpResponse

from sales.reports.sales_report.period import classify_report
from sales.reports.sales_report.ranges import period_range

from .data import get_sku_barcode_breakdown, without_store
from .render.xlsx import build_workbook

FILENAME_PREFIX = {
    "daily": "SKU_Day",
    "weekly": "SKU_Week",
    "monthly": "SKU_Month",
}

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _workbook(start: date, end: date, report_type: str):
    """Книга с листами по подразделениям и сравнением с прошлым периодом той же длины."""
    from sales.reports.meeting_brief.periods import Periods

    p = Periods(start, end)
    df_store = get_sku_barcode_breakdown(start, end, by_store=True)
    df_prev = get_sku_barcode_breakdown(p.prev_start, p.prev_end, by_store=True)
    return build_workbook(without_store(df_store), report_type=report_type, start=start, end=end,
                          df_store=df_store, df_store_prev=df_prev, prev_text=p.prev_range_label)


def build_sku_breakdown_xlsx_response(report_date: date, request=None) -> HttpResponse:
    report_type = classify_report(report_date)
    start, end = period_range(report_date, report_type)

    wb = _workbook(start, end, report_type)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f'{FILENAME_PREFIX.get(report_type, "SKU")}_{report_date:%Y%m%d}.xlsx'

    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # Та же причина, что и у PDF-экспортёров: без этого браузер может
    # отдать закешированный файл по тому же URL вместо свежего.
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response


def build_sku_breakdown_period_response(start: date, end: date) -> HttpResponse:
    """Тот же отчёт за произвольный период [start, end]; один день — start == end."""
    report_type = "daily" if start == end else "period"
    wb = _workbook(start, end, report_type)

    buffer = BytesIO()
    wb.save(buffer)
    name = f"SKU_{start:%Y%m%d}.xlsx" if start == end else f"SKU_{start:%Y%m%d}_{end:%Y%m%d}.xlsx"

    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response
