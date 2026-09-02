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

from .data import get_sku_barcode_breakdown
from .render.xlsx import build_workbook

FILENAME_PREFIX = {
    "daily": "SKU_Day",
    "weekly": "SKU_Week",
    "monthly": "SKU_Month",
}

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_sku_breakdown_xlsx_response(report_date: date, request=None) -> HttpResponse:
    report_type = classify_report(report_date)
    start, end = period_range(report_date, report_type)

    df = get_sku_barcode_breakdown(start, end)
    wb = build_workbook(df, report_type=report_type, start=start, end=end)

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
