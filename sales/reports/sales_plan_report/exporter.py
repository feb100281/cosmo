from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from .builder import build_sales_plan_report_context


def build_sales_plan_pdf_response(report_date, request=None):
    context = build_sales_plan_report_context(report_date, request=request)

    html = render_to_string(
        "reports/sales_plan_report/full_report.html",
        context,
    )

    css_file = (
        Path(settings.BASE_DIR)
        / "static"
        / "css"
        / "sales_plan_report"
        / "sales_plan_report.css"
    )

    stylesheets = []
    if css_file.exists():
        stylesheets.append(CSS(filename=str(css_file)))

    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(stylesheets=stylesheets)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="cash_in_performance_report_{report_date.strftime("%Y%m%d")}.pdf"'
    )
    return response