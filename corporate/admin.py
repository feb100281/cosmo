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
from django.urls import reverse
from django.utils.http import urlencode
from django.db.models import Count, Q
from django.utils import timezone
from mptt.admin import MPTTModelAdmin
import csv
from django.http import HttpResponse
from django.db import connection

from collections import defaultdict
from corporate.reports.manufacturers_revenue import get_manufacturers_net_by_year
from corporate.reports.manufacturers_lost_chart import build_lost_manufacturers_svg
from corporate.reports.manufacturers_revenue_summary import build_manufacturers_brief
from corporate.reports.manufacturers_by_rootcat import get_rootcat_manufacturers_metrics_by_year
# from corporate.reports.manufacturers_wordstrip_chart import build_manufacturers_wordstrip_svg
from corporate.reports.manufacturers_decline_dumbbell_svg import build_decline_dumbbell_svg
from corporate.reports.manufacturers_top_by_year_chart import build_top_manufacturers_by_year
from corporate.reports.manufacturers_top_by_year_svg import build_top_by_year_svg
from corporate.reports.manufacturers_rootcat_mix_svg import build_rootcat_mix_svg
from corporate.reports.manufacturers_revenue_by_rootcat import get_manufacturer_net_by_rootcat_total

from decimal import Decimal
from datetime import date

def _d(x):
    try:
        return Decimal(str(x or "0"))
    except Exception:
        return Decimal("0")





