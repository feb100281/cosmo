from django.contrib import admin
from .models import SalesData,MV_Daily_Sales,MVSalesOrder
from django.urls import path, reverse, NoReverseMatch

from django.db.models import CharField
from django.db.models.expressions import RawSQL


from functools import lru_cache
from corporate.models import Managers


from .models import SalesData,MV_Daily_Sales
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from datetime import date
from sales.dash_apps.dailysales.data import get_month_data, get_ytd_data


from django.utils.html import format_html
from django import forms
from django.utils.safestring import mark_safe

from sales.reports.sales_report.store_logos import STORE_LOGOS
from django.templatetags.static import static

from .print_utils import (
    build_mtd_table,     
    build_ytd_table,     

)
from sales.reports.sales_report.builder import build_daily_sales_report_context





class SalesDataAdmin(admin.ModelAdmin):
    list_display = ('date','operation','store','icon_preview','amount_tot','quant_tot')
    list_filter = ("date","operation","store__gr","orders",)
    date_hierarchy = "date"
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
        '<a href="{}" target="_blank" title="Печать отчёта" '
        'style="text-decoration:none;font-size:14px;">🖨</a>',
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




        context = build_daily_sales_report_context(d, request=request)
        return render(request, "reports/sales_report/full_report.html", context)

    
    
    
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # если тебе не нужен object_id, можно оставить статикой:
        extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        # если нужно фильтровать даш по конкретной записи/дате:
        # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )
        
    
# @admin.register(MVSalesOrder)
# class MVSalesOrderAdmin(admin.ModelAdmin):
    
#     # ПОЛЯ ЧТО Б НЕ ЛАЗИТЬ `orders_id`, `client_order_type`, `client_order`, `client_order_number`, `client_order_date`, `order_min_date`, `order_max_date`, `realization_duration`, `order_duration`, `sales`, `returns`, `amount`, `items_amount`, `service_amount`, `items_quant`, `unique_items`, `manager_name`
    
#     list_display = (
#         "client_order_type",
#         "client_order",
#         "client_order_date",
#         "order_min_date",
#         "order_max_date",
#         "order_duration",
#         "sales",
#         "returns",
#         "amount",
#         "items_amount",
#         "service_amount",
#         "items_quant",
#         "unique_items",
#         "manager_name"
#     )

#     search_fields = ("client_order_date","manager_name")
#     list_filter = ("client_order_date","manager_name" ,  "client_order_type",)
#     list_per_page = 25
    
#     class Media:
#         css = {"all": ("css/admin_overrides.css",)}
    
#     def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
#         extra_context = extra_context or {}

#         # если тебе не нужен object_id, можно оставить статикой:
#         extra_context["iframe_url"] = f"/apps/app/orders_app/?object_id={object_id}"

#         # если нужно фильтровать даш по конкретной записи/дате:
#         # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

#         return super().changeform_view(
#             request, object_id, form_url, extra_context=extra_context
#         )


from functools import lru_cache
from corporate.models import Managers

@lru_cache(maxsize=2048)
def manager_report_name(manager_name: str) -> str:
    if not manager_name:
        return "—"
    name = manager_name.strip()

    m = Managers.objects.filter(name=name).only("name", "report_name").first()
    if not m:
        return name
    return (m.report_name or m.name or name).strip()




class OrderDurationFilter(admin.SimpleListFilter):
    title = "Срок"
    parameter_name = "dur"

    def lookups(self, request, model_admin):
        return (
            ("le2", "≤ 2 дн."),
            ("3_6", "3–6 дн."),
            ("7_10", "7–10 дн."),
            ("gt10", "> 10 дн."),
            ("gt30", "> 30 дн."),
            ("gt60", "> 60 дн."),
            ("gt90", "> 90 дн."),
            ("gt180", "> 180 дн."),
              
        )

    def queryset(self, request, queryset):
        v = self.value()
        if v == "le2":
            return queryset.filter(order_duration__lte=2)
        if v == "3_6":
            return queryset.filter(order_duration__gte=3, order_duration__lte=6)
        if v == "7_10":
            return queryset.filter(order_duration__gte=7, order_duration__lte=10)
        if v == "gt10":
            return queryset.filter(order_duration__gt=10)
        if v == "gt30":
            return queryset.filter(order_duration__gt=30)
        if v == "gt60":
            return queryset.filter(order_duration__gt=60)
        if v == "gt90":
            return queryset.filter(order_duration__gt=90)
        if v == "gt180":
            return queryset.filter(order_duration__gt=180)
        return queryset


