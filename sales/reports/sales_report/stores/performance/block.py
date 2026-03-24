from __future__ import annotations

from datetime import date

from .metrics import build_store_performance_block
from .tables import (
    render_store_kpi_table,
    render_lfl_table,
    render_store_monthly_table,
    render_store_pareto_svg,
)


def build_store_performance_html_block(d: date) -> dict:
    data = build_store_performance_block(d)
    if not data.get("has"):
        return {"has": False}

    ytd = data["ytd"]
    mtd = data["mtd"]
    monthly = data["monthly"]
    lfl = data["lfl"]

    return {
        "has": True,
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