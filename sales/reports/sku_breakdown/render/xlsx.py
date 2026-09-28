# sales/reports/sku_breakdown/render/xlsx.py
"""
Отчёт «Разбивка по номенклатуре и штрихкодам» (.xlsx):
  - Оглавление      — итоги периода и ссылки на листы;
  - Детализация     — все позиции, по убыванию выручки;
  - По категориям   — позиции внутри категорий с подытогами (группы сворачиваются);
  - По производителям — то же по производителям.
"""

from __future__ import annotations

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

# (заголовок, ключ, ширина, формат)
METRIC_COLUMNS = [
    ("Продажи, ₽", "sales_amount", 14, FMT_MONEY),
    ("Продажи, шт.", "sales_qty", 11, FMT_QTY),
    ("Возвраты, ₽", "returns_amount", 14, FMT_MONEY),
    ("Возвраты, шт.", "returns_qty", 11, FMT_QTY),
    ("Итого, ₽", "net_amount", 15, FMT_MONEY),
    ("Итого, шт.", "net_qty", 11, FMT_QTY),
]
TEXT_COLUMNS = [
    ("Номенклатура", "fullname", 46, None),
    ("Артикул", "article", 14, None),
    ("Штрихкод", "barcode", 16, "@"),
    ("Категория", "cat_name", 22, None),
    ("Подкатегория", "subcat_name", 22, None),
    ("Производитель", "manufacturer_name", 22, None),
]
DETAIL_COLUMNS = TEXT_COLUMNS + METRIC_COLUMNS
RETURN_KEYS = {"returns_amount", "returns_qty"}
KEY_HEADER = "net_amount"

_REPORT_TYPE_LABEL = {"daily": "день", "weekly": "неделя", "monthly": "месяц"}
HEADER_ROW = 5


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


def _header(ws, columns) -> None:
    for j, (title, key, width, _fmt) in enumerate(columns, start=1):
        c = ws.cell(row=HEADER_ROW, column=j, value=title)
        c.font = font(10, True, "FFFFFF")
        c.fill = fill(NAVY_3 if key == KEY_HEADER else NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = Border(left=side(), right=side(), top=side(), bottom=side())
        ws.column_dimensions[get_column_letter(j)].width = width
    ws.row_dimensions[HEADER_ROW].height = 30


def _data_row(ws, r: int, columns, rec: dict, zebra: bool) -> None:
    n = len(columns)
    for j, (_t, key, _w, fmt) in enumerate(columns, start=1):
        v = rec.get(key)
        if key == "barcode" and v is not None:
            v = str(v)
        if isinstance(v, float) and pd.isna(v):
            v = None
        c = ws.cell(row=r, column=j, value=v)
        c.font = font(10, color=EXPENSE if key in RETURN_KEYS and v else "1F1F1F")
        c.border = Border(bottom=side(), right=side() if j < n else None)
        if fmt:
            c.number_format = fmt
        if fmt and fmt != "@":
            c.alignment = Alignment(horizontal="right", vertical="center")
        else:
            c.alignment = Alignment(horizontal="left", vertical="center")
        if key == KEY_HEADER:
            c.fill = fill(SURFACE_3)
        elif zebra:
            c.fill = fill(ZEBRA_ROW)


def _sums(df: pd.DataFrame) -> dict:
    return {key: float(df[key].sum()) for _t, key, _w, _f in METRIC_COLUMNS}


def _total_row(ws, r: int, columns, label: str, totals: dict, *, level: str) -> None:
    """level: group — подытог группы; grand — общий итог."""
    n = len(columns)
    bg = TOTAL_ROW if level == "grand" else SURFACE_3
    for j, (_t, key, _w, fmt) in enumerate(columns, start=1):
        v = label if j == 1 else totals.get(key)
        c = ws.cell(row=r, column=j, value=v)
        c.font = font(10, True, NAVY_3 if level == "grand" else "1F1F1F")
        c.fill = fill(bg)
        if level == "grand":
            c.border = Border(top=side(NAVY, "medium"), bottom=side(NAVY, "double"))
        else:
            c.border = Border(top=side(), bottom=side(), right=side() if j < n else None)
        if fmt and fmt != "@" and key in totals:
            c.number_format = fmt
            c.alignment = Alignment(horizontal="right", vertical="center")
    ws.row_dimensions[r].height = 20


def _build_detail_sheet(wb: Workbook, df: pd.DataFrame, meta: dict) -> None:
    ws = wb.create_sheet("Детализация")
    _sheet_top(ws, len(DETAIL_COLUMNS), "Детализация по номенклатуре и штрихкодам", meta)
    _header(ws, DETAIL_COLUMNS)

    r = HEADER_ROW + 1
    for i, (_, rec) in enumerate(df.sort_values("net_amount", ascending=False).iterrows()):
        _data_row(ws, r, DETAIL_COLUMNS, rec.to_dict(), zebra=i % 2 == 1)
        r += 1
    last = r - 1
    _total_row(ws, r, DETAIL_COLUMNS, f"ИТОГО ЗА ПЕРИОД ({len(df)} поз.)", _sums(df), level="grand")

    ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=2)
    if last > HEADER_ROW:
        ws.auto_filter.ref = f"A{HEADER_ROW}:{get_column_letter(len(DETAIL_COLUMNS))}{last}"


