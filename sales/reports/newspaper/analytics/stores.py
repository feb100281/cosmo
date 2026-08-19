# sales/reports/newspaper/analytics/stores.py
"""
Сводит кэш и остатки в единый список магазинов для отчёта.

Каждый элемент результата — это то, что рендерится как компактный блок
магазина в Newspaper: кэш (план/факт/отклонение/% выполнения) и остатки
(количество/доля по количеству), плюс отметки-сигналы. Денежной оценки
остатков здесь нет (см. data/stocks.py) — дисбаланс "магазин/кэш" считается
по доле количества, а не по стоимости.
"""

from __future__ import annotations

from decimal import Decimal

from ..config import STOCK_STORE_IMBALANCE_PP
from ..render.helpers import fmt_qty


def _to_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def build_store_sections(cash_data: dict, stocks_data: dict) -> list:
    cash_rows = cash_data["rows"]
    by_store_stock = stocks_data["by_store"]

    company_qty = stocks_data["company"]["qty_available"] or 1.0

    total_fact = cash_data["totals"]["fact"] or Decimal("1")

    sections = []

    for row in cash_rows:
        store_name = row["store_name"]
        stock = by_store_stock.get(store_name, {
            "qty_available": 0.0,
            "qty_ordered": 0.0,
        })

        stock_qty_share_pct = stock["qty_available"] / company_qty * 100.0

        cash_share_pct = _to_float(row["fact"]) / float(total_fact) * 100.0

        imbalance_pp = stock_qty_share_pct - cash_share_pct
        is_overstocked = imbalance_pp > STOCK_STORE_IMBALANCE_PP

        sections.append({
            "store_name": store_name,
            "group_name": row["group_name"],
            "cash": row,
            "stock": {
                "qty_available": stock["qty_available"],
                "qty_available_fmt": fmt_qty(stock["qty_available"]),
                "qty_ordered": stock["qty_ordered"],
                "qty_ordered_fmt": fmt_qty(stock["qty_ordered"]),
                "qty_share_pct": stock_qty_share_pct,
                "qty_share_pct_fmt": f"{stock_qty_share_pct:.0f}%",
            },
            "cash_share_pct": cash_share_pct,
            "imbalance_pp": imbalance_pp,
            "is_overstocked": is_overstocked,
        })

    # Сначала магазины с планом (по убыванию факта), затем прочие.
    sections.sort(key=lambda s: (not s["cash"]["has_plan"], -_to_float(s["cash"]["fact"])))

    return sections
