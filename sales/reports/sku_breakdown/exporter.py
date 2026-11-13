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


def compare_range(start: date, end: date) -> tuple[date, date]:
    """Период для сравнения: день/неделя/до месяца — предыдущий такой же отрезок,
    целый месяц — прошлый месяц, длиннее месяца (квартал, с начала года) — те же даты год назад."""
    from datetime import timedelta

    from dateutil.relativedelta import relativedelta

    days = (end - start).days + 1
    full_month = start.day == 1 and (end + timedelta(days=1)).day == 1 and start.month == end.month
    if full_month:
        p_end = start - timedelta(days=1)
        return p_end.replace(day=1), p_end
    if days <= 31:
        return start - timedelta(days=days), start - timedelta(days=1)
    return start - relativedelta(years=1), end - relativedelta(years=1)


def _workbook(start: date, end: date, report_type: str):
    """Книга с листами по подразделениям и сравнением с периодом из compare_range."""
    p_start, p_end = compare_range(start, end)
    df_store = get_sku_barcode_breakdown(start, end, by_store=True)
    df_prev = get_sku_barcode_breakdown(p_start, p_end, by_store=True)
    return build_workbook(without_store(df_store), report_type=report_type, start=start, end=end,
                          df_store=df_store, df_store_prev=df_prev, prev_start=p_start, prev_end=p_end)


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
