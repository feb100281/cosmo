from django.contrib import admin
from .models import (Companies, 
                     Projects, 
                     CatTree, 
                     Items, 
                     StoreGroups, 
                     Stores, 
                     ItemProperty, 
                     ItemCollections, 
                     ItemSizes, 
                     ItemColors,
                     ItemBrend,
                     ItemManufacturer,
                     ItemMaterial,
                     ItemZones,SubCategory,
                     Managers,Agents)
from mptt.admin import DraggableMPTTAdmin # type: ignore
from django.utils.html import format_html
from django import forms
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.urls import path
from django.db.models import CharField
from django.db.models.expressions import RawSQL
from sales.reports.sales_report.store_logos import STORE_LOGOS
from django.templatetags.static import static
from django.db import connections
from django.db.models import Subquery




class AssignCategoryForm(forms.Form):
    category = forms.ModelChoiceField(queryset=CatTree.objects.all(), label="Категория")
    class Media:
        css = {"all": ("css/admin_overrides.css",)}

class CatTreeForm(forms.ModelForm):
    class Meta:
        model = CatTree
        fields = '__all__'
        widgets = {
            'icon': forms.Textarea(attrs={'rows': 4, 'style': 'font-family: monospace;'}),
        }
    class Media:
        css = {"all": ("css/admin_overrides.css",)}


class ItemsAdminForm(forms.ModelForm):
    class Meta:
        model = Items
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cat = None
        if self.instance and self.instance.pk:
            cat = self.instance.cat
        elif 'cat' in self.data:
            try:
                cat_id = int(self.data.get('cat'))
                cat = CatTree.objects.get(pk=cat_id)
            except (ValueError, CatTree.DoesNotExist):
                pass

        # проверяем, есть ли поле 'subcat' в форме
        if 'subcat' in self.fields:
            if cat:
                self.fields['subcat'].queryset = SubCategory.objects.filter(category=cat)
            else:
                self.fields['subcat'].queryset = SubCategory.objects.none()
    class Media:
        css = {"all": ("css/admin_overrides.css",)}



class ItemsInline(admin.TabularInline):
    model = Items
    extra = 0
    verbose_name = "Номенклатура"
    verbose_name_plural = "Номенклатуры"
    fields = ('fullname',"item_subcat")
    readonly_fields = fields
    
    def item_subcat(self, obj):
        return obj.subcat.name if obj.subcat else "-"
    
    item_subcat.short_description = "Подкатегория"
    class Media:
        css = {"all": ("css/admin_overrides.css",)}



class StoreAdmin(admin.ModelAdmin):
    list_display = ('name','gr','chanel',)
    class Media:
        css = {"all": ("css/admin_overrides.css",)}

class StoreGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'region','logo_preview')
    def logo_preview(self, obj):
        if obj.pict:
            return format_html('<img src="{}" style="height: 25px;" />', obj.pict.url)
        return "-"
    logo_preview.short_description = "Логотип"
    class Media:
        css = {"all": ("css/admin_overrides.css",)}


class SubCatAdmin(admin.ModelAdmin):
    list_display = ('name','category','icon_preview',)
    inlines = [ItemsInline]
    
    def icon_preview(self, obj):
        if obj.icon and obj.icon.strip().startswith('<svg'):
            return format_html('{}', mark_safe(obj.icon))
        return "-"
    class Media:
        css = {"all": ("css/admin_overrides.css",)}

class CatTreeAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ("tree_actions", "indented_title", "icon_preview",)
    list_display_links = ("indented_title",)
    
    inlines = [ItemsInline]

    def icon_preview(self, obj):
        if obj.icon and obj.icon.strip().startswith('<svg'):
            return format_html('{}', mark_safe(obj.icon))
        return "-"
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
    

class ItemsAdmin(admin.ModelAdmin):
    form = ItemsAdminForm
    list_display = ('icon_preview','article','init_date','cat','subcat')
    list_filter = ("cat",)
    fieldsets = (
        ("Основное", {
            "fields": ("guid", "fullname", "article", "name","brend","cat","subcat","init_date")
        }),
        ("Описание", {
            "fields": ("description","manufacturer",'collection',"weight","volume","zones","pict")
        }),
        ("Характеристики", {
            "fields": ("item_property","colors","sizes",'material')
        }),
        ("Прочие", {
            "fields": ("im_id","onec_cat",'onec_subcat')
        }),
    )
    actions = ['assign_category']
    
    def icon_preview(self, obj):
        if obj.cat and obj.cat.icon and obj.cat.icon.strip().startswith('<svg'):
            return format_html(
                '{}&nbsp;<strong>{}</strong>',
                mark_safe(obj.cat.icon),
                obj.fullname
            )
        return obj.fullname
    icon_preview.short_description = 'Наименование'
    icon_preview.admin_order_field = 'fullname'
    
    def assign_category(self, request, queryset):
        if 'apply' in request.POST:
            form = AssignCategoryForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data['category']
                updated = queryset.update(cat=category)
                self.message_user(request, f"Категория '{category}' назначена для {updated} объектов.")
                return redirect(request.get_full_path())
        else:
            form = AssignCategoryForm()

        return render(request, 'admin/corporate/items/assign_category.html', context={
            'items': queryset,
            'form': form,
            'title': 'Назначить категорию',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })

    assign_category.short_description = "Назначить категорию"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('assign-category/', self.admin_site.admin_view(self.assign_category))
        ]
        return custom_urls + urls
    class Media:
        css = {"all": ("css/admin_overrides.css",)}




