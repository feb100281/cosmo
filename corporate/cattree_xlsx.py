# corporate/cattree_xlsx.py
"""Excel: наше дерево категорий (корень → категория → подкатегория) с уровнями и отступами."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO

LEVEL_NAMES = {1: "Корень", 2: "Категория", 3: "Подкатегория"}


def _collect():
    from django.db.models import Count

    from corporate.models import CatTree, Items, SubCategory

    nodes = list(CatTree.objects.order_by("tree_id", "lft"))
    subcats = defaultdict(list)
    for s in SubCategory.objects.order_by("name"):
        subcats[s.category_id].append(s)
    by_subcat = dict(Items.objects.exclude(subcat=None).values_list("subcat").annotate(n=Count("id")))
    by_cat = dict(Items.objects.exclude(cat=None).values_list("cat").annotate(n=Count("id")))
    return nodes, subcats, by_subcat, by_cat


def _rows():
    """Строки дерева сверху вниз: (уровень, название, путь, подкатегорий, товаров, комментарий)."""
    nodes, subcats, by_subcat, by_cat = _collect()
    children = defaultdict(list)
    for n in nodes:
        children[n.parent_id].append(n)
    out = []

    def items_in(node) -> int:
        total = by_cat.get(node.id, 0)
        for c in children.get(node.id, []):
            total += items_in(c)
        return total

    def walk(node, level, path):
        p = f"{path} / {node.name}" if path else node.name
        out.append((level, node.name, p, len(subcats.get(node.id, [])) or None, items_in(node) or None,
                    node.comments or None))
        for c in children.get(node.id, []):
            walk(c, level + 1, p)
        for s in subcats.get(node.id, []):
            out.append((level + 1, s.name, f"{p} / {s.name}", None, by_subcat.get(s.id) or None,
                        s.comments or None))

    for root in children.get(None, []):
        walk(root, 1, "")
    return out


def build_cattree_excel() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border
    from openpyxl.utils import get_column_letter

    from sales.reports.xl_brand import (
        FMT_QTY, MUTED, NAVY, NAVY_3, SURFACE_3, SURFACE_4, build_toc, fill, finalize, font, side,
        style_table_sheet,
    )

    rows = _rows()
    stamp = f"сформировано {datetime.now():%d.%m.%Y %H:%M}"
    wb = Workbook()
    wb.remove(wb.active)

    def widths(ws, values):
        for i, w in enumerate(values, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # Дерево
    ws = wb.create_sheet("Дерево")
    head = ["Наименование", "Уровень", "Подкатегорий", "Товаров", "Путь", "Комментарий"]
    ws.append(head)
    for level, name, path, n_sub, n_items, comment in rows:
        ws.append([name, LEVEL_NAMES.get(level, level), n_sub, n_items, path, comment])
    n_roots = sum(1 for r in rows if r[0] == 1)
    n_cats = sum(1 for r in rows if r[0] == 2)
    n_subs = sum(1 for r in rows if r[0] == 3)
    hdr = style_table_sheet(ws, title="ДЕРЕВО КАТЕГОРИЙ ТОВАРОВ",
                            subtitle=f"{n_roots} корневых разделов · {n_cats} категорий · {n_subs} подкатегорий "
                                     f"· три уровня по всей номенклатуре · {stamp}",
                            freeze_col=2, key_headers=("Наименование",), wrap_headers=("Подкатегорий",))
    ws.sheet_properties.outlinePr.summaryBelow = False
    styles = {1: (12, True, "FFFFFF", NAVY_3), 2: (10.5, True, NAVY_3, SURFACE_4), 3: (10, False, "1F1F1F", None)}
    for i, (level, *_rest) in enumerate(rows, start=hdr + 1):
        size, bold, color, bg = styles.get(level, styles[3])
        for j in range(1, len(head) + 1):
            c = ws.cell(row=i, column=j)
            c.font = font(size if j == 1 else 10, bold if j <= 2 else False,
                          color if (j == 1 or level == 1) else (MUTED if j == 5 else "1F1F1F"))
            if bg:
                c.fill = fill(bg)
            c.border = Border(bottom=side())
            if j in (3, 4):
                c.number_format = FMT_QTY
                c.alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(row=i, column=1).alignment = Alignment(horizontal="left", indent=(level - 1) * 3, vertical="center")
        ws.row_dimensions[i].height = 22 if level == 1 else (19 if level == 2 else 16)
        if level > 1:
            ws.row_dimensions[i].outlineLevel = level - 1
    widths(ws, [46, 14, 15, 11, 70, 40])

    # Плоский список
    ws = wb.create_sheet("Список")
    ws.append(["Корень", "Категория", "Подкатегория", "Товаров"])
    root = cat = None
    for level, name, _path, _n_sub, n_items, _c in rows:
        if level == 1:
            root, cat = name, None
        elif level == 2:
            cat = name
        else:
            ws.append([root, cat, name, n_items])
    style_table_sheet(ws, title="ДЕРЕВО КАТЕГОРИЙ: ПЛОСКИЙ СПИСОК",
                      subtitle=f"Одна строка — одна подкатегория с её категорией и корнем · {stamp}",
                      freeze_col=2, key_headers=("Подкатегория",))
    widths(ws, [24, 34, 40, 11])

    build_toc(
        wb,
        title="Дерево категорий товаров",
        subtitle="Корень → категория → подкатегория: три уровня по всей номенклатуре, включая услуги",
        params=stamp,
        sheets=[("Дерево", "Уровни с отступами; группы сворачиваются «−» слева"),
                ("Список", "Плоский список подкатегорий — удобно для фильтров и сопоставления")],
        cards=[
            ("КОРНЕВЫХ РАЗДЕЛОВ", n_roots, FMT_QTY, "Мебель, Свет, Декор, Услуги…"),
            ("КАТЕГОРИЙ", n_cats, FMT_QTY, "второй уровень"),
            ("ПОДКАТЕГОРИЙ", n_subs, FMT_QTY, "третий уровень"),
            ("ТОВАРОВ", sum(r[4] or 0 for r in rows if r[0] == 1), FMT_QTY, "привязано к категориям"),
        ],
    )
    finalize(wb, ["Оглавление", "Дерево", "Список"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
