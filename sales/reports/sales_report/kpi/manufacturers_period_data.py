from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from utils.db_engine import get_engine


def get_manufacturers_for_period(start: date, end: date) -> pd.DataFrame:
    """
    Производители за период: net amount и net quantity.
    1 строка = 1 производитель (manufacturer_name).
    Если производителя нет — "Производитель не указан".
    """
    sql = text("""
        SELECT
            CASE
                WHEN i.manufacturer_id IS NULL THEN 0
                ELSE i.manufacturer_id
            END AS manufacturer_id,
            CASE
                WHEN i.manufacturer_id IS NULL THEN 'Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer_name,
            COALESCE(SUM(s.dt - s.cr), 0) AS amount,
            COALESCE(SUM(s.quant_dt - s.quant_cr), 0) AS quant
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = i.manufacturer_id
        WHERE s.`date` BETWEEN :start AND :end
        GROUP BY manufacturer_id, manufacturer_name
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

    df["manufacturer_id"] = pd.to_numeric(df["manufacturer_id"], errors="coerce").fillna(0).astype(int)
    df["manufacturer_name"] = df["manufacturer_name"].fillna("Производитель не указан").astype(str)

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["quant"] = pd.to_numeric(df["quant"], errors="coerce").fillna(0.0)

    return df