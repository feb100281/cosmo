# sales/dash_apps/dailysales/data.py

# Данные для дневного отчета

from django.db import connection
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from datetime import timedelta


def get_month_data(date):
    d = pd.to_datetime(date).date()

    ms = d.replace(day=1)
    me_excl = d + timedelta(days=1)          # включительно по d

    ms_prev = ms - relativedelta(years=1)
    me_prev_excl = me_excl - relativedelta(years=1)

    q = """
        (SELECT * FROM mv_daily_sales
         WHERE date >= %(ms)s AND date < %(me)s)
        UNION ALL
        (SELECT * FROM mv_daily_sales
         WHERE date >= %(ms_prev)s AND date < %(me_prev)s)
        ORDER BY date
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ms": ms, "me": me_excl,
            "ms_prev": ms_prev, "me_prev": me_prev_excl
        })
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]  # самый совместимый вариант
    return pd.DataFrame(rows, columns=cols)

def get_ytd_data(date):
    d = pd.to_datetime(date).date()

    ms = d.replace(month=1, day=1)
    me_excl = d  + timedelta(days=1)

    ms_prev = ms - relativedelta(years=1)
    me_prev_excl = me_excl - relativedelta(years=1)

    q = """
        (SELECT
            LAST_DAY(`date`) AS `date`,
            SUM(amount)  AS amount,
            SUM(quant) AS quant,
            SUM(orders)   AS orders,
            SUM(dt)   AS dt,
            SUM(cr)     AS cr
         FROM mv_daily_sales
         WHERE `date` >= %(ms)s AND `date` < %(me)s
         GROUP BY LAST_DAY(`date`))

        UNION ALL

        (SELECT
            LAST_DAY(`date`) AS `date`,
            SUM(amount)  AS amount,
            SUM(quant) AS quant,
            SUM(orders)   AS orders,
            SUM(dt)   AS dt,
            SUM(cr)     AS cr
         FROM mv_daily_sales
         WHERE `date` >= %(ms_prev)s AND `date` < %(me_prev)s
         GROUP BY LAST_DAY(`date`))

        ORDER BY `date`;
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ms": ms, "me": me_excl,
            "ms_prev": ms_prev, "me_prev": me_prev_excl
        })
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
    return pd.DataFrame(rows, columns=cols)



