from django.contrib import admin
from django.template.response import TemplateResponse
from .models import SalesDash, CatDash


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

admin.site.register(SalesDash, SalesDashAdmin)
admin.site.register(CatDash, CatDashAdmin)


