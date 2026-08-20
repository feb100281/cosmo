# sales/reports/sales_digest/render/pdf.py
"""
Серверный рендер PDF через WeasyPrint — тот же pipeline, что у newspaper:
HTML/CSS -> WeasyPrint -> PDF. Никакой браузерной печати.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from ..config import PDF_FILENAME_PREFIX
from .html import build_sales_digest_context

TEMPLATE_NAME = "reports/sales_digest/report.html"
CSS_RELATIVE_PATH = Path("static") / "sales_digest" / "report.css"


def _resolve_css_path() -> Path:
    return Path(settings.BASE_DIR) / CSS_RELATIVE_PATH


def build_sales_digest_pdf_response(report_date, request=None, inline: bool = True) -> HttpResponse:
    # Один расчёт контекста на весь рендер (report_type нужен и для имени
    # файла, и для самого HTML) — build_daily_sales_report_context вызывается
    # только один раз.
    context = build_sales_digest_context(report_date, request=request)
    html = render_to_string(TEMPLATE_NAME, context, request=request)

    css_file = _resolve_css_path()
    stylesheets = []
    if css_file.exists():
        stylesheets.append(CSS(filename=str(css_file)))

    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(stylesheets=stylesheets)

    prefix = PDF_FILENAME_PREFIX.get(context["report_type"], "Sales_Digest")
    filename = f"{prefix}_{report_date.strftime('%Y-%m-%d')}.pdf"
    disposition = "inline" if inline else "attachment"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    # Свежий PDF при каждой печати — без этого браузер может показать
    # старую закешированную версию по тому же URL (уже наступали на эти
    # грабли с другим отчётом в этом же проекте).
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response
