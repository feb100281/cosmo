# sales/reports/sales_report/categories_data.py
from django.db import connection
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import timedelta


def get_mtd_categories_raw(d):
    """
    Дневные продажи в разрезе cat/subcat за MTD (до d включительно)
    + тот же период прошлого года.
    """
    d = pd.to_datetime(d).date()
    ms = d.replace(day=1)
    me_excl = d + timedelta(days=1)

    ms_prev = ms - relativedelta(years=1)
    me_prev_excl = me_excl - relativedelta(years=1)

    q = """
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,
                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,
                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,
                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant
            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id
            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id
            WHERE s.`date` >= %(ms)s AND s.`date` < %(me)s
            GROUP BY s.`date`, YEAR(s.`date`), i.cat_id, cat.name, i.subcat_id, sc.name
        )
        UNION ALL
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,
                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,
                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,
                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant
            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id
            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id
            WHERE s.`date` >= %(ms_prev)s AND s.`date` < %(me_prev)s
            GROUP BY s.`date`, YEAR(s.`date`), i.cat_id, cat.name, i.subcat_id, sc.name
        )
        ORDER BY `date`, cat_name, sc_name
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ms": ms, "me": me_excl,
            "ms_prev": ms_prev, "me_prev": me_prev_excl
        })
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

    return pd.DataFrame(rows, columns=cols)



def get_ytd_categories_raw(d):
    """
    Продажи в разрезе cat/subcat за YTD (с 1 января по d включительно)
    + тот же период прошлого года.
    """
    d = pd.to_datetime(d).date()
    ys = d.replace(month=1, day=1)             # year start
    ye_excl = d + timedelta(days=1)            # конец включительно

    ys_prev = ys - relativedelta(years=1)
    ye_prev_excl = ye_excl - relativedelta(years=1)

    q = """
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,
                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,
                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,
                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant
            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id
            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id
            WHERE s.`date` >= %(ys)s AND s.`date` < %(ye)s
            GROUP BY s.`date`, YEAR(s.`date`), i.cat_id, cat.name, i.subcat_id, sc.name
        )
        UNION ALL
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,
                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,
                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,
                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant
            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id
            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id
            WHERE s.`date` >= %(ys_prev)s AND s.`date` < %(ye_prev)s
            GROUP BY s.`date`, YEAR(s.`date`), i.cat_id, cat.name, i.subcat_id, sc.name
        )
        ORDER BY `date`, cat_name, sc_name
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ys": ys, "ye": ye_excl,
            "ys_prev": ys_prev, "ye_prev": ye_prev_excl
        })
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

    return pd.DataFrame(rows, columns=cols)