# sales/reports/sales_report/kpi/period_text_block.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from sales.reports.sales_report.kpi.categories_period_data import get_categories_for_period
from sales.reports.sales_report.formatters import (
    fmt_money,
    fmt_int,
    fmt_pct,
    fmt_delta_money,
    fmt_delta_pct,
)

# -------------------------
# helpers
# -------------------------
def _safe_div(a: float, b: float) -> float | None:
    if b in (None, 0):
        return None
    return a / b

def _yoy_range(start: date, end: date) -> tuple[date, date]:
    # аналогичный период прошлого года (по календарю)
    return date(start.year - 1, start.month, start.day), date(end.year - 1, end.month, end.day)

def _prep(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["cat_name", "amount", "quant"])
    out = df.copy()
    out["cat_name"] = out["cat_name"].fillna("Без категории").astype(str)
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)
    out["quant"] = pd.to_numeric(out["quant"], errors="coerce").fillna(0.0)
    return out

def _totals(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"amount": 0.0, "quant": 0.0}
    return {"amount": float(df["amount"].sum()), "quant": float(df["quant"].sum())}

def _top_rows(df: pd.DataFrame, top_n: int = 5) -> list[dict]:
    if df.empty:
        return []
    d = df.sort_values("amount", ascending=False).head(top_n).copy()
    total = float(df["amount"].sum()) or 0.0
    rows = []
    for _, r in d.iterrows():
        share = (float(r["amount"]) / total * 100) if total else 0.0
        rows.append({
            "cat": r["cat_name"],
            "amount": fmt_money(float(r["amount"])),
            "quant": fmt_int(float(r["quant"])),
            "share": fmt_pct(share),
        })
    return rows

def _pareto_share(df: pd.DataFrame, n: int = 5) -> float:
    if df.empty:
        return 0.0
    total = float(df["amount"].sum()) or 0.0
    if not total:
        return 0.0
    top = float(df.sort_values("amount", ascending=False).head(n)["amount"].sum())
    return top / total * 100

def _diff_table(curr: pd.DataFrame, prev: pd.DataFrame) -> pd.DataFrame:
    # по категориям: curr - prev
    c = curr.rename(columns={"amount": "amount_curr", "quant": "quant_curr"})
    p = prev.rename(columns={"amount": "amount_prev", "quant": "quant_prev"})
    m = c.merge(p, on="cat_name", how="outer").fillna(0.0)
    m["d_amount"] = m["amount_curr"] - m["amount_prev"]
    m["d_quant"] = m["quant_curr"] - m["quant_prev"]
    return m

def _top_movers(diff_df: pd.DataFrame, top_n: int = 3) -> dict:
    if diff_df is None or diff_df.empty:
        return {"up": [], "down": []}

    d = diff_df.copy()

    up = d.sort_values("d_amount", ascending=False).head(top_n)
    down = d.sort_values("d_amount", ascending=True).head(top_n)

    def _rows(x: pd.DataFrame) -> list[dict]:
        rows = []
        for _, r in x.iterrows():
            rows.append({
                "cat": r["cat_name"],
                "d_amount": fmt_delta_money(float(r["d_amount"])),
                "d_quant": fmt_int(float(r["d_quant"])),
            })
        return rows

    # фильтруем нулевые, чтобы текст был “живой”
    up_rows = [r for r in _rows(up) if r["d_amount"] not in ("0 ₽", "0")]
    down_rows = [r for r in _rows(down) if r["d_amount"] not in ("0 ₽", "0")]

    return {"up": up_rows, "down": down_rows}

# -------------------------
# public API
# -------------------------
def build_period_text_block(period_start: date, period_end: date, label: str, top_n: int = 5) -> dict | None:
    df_curr = _prep(get_categories_for_period(period_start, period_end))
    prev_start, prev_end = _yoy_range(period_start, period_end)
    df_prev = _prep(get_categories_for_period(prev_start, prev_end))

    t_curr = _totals(df_curr)
    t_prev = _totals(df_prev)

    d_amount = t_curr["amount"] - t_prev["amount"]
    d_quant = t_curr["quant"] - t_prev["quant"]

    d_amount_pct = (_safe_div(d_amount, t_prev["amount"]) * 100) if t_prev["amount"] else None
    d_quant_pct = (_safe_div(d_quant, t_prev["quant"]) * 100) if t_prev["quant"] else None

    diff_df = _diff_table(df_curr, df_prev)
    movers = _top_movers(diff_df, top_n=3)

    pareto = _pareto_share(df_curr, n=top_n)

    # если вообще данных нет — не показываем блок
    if t_curr["amount"] == 0 and t_curr["quant"] == 0:
        return None

    return {
        "label": label,
        "period": f"{period_start:%d.%m.%Y}–{period_end:%d.%m.%Y}",
        "total_amount": fmt_money(t_curr["amount"]),
        "total_quant": fmt_int(t_curr["quant"]),

        "yoy_amount": fmt_delta_money(d_amount),
        "yoy_amount_pct": fmt_delta_pct(d_amount_pct),
        "yoy_quant": fmt_int(d_quant),
        "yoy_quant_pct": fmt_delta_pct(d_quant_pct),

        "top_rows": _top_rows(df_curr, top_n=top_n),
        "pareto_topn_share": fmt_pct(pareto),

        "movers_up": movers["up"],
        "movers_down": movers["down"],
    }


def build_period_text_context(d: date) -> dict:
    # MTD
    mtd_start = d.replace(day=1)
    mtd_end = d

    # YTD
    ytd_start = date(d.year, 1, 1)
    ytd_end = d

    return {
        "mtd_text": build_period_text_block(mtd_start, mtd_end, label="MTD", top_n=5),
        "ytd_text": build_period_text_block(ytd_start, ytd_end, label="YTD", top_n=5),
    }