from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import pandas as pd
from sqlalchemy import text

from utils.db_engine import get_engine


def _shift_prev_year(d: date) -> date:
    """
    Безопасно сдвигаем дату на -1 год (учёт 29 февраля).
    """
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        # если 29 Feb -> 28 Feb прошлого года
        return d.replace(month=2, day=28, year=d.year - 1)


def get_ytd_subcategories(d: date) -> pd.DataFrame:
    """
    Возвращает YTD по подкатегориям для двух периодов:
    - prev: 01.01.(year-1) .. (d - 1 year)
    - curr: 01.01.year .. d

    1 строка = (cat_name, subcat_name, period)
    period: "prev" | "curr"
    """
    start_curr = date(d.year, 1, 1)
    end_curr = d

    end_prev = _shift_prev_year(d)
    start_prev = date(end_prev.year, 1, 1)

    sql = text("""
        SELECT
            COALESCE(cat.name, 'Без категории') AS cat_name,
            COALESCE(sub.name, 'Без подкатегории') AS subcat_name,
            CASE
              WHEN s.`date` BETWEEN :start_prev AND :end_prev THEN 'prev'
              WHEN s.`date` BETWEEN :start_curr AND :end_curr THEN 'curr'
              ELSE NULL
            END AS period,
            COALESCE(SUM(s.dt - s.cr), 0) AS amount,
            COALESCE(SUM(s.quant_dt - s.quant_cr), 0) AS quant
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
        LEFT JOIN corporate_subcategory sub ON sub.id = i.subcat_id
        WHERE s.`date` BETWEEN :start_prev AND :end_curr
        GROUP BY
            COALESCE(cat.name, 'Без категории'),
            COALESCE(sub.name, 'Без подкатегории'),
            period
        HAVING period IS NOT NULL
    """)

    engine = get_engine()
    with engine.connect() as conn:
        res = conn.execute(sql, {
            "start_prev": start_prev, "end_prev": end_prev,
            "start_curr": start_curr, "end_curr": end_curr,
        })
        rows = res.fetchall()
        cols = list(res.keys())

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["quant"] = pd.to_numeric(df["quant"], errors="coerce").fillna(0.0)
    df["cat_name"] = df["cat_name"].fillna("Без категории").astype(str)
    df["subcat_name"] = df["subcat_name"].fillna("Без подкатегории").astype(str)
    df["period"] = df["period"].astype(str)

    return df