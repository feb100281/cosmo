# sales/reports/hub/urls.py
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path("", admin.site.admin_view(views.hub_view), name="reports_hub"),
    path("sku/", admin.site.admin_view(views.sku_view), name="reports_sku"),
]