@admin.register(MVSalesOrder)
class MVSalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_created_pretty",
        # "store_group_pretty",
        # "client_order_type",
        'order_type_pretty',
        "manager_pretty",
        "order_pretty",
        "unique_items_pretty",
        "amount_pretty",
        "service_amount",
        "duration_badge",
        "order_min_pretty",
        "order_max_pretty",

        # "amount_pretty",
        # "sales_pretty",
        # "returns_pretty",

        "actions_col",
    )



    list_display_links = ("order_pretty",)

    # поиск — по текстовым полям (дата через date_hierarchy)
    search_fields = ("client_order", "manager_name", "client_order_type")
    list_select_related = False 

    list_filter = ("client_order_type", OrderDurationFilter, "manager_name", "client_order_date")
    date_hierarchy = "client_order_date"
    ordering = ("-order_max_date", "-client_order_date")
    list_per_page = 50
    empty_value_display = "—"
    change_list_template = "admin/sales/mvsalesorder/change_list.html"


    class Media:
        css = {"all": ("css/admin_overrides.css",)}
        
    
    def _fmt_money(self, val):
        if val is None:
            return "—"
        try:
            v = float(val)
        except Exception:
            return "—"
        return f"{v:,.2f}".replace(",", " ")  

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["today"] = date.today().isoformat()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Стоимость", ordering="amount")
    def amount_pretty(self, obj):
        v = obj.amount
        if v is None:
            return format_html('<span class="money muted">—</span>')

        try:
            is_neg = float(v) < 0
        except Exception:
            is_neg = False

        cls = "money neg" if is_neg else "money"
        return format_html('<span class="{}">{}</span>', cls, self._fmt_money(v))


    @admin.display(description="Продажи", ordering="sales")
    def sales_pretty(self, obj):
        return format_html('<span class="money">{}</span>', self._fmt_money(obj.sales))

    @admin.display(description="Возвраты", ordering="returns")
    def returns_pretty(self, obj):
        v = obj.returns
        if v is None:
            return format_html('<span class="money muted">—</span>')
        # подсветим, если возвраты > 0
        try:
            is_bad = float(v) > 0
        except Exception:
            is_bad = False

        cls = "money neg" if is_bad else "money"
        return format_html('<span class="{}">{}</span>', cls, self._fmt_money(v))

    @admin.display(description="Заказ")
    def order_pretty(self, obj):
        if not obj.client_order:
            return "—"

        parts = obj.client_order.split(" от ")

        if len(parts) == 2:
            main, date_part = parts
            html = f"""
                <span class="order-main">{main}</span>
                <span class="order-date">от {date_part}</span>
            """
        else:
            html = obj.client_order

        url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" class="order-link">{}</a>',
            url,
            mark_safe(html),
        )


    @admin.display(description="Тип", ordering="client_order_type")
    def order_type_pretty(self, obj):
        t = (obj.client_order_type or "").strip()
        tl = t.lower()

        if "розничные продажи" in tl:
            icon = "🛒"
            short = "Розничные продажи"
        elif "заказ клиента" in tl:
            icon = "📦"
            short = "Заказ клиента"
        elif "продажи без заказа" in tl:
            icon = "🧾"
            short = "Без заказа"
        else:
            icon = ""
            short = t or "—"

        return format_html('<span class="type-pill">{} {}</span>', icon, short)



    @admin.display(description="Срок", ordering="order_duration")
    def duration_badge(self, obj):
        d = obj.order_duration
        if d is None:
            return "—"
        try:
            days = int(d)
        except Exception:
            return d

        if days >= 7:
            cls = "badge badge-red"
        elif days >= 3:
            cls = "badge badge-amber"
        else:
            cls = "badge badge-green"

        return format_html('<span class="{}">{} дн.</span>', cls, days)


    @admin.display(description="Первая отгр.", ordering="order_min_date")
    def order_min_pretty(self, obj):
        if not obj.order_min_date:
            return "—"
        return obj.order_min_date.strftime("%d.%m.%Y")


    @admin.display(description="Посл. отгр.", ordering="order_max_date")
    def order_max_pretty(self, obj):
        if not obj.order_max_date:
            return "—"
        return obj.order_max_date.strftime("%d.%m.%Y")


    @admin.display(description="Создан", ordering="client_order_date")
    def order_created_pretty(self, obj):
        if not obj.client_order_date:
            return "—"
        return obj.client_order_date.strftime("%d.%m.%Y")
   
    @admin.display(description="Менеджер")
    def manager_pretty(self, obj):
        name = manager_report_name(obj.manager_name)
        if not name or name == "—":
            return "—"

        parts = name.split()
        if len(parts) >= 2:
            last = parts[0]
            first = " ".join(parts[1:])
            return format_html(
                '<span class="mgr-last">{}</span><span class="mgr-first">{}</span>',
                last, first
            )
        return format_html('<span class="mgr-last">{}</span>', name)

    @admin.display(description="SKU", ordering="unique_items")
    def unique_items_pretty(self, obj):
        return obj.unique_items

    # @admin.display(description="Магазин")
    # def store_group_pretty(self, obj):
    #     s = (getattr(obj, "store_group_agg", None) or "").strip()
    #     if not s or s == "—":
    #         return format_html('<span class="muted">—</span>')

    #     # если вдруг несколько магазинов — берём первый (как основной)
    #     main_store = s.split(",")[0].strip()

    #     logo_path = STORE_LOGOS.get(main_store)

    #     if logo_path:
    #         logo_url = static(logo_path)
    #         return format_html(
    #             '''
    #             <span class="store-cell">
    #                 <img src="{}" class="store-logo">
    #                 <span class="store-name">{}</span>
    #             </span>
    #             ''',
    #             logo_url,
    #             main_store,
    #         )

    #     # если логотипа нет — просто текст красиво
    #     return format_html('<span class="store-name">{}</span>', main_store)



    # MV — только чтение
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Позиции")
    def lines_link(self, obj):
        """
        Ссылка на SalesData с фильтром по orders_id.
        НЕ ПАДАЕТ, если SalesData не зарегистрирована в админке.
        """
        # SalesData должна быть зарегистрирована в admin_site, иначе changelist не существует
        if SalesData not in self.admin_site._registry:
            return "—"

        try:
            url = reverse(
                f"admin:{SalesData._meta.app_label}_{SalesData._meta.model_name}_changelist"
            ) + f"?orders__id__exact={obj.orders_id}"
        except NoReverseMatch:
            return "—"

        return format_html('<a href="{}">Открыть</a>', url)

    @admin.display(description="Dash")
    def dash_link(self, obj):
        url = f"/apps/app/orders_app/?object_id={obj.orders_id}"
        return format_html('<a href="{}" target="_blank">↗</a>', url)

    @admin.display(description="Действия")
    def actions_col(self, obj):
        parts = []

        # Позиции
        if SalesData in self.admin_site._registry:
            try:
                url_lines = reverse(
                    f"admin:{SalesData._meta.app_label}_{SalesData._meta.model_name}_changelist"
                ) + f"?orders__id__exact={obj.orders_id}"
                parts.append(
                    format_html('<a class="act-btn" href="{}" title="Позиции">📄</a>', url_lines)
                )
            except NoReverseMatch:
                pass

        # Dash
        url_dash = f"/apps/app/orders_app/?object_id={obj.orders_id}"
        parts.append(
            format_html('<a class="act-btn" href="{}" target="_blank" title="Dash">↗</a>', url_dash)
        )

        if not parts:
            return "—"
        return format_html(" ".join([str(p) for p in parts]))

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        vendor = qs.db  # алиас БД
        from django.db import connections
        engine = connections[vendor].vendor  # 'postgresql' / 'sqlite' / 'mysql' ...

        if engine == "postgresql":
            sql = """
                SELECT COALESCE(string_agg(DISTINCT sg.name, ', ' ORDER BY sg.name), '—')
                FROM sales_salesdata d
                LEFT JOIN corporate_stores store ON store.id = d.store_id
                LEFT JOIN corporate_storegroups sg ON sg.id = store.gr_id
                WHERE d.orders_id = mv_orders.orders_id
            """
        else:
            # sqlite / mysql — group_concat
            sql = """
                SELECT COALESCE(group_concat(DISTINCT sg.name), '—')
                FROM sales_salesdata d
                LEFT JOIN corporate_stores store ON store.id = d.store_id
                LEFT JOIN corporate_storegroups sg ON sg.id = store.gr_id
                WHERE d.orders_id = mv_orders.orders_id
            """

        return qs.annotate(
            store_group_agg=RawSQL(sql, params=[], output_field=CharField())
        )


    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["iframe_url"] = f"/apps/app/orders_app/?object_id={object_id}"
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


    
# admin.site.register(SalesData,SalesDataAdmin)


