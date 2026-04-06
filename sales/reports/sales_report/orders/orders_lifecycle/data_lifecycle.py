import pandas as pd
from sqlalchemy import text
from utils.db_engine import get_engine

ENGINE = get_engine()


def get_orders_lifecycle(period_start, period_end):
    sql = text("""
        SELECT
            d.orders_id,
            ord.client_order_number,
            ord.client_order_date,
            d.date AS ship_date,
            d.dt,
            d.cr
        FROM sales_salesdata d
        JOIN mv_orders ord ON ord.orders_id = d.orders_id
        WHERE d.date BETWEEN :start AND :end
          AND d.orders_id IS NOT NULL
        ORDER BY d.orders_id, d.date
    """)

    with ENGINE.connect() as conn:
        res = conn.execute(sql, {
            "start": period_start,
            "end": period_end,
        })
        df = pd.DataFrame(res.fetchall(), columns=res.keys())

    if df.empty:
        return df

    # даты
    df["client_order_date"] = pd.to_datetime(df["client_order_date"])
    df["ship_date"] = pd.to_datetime(df["ship_date"])

    # деньги → числа (КРИТИЧНО)
    for c in ("dt", "cr"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # возраст заказа
    df["age_day"] = (df["ship_date"] - df["client_order_date"]).dt.days.clip(lower=0)

    # чистая выручка по отгрузке
    df["net"] = df["dt"] - df["cr"]

    return df