class ManagerStoreGroupFilter(admin.SimpleListFilter):
    title = "Магазин"
    parameter_name = "store_group"

    def lookups(self, request, model_admin):
        # показываем список групп магазинов (как в твоей колонке)
        return list(StoreGroups.objects.order_by("name").values_list("name", "name"))

    def queryset(self, request, queryset):
        v = self.value()
        if not v:
            return queryset

        # managers, у которых есть хотя бы одна продажа/строка SalesData в выбранной группе
        from sales.models import SalesData  # чтобы не ловить циклический импорт

        manager_ids = (
            SalesData.objects
            .filter(store__gr__name=v)
            .exclude(manager_id__isnull=True)
            .values("manager_id")
            .distinct()
        )

        return queryset.filter(id__in=Subquery(manager_ids))



class ManagersAdmin(admin.ModelAdmin):
    list_display = (
        "report_name_main",
        "stores_pretty",
    )
    list_display_links = ("report_name_main",)
    list_filter = (ManagerStoreGroupFilter, 'report_name')
    search_fields = ("name", "report_name",)
    ordering = ("report_name",)
    list_per_page = 50
    empty_value_display = "—"

    fields = ("name", "report_name", )

    class Media:
        css = {"all": ("css/admin_overrides.css",)}

    # -------- подтягиваем магазины по заказам --------
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        from django.db import connections
        engine = connections[qs.db].vendor  # postgresql / sqlite / mysql

        if engine == "postgresql":
            sql = """
                SELECT COALESCE(string_agg(DISTINCT sg.name, ', ' ORDER BY sg.name), '')
                FROM sales_salesdata d
                LEFT JOIN corporate_stores st ON st.id = d.store_id
                LEFT JOIN corporate_storegroups sg ON sg.id = st.gr_id
                WHERE d.manager_id = corporate_managers.id
            """
        else:
            sql = """
                SELECT COALESCE(group_concat(DISTINCT sg.name), '')
                FROM sales_salesdata d
                LEFT JOIN corporate_stores st ON st.id = d.store_id
                LEFT JOIN corporate_storegroups sg ON sg.id = st.gr_id
                WHERE d.manager_id = corporate_managers.id
            """

        return qs.annotate(
            stores_agg=RawSQL(sql, params=[], output_field=CharField())
        )

    # -------- имя в отчёте — главное --------
    @admin.display(description="Менеджер", ordering="report_name")
    def report_name_main(self, obj):
        v = (obj.report_name or obj.name or "").strip()
        if not v:
            return format_html('<span class="muted">—</span>')
        return format_html('<span class="mgr-last">{}</span>', v)

    # -------- магазины менеджера --------
    @admin.display(description="Магазины")
    def stores_pretty(self, obj):
        s = (getattr(obj, "stores_agg", None) or "").strip()
        if not s:
            return format_html('<span class="muted">—</span>')

        stores = [x.strip() for x in s.split(",") if x.strip()]
        cells = []

        for store in stores:
            logo_path = STORE_LOGOS.get(store)
            if logo_path:
                logo_url = static(logo_path)
                cells.append(
                    format_html(
                        '''
                        <span class="store-chip">
                            <img src="{}" class="store-chip-logo">
                            <span>{}</span>
                        </span>
                        ''',
                        logo_url,
                        store
                    )
                )
            else:
                cells.append(
                    format_html(
                        '<span class="store-chip store-text-only">{}</span>',
                        store
                    )
                )

        return format_html(" ".join(cells))













admin.site.register(Companies)
admin.site.register(Projects)
admin.site.register(CatTree, CatTreeAdmin)
admin.site.register(Items,ItemsAdmin)
admin.site.register(StoreGroups,StoreGroupAdmin)
admin.site.register(Stores,StoreAdmin)
admin.site.register(ItemProperty)
admin.site.register(ItemCollections)
admin.site.register(ItemSizes)
admin.site.register(ItemColors)
admin.site.register(ItemMaterial)
admin.site.register(ItemManufacturer)
admin.site.register(ItemBrend)
admin.site.register(ItemZones)
admin.site.register(SubCategory,SubCatAdmin)
admin.site.register(Managers, ManagersAdmin) 
admin.site.register(Agents)










