# sales/reports/sku_breakdown/render/compare.py
"""Лист «Динамика»: категории, подкатегории и производители против прошлого периода."""
from __future__ import annotations

import pandas as pd
from openpyxl.styles import Alignment, Border
from openpyxl.utils import get_column_letter

from sales.reports.xl_brand import (
    EXPENSE, FMT_MONEY, FMT_QTY, MUTED, NAVY, NAVY_3, SURFACE_3, SURFACE_4, TEXT_2, TOTAL_ROW, ZEBRA_ROW,
    fill, font, page_setup, side, toc_button,
)

POSITIVE = "2E7D5B"
FMT_PCT = '+0%;−0%;0%'
FMT_PP = '+0.0" п.п.";−0.0" п.п.";"0 п.п."'
FMT_SHARE = '0.0%'
NBSP = " "

# (заголовок, ключ, ширина, формат)
METRICS = [
    ("Продажи, ₽", "cur", 15, FMT_MONEY),
    ("Прошлый период, ₽", "prev", 15, FMT_MONEY),
    ("Изменение, ₽", "diff", 14, FMT_MONEY),
    ("Изменение, %", "chg", 11, FMT_PCT),
    ("Доля, %", "share", 9, FMT_SHARE),
    ("Доля раньше, %", "share_prev", 10, FMT_SHARE),
    ("Изм. доли", "share_pp", 11, FMT_PP),
    ("Шт.", "qty", 9, FMT_QTY),
    ("Шт. раньше", "qty_prev", 10, FMT_QTY),
]
SIGNED = {"diff", "chg", "share_pp"}


def _money(v: float) -> str:
    a = abs(v)
    sign = "−" if v < 0 else ""
    if a >= 1_000_000:
        return f"{sign}{a / 1_000_000:.1f}".replace(".", ",") + f"{NBSP}млн{NBSP}₽"
    if a >= 1_000:
        return f"{sign}{a / 1_000:.0f}{NBSP}тыс.{NBSP}₽"
    return f"{sign}{a:.0f}{NBSP}₽"