@admin.register(ItemManufacturer)
class ItemManufacturerAdmin(admin.ModelAdmin):
    change_list_template = "admin/corporate/manufacturer/change_list.html"
    change_form_template = "admin/corporate/manufacturer/change_form.html"

    list_display = (
        "report_name_main",
        "items_count_link",
        "cats_preview",
        "subcats_eye",
    )
    list_display_links = ("report_name_main",)

    search_fields = ("name", "report_name")
    ordering = ("report_name", "name")
    list_per_page = 50
    empty_value_display = "—"
    fields = ("name", "report_name", "country")

    actions = ("print_manufacturers_action",)

    class Media:
        css = {"all": ("css/admin_overrides.css",)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.annotate(_items=Count("items", distinct=True))
              .prefetch_related("items__cat", "items__subcat")
        )

    def get_list_per_page(self, request):
        if request.GET.get("all") == "1":
            return 10_000_000
        return super().get_list_per_page(request)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        qs = cl.get_queryset(request)

        stats = qs.aggregate(
            total=Count("id", distinct=True),
            active=Count("id", filter=Q(_items__gt=0), distinct=True),
            empty=Count("id", filter=Q(_items=0), distinct=True),
        )
        extra_context["mf_stats"] = stats
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Производитель", ordering="report_name")
    def report_name_main(self, obj):
        v = (obj.report_name or obj.name or "").strip()
        return v or "—"

    @admin.display(description="Товаров", ordering="_items")
    def items_count_link(self, obj):
        cnt = int(getattr(obj, "_items", 0) or 0)
        if cnt <= 0:
            return "0"
        url = reverse("admin:corporate_items_changelist")
        url = f"{url}?{urlencode({'manufacturer__id__exact': obj.id})}"
        return format_html('<a href="{}" title="Открыть номенклатуру">{}</a>', url, cnt)

    @admin.display(description="Категории")
    def cats_preview(self, obj):
        cats = []
        seen = set()

        for it in obj.items.all():
            c = it.cat
            if c and c.id not in seen:
                seen.add(c.id)
                cats.append(c)

        if not cats:
            return format_html('<span class="muted">—</span>')

        cats.sort(key=lambda x: (x.name or "").lower())

        limit = 10
        shown = cats[:limit]
        more = len(cats) - limit

        chips = []
        for c in shown:
            url = reverse("admin:corporate_items_changelist")
            params = {"manufacturer__id__exact": obj.id, "cat__id__exact": c.id}
            chips.append(format_html('<a class="chip" href="{}?{}">{}</a>', url, urlencode(params), c.name))

        if more > 0:
            url = reverse("admin:corporate_items_changelist")
            url = f"{url}?{urlencode({'manufacturer__id__exact': obj.id})}"
            chips.append(format_html('<a class="chip chip--muted" href="{}">+{}</a>', url, more))

        return mark_safe(" ".join(chips))

    @admin.display(description="Подкатегории")
    def subcats_eye(self, obj):
        url = reverse("admin:corporate_itemmanufacturer_subcats", args=[obj.id])
        return format_html(
            '<a href="{}" title="Открыть подкатегории" style="text-decoration:none;">'
            '<span style="display:inline-flex;align-items:center;gap:6px;'
            'padding:2px 8px;border-radius:999px;border:1px solid rgba(148,163,184,.45);'
            'background:rgba(248,250,252,.8);font-size:12px;">👁️</span></a>',
            url
        )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/subcats/",
                self.admin_site.admin_view(self.subcats_view),
                name="corporate_itemmanufacturer_subcats",
            ),
            path(
                "print-manufacturers/",
                self.admin_site.admin_view(self.print_manufacturers_view),
                name="corporate_itemmanufacturer_print_manufacturers",
            ),
        ]
        return custom + urls

    def subcats_view(self, request, pk: int):
        m = (
            ItemManufacturer.objects
            .prefetch_related("items__subcat")
            .get(pk=pk)
        )

        subcats_map = {}
        for it in m.items.all():
            if it.subcat_id:
                subcats_map[it.subcat_id] = it.subcat.name

        subcats = sorted(subcats_map.items(), key=lambda x: (x[1] or "").lower())

        context = dict(
            self.admin_site.each_context(request),
            title=f"Подкатегории производителя: {m.report_name or m.name}",
            manufacturer=m,
            subcats=subcats,
        )
        return render(request, "admin/corporate/manufacturer/subcats_list.html", context)

    @admin.action(description="🖨️ Печать: категории → производители, затем алфавит (HTML)")
    def print_manufacturers_action(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        if not ids:
            self.message_user(request, "Ничего не выбрано.")
            return
        return redirect(f"print-manufacturers/?ids={','.join(map(str, ids))}")

    
    def print_manufacturers_view(self, request):
        ids_raw = request.GET.get("ids", "")
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]

        qs = ItemManufacturer.objects.all() if not ids else ItemManufacturer.objects.filter(id__in=ids)
        qs = qs.prefetch_related("items__cat", "items__subcat")

        rows = []
        all_cats = set()
        all_subcats = set()

        cats_index = defaultdict(lambda: {"name": "", "icon": "", "mfs": set()})

        for m in qs:
            cats_map = {}
            subcats_map = {}

            for it in m.items.all():
                if it.cat_id and it.cat:
                    cats_map[it.cat_id] = it.cat.name
                if it.subcat_id and it.subcat:
                    subcats_map[it.subcat_id] = it.subcat.name

                if it.cat_id and it.cat and it.subcat_id and it.subcat:
                    cat = it.cat
                    cat_id = cat.id

                    cats_index[cat_id]["name"] = (cat.name or "").strip()
                    cats_index[cat_id]["icon"] = (cat.icon or "")
                    mf_name = (m.report_name or m.name or "").strip() or "—"
                    cats_index[cat_id]["mfs"].add(mf_name)

            cat_names = sorted(cats_map.values(), key=lambda x: (x or "").lower())
            subcat_names = sorted(subcats_map.values(), key=lambda x: (x or "").lower())

            if not subcat_names:
                continue

            for c in cat_names:
                all_cats.add(c)
            for s in subcat_names:
                all_subcats.add(s)

            rows.append({
                "report_name": (m.report_name or m.name or ""),
                "subcats": subcat_names,
            })

        rows.sort(key=lambda r: (r["report_name"] or "").lower())

        # === PART 3: выручка по годам ===
        years, revenue_rows, revenue_totals = get_manufacturers_net_by_year(
            start_year=2022,
            ids=ids
        )

        manufacturers_brief = build_manufacturers_brief(
            years=years,
            revenue_rows=revenue_rows,
            exclude_unknown=False,
            top_n_lists=8,
        )

        # === карта выручки ИТОГО с 2022 года по производителю (как было) ===
        rev_val_map = {}   # name -> Decimal
        rev_disp_map = {}  # name -> "12,3 млн ₽"

        for rr in (revenue_rows or []):
            name = (rr.get("report_name") or rr.get("name") or rr.get("manufacturer") or "").strip()
            if not name:
                continue
            rev_val_map[name] = _d(rr.get("total") or 0)
            rev_disp_map[name] = (rr.get("total_disp") or "").strip()

        # ============================================================
        # === ДОБАВЛЯЕМ: выручка по (cat_id, производитель) ===========
        # ============================================================
        from corporate.reports.manufacturers_revenue_summary import fmt_money_ru

        cat_mf_val_map = {}   # (cat_id, mf_name) -> Decimal
        cat_mf_disp_map = {}  # (cat_id, mf_name) -> str

        cat_ids = list(cats_index.keys())
        if cat_ids:
            params = {"start_year": 2022}

            where_mf = ""
            if ids:
                ph = []
                for i, v in enumerate(ids):
                    k = f"mf{i}"
                    params[k] = int(v)
                    ph.append(f"%({k})s")
                # НЕ теряем NULL (как у тебя в других отчётах)
                where_mf = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

            phc = []
            for i, v in enumerate(cat_ids):
                k = f"c{i}"
                params[k] = int(v)
                phc.append(f"%({k})s")
            where_cat = f" AND it.cat_id IN ({', '.join(phc)}) "

            # ВАЖНО: mf_name формируем так же, как ты формируешь mf_name в cats_index
            q_cat_rev = f"""
                    SELECT
                        it.cat_id AS cat_id,
                        CASE
                            WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                            ELSE COALESCE(m.report_name, m.name, '—')
                        END AS mf_name,
                        SUM(s.dt - s.cr) AS net_amount
                    FROM sales_salesdata s
                    JOIN corporate_items it ON it.id = s.item_id
                    LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
                    WHERE YEAR(s.`date`) >= %(start_year)s
                    {where_cat}
                    {where_mf}
                    GROUP BY it.cat_id, mf_name
                """

            with connection.cursor() as cur:
                cur.execute(q_cat_rev, params)
                rows_rev = cur.fetchall()

            for cat_id, mf_name, net_amount in rows_rev:
                cat_id = int(cat_id)
                name = (mf_name or "—").strip() or "—"
                net = _d(net_amount or 0)

                cat_mf_val_map[(cat_id, name)] = net
                cat_mf_disp_map[(cat_id, name)] = fmt_money_ru(net) if net else f"0\u00A0₽"
                
            
            # добавить "не указан" в список производителей категории, если по нему есть выручка
            UNKNOWN_NAME = "!Производитель не указан"
            for (cat_id, mf_name), net in cat_mf_val_map.items():
                if mf_name == UNKNOWN_NAME and net > 0:
                    cats_index[cat_id]["mfs"].add(UNKNOWN_NAME)

        # === cats_blocks (теперь сортируем и подписываем ПО КАТЕГОРИИ) ===
        cats_blocks = []
        cats_sorted = sorted(
            cats_index.items(),
            key=lambda kv: ((kv[1]["name"] or "").lower(), kv[0])
        )

        for cat_id, payload in cats_sorted:
            mf_names = list(payload["mfs"])
            if not mf_names:
                continue

            # сортируем по выручке В ЭТОЙ КАТЕГОРИИ, fallback на общий total
            mf_names.sort(
                key=lambda n: (
                    cat_mf_val_map.get((cat_id, n), rev_val_map.get(n, Decimal("0"))),
                    (n or "").lower()
                ),
                reverse=True
            )

            mf_list = []
            for i, name in enumerate(mf_names, start=1):
                medal = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else ""

                # ВАЖНО: берем disp по категории, если нет — fallback на общий
                disp = cat_mf_disp_map.get((cat_id, name), rev_disp_map.get(name, ""))

                tail = f" ({disp})" if (i <= 5 and disp) else ""
                mf_list.append(f"{medal}{name}{tail}")

            cats_blocks.append({
                "cat_id": cat_id,
                "cat": payload["name"],
                "icon": payload["icon"],
                "manufacturers": mf_list,
                "manufacturers_count": len(mf_names),
            })

        # === прочие блоки отчёта ===
        root_years, rootcat_rows, rootcat_totals = get_rootcat_manufacturers_metrics_by_year(
            start_year=2022,
            manufacturer_ids=ids,
        )

        rootcat_mix_svg = build_rootcat_mix_svg(
            years=root_years,
            rootcat_rows=rootcat_rows,
            title="Производители по группам категорий и их выручка",
        )

        decline_dumbbell_svg = build_decline_dumbbell_svg(
            manufacturers_brief.get("lists", {}).get("steady_decline", []),
            title=f"Устойчивое снижение выручки ({manufacturers_brief['start_year_str']}→{manufacturers_brief['last_closed_year_str']})",
            year_start=int(manufacturers_brief["start_year_str"]),
            last_closed_year=int(manufacturers_brief["last_closed_year_str"]),
            current_year=int(manufacturers_brief["current_year_str"]),
            max_rows=15,
        )

        lost_manufacturers_svg = build_lost_manufacturers_svg(
            revenue_rows=revenue_rows,
            years=years,
            top_n=15,
            exclude_unknown=True,
        )

        top_by_year = build_top_manufacturers_by_year(
            years=years,
            revenue_rows=revenue_rows,
            start_year=2022,
            top_n=5,
        )
        top_by_year_svg = build_top_by_year_svg(top_by_year, title="Топ-5 производителей по годам")

        context = dict(
            self.admin_site.each_context(request),
            title="Производители",
            generated_at=timezone.now(),
            cats_blocks=cats_blocks,
            rows=rows,
            total_cats=len(all_cats),
            total_subcats=len(all_subcats),

            years=years,
            revenue_rows=revenue_rows,
            revenue_totals=revenue_totals,
            manufacturers_brief=manufacturers_brief,

            lost_manufacturers_svg=lost_manufacturers_svg,
            root_years=root_years,
            rootcat_rows=rootcat_rows,
            rootcat_totals=rootcat_totals,
            decline_dumbbell_svg=decline_dumbbell_svg,

            top_by_year=top_by_year,
            top_by_year_svg=top_by_year_svg,
            rootcat_mix_svg=rootcat_mix_svg,
        )

        return render(request, "admin/corporate/manufacturer/print_manufacturers.html", context)


