# corporate/reports/assouline/urls.py
"""URLs для Assouline"""
from django.urls import path
from . import views

app_name = 'assouline'

urlpatterns = [
    path('analyze/', views.assouline_analyze_view, name='analyze'),
    path('export-excel/', views.assouline_export_excel_view, name='export_excel'),
    path('optimize-by-budget/', views.assouline_optimize_by_budget_view, name='optimize_by_budget'),
    path('update-order/', views.assouline_update_order_view, name='update_order'),
]