# sales/reports/sales_report/orders/data_orders.py

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import text

from utils.db_engine import get_engine


def get_orders_by_period(
    start: date,
    end: date,
    order_type: Optional[int] = None,  # None=все, 1=не розница, 2=розница
) -> pd.DataFrame:
    """
    1 строка = 1 orders_id, агрегировано по sales_salesdata за период.
    Подтягиваем атрибуты заказа из mv_orders.
    + Добавляет накопление по заказу на дату конца периода (<= end) по данным sales_salesdata.
    """

    where_sql = ""
    if order_type == 1:
        where_sql = "WHERE ord.client_order_type != 'Розничные продажи'"
    elif order_type == 2:
        where_sql = "WHERE ord.client_order_type = 'Розничные продажи'"

    sql = text(f"""
        SELECT
            ord.client_order_type,
            ord.client_order_number,
            ord.client_order,
            ord.client_order_date,

            -- totals (как в витрине заказа; обычно "за весь заказ")
            ord.sales as total_sales,
            ord.returns as total_returns,
            ord.amount as total_amount,

            -- ✅ totals up to end (накоплено по проводкам ДО конца периода)
            t.dt_upto_end as total_sales_upto_end,
            t.cr_upto_end as total_returns_upto_end,
            t.dt_upto_end - t.cr_upto_end as total_amount_upto_end,

            -- period (строго за период)
            x.dt as sales_period,
            x.cr as returns_period,
            x.dt - x.cr as amount_period,
            x.max_date as last_ship_date,

            -- товары/сервис (как в витрине заказа)
            ord.items_amount,
            ord.service_amount,
            ord.items_quant,
            ord.unique_items,
            ord.order_duration,

            -- сколько дней "живёт" заказ на текущий момент (до последней отгрузки в периоде)
            DATEDIFF(x.max_date, ord.client_order_date) + 1 AS current_order_duration

        FROM (
            -- строго за период
            SELECT
                orders_id,
                SUM(dt) as dt,
                SUM(cr) as cr,
                MAX(`date`) as max_date
            FROM sales_salesdata
            WHERE `date` BETWEEN :start AND :end
              AND orders_id IS NOT NULL
            GROUP BY orders_id
        ) x

        JOIN (
            -- накоплено по заказу ДО конца периода (на дату end)
            SELECT
                orders_id,
                SUM(dt) as dt_upto_end,
                SUM(cr) as cr_upto_end
            FROM sales_salesdata
            WHERE `date` <= :end
              AND orders_id IS NOT NULL
            GROUP BY orders_id
        ) t ON t.orders_id = x.orders_id

        JOIN mv_orders as ord ON ord.orders_id = x.orders_id
        {where_sql}
        ORDER BY (x.dt - x.cr) DESC
    """)

    engine = get_engine()
    with engine.connect() as conn:
        res = conn.execute(sql, {"start": start, "end": end})
        rows = res.fetchall()
        cols = list(res.keys())

    df = pd.DataFrame(rows, columns=cols)

    # нормализуем типы
    if df.empty:
        return df

    df["client_order_date"] = pd.to_datetime(df["client_order_date"], errors="coerce")
    df["last_ship_date"] = pd.to_datetime(df["last_ship_date"], errors="coerce")

    num_cols = [
        "total_sales", "total_returns", "total_amount",
        "total_sales_upto_end", "total_returns_upto_end", "total_amount_upto_end",
        "sales_period", "returns_period", "amount_period",
        "items_amount", "service_amount",
        "items_quant", "unique_items",
        "order_duration", "current_order_duration"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["client_order_type"] = df["client_order_type"].fillna("—").astype(str)
    df["client_order_number"] = df["client_order_number"].fillna(df["client_order"]).fillna("—").astype(str)

    return df
