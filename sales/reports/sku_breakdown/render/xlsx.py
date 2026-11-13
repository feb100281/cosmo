# sales/reports/sku_breakdown/render/xlsx.py
"""
Отчёт «Разбивка по номенклатуре и штрихкодам» (.xlsx):
  - Оглавление, Выводы, Динамика;
  - Детализация — все позиции по убыванию выручки;
  - группировки по категориям, производителям и подразделениям (уровни сворачиваются).
"""

from __future__ import annotations

from copy import copy
from datetime import date, datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border
from openpyxl.utils import get_column_letter

from sales.reports.xl_brand import (
    EXPENSE,
    FMT_MONEY,
    FMT_QTY,
    MUTED,
    NAVY,
    NAVY_3,
    SURFACE_3,
    SURFACE_4,
    TOTAL_ROW,
    ZEBRA_ROW,
    build_toc,
    fill,
    finalize,
    font,
    page_setup,
    side,
    toc_button,
)

FMT_SHARE = '0.0%;-0.0%;"–"'

# (заголовок, ключ, ширина, формат)
METRIC_COLUMNS = [
    ("Продажи, ₽", "sales_amount", 14, FMT_MONEY),
    ("Продажи, шт.", "sales_qty", 11, FMT_QTY),
    ("Возвраты, ₽", "returns_amount", 14, FMT_MONEY),
    ("Возвраты, шт.", "returns_qty", 11, FMT_QTY),
    ("Итого, ₽", "net_amount", 15, FMT_MONEY),
    ("Итого, шт.", "net_qty", 11, FMT_QTY),
]
SHARE_COLUMN = ("Доля, %", "share", 9, FMT_SHARE)
TEXT_COLUMNS = [
    ("Номенклатура", "fullname", 46, None),
    ("Артикул", "article", 14, None),
    ("Штрихкод", "barcode", 16, "@"),
    ("Категория", "cat_name", 22, None),
    ("Подкатегория", "subcat_name", 22, None),
    ("Производитель", "manufacturer_name", 22, None),
]
DETAIL_COLUMNS = TEXT_COLUMNS + METRIC_COLUMNS
METRIC_KEYS = [k for _t, k, _w, _f in METRIC_COLUMNS]
RETURN_KEYS = {"returns_amount", "returns_qty"}
KEY_HEADER = "net_amount"

_REPORT_TYPE_LABEL = {"daily": "день", "weekly": "неделя", "monthly": "месяц", "period": "период"}
HEADER_ROW = 5
_INDENT = 2
# Уровни группировки: (заливка, цвет текста, размер шрифта)
_LEVEL_STYLE = [(SURFACE_4, NAVY_3, 10.5), (SURFACE_3, NAVY_3, 10), ("F4F7F5", "1F1F1F", 10), ("FAFBFA", "1F1F1F", 10)]


class Styler:
    """Кэш готовых стилей: одинаковые ячейки получают копию уже собранного стиля (в разы быстрее)."""

    def __init__(self):
        self._cache: dict = {}

    def put(self, ws, r: int, c: int, value, spec: tuple):
        cell = ws.cell(row=r, column=c, value=value)
        st = self._cache.get(spec)
        if st is None:
            size, bold, color, bg, border, halign, indent, fmt = spec
            cell.font = font(size, bold, color)
            if bg:
                cell.fill = fill(bg)
            if border == "grand":
                cell.border = Border(top=side(NAVY, "medium"), bottom=side(NAVY, "double"))
            elif border == "head":
                cell.border = Border(left=side(), right=side(), top=side(), bottom=side())
            elif border:
                top = side(NAVY, "thin") if "top" in border else (side() if "line" in border else None)
                cell.border = Border(top=top, bottom=side(), right=side() if "right" in border else None)
            cell.alignment = Alignment(horizontal=halign, vertical="center", indent=indent,
                                       wrap_text=border == "head")
            if fmt:
                cell.number_format = fmt
            self._cache[spec] = copy(cell._style)
        else:
            cell._style = copy(st)
        return cell


def _period_text(meta: dict) -> str:
    kind = _REPORT_TYPE_LABEL.get(meta["report_type"], meta["report_type"])
    s, e = meta["start"], meta["end"]
    rng = f"{s:%d.%m.%Y}" if s == e else f"{s:%d.%m.%Y} — {e:%d.%m.%Y}"
    return f"{kind.capitalize()}: {rng}"


def _params(meta: dict) -> str:
    return f"Рубли и штуки · {_period_text(meta)} · сформировано {meta['generated_at']:%d.%m.%Y %H:%M}"


def _sheet_top(ws, n_cols: int, title: str, meta: dict) -> None:
    page_setup(ws)
    toc_button(ws, 1, n_cols)
    ws.cell(row=2, column=1, value=title.upper()).font = font(14, True)
    ws.row_dimensions[2].height = 24
    ws.cell(row=3, column=1, value=_params(meta)).font = font(9, color=MUTED)
    for c in range(1, n_cols + 1):
        ws.cell(row=4, column=c).border = Border(bottom=side(NAVY, "medium"))
    ws.row_dimensions[4].height = 6


