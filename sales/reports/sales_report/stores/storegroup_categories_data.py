# sales/reports/sales_report/stores/storegroup_categories_data.py
from django.db import connection
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import timedelta


def get_mtd_storegroup_categories_raw(d):
    """
    Дневные продажи в разрезе storegroup/cat/subcat за MTD (до d включительно)
    + тот же период прошлого года.
    Берём ТОЛЬКО активные группы магазинов (sg.is_active = 1).
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

                sg.id AS storegroup_id,
                sg.name AS storegroup_name,

                st.id AS store_id,
                COALESCE(st.name, 'Без магазина') AS store_name,

                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,

                /* root category (нулевой родитель) */
                CASE
                  WHEN cat.parent_id IS NULL OR cat.parent_id = 0 THEN COALESCE(cat.name, 'Без категории')
                  ELSE COALESCE(cat0.name, COALESCE(cat.name, 'Без категории'))
                END AS root_cat_name,

                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,

                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant

            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id

            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_cattree cat0 ON cat0.id = cat.parent_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id

            JOIN corporate_stores st ON st.id = s.store_id
            JOIN corporate_storegroups sg ON sg.id = st.gr_id AND sg.is_active = 1

            WHERE s.`date` >= %(ms)s AND s.`date` < %(me)s
              AND s.store_id IS NOT NULL

            GROUP BY
                s.`date`, YEAR(s.`date`),
                sg.id, sg.name,
                st.id, st.name,
                i.cat_id, cat.name, cat.parent_id, cat0.name,
                i.subcat_id, sc.name
        )
        UNION ALL
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,

                sg.id AS storegroup_id,
                sg.name AS storegroup_name,

                st.id AS store_id,
                COALESCE(st.name, 'Без магазина') AS store_name,

                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,

                /* root category (нулевой родитель) */
                CASE
                  WHEN cat.parent_id IS NULL OR cat.parent_id = 0 THEN COALESCE(cat.name, 'Без категории')
                  ELSE COALESCE(cat0.name, COALESCE(cat.name, 'Без категории'))
                END AS root_cat_name,

                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,

                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant

            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id

            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_cattree cat0 ON cat0.id = cat.parent_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id

            JOIN corporate_stores st ON st.id = s.store_id
            JOIN corporate_storegroups sg ON sg.id = st.gr_id AND sg.is_active = 1

            WHERE s.`date` >= %(ms_prev)s AND s.`date` < %(me_prev)s
              AND s.store_id IS NOT NULL

            GROUP BY
                s.`date`, YEAR(s.`date`),
                sg.id, sg.name,
                st.id, st.name,
                i.cat_id, cat.name, cat.parent_id, cat0.name,
                i.subcat_id, sc.name
        )
        ORDER BY `date`, storegroup_name, store_name, cat_name, sc_name
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ms": ms, "me": me_excl,
            "ms_prev": ms_prev, "me_prev": me_prev_excl
        })
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

    return pd.DataFrame(rows, columns=cols)


def get_ytd_storegroup_categories_raw(d):
    """
    Продажи в разрезе storegroup/cat/subcat за YTD (с 1 января по d включительно)
    + тот же период прошлого года.
    Берём ТОЛЬКО активные группы магазинов (sg.is_active = 1).
    """
    d = pd.to_datetime(d).date()
    ys = d.replace(month=1, day=1)
    ye_excl = d + timedelta(days=1)

    ys_prev = ys - relativedelta(years=1)
    ye_prev_excl = ye_excl - relativedelta(years=1)

    q = """
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,

                sg.id AS storegroup_id,
                sg.name AS storegroup_name,

                st.id AS store_id,
                COALESCE(st.name, 'Без магазина') AS store_name,

                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,

                /* root category (нулевой родитель) */
                CASE
                  WHEN cat.parent_id IS NULL OR cat.parent_id = 0 THEN COALESCE(cat.name, 'Без категории')
                  ELSE COALESCE(cat0.name, COALESCE(cat.name, 'Без категории'))
                END AS root_cat_name,

                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,

                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant

            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id

            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_cattree cat0 ON cat0.id = cat.parent_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id

            JOIN corporate_stores st ON st.id = s.store_id
            JOIN corporate_storegroups sg ON sg.id = st.gr_id AND sg.is_active = 1

            WHERE s.`date` >= %(ys)s AND s.`date` < %(ye)s
              AND s.store_id IS NOT NULL

            GROUP BY
                s.`date`, YEAR(s.`date`),
                sg.id, sg.name,
                st.id, st.name,
                i.cat_id, cat.name, cat.parent_id, cat0.name,
                i.subcat_id, sc.name
        )
        UNION ALL
        (
            SELECT
                s.`date` AS `date`,
                YEAR(s.`date`) AS `year`,

                sg.id AS storegroup_id,
                sg.name AS storegroup_name,

                st.id AS store_id,
                COALESCE(st.name, 'Без магазина') AS store_name,

                i.cat_id AS cat_id,
                COALESCE(cat.name, 'Без категории') AS cat_name,

                /* root category (нулевой родитель) */
                CASE
                  WHEN cat.parent_id IS NULL OR cat.parent_id = 0 THEN COALESCE(cat.name, 'Без категории')
                  ELSE COALESCE(cat0.name, COALESCE(cat.name, 'Без категории'))
                END AS root_cat_name,

                i.subcat_id AS subcat_id,
                COALESCE(sc.name, 'Нет подкатегории') AS sc_name,

                SUM(s.dt - s.cr) AS amount,
                SUM(s.quant_dt - s.quant_cr) AS quant

            FROM sales_salesdata s
            JOIN corporate_items i ON i.id = s.item_id

            LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
            LEFT JOIN corporate_cattree cat0 ON cat0.id = cat.parent_id
            LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id

            JOIN corporate_stores st ON st.id = s.store_id
            JOIN corporate_storegroups sg ON sg.id = st.gr_id AND sg.is_active = 1

            WHERE s.`date` >= %(ys_prev)s AND s.`date` < %(ye_prev)s
              AND s.store_id IS NOT NULL

            GROUP BY
                s.`date`, YEAR(s.`date`),
                sg.id, sg.name,
                st.id, st.name,
                i.cat_id, cat.name, cat.parent_id, cat0.name,
                i.subcat_id, sc.name
        )
        ORDER BY `date`, storegroup_name, store_name, cat_name, sc_name
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ys": ys, "ye": ye_excl,
            "ys_prev": ys_prev, "ye_prev": ye_prev_excl
        })
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

    return pd.DataFrame(rows, columns=cols)