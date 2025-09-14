from django.contrib import admin
from django.template.response import TemplateResponse
from .models import SalesDash, CatDash, SalesReport


class SalesDashAdmin(admin.ModelAdmin):
    change_list_template = "admin/dashboard/salesdash/dummydash.html"

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["app_label"] = "dashboard"  # ⚠️ <-- имя твоего приложения
        return TemplateResponse(request, self.change_list_template, extra_context)

class CatDashAdmin(admin.ModelAdmin):
    change_list_template = "admin/dashboard/salesdash/test.html"

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["app_label"] = "dashboard"  # ⚠️ <-- имя твоего приложения
        return TemplateResponse(request, self.change_list_template, extra_context)

from django.contrib import admin
from django.template.response import TemplateResponse
from .models import SalesReport

class SalesReportAdmin(admin.ModelAdmin):
    change_list_template = "admin/dashboard/salesdash/sales_report.html"
    
    def has_add_permission(self, request):
        return False  # Запрещаем добавление
    
    def has_change_permission(self, request, obj=None):
        return False  # Запрещаем изменение
    
    def has_delete_permission(self, request, obj=None):
        return False  # Запрещаем удаление
    
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        
        extra_context.update({
            'title': 'Панель продаж',
            'dash_url': 'http://127.0.0.1:8050',  # URL вашего Dash
        })
        
        return TemplateResponse(request, self.change_list_template, extra_context)

admin.site.register(SalesReport, SalesReportAdmin)


admin.site.register(SalesDash, SalesDashAdmin)
admin.site.register(CatDash, CatDashAdmin)



