# sales/reports/sku_breakdown/render/story.py
"""Лист «Выводы»: что и как продаёт каждое подразделение, сравнение с периодом для сравнения."""
from __future__ import annotations

import pandas as pd

from .periodfmt import rng

NBSP = " "
TOP_N = 3


def _money(v: float) -> str:
    a = abs(v)
    if a >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".replace(".", ",") + f"{NBSP}млн{NBSP}₽"
    elif a >= 1_000:
        s = f"{v / 1_000:.0f}" + f"{NBSP}тыс.{NBSP}₽"
    else:
        s = f"{v:.0f}{NBSP}₽"
    return s.replace("-", "−")


def _pct(v: float) -> str:
    return f"{v:.0f}%"


def _change(cur: float, prev: float, prev_l: str) -> str:
    if not prev_l:
        return ""
    if prev <= 0:
        return f"за {prev_l} продаж не было" if cur > 0 else ""
    ch = (cur - prev) / prev * 100
    if abs(ch) < 0.5:
        return f"на уровне {prev_l} (было {_money(prev)})"
    return f"{'больше' if ch > 0 else 'меньше'} на {abs(ch):.0f}% к {prev_l} (было {_money(prev)})"


def _qty(v: float) -> str:
    return f"{v:,.0f}".replace(",", NBSP)


def _items(n: int) -> str:
    n = int(n)
    w = "товар" if n % 10 == 1 and n % 100 != 11 else (
        "товара" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "товаров")
    return f"{n}{NBSP}{w}"


def _by(df: pd.DataFrame, col: str) -> pd.Series:
    return df.groupby(col)["net_amount"].sum().sort_values(ascending=False)


def _top_list(s: pd.Series, total: float, n: int = TOP_N) -> str:
    s = s[s > 0].head(n)
    return ", ".join(f"{k} — {_money(v)} ({_pct(v / total * 100) if total else '—'})" for k, v in s.items())


DIMS = [("manufacturer_name", "бренд", "бренда"), ("cat_name", "категория", "категории"),
        ("subcat_name", "подкатегория", "подкатегории")]  # доли подразделений по брендам и категориям
MAIN_SHARE = 0.5      # подразделение даёт не меньше половины продаж бренда/категории в сети
MIN_NET_SHARE = 0.005  # и сам бренд/категория — не меньше 0,5% продаж сети


