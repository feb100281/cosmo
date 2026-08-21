# sales/reports/sales_report/stores/performance/block.py
from __future__ import annotations

from datetime import date

from .metrics import build_store_performance_block
from .tables import (
    render_store_kpi_table,
    render_lfl_table,
    render_store_monthly_table,
    render_store_pareto_svg,
)


def _build_store_insights(df) -> dict | None:
    if df is None or df.empty:
        return None

    work = df.copy()

    total_curr = float(work["amount_curr"].sum())
    total_prev = float(work["amount_prev"].sum())

    if total_curr == 0:
        return None

    total_delta = total_curr - total_prev
    total_delta_pct = (
        total_delta / total_prev * 100
        if total_prev
        else None
    )

    # ---------------------------------------------------------
    # 1. Концентрация выручки — TOP-2
    # ---------------------------------------------------------
    top_share = (
        work[work["amount_curr"] > 0]
        .sort_values("amount_curr", ascending=False)
        .head(2)
    )

    leaders = []
    for _, r in top_share.iterrows():
        leaders.append({
            "store": r["store"],
            "share": float(r["share_curr"]) * 100,
        })

    top2_share = sum(x["share"] for x in leaders)

    # ---------------------------------------------------------
    # 2. Главные положительные / отрицательные драйверы
    # ---------------------------------------------------------
    up_df = (
        work[work["delta_amount"] > 0]
        .sort_values("delta_amount", ascending=False)
        .head(3)
    )

    down_df = (
        work[work["delta_amount"] < 0]
        .sort_values("delta_amount", ascending=True)
        .head(3)
    )

    def _money(v):
        v = float(v)

        sign = "+" if v > 0 else "−" if v < 0 else ""
        a = abs(v)

        if a >= 1_000_000:
            return f"{sign}{a / 1_000_000:.1f} млн ₽".replace(".", ",")

        if a >= 1_000:
            return f"{sign}{a / 1_000:.0f} тыс ₽"

        return f"{sign}{a:.0f} ₽"

    movers_up = [
        {
            "store": r["store"],
            "delta": _money(r["delta_amount"]),
        }
        for _, r in up_df.iterrows()
    ]

    movers_down = [
        {
            "store": r["store"],
            "delta": _money(r["delta_amount"]),
        }
        for _, r in down_df.iterrows()
    ]

    # ---------------------------------------------------------
    # 3. Возвраты
    # ---------------------------------------------------------
    returns_df = work[
        (work["cr_curr"] > 0) &
        (work["dt_curr"] > 0)
    ].copy()

    returns = []

    if not returns_df.empty:
        returns_df = returns_df.sort_values(
            "rtr_ratio_curr",
            ascending=False,
        ).head(3)

        for _, r in returns_df.iterrows():
            returns.append({
                "store": r["store"],
                "amount": _money(-float(r["cr_curr"])).lstrip("−"),
                "ratio": float(r["rtr_ratio_curr"]) * 100,
            })

    return {
        "total_delta": _money(total_delta),
        "total_delta_pct": total_delta_pct,
        "is_positive": total_delta >= 0,

        "leaders": leaders,
        "top2_share": top2_share,

        "movers_up": movers_up,
        "movers_down": movers_down,

        "returns": returns,
    }



def build_store_performance_html_block(d: date) -> dict:
    data = build_store_performance_block(d)
    if not data.get("has"):
        return {"has": False}

    ytd = data["ytd"]
    mtd = data["mtd"]
    monthly = data["monthly"]
    lfl = data["lfl"]
    
    ytd_insights = _build_store_insights(ytd)
    mtd_insights = _build_store_insights(mtd)

    return {
        "has": True,
        "insights": {
                "mtd": mtd_insights,
                "ytd": ytd_insights,
            },
        "summary": {
            "total_curr": data["total_curr"],
            "total_prev": data["total_prev"],
            "total_delta": data["total_delta"],
            "total_delta_pct": data["total_delta_pct"],
            "y_curr": data["y_curr"],
            "y_prev": data["y_prev"],
        },
        "ytd_table_html": render_store_kpi_table(
            ytd,
            title=f"YTD: KPI по магазинам, {data['y_curr']} vs {data['y_prev']}",
            curr_year=data["y_curr"],
            prev_year=data["y_prev"],
        ),
        "mtd_table_html": render_store_kpi_table(
            mtd,
            title=f"MTD: KPI по магазинам, {data['y_curr']} vs {data['y_prev']}",
            curr_year=data["y_curr"],
            prev_year=data["y_prev"],
        ),
        "pareto_html": render_store_pareto_svg(
            ytd,
            title=f"Pareto: вклад магазинов в выручку YTD {data['y_curr']}",
        ),
        "lfl_html": render_lfl_table(
            lfl,
            title=f"LFL: сопоставимые магазины, {data['y_curr']} vs {data['y_prev']}",
        ),
        "monthly_html": render_store_monthly_table(
            monthly,
            title=f"Помесячная динамика по магазинам, {data['y_curr']} vs {data['y_prev']}",
        ),
    }