@admin.register(ItemBrend)
class ItemBrendAdmin(admin.ModelAdmin):
    search_fields = ("name",)






class SubCategoryInline(admin.StackedInline):
    model = SubCategory
    extra = 0
    fields = ("name",)
    show_change_link = True




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
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "cat" in self.fields:
            self.fields["cat"].queryset = CatTree.objects.filter(
                parent__isnull=False
            ).order_by("name")

        cat = None
        if self.instance and self.instance.pk:
            cat = self.instance.cat
        elif "cat" in self.data:
            try:
                cat_id = int(self.data.get("cat"))
                cat = CatTree.objects.get(pk=cat_id)
            except (ValueError, CatTree.DoesNotExist):
                cat = None

        if "subcat" in self.fields:
            if cat:
                self.fields["subcat"].queryset = (
                    SubCategory.objects
                    .filter(category=cat)
                    .order_by("name")
                )
            else:
                self.fields["subcat"].queryset = SubCategory.objects.none()


class RootCategoryFilter(admin.SimpleListFilter):
    title = "Группа (1 уровень)"
    parameter_name = "root_cat"

    def lookups(self, request, model_admin):
        roots = CatTree.objects.filter(parent__isnull=True).order_by("name")
        return [(str(r.id), r.name) for r in roots]

    def queryset(self, request, queryset):
        v = self.value()
        if not v:
            return queryset

        try:
            root = CatTree.objects.get(pk=int(v))
        except (ValueError, CatTree.DoesNotExist):
            return queryset

        # MPTT: берём все категории внутри поддерева root
        return queryset.filter(
            cat__tree_id=root.tree_id,
            cat__lft__gte=root.lft,
            cat__rght__lte=root.rght,
        )


