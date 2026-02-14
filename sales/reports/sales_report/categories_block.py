# sales/reports/sales_report/categories_block.py
import pandas as pd

from .categories_data import get_mtd_categories_raw, get_ytd_categories_raw
from .formatters import (
    fmt_money,
    fmt_int,
    fmt_delta_money_signed,
    fmt_delta_pct,

)

def _add_yoy(df, key_cols):
    """
    df: columns include year, amount, quant
    key_cols: ['cat_id','cat_name'] or + subcat fields
    returns summary table with curr/prev/yoy
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

    out = curr.merge(prev, on=key_cols, how="left")
    out[["amount_prev", "quant_prev"]] = out[["amount_prev", "quant_prev"]].fillna(0)

    out["delta_amount"] = out["amount_curr"] - out["amount_prev"]
    out["delta_amount_pct"] = out.apply(
        lambda r: (r["delta_amount"] / r["amount_prev"] * 100) if r["amount_prev"] else None,
        axis=1
    )

    out = out.sort_values("amount_curr", ascending=False)
    return out


def build_categories_context(report_date, top_n=12):
    raw = get_mtd_categories_raw(report_date)
    if raw.empty:
        return {"raw": None, "cats": [], "subcats": [], "years": None}

    years = sorted(raw["year"].unique())[-2:]
    years_ctx = {"prev": years[0], "curr": years[1]} if len(years) >= 2 else None

    # --- TOP categories ---
    cats = _add_yoy(raw, ["cat_id", "cat_name"])
    cats_top = cats.head(top_n) if not cats.empty else cats

    cats_rows = []
    for _, r in cats_top.iterrows():
        cats_rows.append({
            "cat_name": r["cat_name"],
            "amount": fmt_money(r["amount_curr"]),
            "quant": fmt_int(r.get("quant_curr", 0)),
            "delta": {
                "abs": fmt_delta_money_signed(r["delta_amount"]),
                "pct": fmt_delta_pct(r["delta_amount_pct"]),
            }
        })

    # --- TOP subcategories ---
    subcats = _add_yoy(raw, ["cat_id", "cat_name", "subcat_id", "sc_name"])
    subcats_top = subcats.head(top_n) if not subcats.empty else subcats

    subcats_rows = []
    for _, r in subcats_top.iterrows():
        subcats_rows.append({
            "cat_name": r["cat_name"],
            "sc_name": r["sc_name"],
            "amount": fmt_money(r["amount_curr"]),
            "quant": fmt_int(r.get("quant_curr", 0)),
            "delta": {
                "abs": fmt_delta_money_signed(r["delta_amount"]),
                "pct": fmt_delta_pct(r["delta_amount_pct"]),
            }
        })

    return {
        "raw": raw,              # пригодится для графиков
        "years": years_ctx,
        "cats": cats_rows,
        "subcats": subcats_rows,
    }



def build_categories_context_ytd(report_date, top_n=12):
    raw = get_ytd_categories_raw(report_date)
    if raw.empty:
        return {"raw": None, "cats": [], "subcats": [], "years": None}

    years = sorted(raw["year"].unique())[-2:]
    years_ctx = {"prev": years[0], "curr": years[1]} if len(years) >= 2 else None

    cats = _add_yoy(raw, ["cat_id", "cat_name"])
    cats_top = cats.head(top_n)

    cats_rows = []
    for _, r in cats_top.iterrows():
        cats_rows.append({
            "cat_name": r["cat_name"],
            "amount": fmt_money(r["amount_curr"]),
            "quant": fmt_int(r.get("quant_curr", 0)),
            "delta": {
                "abs": fmt_delta_money_signed(r["delta_amount"]),   # важно: у тебя уже верно
                "pct": fmt_delta_pct(r["delta_amount_pct"]),
            }
        })

    subcats = _add_yoy(raw, ["cat_id", "cat_name", "subcat_id", "sc_name"])
    subcats_top = subcats.head(top_n)

    subcats_rows = []
    for _, r in subcats_top.iterrows():
        subcats_rows.append({
            "cat_name": r["cat_name"],
            "sc_name": r["sc_name"],
            "amount": fmt_money(r["amount_curr"]),
            "quant": fmt_int(r.get("quant_curr", 0)),
            "delta": {
                "abs": fmt_delta_money_signed(r["delta_amount"]),
                "pct": fmt_delta_pct(r["delta_amount_pct"]),
            }
        })

    return {
        "raw": raw,
        "years": years_ctx,
        "cats": cats_rows,
        "subcats": subcats_rows,
    }
