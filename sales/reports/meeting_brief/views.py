# sales/reports/meeting_brief/views.py
"""Страница выбора периода, просмотр отчёта и PDF."""
from __future__ import annotations

from datetime import date
from html import escape
from urllib.parse import urlencode

from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from . import config as C
from .insights import build_insights
from .metrics import build_metrics
from .orders_xlsx import build_orders_excel
from .periods import Periods, last_full_week, presets
from .render import render_html
from .sources import load_all, load_exclusions, load_managers, load_orders, load_paid, load_shipped
from .tasks import build_tasks, build_tasks_excel

MAX_DAYS = 366


def _parse(request) -> tuple[Periods | None, str]:
    try:
        d1 = date.fromisoformat(request.GET.get("start", ""))
        d2 = date.fromisoformat(request.GET.get("end", ""))
    except ValueError:
        return None, "Укажите даты начала и конца периода"
    if d1 > d2:
        return None, "Дата начала позже даты окончания"
    if (d2 - d1).days + 1 > MAX_DAYS:
        return None, f"Период не может быть длиннее {MAX_DAYS} дней"
    return Periods(d1, d2), ""


def build_report_html(p: Periods, toolbar: str = "", src: dict | None = None) -> str:
    metrics = build_metrics(src or load_all(p), p)
    return render_html(metrics, build_insights(metrics, p), p, toolbar=toolbar)


def build_tasks_bytes(p: Periods, src: dict | None = None) -> bytes:
    orders = src["orders"] if src else load_orders()
    managers = src["managers"] if src else load_managers()
    ex = src["exclusions"] if src else load_exclusions()
    return build_tasks_excel(build_tasks(orders, managers, p, ex), p,
                             build_tasks(orders, managers, p, ex, only_excluded=True))


def _attachment(data: bytes, name: str, content_type: str) -> HttpResponse:
    resp = HttpResponse(data, content_type=content_type)
    resp["Content-Disposition"] = f"attachment; filename*=UTF-8''{_quote(name)}"
    resp["Cache-Control"] = "no-store"
    return resp


def form_view(request):
    default = last_full_week()
    context = {
        **admin.site.each_context(request),
        "title": C.REPORT_TITLE,
        "start": request.GET.get("start") or default.start.isoformat(),
        "end": request.GET.get("end") or default.end.isoformat(),
        "presets": [{"name": n, "start": a.isoformat(), "end": b.isoformat()} for n, a, b in presets()],
        "error": request.GET.get("error", ""),
        "report_url": reverse("meeting_brief_report"),
    }
    return render(request, "admin/meeting_brief/form.html", context)


def report_view(request):
    p, error = _parse(request)
    if p is None:
        return HttpResponse(escape(error), status=400, content_type="text/plain; charset=utf-8")

    qs = urlencode({"start": p.start.isoformat(), "end": p.end.isoformat()})
    fmt = request.GET.get("format")
    stamp = f"{p.start:%d.%m.%Y}_{p.end:%d.%m.%Y}"
    xlsx_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    if fmt == "xlsx":
        return _attachment(build_tasks_bytes(p), C.TASKS_FILENAME.format(stamp=stamp), xlsx_type)

    if fmt == "orders":
        src = {"orders": load_orders(), "managers": load_managers(), "exclusions": load_exclusions(),
               "paid_end": load_paid(p.end), "shipped_end": load_shipped(p.end)}
        return _attachment(build_orders_excel(src, p), C.ORDERS_FILENAME.format(stamp=stamp), xlsx_type)

    if fmt in ("pdf", "zip"):
        from weasyprint import HTML

        src = load_all(p)
        pdf = HTML(string=build_report_html(p, src=src)).write_pdf()
        pdf_name = C.PDF_FILENAME.format(start=f"{p.start:%d.%m.%Y}", end=f"{p.end:%d.%m.%Y}")
        if fmt == "pdf":
            return _attachment(pdf, pdf_name, "application/pdf")

        import zipfile
        from io import BytesIO

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(pdf_name, pdf)
            z.writestr(C.TASKS_FILENAME.format(stamp=stamp), build_tasks_bytes(p, src))
            z.writestr(C.ORDERS_FILENAME.format(stamp=stamp), build_orders_excel(src, p))
        return _attachment(buf.getvalue(), C.ZIP_FILENAME.format(stamp=stamp), "application/zip")

    toolbar = (
        '<div class="toolbar">'
        f'<a href="{reverse("meeting_brief")}?{qs}">← Изменить период</a>'
        f'<span class="sp"></span><span>{escape(p.label)}</span>'
        f'<a class="primary" href="?{qs}&format=pdf">Скачать PDF</a>'
        f'<a href="?{qs}&format=xlsx">Excel по менеджерам</a>'
        f'<a href="?{qs}&format=orders">Заказы по подразделениям</a>'
        '<button onclick="window.print()">Печать</button>'
        '</div>'
    )
    resp = HttpResponse(build_report_html(p, toolbar))
    resp["Cache-Control"] = "no-store"
    return resp


def _quote(name: str) -> str:
    from urllib.parse import quote
    return quote(name)
