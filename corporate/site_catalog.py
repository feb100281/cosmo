# corporate/site_catalog.py
"""Каталог сайта (Битрикс): загрузка JSON, проверка структуры, выгрузка в Excel."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO

EMPTY_XML = {"", "none", "null", "nan"}
MIXED_SCRIPT = re.compile(r"\b(?=\w*[А-Яа-яЁё])(?=\w*[A-Za-z])\w+\b")


def parse(raw: bytes | str) -> list[dict]:
    """Список разделов из JSON; проверяет обязательные поля."""
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("items") or data.get("sections") or list(data.values())
    if not isinstance(data, list) or not data:
        raise ValueError("В файле нет списка разделов")
    rows = []
    for i, r in enumerate(data, start=1):
        if not isinstance(r, dict) or "id" not in r or "name" not in r:
            raise ValueError(f"Запись {i}: нет полей id / name")
        rows.append({
            "site_id": int(r["id"]),
            "name": str(r.get("name") or "").strip(),
            "code": str(r.get("code") or "").strip(),
            "xml_id": str(r.get("xml_id") or "").strip(),
            "parent_site_id": int(r["parent_id"]) if r.get("parent_id") not in (None, "") else None,
            "parent_xml_id": str(r.get("parent_xml_id") or "").strip(),
            "depth": int(r.get("depth_level") or 0),
            "sort": int(r.get("sort") or 500),
            "active": bool(r.get("active", True)) and bool(r.get("global_active", True)),
            "path": str(r.get("path") or "").strip(),
        })
    return rows


def find_issues(rows: list[dict]) -> dict[int, list[str]]:
    """Замечания по каждому разделу: {site_id: [текст, ...]}."""
    by_id = {r["site_id"]: r for r in rows}
    children = defaultdict(list)
    for r in rows:
        if r["parent_site_id"] is not None:
            children[r["parent_site_id"]].append(r)
    names = Counter(r["name"].casefold() for r in rows)
    out: dict[int, list[str]] = defaultdict(list)

    for r in rows:
        sid, kids = r["site_id"], children.get(r["site_id"], [])
        active_kids = [k for k in kids if k["active"]]
        parent = by_id.get(r["parent_site_id"])

        if r["parent_site_id"] is not None and parent is None:
            out[sid].append("Родитель не найден в файле")
        if not r["active"]:
            out[sid].append("Раздел неактивен")
        if len(kids) == 1:
            out[sid].append(f"Один подраздел («{kids[0]['name']}») — уровень лишний или товары лежат в двух местах")
        elif kids and len(active_kids) == 1 and len(kids) > 1:
            out[sid].append(f"Активен только один подраздел («{active_kids[0]['name']}»)")
        elif kids and not active_kids and r["active"]:
            out[sid].append("Все подразделы неактивны")
        if r["xml_id"].casefold() in EMPTY_XML:
            out[sid].append("Нет связи с 1С: пустой xml_id")
        elif not re.fullmatch(r"[0-9a-fA-F-]{36}", r["xml_id"]):
            out[sid].append(f"Старый формат xml_id («{r['xml_id']}»), не GUID 1С")
        if parent and r["parent_xml_id"] != parent["xml_id"]:
            out[sid].append("parent_xml_id не совпадает с xml_id родителя")
        if MIXED_SCRIPT.search(r["name"]):
            out[sid].append("В названии смешаны русские и латинские буквы")
        if names[r["name"].casefold()] > 1:
            out[sid].append("Название повторяется в другом разделе")
        if r["active"] and parent and not parent["active"]:
            out[sid].append("Активный раздел внутри неактивного")
        # Разная глубина: лист, хотя у соседей есть подразделы
        if not kids and parent:
            siblings = [s for s in children[parent["site_id"]] if s is not r]
            if any(children.get(s["site_id"]) for s in siblings):
                out[sid].append("Конечный раздел, хотя у соседних есть подразделы (разная глубина)")
    return dict(out)


def tree_order(rows: list[dict]) -> list[dict]:
    """Обход дерева сверху вниз: родитель, затем дети по sort и названию."""
    children = defaultdict(list)
    ids = {r["site_id"] for r in rows}
    roots = []
    for r in rows:
        p = r["parent_site_id"]
        (children[p] if p in ids else roots).append(r)
    key = lambda r: (r["sort"], r["name"])
    out = []

    def walk(nodes, level):
        for n in sorted(nodes, key=key):
            out.append({**n, "level": level})
            walk(children.get(n["site_id"], []), level + 1)

    walk(roots, 1)
    return out


def summary(rows: list[dict], issues: dict[int, list[str]]) -> dict:
    ordered = tree_order(rows)
    return {
        "total": len(rows),
        "active": sum(r["active"] for r in rows),
        "roots": sum(1 for r in ordered if r["level"] == 1),
        "max_depth": max((r["level"] for r in ordered), default=0),
        "with_issues": len(issues),
        "issue_types": Counter(t.split(" (")[0].split(" («")[0] for v in issues.values() for t in v),
    }


# ---------------------------------------------------------------- Excel

_LEVEL_FILL = {1: "E7F1ED", 2: "F3F8F6", 3: None}


def build_excel(rows: list[dict], mapping: dict[int, tuple[str, str]] | None = None,
                loaded_at: datetime | None = None) -> bytes:
    """rows — разделы (как из parse); mapping — {site_id: (наша категория, наша подкатегория)}."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border
    from openpyxl.utils import get_column_letter

    from sales.reports.xl_brand import (
        EXPENSE, MUTED, NAVY, NAVY_3, build_toc, fill, finalize, font, side, style_table_sheet,
    )

    mapping = mapping or {}
    issues = find_issues(rows)
    ordered = tree_order(rows)
    info = summary(rows, issues)
    stamp = f"загрузка от {loaded_at:%d.%m.%Y %H:%M}" if loaded_at else f"сформировано {datetime.now():%d.%m.%Y %H:%M}"
    wb = Workbook()
    wb.remove(wb.active)

    def widths(ws, values):
        for i, w in enumerate(values, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # Дерево
    ws = wb.create_sheet("Дерево")
    head = ["Раздел", "Уровень", "Активен", "Подразделов", "Код", "xml_id (1С)", "id сайта", "Путь", "Замечания"]
    ws.append(head)
    kids = Counter(r["parent_site_id"] for r in rows)
    for r in ordered:
        ws.append([r["name"], r["level"], "да" if r["active"] else "нет", kids.get(r["site_id"], 0) or None,
                   r["code"], r["xml_id"], r["site_id"], r["path"], "; ".join(issues.get(r["site_id"], [])) or None])
    hdr = style_table_sheet(ws, title="КАТАЛОГ САЙТА: ДЕРЕВО РАЗДЕЛОВ",
                            subtitle=f"{info['total']} разделов, активных {info['active']}, "
                                     f"уровней {info['max_depth']} · {stamp}",
                            freeze_col=2, key_headers=("Раздел",), wrap_headers=("Подразделов",))
    ws.sheet_properties.outlinePr.summaryBelow = False
    for i, r in enumerate(ordered, start=hdr + 1):
        c = ws.cell(row=i, column=1)
        lvl = r["level"]
        c.alignment = Alignment(indent=(lvl - 1) * 2, vertical="center")
        c.font = font(11 if lvl == 1 else 10, lvl < 3, NAVY_3 if lvl < 3 else "1F1F1F")
        bg = _LEVEL_FILL.get(lvl)
        for j in range(1, len(head) + 1):
            cell = ws.cell(row=i, column=j)
            if bg:
                cell.fill = fill(bg)
            if not r["active"]:
                cell.font = font(10, False, MUTED, italic=True)
        if issues.get(r["site_id"]):
            ws.cell(row=i, column=len(head)).font = font(9, False, EXPENSE)
            ws.cell(row=i, column=len(head)).alignment = Alignment(wrap_text=True, vertical="top")
        if lvl > 1:
            ws.row_dimensions[i].outlineLevel = lvl - 1
    widths(ws, [44, 9, 9, 12, 26, 38, 10, 52, 70])

    # Проблемы
    ws = wb.create_sheet("Замечания")
    ws.append(["Раздел", "Путь", "Уровень", "Активен", "Замечание"])
    n_issues = 0
    for r in ordered:
        for t in issues.get(r["site_id"], []):
            ws.append([r["name"], r["path"], r["level"], "да" if r["active"] else "нет", t])
            n_issues += 1
    style_table_sheet(ws, title="ЗАМЕЧАНИЯ ПО СТРУКТУРЕ",
                      subtitle=f"{n_issues} замечаний по {info['with_issues']} разделам · фильтр — по колонке «Замечание»",
                      freeze_col=2, key_headers=("Замечание",))
    widths(ws, [34, 52, 9, 9, 80])

    # Сопоставление
    ws = wb.create_sheet("Сопоставление")
    ws.append(["Путь в каталоге сайта", "Уровень", "Активен", "Наша категория", "Наша подкатегория", "id сайта"])
    for r in ordered:
        cat, sub = mapping.get(r["site_id"], (None, None))
        ws.append([r["path"] or r["name"], r["level"], "да" if r["active"] else "нет", cat, sub, r["site_id"]])
    style_table_sheet(ws, title="СОПОСТАВЛЕНИЕ С НАШИМ ДЕРЕВОМ",
                      subtitle="Заполняется в админке: Каталог сайта → раздел → «Наша категория / подкатегория»",
                      freeze_col=2, key_headers=("Наша категория", "Наша подкатегория"))
    widths(ws, [60, 9, 9, 28, 28, 10])

    cards = [
        ("РАЗДЕЛОВ", info["total"], "#,##0", f"активных {info['active']}"),
        ("УРОВНЕЙ", info["max_depth"], "#,##0", f"корневых разделов {info['roots']}"),
        ("С ЗАМЕЧАНИЯМИ", info["with_issues"], "#,##0", f"замечаний {n_issues}"),
        ("СОПОСТАВЛЕНО", sum(1 for v in mapping.values() if v[0]), "#,##0", "с нашими категориями"),
    ]
    build_toc(
        wb,
        title="Каталог сайта (Битрикс)",
        subtitle="Дерево разделов, замечания по структуре, сопоставление с нашими категориями",
        params=stamp,
        sheets=[("Дерево", "Разделы с отступами по уровням; неактивные — серым курсивом"),
                ("Замечания", "Один подраздел, неактивные, нет связи с 1С, разная глубина и т.д."),
                ("Сопоставление", "Раздел сайта → наша категория и подкатегория")],
        cards=cards,
    )
    finalize(wb, ["Оглавление", "Дерево", "Замечания", "Сопоставление"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- база

def save_to_db(rows: list[dict]) -> dict:
    """Обновляет справочник SiteCategory по id сайта; сопоставление с нашими категориями сохраняется."""
    from django.db import transaction

    from corporate.models import SiteCategory

    fields = ["name", "code", "xml_id", "depth", "sort", "active", "path"]
    with transaction.atomic():
        existing = {o.site_id: o for o in SiteCategory.objects.all()}
        created = updated = 0
        objs = {}
        for r in rows:
            o = existing.get(r["site_id"])
            if o is None:
                o = SiteCategory(site_id=r["site_id"])
                created += 1
            else:
                updated += 1
            for f in fields:
                setattr(o, f, r[f])
            o.in_last_upload = True
            o.save()
            objs[r["site_id"]] = o
        for r in rows:
            o = objs[r["site_id"]]
            parent = objs.get(r["parent_site_id"])
            if o.parent_id != (parent.pk if parent else None):
                o.parent = parent
                o.save(update_fields=["parent"])
        gone = SiteCategory.objects.exclude(site_id__in=objs.keys()).update(in_last_upload=False, active=False)
    return {"created": created, "updated": updated, "gone": gone}


def rows_from_db() -> tuple[list[dict], dict[int, tuple[str, str]]]:
    """Разделы из справочника в формате parse() и сопоставление с нашими категориями."""
    from corporate.models import SiteCategory

    qs = SiteCategory.objects.select_related("parent", "our_cat", "our_subcat").filter(in_last_upload=True)
    rows, mapping = [], {}
    for o in qs:
        rows.append({
            "site_id": o.site_id, "name": o.name, "code": o.code, "xml_id": o.xml_id,
            "parent_site_id": o.parent.site_id if o.parent else None,
            "parent_xml_id": o.parent.xml_id if o.parent else "",
            "depth": o.depth, "sort": o.sort, "active": o.active, "path": o.path,
        })
        if o.our_cat_id or o.our_subcat_id:
            mapping[o.site_id] = (str(o.our_cat) if o.our_cat else None,
                                  str(o.our_subcat) if o.our_subcat else None)
    return rows, mapping
