from __future__ import annotations

from datetime import date
import pandas as pd

from .data import get_store_yoy_raw


RU_MONTHS = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}


def _safe_pct(curr, prev):
    if prev in (None, 0):
        return None
    return (curr - prev) / prev * 100.0


def _merge_periods(curr: pd.DataFrame, prev: pd.DataFrame, suffix_curr="curr", suffix_prev="prev") -> pd.DataFrame:
    if curr is None or curr.empty:
        curr = pd.DataFrame(columns=["store_id", "store", "dt", "cr", "amount", "quant", "orders", "ave_check", "rtr_ratio"])
    if prev is None or prev.empty:
        prev = pd.DataFrame(columns=["store_id", "store", "dt", "cr", "amount", "quant", "orders", "ave_check", "rtr_ratio"])

    c = curr.rename(columns={
        "dt": f"dt_{suffix_curr}",
        "cr": f"cr_{suffix_curr}",
        "amount": f"amount_{suffix_curr}",
        "quant": f"quant_{suffix_curr}",
        "orders": f"orders_{suffix_curr}",
        "ave_check": f"ave_check_{suffix_curr}",
        "rtr_ratio": f"rtr_ratio_{suffix_curr}",
    })

    p = prev.rename(columns={
        "dt": f"dt_{suffix_prev}",
        "cr": f"cr_{suffix_prev}",
        "amount": f"amount_{suffix_prev}",
        "quant": f"quant_{suffix_prev}",
        "orders": f"orders_{suffix_prev}",
        "ave_check": f"ave_check_{suffix_prev}",
        "rtr_ratio": f"rtr_ratio_{suffix_prev}",
    })

    df = c.merge(p, on=["store_id", "store"], how="outer").fillna(0)

    df["delta_amount"] = df[f"amount_{suffix_curr}"] - df[f"amount_{suffix_prev}"]
    df["delta_amount_pct"] = df.apply(
        lambda r: _safe_pct(r[f"amount_{suffix_curr}"], r[f"amount_{suffix_prev}"]),
        axis=1
    )
    df["delta_orders"] = df[f"orders_{suffix_curr}"] - df[f"orders_{suffix_prev}"]
    df["delta_quant"] = df[f"quant_{suffix_curr}"] - df[f"quant_{suffix_prev}"]

    df["share_curr"] = df[f"amount_{suffix_curr}"] / df[f"amount_{suffix_curr}"].sum() if df[f"amount_{suffix_curr}"].sum() else 0
    df = df.sort_values(by=f"amount_{suffix_curr}", ascending=False).reset_index(drop=True)
    df["cum_share_curr"] = df["share_curr"].cumsum()

    df["lfl"] = (df[f"amount_{suffix_curr}"] > 0) & (df[f"amount_{suffix_prev}"] > 0)

    return df


def _build_monthly_compare(monthly_curr: pd.DataFrame, monthly_prev: pd.DataFrame) -> pd.DataFrame:
    if monthly_curr is None or monthly_curr.empty:
        monthly_curr = pd.DataFrame(columns=["store", "month", "amount"])
    if monthly_prev is None or monthly_prev.empty:
        monthly_prev = pd.DataFrame(columns=["store", "month", "amount"])

    if not monthly_curr.empty:
        monthly_curr = monthly_curr.copy()
        monthly_curr["month_no"] = monthly_curr["month"].dt.month
    else:
        monthly_curr["month_no"] = []

    if not monthly_prev.empty:
        monthly_prev = monthly_prev.copy()
        monthly_prev["month_no"] = monthly_prev["month"].dt.month
    else:
        monthly_prev["month_no"] = []

    c = (
        monthly_curr.groupby(["store", "month_no"], as_index=False)
        .agg(curr_amount=("amount", "sum"))
    )
    p = (
        monthly_prev.groupby(["store", "month_no"], as_index=False)
        .agg(prev_amount=("amount", "sum"))
    )

    out = c.merge(p, on=["store", "month_no"], how="outer").fillna(0)
    out["delta_amount"] = out["curr_amount"] - out["prev_amount"]
    out["delta_amount_pct"] = out.apply(
        lambda r: _safe_pct(r["curr_amount"], r["prev_amount"]),
        axis=1
    )
    out["month_name"] = out["month_no"].map(RU_MONTHS)

    out = out.sort_values(["store", "month_no"]).reset_index(drop=True)
    return out


def build_store_performance_block(d: date) -> dict:
    raw = get_store_yoy_raw(d)

    ytd = _merge_periods(raw["curr_ytd"], raw["prev_ytd"])
    mtd = _merge_periods(raw["curr_mtd"], raw["prev_mtd"])
    monthly = _build_monthly_compare(raw["monthly_curr"], raw["monthly_prev"])

    if ytd.empty and mtd.empty:
        return {"has": False}

    lfl = ytd[ytd["lfl"]].copy().sort_values("amount_curr", ascending=False)

    total_curr = float(ytd["amount_curr"].sum()) if not ytd.empty else 0
    total_prev = float(ytd["amount_prev"].sum()) if not ytd.empty else 0

    return {
        "has": True,
        "date": raw["date"],
        "y_curr": raw["y_curr"],
        "y_prev": raw["y_prev"],
        "ytd": ytd,
        "mtd": mtd,
        "monthly": monthly,
        "lfl": lfl,
        "total_curr": total_curr,
        "total_prev": total_prev,
        "total_delta": total_curr - total_prev,
        "total_delta_pct": _safe_pct(total_curr, total_prev),
    }