def _header(ws, S: Styler, columns) -> None:
    for j, (title, key, width, _fmt) in enumerate(columns, start=1):
        bg = NAVY_3 if key == KEY_HEADER else NAVY
        S.put(ws, HEADER_ROW, j, title, (10, True, "FFFFFF", bg, "head", "center", 0, None))
        ws.column_dimensions[get_column_letter(j)].width = width
    ws.row_dimensions[HEADER_ROW].height = 30


def _write_rows(ws, S: Styler, r: int, columns, df: pd.DataFrame, *, indent: int = 0,
                outline: int = 0) -> int:
    """Строки позиций; df уже отсортирован."""
    n = len(columns)
    keys = [k for _t, k, _w, _f in columns]
    data = df[keys].to_numpy(dtype=object) if len(df) else []
    for i, row in enumerate(data):
        zebra = i % 2 == 1
        for j, (_t, key, _w, fmt) in enumerate(columns, start=1):
            v = row[j - 1]
            if v is not None and isinstance(v, float) and v != v:
                v = None
            elif key == "barcode" and v is not None:
                v = str(v)
            color = EXPENSE if key in RETURN_KEYS and v else "1F1F1F"
            bg = SURFACE_3 if key == KEY_HEADER else (ZEBRA_ROW if zebra else None)
            numeric = fmt is not None and fmt != "@"
            S.put(ws, r, j, v, (10, False, color, bg, "right" if j < n else "bottom",
                                "right" if numeric else "left", indent if j == 1 else 0, fmt))
        if outline:
            dim = ws.row_dimensions[r]
            dim.outlineLevel, dim.hidden = outline, True
        r += 1
    return r


def _sums(df: pd.DataFrame, total: float | None = None) -> dict:
    out = {k: float(df[k].sum()) for k in METRIC_KEYS}
    if total:
        out["share"] = out["net_amount"] / total
    return out


def _total_row(ws, S: Styler, r: int, columns, label: str, totals: dict) -> None:
    for j, (_t, key, _w, fmt) in enumerate(columns, start=1):
        v = label if j == 1 else totals.get(key)
        numeric = fmt and fmt != "@" and key in totals
        S.put(ws, r, j, v, (10, True, NAVY_3, TOTAL_ROW, "grand", "right" if numeric else "left", 0,
                            fmt if numeric else None))
    ws.row_dimensions[r].height = 20


def _build_detail_sheet(wb: Workbook, S: Styler, df: pd.DataFrame, meta: dict) -> None:
    ws = wb.create_sheet("Детализация")
    _sheet_top(ws, len(DETAIL_COLUMNS), "Детализация по номенклатуре и штрихкодам", meta)
    _header(ws, S, DETAIL_COLUMNS)
    r = _write_rows(ws, S, HEADER_ROW + 1, DETAIL_COLUMNS, df.sort_values("net_amount", ascending=False))
    last = r - 1
    _total_row(ws, S, r, DETAIL_COLUMNS, f"ИТОГО ЗА ПЕРИОД ({len(df)} поз.)", _sums(df))
    ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=2)
    if last > HEADER_ROW:
        ws.auto_filter.ref = f"A{HEADER_ROW}:{get_column_letter(len(DETAIL_COLUMNS))}{last}"


def _group_row(ws, S: Styler, r: int, columns, label: str, sums: dict, depth: int) -> None:
    n = len(columns)
    bg, color, size = _LEVEL_STYLE[min(depth, len(_LEVEL_STYLE) - 1)]
    border = ("top" if depth == 0 else "line") + ("right" if True else "")
    for j, (_t, key, _w, fmt) in enumerate(columns, start=1):
        v = label if j == 1 else sums.get(key)
        numeric = j > 1 and fmt and fmt != "@" and key in sums
        S.put(ws, r, j, v, (size, True, color, bg, border if j < n else border.replace("right", ""),
                            "right" if numeric else "left", depth * _INDENT if j == 1 else 0,
                            fmt if numeric else None))
    ws.row_dimensions[r].height = 20 if depth == 0 else 18


