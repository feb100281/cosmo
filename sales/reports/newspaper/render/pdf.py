# sales/reports/newspaper/render/pdf.py
"""
Серверный рендер PDF через WeasyPrint.

Pipeline: DATA -> ANALYTICS -> PAYLOAD -> CHARTS -> HTML/CSS -> WEASYPRINT -> PDF.

Никакой браузерной печати: PDF формируется на сервере и возвращается как
готовый application/pdf. Постранично он полностью контролируется через
@page-правила в static/newspaper/report.css.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from weasyprint import CSS, HTML

from ..config import PDF_FILENAME_TEMPLATE
from .html import render_newspaper_html

CSS_RELATIVE_PATH = Path("static") / "newspaper" / "report.css"


def _resolve_css_path() -> Path:
    return Path(settings.BASE_DIR) / CSS_RELATIVE_PATH


def build_newspaper_pdf_bytes(report_date, request=None) -> bytes:
    html = render_newspaper_html(report_date, request=request)

    css_file = _resolve_css_path()
    stylesheets = []
    if css_file.exists():
        stylesheets.append(CSS(filename=str(css_file)))

    return HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(stylesheets=stylesheets)


def build_newspaper_pdf_response(report_date, request=None, inline: bool = True) -> HttpResponse:
    pdf_bytes = build_newspaper_pdf_bytes(report_date, request=request)

    filename = PDF_FILENAME_TEMPLATE.format(date=report_date.strftime("%Y-%m-%d"))
    disposition = "inline" if inline else "attachment"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response
