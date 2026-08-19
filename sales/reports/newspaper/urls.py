# sales/reports/newspaper/urls.py
"""
Опциональные прямые URL для отчёта Newspaper.

Подключение — см. INTEGRATION.md. Основной сценарий использования всё же
кнопка в Django Admin, которая вызывает render/pdf.py напрямую и не требует
этих URL. Этот файл нужен, если вы хотите открывать отчёт по прямой ссылке
вида /reports/newspaper/2026-08-18/.
"""

from __future__ import annotations

from django.urls import path

from .views import newspaper_pdf_view

app_name = "newspaper"

urlpatterns = [
    path("<str:pk>/", newspaper_pdf_view, name="newspaper_pdf"),
]