@admin.register(Items)
class ItemsAdmin(admin.ModelAdmin):
    form = ItemsAdminForm

    change_list_template = "admin/corporate/items/change_list.html"
    change_form_template = "admin/corporate/items/change_form.html"
    list_display = ("item_title", "article", "init_date", "cat_link", "subcat_link")
    list_display_links = ("item_title",)
    list_per_page = 50
    ordering = ("-init_date", "fullname")
    empty_value_display = "—"

    search_fields = (
        "fullname", "name", "article", "im_id", "guid",
        "manufacturer__name", "brend__name",
        "cat__name", "subcat__name",
        "onec_cat", "onec_subcat",
    )

    list_filter = (RootCategoryFilter, "cat", "subcat", "brend", "manufacturer")

    autocomplete_fields = ( "manufacturer", "brend")
    filter_horizontal = ("collection", "item_property", "colors", "sizes", "material", "zones",)

    fieldsets = (
        ("🧾 Основное", {
            "fields": ("guid", "fullname", "name", "article", "brend", "cat", "subcat", "init_date"),
        }),
        ("📝 Описание", {
            "fields": ("description", "manufacturer", "collection", "weight", "volume", "zones", "pict"),
        }),
        ("🎛️ Характеристики", {
            "fields": ("item_property", "colors", "sizes", "material"),
        }),
        ("🔎 Прочее", {
            "fields": ("im_id", "onec_cat", "onec_subcat", "barcode"),
        }),
    )



    actions = ["export_items_csv", "print_items_action", "assign_category"]

    # -------- красивые колонки --------
    @admin.display(description="Номенклатура", ordering="fullname")
    def item_title(self, obj):
        icon = ""
        if obj.cat and obj.cat.icon:
            s = (obj.cat.icon or "").strip()
            if s.startswith("<svg"):
                icon = format_html('<span class="it-icon">{}</span>', mark_safe(s))
            else:
                icon = format_html('<span class="it-emoji">{}</span>', s)
        return format_html('{}{}', icon, obj.fullname)

    @admin.display(description="Категория", ordering="cat__name")
    def cat_link(self, obj):
        if not obj.cat:
            return "—"
        url = reverse("admin:corporate_cattree_change", args=[obj.cat_id])
        return format_html('<a href="{}">{}</a>', url, obj.cat.name)

    @admin.display(description="Подкатегория", ordering="subcat__name")
    def subcat_link(self, obj):
        if not obj.subcat:
            return "—"
        url = reverse("admin:corporate_subcategory_change", args=[obj.subcat_id])
        return format_html('<a href="{}">{}</a>', url, obj.subcat.name)

    @admin.display(description="Группа", ordering="cat__tree_id")
    def cat_root_link(self, obj):
        if not obj.cat:
            return "—"

        root = obj.cat.get_root()  # parent=None -> root
        url = reverse("admin:corporate_cattree_change", args=[root.id])

        # если хочешь иконку корня
        icon_html = ""
        if root.icon:
            s = (root.icon or "").strip()
            if s.startswith("<svg"):
                icon_html = format_html('<span class="it-icon">{}</span>', mark_safe(s))
            else:
                icon_html = format_html('<span class="it-emoji">{}</span>', s)

        return format_html('{}<a href="{}">{}</a>', icon_html, url, root.name)





    # --------  action назначить категорию --------
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
        custom = [
            path(
                "print-items/",
                self.admin_site.admin_view(self.print_items_view),
                name="corporate_items_print_items",
            ),
        ]
        return custom + urls

    @admin.action(description="🖨️ Печать списка (по группам) (HTML → PDF)")
    def print_items_action(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        if not ids:
            self.message_user(request, "Ничего не выбрано.")
            return
        return redirect(f"print-items/?ids={','.join(map(str, ids))}")

    def print_items_view(self, request):
        ids_raw = request.GET.get("ids", "")
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]

        qs = (
            Items.objects.all() if not ids else Items.objects.filter(id__in=ids)
        ).select_related("cat", "subcat", "manufacturer", "brend").prefetch_related("barcode")

        # --- собираем tree_id категорий, чтобы одним запросом получить корни ---
        tree_ids = set()
        for it in qs:
            if it.cat_id:
                tree_ids.add(it.cat.tree_id)

        roots = CatTree.objects.filter(tree_id__in=tree_ids, level=0)
        roots_map = {r.tree_id: r for r in roots}

        rows = []
        for it in qs:
            root = None
            group_name = ""
            group_icon = ""

            if it.cat_id:
                root = roots_map.get(it.cat.tree_id)
                if root:
                    group_name = root.name or ""
                    group_icon = (root.icon or "")

            rows.append({
                "group": group_name,
                "group_icon": group_icon,
                "fullname": it.fullname,
                "name": it.name,
                "article": it.article,
                "cat": it.cat.name if it.cat else "",
                "subcat": it.subcat.name if it.subcat else "",
                "brend": it.brend.name if it.brend else "",
                "manufacturer": it.manufacturer.name if it.manufacturer else "",
                "barcodes": list(it.barcode.values_list("barcode", flat=True)),
 
            })


        rows.sort(key=lambda r: (
            r["group"] or "ЯЯЯ_без_группы",
            r["cat"] or "",
            r["subcat"] or "",
            r["fullname"] or "",
        ))

        context = dict(
            self.admin_site.each_context(request),
            title="Печать номенклатуры",
            generated_at=timezone.now(),
            rows=rows,
        )
        return render(request, "admin/corporate/items/print_items.html", context)

    @admin.action(description="⬇️ Скачать CSV (выбранные позиции)")
    def export_items_csv(self, request, queryset):
        # чтобы не было N+1
        qs = queryset.select_related("cat", "subcat", "manufacturer", "brend").prefetch_related("barcode")

        # корни по tree_id (группа = первый уровень)
        tree_ids = {it.cat.tree_id for it in qs if it.cat_id}
        roots = CatTree.objects.filter(tree_id__in=tree_ids, level=0)
        roots_map = {r.tree_id: r for r in roots}

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="items_export.csv"'

        # BOM для корректного открытия в Excel
        # response.write("\ufeff")
        # writer = csv.writer(response, delimiter="|")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="items_export.csv"'
        response.write("\ufeff")   # BOM для Excel

        writer = csv.writer(response, delimiter="|")


        writer.writerow([
            "Группа(корень)",
            "Категория",
            "Подкатегория",
            "Номенклатура(1С)",
            "Название на сайте",
            "Артикль",
            "Бренд",
            "Производитель",
            "Штрихкоды",
            "im_id",
            "guid",
            "Дата инициализации",
        ])

        for it in qs:
            root_name = ""
            if it.cat_id:
                root = roots_map.get(it.cat.tree_id)
                root_name = root.name if root else ""

            barcodes = list(it.barcode.values_list("barcode", flat=True))

            writer.writerow([
                root_name,
                it.cat.name if it.cat else "",
                it.subcat.name if it.subcat else "",
                it.fullname or "",
                it.name or "",
                it.article or "",
                it.brend.name if it.brend else "",
                it.manufacturer.name if it.manufacturer else "",
                ", ".join(barcodes),
                it.im_id or "",
                it.guid or "",
                it.init_date.strftime("%d.%m.%Y") if it.init_date else "",
            ])

        return response


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
    list_display = ('name','category','items_count_link','icon_preview',)
    search_fields = ("name", "category__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_items=Count("items", distinct=True))

    @admin.display(description="Товаров", ordering="_items")
    def items_count_link(self, obj):
        cnt = getattr(obj, "_items", 0)
        if not cnt:
            return "0"
        url = (
            reverse("admin:corporate_items_changelist")
            + "?"
            + urlencode({"subcat__id__exact": obj.id})
        )
        return format_html('<a href="{}" title="Открыть номенклатуру">{}</a>', url, cnt)
    
    
    def icon_preview(self, obj):
        if obj.icon and obj.icon.strip().startswith('<svg'):
            return format_html('{}', mark_safe(obj.icon))
        return "-"
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
        
        

    
    

class CatTreeForm(forms.ModelForm):
    class Meta:
        model = CatTree
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Например: Мебель / Свет / Декор",
                "style": "width: 100%;",
            }),
            "comments": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Комментарий для команды (не обязателен)",
                "style": "width: 100%;",
            }),
            "icon": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": "Вставьте SVG-код целиком (начиная с <svg ...>)",
                "style": "width: 100%; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;",
            }),
        }

    class Media:
        css = {"all": ("css/admin_overrides.css", "css/admin_cattree_form.css")}
   
