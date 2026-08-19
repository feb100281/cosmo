# sales/reports/newspaper/analytics/stocks.py
"""
Аналитический слой над данными остатков (см. data/stocks.py).

Строит компанейский взгляд: концентрацию запасов по категориям —
по количеству (денежной оценки остатков в отчёте нет).
"""

from __future__ import annotations

from ..config import STOCK_TOP_CATEGORY_CONCENTRATION_PCT


def analyze_stocks(stocks_data: dict) -> dict:
    company = stocks_data["company"]
    top_categories = stocks_data["top_categories"]

    total_qty = company["qty_available"] or 0

    top3 = top_categories[:3]
    top3_qty = sum(c["qty_available"] for c in top3)

    top3_share_pct = (
        (top3_qty / total_qty * 100) if total_qty > 0 else 0.0
    )

    is_concentrated = top3_share_pct >= STOCK_TOP_CATEGORY_CONCENTRATION_PCT

    return {
        "top3_categories": top3,
        "top3_share_pct": top3_share_pct,
        "top3_share_pct_fmt": f"{top3_share_pct:.0f}%",
        "is_concentrated": is_concentrated,
    }
