from django.contrib import admin
from django.template.response import TemplateResponse
from .models import SalesReport #SalesDash, CatDash, SalesReport
from django.utils.html import format_html
from django.conf import settings
from django.http import HttpResponseRedirect


# class SalesDashAdmin(admin.ModelAdmin):
#     change_list_template = "admin/dashboard/salesdash/dummydash.html"

#     def changelist_view(self, request, extra_context=None):
#         if extra_context is None:
#             extra_context = {}
#         extra_context["app_label"] = "dashboard"  # ⚠️ <-- имя твоего приложения
#         return TemplateResponse(request, self.change_list_template, extra_context)

# class CatDashAdmin(admin.ModelAdmin):
#     change_list_template = "admin/dashboard/salesdash/test.html"

#     def changelist_view(self, request, extra_context=None):
#         if extra_context is None:
#             extra_context = {}
#         extra_context["app_label"] = "dashboard"  # ⚠️ <-- имя твоего приложения
#         return TemplateResponse(request, self.change_list_template, extra_context)

from django.contrib import admin
from django.template.response import TemplateResponse
from .models import SalesReport

@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        key = getattr(settings, "SALES_REPORT_KEY", "no-key")
        url = f"http://37.46.129.233:8050/?key={key}"
        return HttpResponseRedirect(url)


# admin.site.register(SalesDash, SalesDashAdmin)
# admin.site.register(CatDash, CatDashAdmin)



