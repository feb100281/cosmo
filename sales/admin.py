from django.contrib import admin
from .models import SalesData,MV_Daily_Sales,MVSalesOrder

from django.utils.html import format_html
from django import forms
from django.utils.safestring import mark_safe

# Register your models here.

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
        "rtr_ratio"
    )
    search_fields = ("date",)
    list_filter = ("date", )
    list_per_page = 25
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
    
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # если тебе не нужен object_id, можно оставить статикой:
        extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        # если нужно фильтровать даш по конкретной записи/дате:
        # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )
        
    
@admin.register(MVSalesOrder)
class MVSalesOrderAdmin(admin.ModelAdmin):
    
    # ПОЛЯ ЧТО Б НЕ ЛАЗИТЬ `orders_id`, `client_order_type`, `client_order`, `client_order_number`, `client_order_date`, `order_min_date`, `order_max_date`, `realization_duration`, `order_duration`, `sales`, `returns`, `amount`, `items_amount`, `service_amount`, `items_quant`, `unique_items`, `manager_name`
    
    list_display = (
        "client_order_type",
        "client_order",
        "client_order_date",
        "order_min_date",
        "order_max_date",
        "order_duration",
        "sales",
        "returns",
        "amount",
        "items_amount",
        "service_amount",
        "items_quant",
        "unique_items",
        "manager_name"
    )
    search_fields = ("client_order_date","manager_name")
    list_filter = ("client_order_date","manager_name" )
    list_per_page = 25
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}


    
# admin.site.register(SalesData,SalesDataAdmin)


