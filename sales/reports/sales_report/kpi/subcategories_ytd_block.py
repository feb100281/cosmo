from __future__ import annotations

from datetime import date
import pandas as pd

from ..categories_data import get_ytd_categories_raw
from ..formatters import (
    fmt_money,
    fmt_int,
    fmt_delta_money_signed,   # чтобы знак был как в отчёте
    fmt_delta_pct,
)


# def _add_yoy(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
#     """
#     Абсолютно такая же логика, как в categories_block.py
#     Делает таблицу: curr/prev + delta по amount/quant.
#     """
#     if df.empty:
#         return pd.DataFrame()

#     years = sorted(df["year"].unique())[-2:]
#     if len(years) < 2:
#         return pd.DataFrame()

#     y_prev, y_curr = years[0], years[1]

#     g = (
#         df.groupby(key_cols + ["year"], as_index=False)[["amount", "quant"]]
#         .sum()
#     )

#     curr = g[g["year"] == y_curr].drop(columns=["year"]).rename(
#         columns={"amount": "amount_curr", "quant": "quant_curr"}
#     )
#     prev = g[g["year"] == y_prev].drop(columns=["year"]).rename(
#         columns={"amount": "amount_prev", "quant": "quant_prev"}
#     )

#     out = curr.merge(prev, on=key_cols, how="left")
#     out[["amount_prev", "quant_prev"]] = out[["amount_prev", "quant_prev"]].fillna(0)

#     out["delta_amount"] = out["amount_curr"] - out["amount_prev"]
#     out["delta_amount_pct"] = out.apply(
#         lambda r: (r["delta_amount"] / r["amount_prev"] * 100) if r["amount_prev"] else None,
#         axis=1
#     )

#     out["delta_quant"] = out["quant_curr"] - out["quant_prev"]
#     out["delta_quant_pct"] = out.apply(
#         lambda r: (r["delta_quant"] / r["quant_prev"] * 100) if r["quant_prev"] else None,
#         axis=1
#     )

#     # сортируем по текущей выручке
#     out = out.sort_values("amount_curr", ascending=False)
#     return out