def _build_grouped_sheet(wb: Workbook, df: pd.DataFrame, meta: dict, *, group_col: str,
                         sheet_title: str, title: str) -> None:
    columns = [c for c in DETAIL_COLUMNS if c[1] != group_col]
    n = len(columns)
    ws = wb.create_sheet(sheet_title)
    _sheet_top(ws, n, title, meta)
    _header(ws, columns)
    ws.sheet_properties.outlinePr.summaryBelow = False

    order = df.groupby(group_col, dropna=False)["net_amount"].sum().sort_values(ascending=False)
    r = HEADER_ROW + 1
    for group_value in order.index.tolist():
        g = df[df[group_col] == group_value].sort_values("net_amount", ascending=False)
        sums = _sums(g)
        for j, (_t, key, _w, fmt) in enumerate(columns, start=1):
            v = f"{group_value}  ·  {len(g)} поз." if j == 1 else sums.get(key)
            c = ws.cell(row=r, column=j, value=v)
            c.font = font(10, True, NAVY_3)
            c.fill = fill(SURFACE_4)
            c.border = Border(top=side(NAVY, "thin"), bottom=side(), right=side() if j < n else None)
            if fmt and fmt != "@" and key in sums:
                c.number_format = fmt
                c.alignment = Alignment(horizontal="right", vertical="center")
        ws.row_dimensions[r].height = 20
        r += 1
        for i, (_, rec) in enumerate(g.iterrows()):
            _data_row(ws, r, columns, rec.to_dict(), zebra=i % 2 == 1)
            ws.row_dimensions[r].outlineLevel = 1
            r += 1

    _total_row(ws, r, columns, f"ОБЩИЙ ИТОГ ({len(df)} поз.)", _sums(df), level="grand")
    ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=2)


def _meta(report_type, start, end) -> dict:
    return {"report_type": report_type, "start": start, "end": end, "generated_at": datetime.now()}


def build_workbook(df: pd.DataFrame, *, report_type: str, start: date, end: date) -> Workbook:
    meta = _meta(report_type, start, end)
    wb = Workbook()
    wb.remove(wb.active)

    if df.empty:
        ws = wb.create_sheet("Детализация")
        _sheet_top(ws, 6, "Детализация по номенклатуре и штрихкодам", meta)
        ws.cell(row=6, column=1, value="За этот период продаж нет.").font = font(10, color=MUTED)
        ws.column_dimensions["A"].width = 60
        cards = []
    else:
        _build_detail_sheet(wb, df, meta)
        _build_grouped_sheet(wb, df, meta, group_col="cat_name", sheet_title="По категориям",
                             title="Продажи по категориям")
        _build_grouped_sheet(wb, df, meta, group_col="manufacturer_name", sheet_title="По производителям",
                             title="Продажи по производителям")
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
        sheets=[
            ("Детализация", "Все позиции и штрихкоды по убыванию выручки"),
            ("По категориям", "Позиции внутри категорий с подытогами; группы сворачиваются «−»"),
            ("По производителям", "То же в разрезе производителей"),
        ],
    )
    finalize(wb, ["Оглавление", "Детализация", "По категориям", "По производителям"])
    return wb
