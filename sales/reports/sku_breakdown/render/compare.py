# sales/reports/sku_breakdown/render/compare.py
"""Лист «Динамика»: категории, подкатегории и производители против прошлого периода."""
from __future__ import annotations

import pandas as pd
from openpyxl.styles import Alignment, Border
from openpyxl.utils import get_column_letter

from sales.reports.xl_brand import (
    EXPENSE, FMT_MONEY, FMT_QTY, MUTED, NAVY, NAVY_3, SURFACE_3, TEXT_2, TOTAL_ROW, ZEBRA_ROW,
    font, page_setup, toc_button,
)

from .periodfmt import rng

POSITIVE = "2E7D5B"
FMT_PCT = '+0%;−0%;0%'
FMT_PP = '+0.0" п.п.";−0.0" п.п.";"0 п.п."'
FMT_SHARE = '0.0%'
NBSP = " "

def _metrics(cur: str, prev: str) -> list[tuple[str, str, int, str]]:
    """(заголовок, ключ, ширина, формат); в заголовках — реальные даты периодов."""
    return [
        (f"Итого {cur}, ₽", "cur", 16, FMT_MONEY),
        (f"Итого {prev}, ₽", "prev", 16, FMT_MONEY),
        ("Изменение, ₽", "diff", 14, FMT_MONEY),
        ("Изменение, %", "chg", 11, FMT_PCT),
        (f"Доля {cur}", "share", 11, FMT_SHARE),
        (f"Доля {prev}", "share_prev", 11, FMT_SHARE),
        ("Изменение доли", "share_pp", 11, FMT_PP),
        (f"Шт. {cur}", "qty", 11, FMT_QTY),
        (f"Шт. {prev}", "qty_prev", 11, FMT_QTY),
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


def _block(ws, S, r: int, title: str, t: pd.DataFrame, labels: list[tuple[str, str, int]],
           summary: list[str], metrics, n_cols: int) -> int:
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

    cols = labels + [(h, k, w) for h, k, w, _f in metrics]
    for j, (h, k, _w) in enumerate(cols, start=1):
        S.put(ws, r, j, h, (10, True, "FFFFFF", NAVY_3 if k == "diff" else NAVY, "head", "center", 0, None))
    ws.row_dimensions[r].height = 42
    r += 1

    fmts = {k: f for _h, k, _w, f in metrics}
    keys = [k for _h, k, _w in cols]
    n = len(cols)
    for i, row in enumerate(t.reindex(columns=keys).to_numpy(dtype=object)):
        for j, k in enumerate(keys, start=1):
            v = row[j - 1]
            if v is not None and isinstance(v, float) and v != v:
                v = None
            color = "1F1F1F"
            if k in SIGNED and v:
                color = POSITIVE if v > 0 else EXPENSE
            bg = SURFACE_3 if k == "diff" else (ZEBRA_ROW if i % 2 else None)
            S.put(ws, r, j, v, (10, k == "cur", color, bg, "right" if j < n else "bottom",
                                "right" if k in fmts else "left", 0, fmts.get(k)))
        r += 1

    tot = {"cur": t["cur"].sum(), "prev": t["prev"].sum(), "qty": t["qty"].sum(), "qty_prev": t["qty_prev"].sum()}
    tot["diff"] = tot["cur"] - tot["prev"]
    tot["chg"] = tot["diff"] / tot["prev"] if tot["prev"] else None
    tot["share"], tot["share_prev"] = 1.0, 1.0
    for j, k in enumerate(keys, start=1):
        v = "Итого" if j == 1 else tot.get(k)
        numeric = k in fmts and v is not None
        S.put(ws, r, j, v, (10, True, NAVY_3, TOTAL_ROW, "grand", "right" if numeric else "left", 0,
                            fmts[k] if numeric else None))
    return r + 3


def build_compare_sheet(wb, S, cur: pd.DataFrame, prev: pd.DataFrame, start, end, prev_start, prev_end,
                        sheet: str = "Динамика", cur_store: pd.DataFrame | None = None) -> None:
    cur_l, prev_l = rng(start, end), rng(prev_start, prev_end)
    metrics = _metrics(cur_l, prev_l)
    ws = wb.create_sheet(sheet)
    page_setup(ws)
    n_cols = 2 + len(metrics)
    toc_button(ws, 1, n_cols)
    ws.cell(row=2, column=1, value="ДИНАМИКА: ПОДРАЗДЕЛЕНИЯ, КАТЕГОРИИ, ПОДКАТЕГОРИИ, ПРОИЗВОДИТЕЛИ").font = font(14, True)
    ws.row_dimensions[2].height = 24
    ws.cell(row=3, column=1, value=f"{cur_l} против {prev_l} · «Итого» — продажи за вычетом возвратов · "
                                   "доля — от итога сети за период").font = font(9, color=MUTED)

    widths = [30, 26] + [w for _h, _k, w, _f in metrics]
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(j)].width = w

    r = 5
    if cur_store is not None and "store_name" in cur_store.columns and "store_name" in prev.columns:
        t = compare_table(cur_store, prev, ["store_name"])
        r = _block(ws, S, r, "Подразделения", t, [("Подразделение", "store_name", 30), ("", "_", 26)],
                   _summary(t, "store_name", "подразделения"), metrics, n_cols)

    t = compare_table(cur, prev, ["cat_name"])
    r = _block(ws, S, r, "Категории", t, [("Категория", "cat_name", 30), ("", "_", 26)],
               _summary(t, "cat_name", "категории"), metrics, n_cols)

    t = compare_table(cur, prev, ["cat_name", "subcat_name"])
    r = _block(ws, S, r, "Подкатегории", t, [("Подкатегория", "subcat_name", 30), ("Категория", "cat_name", 26)],
               _summary(t, "subcat_name", "подкатегории"), metrics, n_cols)

    t = compare_table(cur, prev, ["manufacturer_name"])
    _block(ws, S, r, "Производители (бренды)", t, [("Производитель", "manufacturer_name", 30), ("", "_", 26)],
           _summary(t, "manufacturer_name", "производители"), metrics, n_cols)

    ws.freeze_panes = "B5"