def _add_yoy(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    """
    YOY-таблица curr/prev + delta по amount/quant.
    Важно: показываем ВСЕ ключи, которые есть хотя бы в prev или curr.
    """
    if df.empty:
        return pd.DataFrame()

    years = sorted(df["year"].unique())[-2:]
    if len(years) < 2:
        return pd.DataFrame()

    y_prev, y_curr = years[0], years[1]

    g = (
        df.groupby(key_cols + ["year"], as_index=False)[["amount", "quant"]]
        .sum()
    )

    curr = g[g["year"] == y_curr].drop(columns=["year"]).rename(
        columns={"amount": "amount_curr", "quant": "quant_curr"}
    )
    prev = g[g["year"] == y_prev].drop(columns=["year"]).rename(
        columns={"amount": "amount_prev", "quant": "quant_prev"}
    )

    # ✅ КЛЮЧЕВОЕ: outer, чтобы не терялись prev-only и curr-only
    out = curr.merge(prev, on=key_cols, how="outer")

    # ✅ нули для отсутствующего периода
    out[["amount_prev", "quant_prev", "amount_curr", "quant_curr"]] = (
        out[["amount_prev", "quant_prev", "amount_curr", "quant_curr"]].fillna(0)
    )

    out["delta_amount"] = out["amount_curr"] - out["amount_prev"]
    out["delta_amount_pct"] = out.apply(
        lambda r: (r["delta_amount"] / r["amount_prev"] * 100) if r["amount_prev"] else None,
        axis=1
    )

    out["delta_quant"] = out["quant_curr"] - out["quant_prev"]
    out["delta_quant_pct"] = out.apply(
        lambda r: (r["delta_quant"] / r["quant_prev"] * 100) if r["quant_prev"] else None,
        axis=1
    )

    # сортируем по текущей выручке (prev-only уйдут вниз, но будут видны)
    out = out.sort_values("amount_curr", ascending=False)
    return out

def _dir(v: float) -> str:
    if v > 0:
        return "pos"
    if v < 0:
        return "neg"
    return "flat"


def build_subcategories_ytd_context(report_date: date, min_curr_amount: float = 0.0) -> dict:
    """
    Статичный блок "YTD по подкатегориям: было/стало" в виде:
    Категория -> таблица подкатегорий (prev/curr/Δ по ₽ и шт).

    min_curr_amount — опционально: отсекаем микроподкатегории по текущей выручке.
    """
    raw = get_ytd_categories_raw(report_date)
    if raw is None or raw.empty:
        return {"has": False, "cats": [], "years": None}

    years = sorted(raw["year"].unique())[-2:]
    if len(years) < 2:
        return {"has": False, "cats": [], "years": None}

    years_ctx = {"prev": years[0], "curr": years[1]}

    # Берём YOY по подкатегориям (cat + subcat)
    sub = _add_yoy(raw, ["cat_id", "cat_name", "subcat_id", "sc_name"])
    if sub.empty:
        return {"has": False, "cats": [], "years": years_ctx}

    # опциональный фильтр по текущей выручке
    if min_curr_amount and min_curr_amount > 0:
        sub = sub[sub["amount_curr"] >= float(min_curr_amount)]

    # собираем дерево
    cats_out: list[dict] = []

    # сортируем категории по сумме текущей выручки (чтобы блок был “по важности”)
    cat_order = (
        sub.groupby(["cat_id", "cat_name"], as_index=False)["amount_curr"]
        .sum()
        .sort_values("amount_curr", ascending=False)
    )

    for _, crow in cat_order.iterrows():
        cat_id = crow["cat_id"]
        cat_name = crow["cat_name"]

        g = sub[sub["cat_id"] == cat_id].copy()
        if g.empty:
            continue

        # итоги по категории
        tot_amount_prev = float(g["amount_prev"].sum())
        tot_amount_curr = float(g["amount_curr"].sum())
        tot_quant_prev = float(g["quant_prev"].sum())
        tot_quant_curr = float(g["quant_curr"].sum())

        rows = []
        for rr in g.sort_values("amount_curr", ascending=False).to_dict("records"):
            da = float(rr["delta_amount"])
            dq = float(rr["delta_quant"])

            rows.append({
                "subcat": rr["sc_name"],

                "amount_prev": fmt_money(float(rr["amount_prev"])),
                "amount_curr": fmt_money(float(rr["amount_curr"])),
                "d_amount": fmt_delta_money_signed(da),
                "d_amount_dir": _dir(da),

                "quant_prev": fmt_int(float(rr["quant_prev"])),
                "quant_curr": fmt_int(float(rr["quant_curr"])),
                "d_quant": (("+" if dq > 0 else "−" if dq < 0 else "") + fmt_int(abs(dq))),
                "d_quant_dir": _dir(dq),
            })

        da_tot = tot_amount_curr - tot_amount_prev
        dq_tot = tot_quant_curr - tot_quant_prev

        cats_out.append({
            "cat": cat_name,
            "rows": rows,
            "totals": {
                "amount_prev": fmt_money(tot_amount_prev),
                "amount_curr": fmt_money(tot_amount_curr),
                "d_amount": fmt_delta_money_signed(da_tot),
                "d_amount_dir": _dir(da_tot),

                "quant_prev": fmt_int(tot_quant_prev),
                "quant_curr": fmt_int(tot_quant_curr),
                "d_quant": (("+" if dq_tot > 0 else "−" if dq_tot < 0 else "") + fmt_int(abs(dq_tot))),
                "d_quant_dir": _dir(dq_tot),
            }
        })

    return {
        "has": True,
        "title": f"YTD по подкатегориям (было / стало), на {report_date.strftime('%d.%m.%Y')}",
        "years": years_ctx,
        "cats": cats_out,
    }