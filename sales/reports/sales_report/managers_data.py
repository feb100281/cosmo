# sales/reports/sales_report/managers_data.py
from django.db import connection
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import timedelta

def _fetch_managers_period(date_from, date_to_excl, big_order_threshold=100_000):
    """
    1) Денежные суммы считаем ПРОСТО по строкам за период:
       dt_sum, cr_sum, amount_sum
    2) Заказы и заказы ≥ threshold считаем по заказам (client_order_number),
       чтобы не было задвоений в orders и в пороге.
    Всё склеиваем в одну таблицу по manager_id.
    """
    q = """
        WITH money AS (
            SELECT
                s.manager_id AS manager_id,
                COALESCE(m.report_name, m.name, 'Без менеджера') AS manager_name,
                SUM(s.dt)        AS dt,
                SUM(s.cr)        AS cr,
                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant
            FROM sales_salesdata s
            LEFT JOIN corporate_managers m ON m.id = s.manager_id
            WHERE s.`date` >= %(df)s AND s.`date` < %(dt)s
            GROUP BY s.manager_id, manager_name
        ),
        orders AS (
            SELECT
                t.manager_id AS manager_id,
                COUNT(*)     AS orders,
                SUM(t.order_dt >= %(big)s) AS orders_100k
            FROM (
                SELECT
                    s.manager_id,
                    s.client_order_number,
                    SUM(s.dt) AS order_dt
                FROM sales_salesdata s
                WHERE s.`date` >= %(df)s AND s.`date` < %(dt)s
                GROUP BY s.manager_id, s.client_order_number
            ) t
            GROUP BY t.manager_id
        )
        SELECT
            money.manager_id,
            money.manager_name,
            money.amount,
            money.dt,
            money.cr,
            money.quant,
            COALESCE(orders.orders, 0) AS orders,
            COALESCE(orders.orders_100k, 0) AS orders_100k
        FROM money
        LEFT JOIN orders ON orders.manager_id = money.manager_id
        ORDER BY money.amount DESC
    """

    with connection.cursor() as cur:
        cur.execute(q, {"df": date_from, "dt": date_to_excl, "big": big_order_threshold})
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    for c in ("amount", "dt", "cr", "quant", "orders", "orders_100k"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df


def get_mtd_managers_bundle(d, big_order_threshold=100_000):
    d = pd.to_datetime(d).date()
    ms = d.replace(day=1)
    me_excl = d + timedelta(days=1)

    ms_ly = ms - relativedelta(years=1)
    me_ly_excl = me_excl - relativedelta(years=1)

    ms_pm = ms - relativedelta(months=1)
    me_pm_excl = me_excl - relativedelta(months=1)

    return {
        "cur": _fetch_managers_period(ms, me_excl, big_order_threshold),
        "ly":  _fetch_managers_period(ms_ly, me_ly_excl, big_order_threshold),
        "pm":  _fetch_managers_period(ms_pm, me_pm_excl, big_order_threshold),
    }


def get_ytd_managers_bundle(d, big_order_threshold=100_000):
    d = pd.to_datetime(d).date()
    ys = d.replace(month=1, day=1)
    ye_excl = d + timedelta(days=1)

    ys_ly = ys - relativedelta(years=1)
    ye_ly_excl = ye_excl - relativedelta(years=1)

    return {
        "cur": _fetch_managers_period(ys, ye_excl, big_order_threshold),
        "ly":  _fetch_managers_period(ys_ly, ye_ly_excl, big_order_threshold),
    }

