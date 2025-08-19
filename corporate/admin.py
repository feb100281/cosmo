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


# Register your models here.

class AssignCategoryForm(forms.Form):
    category = forms.ModelChoiceField(queryset=CatTree.objects.all(), label="Категория")

class CatTreeForm(forms.ModelForm):
    class Meta:
        model = CatTree
        fields = '__all__'
        widgets = {
            'icon': forms.Textarea(attrs={'rows': 4, 'style': 'font-family: monospace;'}),
        }


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



class StoreAdmin(admin.ModelAdmin):
    list_display = ('name','gr','chanel',)

class StoreGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'region','logo_preview')
    def logo_preview(self, obj):
        if obj.pict:
            return format_html('<img src="{}" style="height: 25px;" />', obj.pict.url)
        return "-"
    logo_preview.short_description = "Логотип"

class SubCatAdmin(admin.ModelAdmin):
    list_display = ('name','category','icon_preview',)
    inlines = [ItemsInline]
    
    def icon_preview(self, obj):
        if obj.icon and obj.icon.strip().startswith('<svg'):
            return format_html('{}', mark_safe(obj.icon))
        return "-"

class CatTreeAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ("tree_actions", "indented_title", "icon_preview",)
    list_display_links = ("indented_title",)
    
    inlines = [ItemsInline]

    def icon_preview(self, obj):
        if obj.icon and obj.icon.strip().startswith('<svg'):
            return format_html('{}', mark_safe(obj.icon))
        return "-"
    

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
admin.site.register(Managers)
admin.site.register(Agents)










