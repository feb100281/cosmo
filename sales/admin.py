from django.contrib import admin
from django.urls import path, reverse

from .models import SalesData,MV_Daily_Sales
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from datetime import date
from sales.dash_apps.dailysales.data import get_month_data, get_ytd_data


from django.utils.html import format_html
from django import forms
from django.utils.safestring import mark_safe

from .print_utils import (
    build_mtd_table,     # -> str (готовый HTML таблицы)
    build_ytd_table,     # -> str (готовый HTML таблицы)

)




class SalesDataAdmin(admin.ModelAdmin):
    list_display = ('date','operation','store','icon_preview','amount_tot','quant_tot')
    list_filter = ("date","operation","store__gr",)
    fieldsets = (
        ("Основное", {
            "fields": ("date", "operation", "dt", "cr","quant_dt","quant_cr")
        }),
        ("Скидки", {
            "fields": ("amount_undisc","discount_auto",'discount_design',"discount_amount","discount_percent_auto","discount_percent_design",'diccount_percent')
        }),
        
    )
    def amount_tot(self, obj):
        amount = obj.dt - obj.cr
        return amount
    amount_tot.short_description = "Сумма"
    
    def quant_tot(self, obj):
        amount = obj.quant_dt - obj.quant_cr
        return amount
    quant_tot.short_description = "Количество"
    
    def icon_preview(self, obj):
        if obj.item.cat and obj.item.cat.icon and obj.item.cat.icon.strip().startswith('<svg'):
            return format_html(
                '{}&nbsp;<strong>{}</strong>',
                mark_safe(obj.item.cat.icon),
                obj.item
            )
        return obj.item
    icon_preview.short_description = 'Наименование'
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
    

@admin.register(MV_Daily_Sales)
class MVSalesDailyAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "amount",         
        "quant",
        "orders",
        "ave_check",
        "dt",
        "cr",
        "rtr_ratio", 
        "print_link",
    )
    search_fields = ("date",)
    # list_filter = ("date", )
    list_per_page = 25
    date_hierarchy = "date"

    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
    
    
        # --- Кнопка печати в списке ---
    @admin.display(description="Печать")
    def print_link(self, obj):
        url = reverse(
            f"admin:{MV_Daily_Sales._meta.app_label}_{MV_Daily_Sales._meta.model_name}_print",
            args=[obj.pk.isoformat()],  # pk у тебя date => безопасно делаем строку
        )
        return format_html(
            '<a href="{}" title="Печать отчёта" style="text-decoration:none;font-size:14px;">🖨</a>',
            url,
        )

    # --- Добавляем кастомный url /print/ ---
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<slug:pk>/print/",
                self.admin_site.admin_view(self.print_daily_sales),
                name=f"{MV_Daily_Sales._meta.app_label}_{MV_Daily_Sales._meta.model_name}_print",
            ),
        ]
        return my_urls + urls

    # --- View печати ---
    def print_daily_sales(self, request, pk: str):
        # pk приходит как 'YYYY-MM-DD'
        try:
            d = date.fromisoformat(pk)
        except ValueError:
            raise Http404("Invalid date format. Expected YYYY-MM-DD")

        obj = get_object_or_404(MV_Daily_Sales, pk=d)

        # сырые данные (как в dash)
        df_mtd_raw = get_month_data(d)
        df_ytd_raw = get_ytd_data(d)

        # таблицы (в print_utils делай красивый HTML и стили)
        table_mtd = build_mtd_table(df_mtd_raw)
        table_ytd = build_ytd_table(df_ytd_raw)




        context = {
            "obj": obj,
            "report_date": d,
            "table_mtd_html": table_mtd["html"],
            "table_ytd_html": table_ytd["html"],
            "src": request.GET.get("src", "list"),
        }
        return render(request, "admin/daily_sales_print.html", context)
    
    
    
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # если тебе не нужен object_id, можно оставить статикой:
        extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        # если нужно фильтровать даш по конкретной записи/дате:
        # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )
        
    



    
# admin.site.register(SalesData,SalesDataAdmin)


