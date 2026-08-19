# sales/reports/store_plan/render/pdf.py
"""
Серверный рендер PDF через WeasyPrint — тот же pipeline, что и в Newspaper:
DATA -> PAYLOAD -> CHARTS(SVG) -> HTML/CSS -> WEASYPRINT -> PDF, без
браузерной печати.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from weasyprint import CSS, HTML

from ..config import PDF_FILENAME_TEMPLATE_ALL, PDF_FILENAME_TEMPLATE_SINGLE
from .html import render_store_plan_html

CSS_RELATIVE_PATH = Path("static") / "store_plan" / "report.css"


def _resolve_css_path() -> Path:
    return Path(settings.BASE_DIR) / CSS_RELATIVE_PATH


def build_store_plan_pdf_bytes(plan_month, store_ids=None, request=None) -> bytes:
    html = render_store_plan_html(plan_month, store_ids=store_ids, request=request)

    css_file = _resolve_css_path()
    stylesheets = []
    if css_file.exists():
        stylesheets.append(CSS(filename=str(css_file)))

    return HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(stylesheets=stylesheets)


def _build_filename(plan_month, store_ids) -> str:
    month_str = plan_month.strftime("%Y-%m")
    if store_ids and len(store_ids) == 1:
        return PDF_FILENAME_TEMPLATE_SINGLE.format(month=month_str, store_id=store_ids[0])
    return PDF_FILENAME_TEMPLATE_ALL.format(month=month_str)


def build_store_plan_pdf_response(plan_month, store_ids=None, request=None, inline: bool = True) -> HttpResponse:
    pdf_bytes = build_store_plan_pdf_bytes(plan_month, store_ids=store_ids, request=request)

    filename = _build_filename(plan_month, store_ids)
    disposition = "inline" if inline else "attachment"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response
