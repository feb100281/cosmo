# sales/reports/sales_report/stores/storegroup_category_block.py
from __future__ import annotations
from datetime import date
import pandas as pd

from .storegroup_categories_data import get_ytd_storegroup_categories_raw, get_mtd_storegroup_categories_raw
from .storegroup_category_diagnostics import (
    build_yoy_storegroup_category,
    top_drops,
    build_delta_matrices_by_root,
    build_delta_qty_matrices_by_root,

)
from .storegroup_category_tables import (
    render_top_drops_table,
    render_delta_matrices_by_root_html,
    render_delta_qty_matrices_by_root_html,
    render_delta_matrices_by_root_pair_html,
)


def build_storegroup_category_diagnostics_block(d: date, mode: str = "ytd") -> dict:
    """
    mode: "mtd" или "ytd"
    Возвращает готовые html-блоки для вставки в отчёт.
    """
    if mode == "mtd":
        df_raw = get_mtd_storegroup_categories_raw(d)
        period_label = "MTD"
    else:
        df_raw = get_ytd_storegroup_categories_raw(d)
        period_label = "YTD"

    yoy = build_yoy_storegroup_category(df_raw)
    if yoy.empty:
        return {"has": False}

    y_prev = yoy.attrs.get("y_prev")
    y_curr = yoy.attrs.get("y_curr")

    drops = top_drops(yoy, n=15)

    # делаем несколько матриц по root category (нулевой родитель)
    matrices = build_delta_matrices_by_root(
        yoy,
        top_roots=6,          # сколько root показываем
        top_cats_per_root=8,  # сколько категорий в матрице каждого root
        top_groups=12,
        min_abs_total=1.0
    )
    
    matrices_qty = build_delta_qty_matrices_by_root(
        yoy,
        top_roots=6,
        top_cats_per_root=8,
        top_groups=12,
        min_abs_total=1.0
    )

    top_table_html = render_top_drops_table(
        drops,
        title=f"{period_label}: ТОП падений (магазин × категория), {y_curr} vs {y_prev}",
    )

    # matrix_html = render_delta_matrices_by_root_html(
    #     matrices,
    #     title_prefix=f"{period_label}: Матрица изменений Δ₽ (магазин × категории), {y_curr} vs {y_prev}",
    #     max_cols=10
    # )
    
    # matrix_qty_html = render_delta_qty_matrices_by_root_html(
    #     matrices_qty,
    #     title_prefix=f"{period_label}: Матрица изменений Δшт (магазин × категории), {y_curr} vs {y_prev}",
    #     max_cols=10
    # )
    matrix_pairs_html = render_delta_matrices_by_root_pair_html(
            matrices_money=matrices,
            matrices_qty=matrices_qty,
            title_prefix_money=f"{period_label}: Матрица изменений Δ₽ (магазин × категории), {y_curr} vs {y_prev}",
            title_prefix_qty=f"{period_label}: Матрица изменений Δшт (магазин × категории), {y_curr} vs {y_prev}",
            max_cols=10
        )

    return {
        "has": True,
        "period_label": period_label,
        "y_prev": y_prev,
        "y_curr": y_curr,
        "top_drops_html": top_table_html,
        # "matrix_html": matrix_html,
        # "matrix_qty_html": matrix_qty_html,
        "matrix_html": matrix_pairs_html,
    }