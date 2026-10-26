# sales/reports/meeting_brief/urls.py
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path("", admin.site.admin_view(views.form_view), name="meeting_brief"),
    path("report/", admin.site.admin_view(views.report_view), name="meeting_brief_report"),
]
