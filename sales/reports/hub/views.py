# sales/reports/hub/views.py
"""Раздел «Отчёты»: список отчётов и формы выгрузки за период."""
from __future__ import annotations

from datetime import date, timedelta

from django.contrib import admin
from django.shortcuts import render
from django.urls import reverse

from sales.reports.meeting_brief.periods import presets

MAX_DAYS = 366

REPORTS = [
    {
        "title": "Отчёт к совещанию",
        "text": "Деньги и план, заказы по менеджерам и подразделениям, контроль заказов, остатки. "
                "PDF, Excel с задачами менеджерам и Excel по заказам.",
        "url_name": "meeting_brief",
        "icon": "fa-solid fa-people-group",
    },
    {
        "title": "Продажи по SKU",
        "text": "Excel: продажи и возвраты по номенклатуре и штрихкодам, с разбивкой по категориям "
                "и производителям. Любой период, в том числе один день.",
        "url_name": "reports_sku",
        "icon": "fa-solid fa-barcode",
    },
]


def _presets() -> list[dict]:
    today = date.today()
    yesterday = today - timedelta(days=1)
    items = [("Вчера", yesterday, yesterday)] + presets(today)
    return [{"name": n, "start": a.isoformat(), "end": b.isoformat()} for n, a, b in items]


def hub_view(request):
    reports = [{**r, "url": reverse(r["url_name"])} for r in REPORTS]
    context = {**admin.site.each_context(request), "title": "Отчёты", "reports": reports}
    return render(request, "admin/reports/hub.html", context)


def sku_view(request):
    yesterday = date.today() - timedelta(days=1)
    error = ""
    start_s = request.GET.get("start") or yesterday.isoformat()
    end_s = request.GET.get("end") or start_s

    if request.GET.get("download"):
        try:
            start, end = date.fromisoformat(start_s), date.fromisoformat(end_s)
        except ValueError:
            error = "Укажите даты начала и конца периода"
        else:
            if start > end:
                error = "Дата начала позже даты окончания"
            elif (end - start).days + 1 > MAX_DAYS:
                error = f"Период не может быть длиннее {MAX_DAYS} дней"
            else:
                from sales.reports.sku_breakdown.exporter import build_sku_breakdown_period_response

                return build_sku_breakdown_period_response(start, end)

    context = {
        **admin.site.each_context(request),
        "title": "Продажи по SKU",
        "start": start_s,
        "end": end_s,
        "presets": _presets(),
        "error": error,
        "hub_url": reverse("reports_hub"),
    }
    return render(request, "admin/reports/sku.html", context)