def compare_table(cur: pd.DataFrame, prev: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    def agg(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=keys + ["amount", "qty"]).set_index(keys)
        return df.groupby(keys, dropna=False).agg(amount=("net_amount", "sum"), qty=("net_qty", "sum"))

    a, b = agg(cur), agg(prev)
    t = a.join(b, how="outer", lsuffix="", rsuffix="_prev").fillna(0.0).reset_index()
    t = t.rename(columns={"amount": "cur", "amount_prev": "prev"})
    tot, tot_prev = t["cur"].sum(), t["prev"].sum()
    t["diff"] = t["cur"] - t["prev"]
    t["chg"] = (t["diff"] / t["prev"]).where(t["prev"] > 0)
    t["share"] = t["cur"] / tot if tot else 0.0
    t["share_prev"] = t["prev"] / tot_prev if tot_prev else 0.0
    t["share_pp"] = (t["share"] - t["share_prev"]) * 100
    t = t[(t["cur"] != 0) | (t["prev"] != 0)]
    return t.sort_values(["cur", "prev"], ascending=False).reset_index(drop=True)


def _summary(t: pd.DataFrame, name_col: str, what: str) -> list[str]:
    """Короткие выводы над таблицей: кто дал рост, кто просел, что появилось и исчезло."""
    lines = []
    up = t[t["diff"] > 0].nlargest(3, "diff")
    down = t[t["diff"] < 0].nsmallest(3, "diff")
    if len(up):
        lines.append("Рост дали: " + ", ".join(f"{r[name_col]} (+{_money(r['diff'])})" for _, r in up.iterrows()))
    if len(down):
        lines.append("Просели: " + ", ".join(f"{r[name_col]} ({_money(r['diff'])})" for _, r in down.iterrows()))
    new = t[(t["prev"] == 0) & (t["cur"] > 0)]
    gone = t[(t["cur"] == 0) & (t["prev"] > 0)]
    if len(new):
        lines.append(f"Новые {what} без продаж в прошлом периоде: {len(new)} на {_money(new['cur'].sum())}")
    if len(gone):
        lines.append(f"Не продавались в этом периоде: {len(gone)} (в прошлом было {_money(gone['prev'].sum())})")
    gain = t.nlargest(1, "share_pp")
    if len(gain) and gain.iloc[0]["share_pp"] >= 1:
        g = gain.iloc[0]
        lines.append(f"Сильнее всего выросла доля: {g[name_col]} — "
                     f"{g['share_prev'] * 100:.1f}% → {g['share'] * 100:.1f}%".replace(".", ","))
    return lines


def _block(ws, r: int, title: str, t: pd.DataFrame, labels: list[tuple[str, str, int]],
           summary: list[str], n_cols: int) -> int:
    ws.cell(row=r, column=1, value=title.upper()).font = font(12, True, NAVY)
    ws.row_dimensions[r].height = 22
    r += 1
    for line in summary:
        c = ws.cell(row=r, column=1, value=f"•  {line}")
        c.font = font(10, color=TEXT_2)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 16 * max(1, -(-len(line) // 150)) + 2
        r += 1
    r += 1

    cols = labels + [(h, k, w) for h, k, w, _f in METRICS]
    for j, (h, k, _w) in enumerate(cols, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font = font(10, True, "FFFFFF")
        c.fill = fill(NAVY_3 if k == "diff" else NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = Border(left=side(), right=side(), top=side(), bottom=side())
    ws.row_dimensions[r].height = 38
    r += 1

    fmts = {k: f for _h, k, _w, f in METRICS}
    for i, (_, row) in enumerate(t.iterrows()):
        for j, (_h, k, _w) in enumerate(cols, start=1):
            v = row.get(k)
            if isinstance(v, float) and pd.isna(v):
                v = None
            c = ws.cell(row=r, column=j, value=v)
            color = "1F1F1F"
            if k in SIGNED and v:
                color = POSITIVE if v > 0 else EXPENSE
            c.font = font(10, k == "cur", color)
            c.border = Border(bottom=side(), right=side() if j < len(cols) else None)
            if k in fmts:
                c.number_format = fmts[k]
                c.alignment = Alignment(horizontal="right", vertical="center")
            if k == "diff":
                c.fill = fill(SURFACE_3)
            elif i % 2:
                c.fill = fill(ZEBRA_ROW)
        r += 1

    tot = {"cur": t["cur"].sum(), "prev": t["prev"].sum(), "qty": t["qty"].sum(), "qty_prev": t["qty_prev"].sum()}
    tot["diff"] = tot["cur"] - tot["prev"]
    tot["chg"] = tot["diff"] / tot["prev"] if tot["prev"] else None
    tot["share"], tot["share_prev"] = 1.0, 1.0
    for j, (_h, k, _w) in enumerate(cols, start=1):
        v = "Итого" if j == 1 else tot.get(k)
        c = ws.cell(row=r, column=j, value=v)
        c.font = font(10, True, NAVY_3)
        c.fill = fill(TOTAL_ROW)
        c.border = Border(top=side(NAVY, "medium"), bottom=side(NAVY, "double"))
        if k in fmts and v is not None:
            c.number_format = fmts[k]
            c.alignment = Alignment(horizontal="right", vertical="center")
    return r + 3


def build_compare_sheet(wb, cur: pd.DataFrame, prev: pd.DataFrame, period_text: str, prev_text: str,
                        sheet: str = "Динамика") -> None:
    ws = wb.create_sheet(sheet)
    page_setup(ws)
    n_cols = 2 + len(METRICS)
    toc_button(ws, 1, n_cols)
    ws.cell(row=2, column=1, value="ДИНАМИКА: КАТЕГОРИИ, ПОДКАТЕГОРИИ, ПРОИЗВОДИТЕЛИ").font = font(14, True)
    ws.row_dimensions[2].height = 24
    ws.cell(row=3, column=1, value=f"{period_text} против {prev_text} · продажи за вычетом возвратов · "
                                   "доля — от продаж сети за период").font = font(9, color=MUTED)

    widths = [30, 26] + [w for _h, _k, w, _f in METRICS]
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(j)].width = w

    r = 5
    t = compare_table(cur, prev, ["cat_name"])
    r = _block(ws, r, "Категории", t, [("Категория", "cat_name", 30), ("", "_", 26)],
               _summary(t, "cat_name", "категории"), n_cols)

    t = compare_table(cur, prev, ["cat_name", "subcat_name"])
    r = _block(ws, r, "Подкатегории", t, [("Подкатегория", "subcat_name", 30), ("Категория", "cat_name", 26)],
               _summary(t, "subcat_name", "подкатегории"), n_cols)

    t = compare_table(cur, prev, ["manufacturer_name"])
    _block(ws, r, "Производители (бренды)", t, [("Производитель", "manufacturer_name", 30), ("", "_", 26)],
           _summary(t, "manufacturer_name", "производители"), n_cols)

    ws.freeze_panes = "B5"