def _build_grouped_sheet(wb: Workbook, S: Styler, df: pd.DataFrame, meta: dict, *, group_cols: list[str],
                         sheet_title: str, title: str) -> None:
    """Многоуровневая группировка; все уровни свёрнуты, раскрываются «+» слева."""
    columns = [c for c in DETAIL_COLUMNS if c[1] not in group_cols] + [SHARE_COLUMN]
    depth_items = len(group_cols)
    total = float(df["net_amount"].sum()) or None
    df = df.assign(share=df["net_amount"] / total if total else 0.0)

    ws = wb.create_sheet(sheet_title)
    _sheet_top(ws, len(columns), title, meta)
    _header(ws, S, columns)
    ws.sheet_properties.outlinePr.summaryBelow = False
    ws.sheet_format.outlineLevelRow = depth_items

    def write(part: pd.DataFrame, depth: int, r: int) -> int:
        col = group_cols[depth]
        groups = dict(tuple(part.groupby(col, dropna=False, sort=False)))
        order = sorted(groups, key=lambda k: -groups[k]["net_amount"].sum())
        for value in order:
            g = groups[value]
            _group_row(ws, S, r, columns, f"{value}  ·  {len(g)} поз.", _sums(g, total), depth)
            dim = ws.row_dimensions[r]
            if depth:
                dim.outlineLevel, dim.hidden = depth, True
            dim.collapsed = True
            r += 1
            if depth + 1 < depth_items:
                r = write(g, depth + 1, r)
            else:
                r = _write_rows(ws, S, r, columns, g.sort_values("net_amount", ascending=False),
                                indent=depth_items * _INDENT, outline=depth_items)
        return r

    r = write(df, 0, HEADER_ROW + 1)
    _total_row(ws, S, r, columns, f"ОБЩИЙ ИТОГ ({len(df)} поз.)", _sums(df, total))
    ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=2)


def _meta(report_type, start, end) -> dict:
    return {"report_type": report_type, "start": start, "end": end, "generated_at": datetime.now()}


STORE_SHEETS = [
    ("Подразделения → категории", ["store_name", "cat_name", "subcat_name"],
     "Продажи по подразделениям и категориям", "Подразделение → категория → подкатегория → позиции"),
    ("Подразделения → производители", ["store_name", "manufacturer_name", "cat_name", "subcat_name"],
     "Продажи по подразделениям и производителям",
     "Подразделение → производитель → категория → подкатегория → позиции"),
]


def build_workbook(df: pd.DataFrame, *, report_type: str, start: date, end: date,
                   df_store: pd.DataFrame | None = None, df_store_prev: pd.DataFrame | None = None,
                   prev_start: date | None = None, prev_end: date | None = None) -> Workbook:
    meta = _meta(report_type, start, end)
    wb = Workbook()
    wb.remove(wb.active)
    S = Styler()
    toc_sheets = []

    if df.empty:
        ws = wb.create_sheet("Детализация")
        _sheet_top(ws, 6, "Детализация по номенклатуре и штрихкодам", meta)
        ws.cell(row=6, column=1, value="За этот период продаж нет.").font = font(10, color=MUTED)
        ws.column_dimensions["A"].width = 60
        cards = []
    else:
        has_store = df_store is not None and not df_store.empty
        has_prev = df_store_prev is not None and prev_start is not None
        if has_store:
            from .story import build_store_story, write_story

            write_story(wb, build_store_story(df_store, df_store_prev if has_prev else None,
                                              start, end, prev_start, prev_end))
            toc_sheets.append(("Выводы", "Подразделения: кто чем торгует, сравнение с прошлым периодом"))
        if has_prev:
            from .compare import build_compare_sheet

            build_compare_sheet(wb, S, df, df_store_prev, start, end, prev_start, prev_end,
                                cur_store=df_store if has_store else None)
            toc_sheets.append(("Динамика", "Подразделения, категории, подкатегории и производители "
                                           "против периода сравнения"))

        _build_detail_sheet(wb, S, df, meta)
        _build_grouped_sheet(wb, S, df, meta, group_cols=["cat_name", "subcat_name"],
                             sheet_title="По категориям", title="Продажи по категориям")
        _build_grouped_sheet(wb, S, df, meta, group_cols=["manufacturer_name", "cat_name", "subcat_name"],
                             sheet_title="По производителям", title="Продажи по производителям")
        toc_sheets += [
            ("Детализация", "Все позиции и штрихкоды по убыванию выручки"),
            ("По категориям", "Категория → подкатегория → позиции; раскрываются «+» слева"),
            ("По производителям", "Производитель → категория → подкатегория → позиции"),
        ]
        if has_store:
            for name, cols, title, hint in STORE_SHEETS:
                _build_grouped_sheet(wb, S, df_store, meta, group_cols=cols, sheet_title=name, title=title)
                toc_sheets.append((name, hint))

        t = _sums(df)
        ret_share = t["returns_amount"] / t["sales_amount"] if t["sales_amount"] else 0.0
        cards = [
            ("ВЫРУЧКА (ИТОГО), ₽", t["net_amount"], FMT_MONEY, _period_text(meta)),
            ("ПРОДАНО, ШТ.", t["net_qty"], FMT_QTY, "за вычетом возвратов"),
            ("ВОЗВРАТЫ, ₽", t["returns_amount"], FMT_MONEY, f"{ret_share:.1%} от продаж".replace(".", ",")),
            ("ПОЗИЦИЙ", len(df), FMT_QTY, f"{df['item_id'].nunique()} SKU · {df['barcode'].nunique()} штрихкодов"),
        ]

    build_toc(
        wb,
        title="Продажи по номенклатуре",
        subtitle="Разбивка по номенклатуре и штрихкодам",
        params=_params(meta),
        cards=cards,
        sheets=toc_sheets or [("Детализация", "Продаж за период нет")],
    )
    finalize(wb, ["Оглавление"] + [s for s, _ in toc_sheets])
    return wb
