# sales/reports/sales_report/kpi/categories_period_data.py

from __future__ import annotations

from datetime import date
from typing import Any, Dict

import pandas as pd
from sqlalchemy import text

from utils.db_engine import get_engine


def get_categories_for_period(start: date, end: date) -> pd.DataFrame:
    """
    Категории за период: net amount и net quantity.
    1 строка = 1 категория (cat_name).
    """
    sql = text("""
        SELECT
            COALESCE(cat.name, 'Без категории') AS cat_name,
            COALESCE(SUM(s.dt - s.cr), 0) AS amount,
            COALESCE(SUM(s.quant_dt - s.quant_cr), 0) AS quant
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
        WHERE s.`date` BETWEEN :start AND :end
        GROUP BY COALESCE(cat.name, 'Без категории')
        ORDER BY amount DESC
    """)

    engine = get_engine()
    with engine.connect() as conn:
        res = conn.execute(sql, {"start": start, "end": end})
        rows = res.fetchall()
        cols = list(res.keys())

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["quant"] = pd.to_numeric(df["quant"], errors="coerce").fillna(0.0)
    df["cat_name"] = df["cat_name"].fillna("Без категории").astype(str)

    return df