def _store_shares(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Доля каждого подразделения в продажах бренда/категории по сети."""
    t = df.groupby([col, "store_name"])["net_amount"].sum()
    tot = t.groupby(level=0).sum()
    out = t.reset_index().rename(columns={"net_amount": "amount"})
    out["total"] = out[col].map(tot)
    out["share"] = (out["amount"] / out["total"]).where(out["total"] > 0, 0.0)
    return out


def _where_sold(df: pd.DataFrame, col: str, total: float, n: int = 5) -> str:
    """Топ брендов/категорий сети и где их продают больше всего."""
    sh = _store_shares(df, col)
    top = sh.groupby(col)["amount"].sum().sort_values(ascending=False)
    parts = []
    for k, v in top[top > 0].head(n).items():
        best = sh[sh[col] == k].sort_values("amount", ascending=False).iloc[0]
        parts.append(f"{k} — {_money(v)}, больше всего в «{best['store_name']}» ({_pct(best['share'] * 100)})")
    return "; ".join(parts)


def build_store_story(df: pd.DataFrame, prev: pd.DataFrame | None, start, end, prev_start=None,
                      prev_end=None) -> list[tuple[str, str]]:
    """df / prev — разбивка по подразделениям (колонка store_name). Стили: h1, sub, h2, h3, store, p, li, note."""
    S: list[tuple[str, str]] = []
    prev = prev if prev is not None else pd.DataFrame(columns=df.columns)
    total = float(df["net_amount"].sum())
    total_prev = float(prev["net_amount"].sum()) if len(prev) else 0.0
    stores = _by(df, "store_name")
    stores_prev = _by(prev, "store_name") if len(prev) else pd.Series(dtype=float)
    net_cat = _by(df, "cat_name")
    net_cat_share = net_cat / total if total else net_cat * 0

    S.append(("h1", "Подразделения: кто чем торгует"))
    cur_l = rng(start, end)
    prev_l = rng(prev_start, prev_end) if prev_start else ""
    S.append(("sub", f"Период {cur_l}" + (f", сравнение с {prev_l}" if prev_l else "")
                     + ". Все суммы — продажи за вычетом возвратов (как «Итого» на других листах)."))

    # Сеть
    S.append(("h2", "Сеть в целом"))
    ch = _change(total, total_prev, prev_l)
    S.append(("p", f"Продажи сети — {_money(total)}" + (f", {ch}" if ch else "") + "."))
    if len(stores):
        lead = stores.index[0]
        S.append(("p", f"Больше всех продало подразделение «{lead}» — {_money(stores.iloc[0])}, "
                       f"{_pct(stores.iloc[0] / total * 100) if total else '—'} продаж сети."))
        if len(stores_prev):
            delta = (stores - stores_prev.reindex(stores.index).fillna(0)).sort_values()
            up, down = delta[delta > 0], delta[delta < 0]
            if len(up):
                S.append(("li", f"Сильнее всех выросло «{up.index[-1]}»: +{_money(up.iloc[-1])} к {prev_l}"))
            if len(down):
                S.append(("li", f"Сильнее всех снизилось «{down.index[0]}»: −{_money(-down.iloc[0])} к {prev_l}"))
    S.append(("li", "Главные категории сети: " + _top_list(net_cat, total)))
    S.append(("li", "Главные производители сети: " + _top_list(_by(df, "manufacturer_name"), total)))
    multi = len(stores) > 1
    shares = {col: _store_shares(df, col) for col, _a, _b in DIMS} if multi else {}
    if multi:
        S.append(("h3", "Где что продают"))
        S.append(("li", "Бренды: " + _where_sold(df, "manufacturer_name", total)))
        S.append(("li", "Категории: " + _where_sold(df, "cat_name", total)))
        S.append(("li", "Подкатегории: " + _where_sold(df, "subcat_name", total)))

    # По каждому подразделению
    for store, amount in stores.items():
        g = df[df["store_name"] == store]
        gp = prev[prev["store_name"] == store] if len(prev) else prev
        amount_prev = float(gp["net_amount"].sum()) if len(gp) else 0.0
        share = f"{_pct(amount / total * 100)} сети" if total else ""
        S.append(("store", f"{store} — {_money(amount)}" + (f" ({share})" if share else "")))

        ch = _change(amount, amount_prev, prev_l)
        sales, ret = float(g["sales_amount"].sum()), float(g["returns_amount"].sum())
        S.append(("p", (ch[0].upper() + ch[1:] + ". " if ch else "")
                       + f"Продано {_qty(g['net_qty'].sum())} шт., {_items(g['item_id'].nunique())}"
                       + (f"; возвраты {_money(ret)} ({_pct(ret / sales * 100)} продаж)" if ret > 0 and sales else "")
                       + "."))

        cats = _by(g, "cat_name")
        S.append(("li", "Категории: " + _top_list(cats, amount)))
        S.append(("li", "Производители: " + _top_list(_by(g, "manufacturer_name"), amount)))

        hits = (g.groupby("fullname").agg(net=("net_amount", "sum"), qty=("net_qty", "sum"))
                .sort_values("net", ascending=False).head(TOP_N))
        if len(hits):
            S.append(("li", "Хиты: " + ", ".join(f"{k} — {_money(r.net)} ({_qty(r.qty)} шт.)"
                                                  for k, r in hits.iterrows())))

        # Чем подразделение отличается от сети
        if amount > 0 and len(stores) > 1:
            diff = (cats / amount - net_cat_share.reindex(cats.index).fillna(0)).sort_values(ascending=False)
            k = diff.index[0]
            if diff.iloc[0] >= 0.05:
                S.append(("li", f"Особенность: «{k}» — {_pct(cats[k] / amount * 100)} продаж подразделения "
                                f"против {_pct(net_cat_share[k] * 100)} по сети"))

        # Для чего подразделение — основная площадка в сети
        if multi:
            main = []
            for col, label in (("manufacturer_name", "бренды"), ("cat_name", "категории"),
                               ("subcat_name", "подкатегории")):
                sh = shares[col]
                m = sh[(sh["store_name"] == store) & (sh["share"] >= MAIN_SHARE)
                       & (sh["total"] >= total * MIN_NET_SHARE)].sort_values("total", ascending=False).head(TOP_N)
                if len(m):
                    main.append(f"{label} — " + ", ".join(f"{r[col]} {_pct(r['share'] * 100)}"
                                                           for _, r in m.iterrows()))
            if main:
                S.append(("li", "Больше половины продаж сети приходится сюда: " + "; ".join(main)))

        if len(gp):
            dc = (cats - _by(gp, "cat_name").reindex(cats.index).fillna(0))
            lost = _by(gp, "cat_name")
            lost = lost[~lost.index.isin(cats.index)]
            dc = pd.concat([dc, -lost]).sort_values()
            parts = []
            if (dc > 0).any():
                parts.append(f"растёт «{dc.index[-1]}» (+{_money(dc.iloc[-1])})")
            if (dc < 0).any():
                parts.append(f"падает «{dc.index[0]}» (−{_money(-dc.iloc[0])})")
            if parts:
                S.append(("li", f"К {prev_l}: " + "; ".join(parts)))

    S.append(("note", "Подробности — на листах «Подразделения → категории» и «Подразделения → производители». "
                      "Продажи без привязки к магазину — в группе «Без подразделения»."))
    return S


def write_story(wb, story: list[tuple[str, str]], sheet: str = "Выводы") -> None:
    from openpyxl.styles import Alignment

    from sales.reports.xl_brand import MUTED, NAVY, NAVY_3, SURFACE_4, TEXT, TEXT_2, fill, font, page_setup, toc_button

    ws = wb.create_sheet(sheet)
    page_setup(ws, landscape=False)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 110
    toc_button(ws, 1, 2)
    styles = {
        "h1": (font(16, True, NAVY), 26, 0),
        "sub": (font(10, color=MUTED, italic=True), 16, 0),
        "h2": (font(12, True, NAVY), 22, 0),
        "h3": (font(11, True, NAVY), 20, 0),
        "store": (font(12, True, NAVY_3), 24, 1),
        "p": (font(10.5, color=TEXT), 16, 0),
        "li": (font(10.5, color=TEXT_2), 16, 1),
        "note": (font(9.5, color=MUTED, italic=True), 15, 0),
    }
    r = 2
    for kind, text in story:
        if kind in ("h1", "h2", "store", "note"):
            r += 1
        f, line_h, indent = styles[kind]
        value = f"•  {text}" if kind == "li" else text
        c = ws.cell(row=r, column=2, value=value)
        c.font = f
        c.alignment = Alignment(wrap_text=True, vertical="top", indent=indent)
        ws.row_dimensions[r].height = line_h * max(1, -(-len(value) // 95)) + 2
        if kind == "store":
            ws.cell(row=r, column=1).fill = fill(SURFACE_4)
            c.fill = fill(SURFACE_4)
            c.alignment = Alignment(vertical="center", indent=indent)
        r += 1