class HasIconFilter(admin.SimpleListFilter):
    title = "Иконка"
    parameter_name = "has_icon"

    def lookups(self, request, model_admin):
        return (("1", "Есть"), ("0", "Нет"))

    def queryset(self, request, queryset):
        v = self.value()
        if v == "1":
            return queryset.exclude(icon__isnull=True).exclude(icon__exact="")
        if v == "0":
            return queryset.filter(icon__isnull=True) | queryset.filter(icon__exact="")
        return queryset


class CatTreeAdmin(DraggableMPTTAdmin):
    # mptt_indent_field = "name"
    mptt_level_indent = 32 
    change_list_template = "admin/corporate/cattree/change_list.html"
    actions = ["print_tree_action"]
    inlines = [SubCategoryInline]

    list_display = (
        "tree_actions",
        "category_title", 
        # "indented_title",
        # "icon_preview",
        # "subcats_count",
        "subcats_preview", 
        # "items_count",
    )
    
    # list_display_links = ("indented_title",)
    list_display_links = ("category_title",)
    



    search_fields = (
        "name",
        "comments",
        "subcategories__name",
        "items__fullname",
        "items__article",
        "items__name",
    )
    list_filter = (
        HasIconFilter,
        "parent",
    )

    ordering = ("tree_id", "lft")
    list_per_page = 50
    empty_value_display = "—"
    
    fieldsets = (
        ("🧾 Основное", {
            "fields": ("name", "parent"),
        }),
        ("🎨 Визуальное оформление", {
            "fields": ("icon_preview_form", "icon"),
        }),
        ("🗒️ Комментарий", {
            "fields": ("comments",),
        }),
    )


    readonly_fields = ("icon_preview_form",)

    # def icon_preview(self, obj):
    #     if obj.icon and obj.icon.strip().startswith("<svg"):
    #         return format_html("{}", mark_safe(obj.icon))
    #     return "—"
    # icon_preview.short_description = "Иконка"

    @admin.display(description="Предпросмотр")
    def icon_preview_form(self, obj):
        if obj and obj.icon and obj.icon.strip().startswith("<svg"):
            return format_html(
                '<div class="ct-preview">{}</div>',
                mark_safe(obj.icon)
            )
        return format_html('<div class="ct-preview ct-preview--empty">Иконка не задана</div>')


    @admin.display(description="Категория", ordering="name")
    def category_title(self, obj):
        # DraggableMPTTAdmin сам отдаёт obj.level
        indent = (getattr(obj, "level", 0) or 0) * 18  # можно 16–22

        icon_html = ""
        if obj.icon:
            s = (obj.icon or "").strip()
            if s.startswith("<svg"):
                icon_html = format_html('<span class="it-icon">{}</span>', mark_safe(s))
            else:
                icon_html = format_html('<span class="it-emoji">{}</span>', s)

        comment_html = ""
        if obj.comments:
            comment_html = format_html(
                '<div style="margin-top:3px;font-size:11px;color:#6b7280;white-space:pre-wrap;">{}</div>',
                obj.comments
            )

        return format_html(
            '<div style="padding-left:{}px;">'
            '  <div style="display:flex;align-items:center;gap:8px;">'
            '    {}'
            '    <span style="font-weight:700;color:#0f172a;">{}</span>'
            '  </div>'
            '  {}'
            '</div>',
            indent,
            icon_html,
            obj.name,
            comment_html,
        )



    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_subcats=Count("subcategories", distinct=True),
                           _items=Count("items", distinct=True)).prefetch_related("subcategories")

    @admin.display(description="Подкатегорий", ordering="_subcats")
    def subcats_count_link(self, obj):
        cnt = getattr(obj, "_subcats", 0)
        if not cnt:
            return "0"
        url = (
            reverse("admin:corporate_subcategory_changelist")
            + "?"
            + urlencode({"category__id__exact": obj.id})
        )
        return format_html('<a href="{}" title="Открыть подкатегории">{}</a>', url, cnt)
    





    @admin.display(description="Подкатегории")
    def subcats_preview(self, obj):
        subs = list(obj.subcategories.all())
        if not subs:
            return format_html('<span class="muted">—</span>')

        limit = 14
        shown = subs[:limit]
        more = len(subs) - limit

        chips = []
        for s in shown:
            # ВАЖНО: ведём в список номенклатуры, отфильтрованный по subcat
            url = reverse("admin:corporate_items_changelist")
            url = f"{url}?{urlencode({'subcat__id__exact': s.id})}"
            chips.append(format_html('<a class="chip" href="{}">{}</a>', url, s.name))

        if more > 0:
            # если подкатегорий больше лимита — ведём в список номенклатуры по категории
            # (или можно вести в список подкатегорий — как тебе удобнее)
            url = reverse("admin:corporate_items_changelist")
            url = f"{url}?{urlencode({'cat__id__exact': obj.id})}"
            chips.append(format_html('<a class="chip chip--muted" href="{}">+{}</a>', url, more))

        return mark_safe(" ".join(chips))

    
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "print-tree/",
                self.admin_site.admin_view(self.print_tree_view),
                name="corporate_cattree_print_tree",
            ),
        ]
        return custom + urls

    # ---------- action ----------
    @admin.action(description="🖨️ Печать дерева (HTML → PDF)")
    def print_tree_action(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        if not ids:
            self.message_user(request, "Ничего не выбрано.")
            return
        return redirect(f"print-tree/?ids={','.join(map(str, ids))}")


   # ---------- view ----------
    def print_tree_view(self, request):
        ids_raw = request.GET.get("ids", "")
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]

        roots = CatTree.objects.all() if not ids else CatTree.objects.filter(id__in=ids)


        nodes = []
        for r in roots:
            nodes.append(r)
            nodes.extend(list(r.get_descendants()))


        uniq = {}
        for n in nodes:
            uniq[n.id] = n
        nodes = list(uniq.values())

        # сортировка по дереву
        nodes = sorted(nodes, key=lambda x: (x.tree_id, x.lft))
        nodes_ids = [n.id for n in nodes]

        # ---- 1) считаем кол-во подкатегорий и товаров ----
        counts = (
            CatTree.objects.filter(id__in=nodes_ids)
            .annotate(
                subcats_count=Count("subcategories", distinct=True),
                items_count=Count("items", distinct=True),
            )
        )
        counts_map = {c.id: c for c in counts}

        # ---- 2) подтягиваем НАЗВАНИЯ подкатегорий ----
        subcats_qs = (
            SubCategory.objects
            .filter(category_id__in=nodes_ids)
            .values("category_id", "name")
            .order_by("name")
        )
        subcats_map = {}
        for sc in subcats_qs:
            subcats_map.setdefault(sc["category_id"], []).append(sc["name"])

        # ---- 3) собираем rows ----
        rows = []
        for n in nodes:
            c = counts_map.get(n.id)
            level = int(getattr(n, "level", 0) or 0)

            rows.append({
                "id": n.id,
                "parent_id": n.parent_id,  
                "name": n.name,
                "level": level,
                "icon": n.icon,
                "comments": n.comments,
                "subcats": int(getattr(c, "subcats_count", 0) or 0) if c else 0,
                "items": int(getattr(c, "items_count", 0) or 0) if c else 0,
                "subcat_names": subcats_map.get(n.id, []),

                # для оформления
                "is_top": (level == 0),   # корни
                "is_l1": (level == 1),    # 1-й уровень вложенности
                "l2_names": subcats_map.get(n.id, []),
            })

        # ---- 4) график (corporate/reports/cattree_chart.py) ----
        chart_png = None
        try:
            from corporate.reports.cattree_chart import build_cattree_chart_base64
            from corporate.reports.cattree_weights_bar import build_cattree_weights_bar_base64
            chart_png = build_cattree_chart_base64(
                rows=rows,
                top_n_roots=8,
                max_l1_per_root=10,
                max_l2_per_l1=10,
                sort="alpha",  # или "structure"
            )
            
            
            weights_bar_png = build_cattree_weights_bar_base64(
                rows=rows,      
                top_n_roots=12,
                max_l1_per_root=10,
                max_l2_per_l1=12,
                sort="structure",
            )


        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("cattree chart build failed: %s", e)
            chart_png = None

        context = dict(
            self.admin_site.each_context(request),
            title="Печать категорий",
            generated_at=timezone.now(),
            rows=rows,
            chart_png=chart_png,
            weights_bar_png=weights_bar_png,
        )
        return render(request, "admin/corporate/cattree/print_tree.html", context)

    

    @admin.display(description="Иконка")
    def icon_preview(self, obj):
        if obj.icon and obj.icon.strip().startswith("<svg"):
            return format_html("{}", mark_safe(obj.icon))
        return "—"

    @admin.display(description="Подкатегорий", ordering="_subcats")
    def subcats_count(self, obj):
        return getattr(obj, "_subcats", 0)


    class Media:
        css = {"all": ("css/admin_overrides.css", "css/cattree_no_drag.css")}
        js = ("js/cattree_no_drag.js",)


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
# admin.site.register(Items,ItemsAdmin)
admin.site.register(StoreGroups,StoreGroupAdmin)
admin.site.register(Stores,StoreAdmin)
admin.site.register(ItemProperty)
admin.site.register(ItemCollections)
admin.site.register(ItemSizes)
admin.site.register(ItemColors)
admin.site.register(ItemMaterial)
# admin.site.register(ItemManufacturer)
# admin.site.register(ItemBrend)
admin.site.register(ItemZones)
admin.site.register(SubCategory,SubCatAdmin)
admin.site.register(Managers, ManagersAdmin) 
admin.site.register(Agents)










