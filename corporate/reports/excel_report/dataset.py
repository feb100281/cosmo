# corporate/reports/excel_report/dataset.py
from __future__ import annotations

from decimal import Decimal
from typing import Any
from django.db import connection
from collections import defaultdict


def fetch_all_dict(query: str, params: dict | None = None) -> list[dict[str, Any]]:
    params = params or {}
    with connection.cursor() as cur:
        cur.execute(query, params)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def get_years(start_year: int = 2022) -> list[int]:
    q = """
        SELECT DISTINCT YEAR(`date`) AS y
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
        ORDER BY y
    """
    rows = fetch_all_dict(q, {"start_year": start_year})
    return [int(r["y"]) for r in rows]


def get_overview_store_details(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            YEAR(s.`date`) AS year,
            COALESCE(st.name, '—') AS store_name,
            SUM(s.dt - s.cr) AS net_amount,
            COUNT(DISTINCT it.id) AS items_cnt,
            COUNT(DISTINCT COALESCE(it.manufacturer_id, 0)) AS manufacturers_cnt
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_stores st ON st.id = s.store_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            YEAR(s.`date`),
            COALESCE(st.name, '—')
        ORDER BY
            YEAR(s.`date`),
            SUM(s.dt - s.cr) DESC,
            COALESCE(st.name, '—')
    """
    return fetch_all_dict(q, params)


def get_overview_metrics(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS net_amount,
            COUNT(DISTINCT it.id) AS items_cnt,
            COUNT(DISTINCT COALESCE(it.manufacturer_id, 0)) AS manufacturers_cnt,
            COUNT(DISTINCT st.id) AS stores_cnt
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_stores st ON st.id = s.store_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY YEAR(s.`date`)
        ORDER BY year
    """
    return fetch_all_dict(q, params)

def get_manufacturers_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY manufacturer, YEAR(s.`date`)
        ORDER BY manufacturer, year
    """
    return fetch_all_dict(q, params)


def get_categories_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            COALESCE(c.name, '—') AS category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY category, YEAR(s.`date`)
        ORDER BY category, year
    """
    return fetch_all_dict(q, params)


def get_root_categories_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            COALESCE(r.name, '—') AS root_category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        JOIN corporate_cattree c ON c.id = it.cat_id
        JOIN corporate_cattree r
          ON r.parent_id IS NULL
         AND r.tree_id = c.tree_id
         AND c.lft >= r.lft
         AND c.rght <= r.rght
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY root_category, YEAR(s.`date`)
        ORDER BY root_category, year
    """
    return fetch_all_dict(q, params)


def get_manufacturer_category_matrix(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            COALESCE(c.name, '—') AS category,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY manufacturer, category
        ORDER BY manufacturer, category
    """
    return fetch_all_dict(q, params)


# def get_top_items(start_year: int = 2022, manufacturer_ids: list[int] | None = None, limit: int = 200):
#     params = {
#         "start_year": start_year,
#         "limit": int(limit),
#     }
#     mf_filter = ""

#     if manufacturer_ids:
#         ph = []
#         for i, v in enumerate(manufacturer_ids):
#             k = f"mf{i}"
#             params[k] = int(v)
#             ph.append(f"%({k})s")
#         mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

#     q = f"""
#         SELECT
#             it.id AS item_id,
#             COALESCE(it.fullname, '—') AS item_name,
#             COALESCE(it.article, '') AS article,
#             COALESCE(m.report_name, m.name, '!Производитель не указан') AS manufacturer,
#             COALESCE(c.name, '—') AS category,
#             SUM(s.dt - s.cr) AS net_amount
#         FROM sales_salesdata s
#         JOIN corporate_items it ON it.id = s.item_id
#         LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
#         LEFT JOIN corporate_cattree c ON c.id = it.cat_id
#         WHERE YEAR(s.`date`) >= %(start_year)s
#         {mf_filter}
#         GROUP BY it.id, item_name, article, manufacturer, category
#         ORDER BY net_amount DESC
#         LIMIT %(limit)s
#     """
#     return fetch_all_dict(q, params)


def get_top_items(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
    limit: int = 100
):
    params = {
        "start_year": start_year,
        "limit": limit,
    }

    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")

        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            it.id AS item_id,
            COALESCE(it.name, '—') AS item_name,
            COALESCE(it.article, '—') AS article,
            COALESCE(m.report_name, m.name, '—') AS manufacturer,
            COALESCE(c.name, '—') AS category,
            SUM(s.quant_dt - s.quant_cr) AS qty_sold,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            it.id,
            it.name,
            it.article,
            m.report_name,
            m.name,
            c.name
        ORDER BY net_amount DESC
        LIMIT %(limit)s
    """

    return fetch_all_dict(q, params)




def get_top_items_qty_by_year(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
    limit: int = 100
):
    params = {
        "start_year": start_year,
        "limit": limit,
    }

    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")

        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            base.item_id,
            YEAR(s.`date`) AS year,
            SUM(s.quant_dt - s.quant_cr) AS qty_sold_year
        FROM (
            SELECT
                it.id AS item_id,
                SUM(s.dt - s.cr) AS net_amount
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            GROUP BY it.id
            ORDER BY net_amount DESC
            LIMIT %(limit)s
        ) base
        JOIN sales_salesdata s ON s.item_id = base.item_id
        JOIN corporate_items it ON it.id = s.item_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            base.item_id,
            YEAR(s.`date`)
        ORDER BY
            base.item_id,
            year
    """

    return fetch_all_dict(q, params)






def get_manufacturer_item_counts(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Сколько уникальных товаров у производителя участвовало в продажах за период
    + выручка за период.
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            COUNT(DISTINCT it.id) AS item_count,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY manufacturer
        ORDER BY net_amount DESC
    """
    return fetch_all_dict(q, params)


def get_manufacturer_share_by_year(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Доля производителя в общей выручке по каждому году.
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            t.manufacturer,
            t.year,
            t.net_amount,
            y.year_total,
            CASE
                WHEN y.year_total = 0 OR y.year_total IS NULL THEN 0
                ELSE t.net_amount / y.year_total
            END AS share
        FROM (
            SELECT
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END AS manufacturer,
                YEAR(s.`date`) AS year,
                SUM(s.dt - s.cr) AS net_amount
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            {mf_filter}
            GROUP BY manufacturer, YEAR(s.`date`)
        ) t
        JOIN (
            SELECT
                YEAR(s.`date`) AS year,
                SUM(s.dt - s.cr) AS year_total
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            {mf_filter}
            GROUP BY YEAR(s.`date`)
        ) y ON y.year = t.year
        ORDER BY t.manufacturer, t.year
    """
    return fetch_all_dict(q, params)





def get_category_manufacturer_dependence(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Для каждой категории:
    - общая выручка категории
    - крупнейший производитель
    - выручка крупнейшего производителя в этой категории
    - доля крупнейшего производителя в выручке категории
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            z.category,
            z.manufacturer,
            z.manufacturer_revenue,
            z.total_category_revenue,
            CASE
                WHEN z.total_category_revenue = 0 OR z.total_category_revenue IS NULL THEN 0
                ELSE z.manufacturer_revenue / z.total_category_revenue
            END AS dependence_share
        FROM (
            SELECT
                x.category,
                x.manufacturer,
                x.manufacturer_revenue,
                y.total_category_revenue,
                ROW_NUMBER() OVER (
                    PARTITION BY x.category
                    ORDER BY x.manufacturer_revenue DESC, x.manufacturer
                ) AS rn
            FROM (
                SELECT
                    COALESCE(c.name, '—') AS category,
                    CASE
                        WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                        ELSE COALESCE(m.report_name, m.name, '—')
                    END AS manufacturer,
                    SUM(s.dt - s.cr) AS manufacturer_revenue
                FROM sales_salesdata s
                JOIN corporate_items it ON it.id = s.item_id
                LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
                LEFT JOIN corporate_cattree c ON c.id = it.cat_id
                WHERE YEAR(s.`date`) >= %(start_year)s
                {mf_filter}
                GROUP BY
                    COALESCE(c.name, '—'),
                    CASE
                        WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                        ELSE COALESCE(m.report_name, m.name, '—')
                    END
            ) x
            JOIN (
                SELECT
                    COALESCE(c.name, '—') AS category,
                    SUM(s.dt - s.cr) AS total_category_revenue
                FROM sales_salesdata s
                JOIN corporate_items it ON it.id = s.item_id
                LEFT JOIN corporate_cattree c ON c.id = it.cat_id
                WHERE YEAR(s.`date`) >= %(start_year)s
                {mf_filter}
                GROUP BY COALESCE(c.name, '—')
            ) y ON y.category = x.category
        ) z
        WHERE z.rn = 1
        ORDER BY
            CASE
                WHEN z.total_category_revenue = 0 OR z.total_category_revenue IS NULL THEN 0
                ELSE z.manufacturer_revenue / z.total_category_revenue
            END DESC,
            z.total_category_revenue DESC,
            z.category
    """
    return fetch_all_dict(q, params)




def get_subcategory_manufacturer_dependence(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Для каждой подкатегории:
    - общая выручка подкатегории
    - крупнейший производитель
    - выручка крупнейшего производителя в этой подкатегории
    - доля крупнейшего производителя в выручке подкатегории
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            z.category,
            z.subcategory,
            z.manufacturer,
            z.manufacturer_revenue,
            z.total_subcategory_revenue,
            CASE
                WHEN z.total_subcategory_revenue = 0 OR z.total_subcategory_revenue IS NULL THEN 0
                ELSE z.manufacturer_revenue / z.total_subcategory_revenue
            END AS dependence_share
        FROM (
            SELECT
                x.category,
                x.subcategory,
                x.manufacturer,
                x.manufacturer_revenue,
                y.total_subcategory_revenue,
                ROW_NUMBER() OVER (
                    PARTITION BY x.category, x.subcategory
                    ORDER BY x.manufacturer_revenue DESC, x.manufacturer
                ) AS rn
            FROM (
                SELECT
                    COALESCE(c.name, 'Без категории') AS category,
                    COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
                    CASE
                        WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                        ELSE COALESCE(m.report_name, m.name, '—')
                    END AS manufacturer,
                    SUM(s.dt - s.cr) AS manufacturer_revenue
                FROM sales_salesdata s
                JOIN corporate_items it ON it.id = s.item_id
                LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
                LEFT JOIN corporate_cattree c ON c.id = it.cat_id
                LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
                WHERE YEAR(s.`date`) >= %(start_year)s
                {mf_filter}
                GROUP BY
                    COALESCE(c.name, 'Без категории'),
                    COALESCE(sc.name, 'Нет подкатегории'),
                    CASE
                        WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                        ELSE COALESCE(m.report_name, m.name, '—')
                    END
            ) x
            JOIN (
                SELECT
                    COALESCE(c.name, 'Без категории') AS category,
                    COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
                    SUM(s.dt - s.cr) AS total_subcategory_revenue
                FROM sales_salesdata s
                JOIN corporate_items it ON it.id = s.item_id
                LEFT JOIN corporate_cattree c ON c.id = it.cat_id
                LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
                WHERE YEAR(s.`date`) >= %(start_year)s
                {mf_filter}
                GROUP BY
                    COALESCE(c.name, 'Без категории'),
                    COALESCE(sc.name, 'Нет подкатегории')
            ) y
              ON y.category = x.category
             AND y.subcategory = x.subcategory
        ) z
        WHERE z.rn = 1
        ORDER BY
            CASE
                WHEN z.total_subcategory_revenue = 0 OR z.total_subcategory_revenue IS NULL THEN 0
                ELSE z.manufacturer_revenue / z.total_subcategory_revenue
            END DESC,
            z.total_subcategory_revenue DESC,
            z.category,
            z.subcategory
    """
    return fetch_all_dict(q, params)


def get_category_totals(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            COALESCE(c.name, '—') AS category,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY category
        ORDER BY net_amount DESC
    """
    return fetch_all_dict(q, params)




def get_lost_categories(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Категории с самым сильным падением в последнем году относительно предыдущего.
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return []

    prev_year = years[-2]
    last_year = years[-1]

    params = {
        "prev_year": prev_year,
        "last_year": last_year,
    }
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            t.category,
            SUM(CASE WHEN t.year = %(prev_year)s THEN t.net_amount ELSE 0 END) AS prev_year_amount,
            SUM(CASE WHEN t.year = %(last_year)s THEN t.net_amount ELSE 0 END) AS last_year_amount,
            SUM(CASE WHEN t.year = %(last_year)s THEN t.net_amount ELSE 0 END)
              - SUM(CASE WHEN t.year = %(prev_year)s THEN t.net_amount ELSE 0 END) AS diff_amount
        FROM (
            SELECT
                COALESCE(c.name, '—') AS category,
                YEAR(s.`date`) AS year,
                SUM(s.dt - s.cr) AS net_amount
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_cattree c ON c.id = it.cat_id
            WHERE YEAR(s.`date`) IN (%(prev_year)s, %(last_year)s)
            {mf_filter}
            GROUP BY COALESCE(c.name, '—'), YEAR(s.`date`)
        ) t
        GROUP BY t.category
        ORDER BY diff_amount ASC, last_year_amount ASC, category
    """
    return fetch_all_dict(q, params)


def get_top_growth_manufacturers(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
    limit: int = 20,
):
    """
    Данные для листа Top growth manufacturers.

    Логика:
    - показываем 3 последних года для контекста
    - сравнение делаем между двумя последними годами
    - если последний год не закрыт, сравниваем YTD последнего года
      с YTD предыдущего года на сопоставимую дату
    - в лист попадают только производители с положительным diff
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return {
            "years_for_display": years[-3:],
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": None,
            "compare_last_year": None,
        }

    years_for_display = years[-3:] if len(years) >= 3 else years[:]
    compare_prev_year = years[-2]
    compare_last_year = years[-1]

    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return {
            "years_for_display": years_for_display,
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": compare_prev_year,
            "compare_last_year": compare_last_year,
        }

    cutoff_year = int(cutoff_date.year)
    cutoff_month = int(cutoff_date.month)
    cutoff_day = int(cutoff_date.day)

    is_ytd_comparison = bool(
        compare_last_year == cutoff_year and (cutoff_month < 12 or cutoff_day < 31)
    )

    params["cutoff_month"] = cutoff_month
    params["cutoff_day"] = cutoff_day

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END,
            YEAR(s.`date`)
        ORDER BY manufacturer, year
    """
    raw_rows = fetch_all_dict(q, params)

    data = defaultdict(dict)
    for r in raw_rows:
        manufacturer = r.get("manufacturer") or "—"
        year = int(r.get("year"))
        data[manufacturer][year] = {
            "full_amount": float(r.get("full_amount") or 0),
            "ytd_amount": float(r.get("ytd_amount") or 0),
        }

    prepared = []

    for manufacturer, vals in data.items():
        prev_compare_amount = (
            float(vals.get(compare_prev_year, {}).get("ytd_amount", 0) or 0)
            if is_ytd_comparison
            else float(vals.get(compare_prev_year, {}).get("full_amount", 0) or 0)
        )
        last_compare_amount = (
            float(vals.get(compare_last_year, {}).get("ytd_amount", 0) or 0)
            if is_ytd_comparison
            else float(vals.get(compare_last_year, {}).get("full_amount", 0) or 0)
        )

        diff_amount = last_compare_amount - prev_compare_amount

        if diff_amount <= 0:
            continue

        diff_pct = 0 if prev_compare_amount == 0 else diff_amount / prev_compare_amount

        year_values = []
        for y in years_for_display:
            if is_ytd_comparison and y == compare_last_year:
                display_val = float(vals.get(y, {}).get("ytd_amount", 0) or 0)
            else:
                display_val = float(vals.get(y, {}).get("full_amount", 0) or 0)
            year_values.append(display_val)

        prepared.append(
            {
                "manufacturer": manufacturer,
                "year_values": year_values,
                "prev_compare_amount": prev_compare_amount,
                "last_compare_amount": last_compare_amount,
                "diff_amount": diff_amount,
                "diff_pct": diff_pct,
            }
        )

    prepared.sort(key=lambda x: x["diff_amount"], reverse=True)
    prepared = prepared[:limit]

    total_positive_diff = sum(float(r["diff_amount"] or 0) for r in prepared)

    for row in prepared:
        row["growth_share"] = (
            0 if total_positive_diff == 0 else float(row["diff_amount"]) / total_positive_diff
        )

    return {
        "years_for_display": years_for_display,
        "rows": prepared,
        "is_ytd_comparison": is_ytd_comparison,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "cutoff_day": cutoff_day,
        "compare_prev_year": compare_prev_year,
        "compare_last_year": compare_last_year,
    }

def get_top_growth_categories(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
    top_growth_manufacturers: list[str] | None = None,
):
    """
    Категории для листа Top growth manufacturers.

    Возвращает по каждому производителю/категории:
    - full_amount по году
    - ytd_amount по году
    с той же cutoff-логикой, что и top growth.
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return {
            "years_for_display": years[-3:],
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": None,
            "compare_last_year": None,
        }

    years_for_display = years[-3:] if len(years) >= 3 else years[:]
    compare_prev_year = years[-2]
    compare_last_year = years[-1]

    params = {"start_year": start_year}
    mf_filter = ""
    growth_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    if top_growth_manufacturers:
        ph = []
        for i, v in enumerate(top_growth_manufacturers):
            k = f"tgm{i}"
            params[k] = v
            ph.append(f"%({k})s")

        growth_filter = f"""
            AND (
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END
            ) IN ({', '.join(ph)})
        """

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return {
            "years_for_display": years_for_display,
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": compare_prev_year,
            "compare_last_year": compare_last_year,
        }

    cutoff_year = int(cutoff_date.year)
    cutoff_month = int(cutoff_date.month)
    cutoff_day = int(cutoff_date.day)

    is_ytd_comparison = bool(
        compare_last_year == cutoff_year and (cutoff_month < 12 or cutoff_day < 31)
    )

    params["cutoff_month"] = cutoff_month
    params["cutoff_day"] = cutoff_day

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            COALESCE(c.name, '—') AS category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        {growth_filter}
        GROUP BY
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END,
            COALESCE(c.name, '—'),
            YEAR(s.`date`)
        ORDER BY manufacturer, category, year
    """
    rows = fetch_all_dict(q, params)

    return {
        "years_for_display": years_for_display,
        "rows": rows,
        "is_ytd_comparison": is_ytd_comparison,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "cutoff_day": cutoff_day,
        "compare_prev_year": compare_prev_year,
        "compare_last_year": compare_last_year,
    }
    
    
def get_new_vs_old_manufacturers(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Делим производителей на:
    - New: первая продажа в последнем году
    - Old: первая продажа раньше последнего года
    """
    years = get_years(start_year=start_year)
    if not years:
        return []

    last_year = years[-1]

    params = {
        "start_year": start_year,
        "last_year": last_year,
    }
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            CASE
                WHEN x.first_sale_year = %(last_year)s THEN 'New'
                ELSE 'Old'
            END AS mf_group,
            COUNT(*) AS manufacturers_count,
            SUM(x.total_revenue) AS total_revenue
        FROM (
            SELECT
                manufacturer,
                MIN(year_num) AS first_sale_year,
                SUM(net_amount) AS total_revenue
            FROM (
                SELECT
                    CASE
                        WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                        ELSE COALESCE(m.report_name, m.name, '—')
                    END AS manufacturer,
                    YEAR(s.`date`) AS year_num,
                    SUM(s.dt - s.cr) AS net_amount
                FROM sales_salesdata s
                JOIN corporate_items it ON it.id = s.item_id
                LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
                WHERE YEAR(s.`date`) >= %(start_year)s
                {mf_filter}
                GROUP BY
                    CASE
                        WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                        ELSE COALESCE(m.report_name, m.name, '—')
                    END,
                    YEAR(s.`date`)
            ) base
            GROUP BY manufacturer
        ) x
        GROUP BY
            CASE
                WHEN x.first_sale_year = %(last_year)s THEN 'New'
                ELSE 'Old'
            END
        ORDER BY mf_group
    """
    return fetch_all_dict(q, params)


def get_store_x_manufacturer(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Матрица магазин × производитель.
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            COALESCE(st.name, '—') AS store_name,
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_stores st ON st.id = s.store_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            COALESCE(st.name, '—'),
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END
        ORDER BY store_name, net_amount DESC, manufacturer
    """
    return fetch_all_dict(q, params)





def get_manufacturers_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Данные для YOY-листа.

    Возвращает по каждому производителю и году:
    - full_amount: полная сумма за год (по фактически имеющимся данным в базе)
    - ytd_amount: сумма по этот же месяц/день, что и max(date) в базе
                  (нужна для корректного сравнения последнего незакрытого года с прошлым годом)
    - cutoff_year / cutoff_month / cutoff_day: дата среза отчета
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY manufacturer, YEAR(s.`date`)
        ORDER BY manufacturer, year
    """
    return fetch_all_dict(q, params)






def get_manufacturer_categories_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Данные для вложенных строк категорий под производителем на YOY-листе.
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            COALESCE(c.name, '—') AS category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY manufacturer, category, YEAR(s.`date`)
        ORDER BY manufacturer, category, year
    """
    return fetch_all_dict(q, params)






def get_anti_top_manufacturers(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
    limit: int = 20,
):
    """
    Данные для листа Anti-top manufacturers.

    Логика:
    - показываем 3 последних года для контекста
    - сравнение делаем между двумя последними годами
    - если последний год не закрыт, сравниваем YTD последнего года
      с YTD предыдущего года на сопоставимую дату
    - в лист попадают только производители с отрицательным diff
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return {
            "years_for_display": years[-3:],
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": None,
            "compare_last_year": None,
        }

    years_for_display = years[-3:] if len(years) >= 3 else years[:]
    compare_prev_year = years[-2]
    compare_last_year = years[-1]

    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    # -------------------------------------------------
    # Дата среза
    # -------------------------------------------------
    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return {
            "years_for_display": years_for_display,
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": compare_prev_year,
            "compare_last_year": compare_last_year,
        }

    cutoff_year = int(cutoff_date.year)
    cutoff_month = int(cutoff_date.month)
    cutoff_day = int(cutoff_date.day)

    is_ytd_comparison = bool(
        compare_last_year == cutoff_year and (cutoff_month < 12 or cutoff_day < 31)
    )

    params["cutoff_month"] = cutoff_month
    params["cutoff_day"] = cutoff_day

    # -------------------------------------------------
    # Агрегат по производителю и году
    # -------------------------------------------------
    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END,
            YEAR(s.`date`)
        ORDER BY manufacturer, year
    """
    raw_rows = fetch_all_dict(q, params)

    # -------------------------------------------------
    # Складываем в словарь
    # -------------------------------------------------
    data = defaultdict(dict)
    for r in raw_rows:
        manufacturer = r.get("manufacturer") or "—"
        year = int(r.get("year"))
        data[manufacturer][year] = {
            "full_amount": float(r.get("full_amount") or 0),
            "ytd_amount": float(r.get("ytd_amount") or 0),
        }

    # -------------------------------------------------
    # Подготовка строк anti-top
    # -------------------------------------------------
    prepared = []

    for manufacturer, vals in data.items():
        prev_compare_amount = (
            float(vals.get(compare_prev_year, {}).get("ytd_amount", 0) or 0)
            if is_ytd_comparison
            else float(vals.get(compare_prev_year, {}).get("full_amount", 0) or 0)
        )
        last_compare_amount = (
            float(vals.get(compare_last_year, {}).get("ytd_amount", 0) or 0)
            if is_ytd_comparison
            else float(vals.get(compare_last_year, {}).get("full_amount", 0) or 0)
        )

        diff_amount = last_compare_amount - prev_compare_amount

        # только падение
        if diff_amount >= 0:
            continue

        diff_pct = 0 if prev_compare_amount == 0 else diff_amount / prev_compare_amount

        year_values = []
        for y in years_for_display:
            if is_ytd_comparison and y == compare_last_year:
                display_val = float(vals.get(y, {}).get("ytd_amount", 0) or 0)
            else:
                display_val = float(vals.get(y, {}).get("full_amount", 0) or 0)
            year_values.append(display_val)

        prepared.append(
            {
                "manufacturer": manufacturer,
                "year_values": year_values,
                "prev_compare_amount": prev_compare_amount,
                "last_compare_amount": last_compare_amount,
                "diff_amount": diff_amount,
                "diff_pct": diff_pct,
            }
        )

    # сортируем по наибольшему падению
    prepared.sort(key=lambda x: x["diff_amount"])

    # берём top N
    prepared = prepared[:limit]

    # вклад в общее падение считаем только по показанным строкам
    total_negative_diff = sum(abs(float(r["diff_amount"] or 0)) for r in prepared)

    for row in prepared:
        row["decline_share"] = (
            0 if total_negative_diff == 0 else abs(row["diff_amount"]) / total_negative_diff
        )

    return {
        "years_for_display": years_for_display,
        "rows": prepared,
        "is_ytd_comparison": is_ytd_comparison,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "cutoff_day": cutoff_day,
        "compare_prev_year": compare_prev_year,
        "compare_last_year": compare_last_year,
    }
    
    
    
def get_anti_top_categories(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
    anti_top_manufacturers: list[str] | None = None,
):
    """
    Категории для листа Anti-top manufacturers.

    Возвращает по каждому производителю/категории:
    - full_amount по году
    - ytd_amount по году
    с той же cutoff-логикой, что и anti-top.
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return {
            "years_for_display": years[-3:],
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": None,
            "compare_last_year": None,
        }

    years_for_display = years[-3:] if len(years) >= 3 else years[:]
    compare_prev_year = years[-2]
    compare_last_year = years[-1]

    params = {"start_year": start_year}
    mf_filter = ""
    anti_top_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    if anti_top_manufacturers:
        ph = []
        for i, v in enumerate(anti_top_manufacturers):
            k = f"atm{i}"
            params[k] = v
            ph.append(f"%({k})s")

        anti_top_filter = f"""
            AND (
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END
            ) IN ({', '.join(ph)})
        """

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return {
            "years_for_display": years_for_display,
            "rows": [],
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
            "compare_prev_year": compare_prev_year,
            "compare_last_year": compare_last_year,
        }

    cutoff_year = int(cutoff_date.year)
    cutoff_month = int(cutoff_date.month)
    cutoff_day = int(cutoff_date.day)

    is_ytd_comparison = bool(
        compare_last_year == cutoff_year and (cutoff_month < 12 or cutoff_day < 31)
    )

    params["cutoff_month"] = cutoff_month
    params["cutoff_day"] = cutoff_day

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            COALESCE(c.name, '—') AS category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        {anti_top_filter}
        GROUP BY
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END,
            COALESCE(c.name, '—'),
            YEAR(s.`date`)
        ORDER BY manufacturer, category, year
    """
    rows = fetch_all_dict(q, params)

    return {
        "years_for_display": years_for_display,
        "rows": rows,
        "is_ytd_comparison": is_ytd_comparison,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "cutoff_day": cutoff_day,
        "compare_prev_year": compare_prev_year,
        "compare_last_year": compare_last_year,
    }
    
    
    
    
# def get_categories_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
#     """
#     Данные для листа Categories с поддержкой YTD для последнего незакрытого года.

#     Возвращает по каждой категории и году:
#     - full_amount
#     - ytd_amount
#     - cutoff_year / cutoff_month / cutoff_day
#     """
#     params = {"start_year": start_year}
#     mf_filter = ""

#     if manufacturer_ids:
#         ph = []
#         for i, v in enumerate(manufacturer_ids):
#             k = f"mf{i}"
#             params[k] = int(v)
#             ph.append(f"%({k})s")
#         mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

#     cutoff_q = """
#         SELECT MAX(`date`) AS cutoff_date
#         FROM sales_salesdata
#         WHERE YEAR(`date`) >= %(start_year)s
#     """
#     cutoff_rows = fetch_all_dict(cutoff_q, params)
#     cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

#     if not cutoff_date:
#         return []

#     params["cutoff_year"] = int(cutoff_date.year)
#     params["cutoff_month"] = int(cutoff_date.month)
#     params["cutoff_day"] = int(cutoff_date.day)

#     q = f"""
#         SELECT
#             COALESCE(c.name, '—') AS category,
#             YEAR(s.`date`) AS year,
#             SUM(s.dt - s.cr) AS full_amount,
#             SUM(
#                 CASE
#                     WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
#                     WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
#                     ELSE 0
#                 END
#             ) AS ytd_amount,
#             %(cutoff_year)s AS cutoff_year,
#             %(cutoff_month)s AS cutoff_month,
#             %(cutoff_day)s AS cutoff_day
#         FROM sales_salesdata s
#         JOIN corporate_items it ON it.id = s.item_id
#         LEFT JOIN corporate_cattree c ON c.id = it.cat_id
#         WHERE YEAR(s.`date`) >= %(start_year)s
#         {mf_filter}
#         GROUP BY COALESCE(c.name, '—'), YEAR(s.`date`)
#         ORDER BY category, year
#     """
#     return fetch_all_dict(q, params)



def get_categories_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Данные для листа Categories с поддержкой YTD для последнего незакрытого года.

    Возвращает по каждой категории и году:
    - full_amount
    - ytd_amount
    - full_qty
    - ytd_qty
    - sku_count
    - cutoff_year / cutoff_month / cutoff_day
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            COALESCE(c.name, '—') AS category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount,
            SUM(s.quant_dt - s.quant_cr) AS full_qty,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                    ELSE 0
                END
            ) AS ytd_qty,
            COUNT(DISTINCT it.id) AS sku_count,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY COALESCE(c.name, '—'), YEAR(s.`date`)
        ORDER BY category, year
    """
    return fetch_all_dict(q, params)


def get_subcategories_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Данные для листа Subcategories с поддержкой YTD для последнего незакрытого года.

    Возвращает по каждой категории / подкатегории и году:
    - full_amount
    - ytd_amount
    - cutoff_year / cutoff_month / cutoff_day
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            COALESCE(c.name, 'Без категории') AS category,
            COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY
            COALESCE(c.name, 'Без категории'),
            COALESCE(sc.name, 'Нет подкатегории'),
            YEAR(s.`date`)
        ORDER BY category, subcategory, year
    """
    return fetch_all_dict(q, params)

def get_root_categories_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Данные для листа Root Categories с поддержкой YTD для последнего незакрытого года.

    Возвращает по каждой группе категорий и году:
    - full_amount
    - ytd_amount
    - cutoff_year / cutoff_month / cutoff_day
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            COALESCE(r.name, '—') AS root_category,
            YEAR(s.`date`) AS year,
            SUM(s.dt - s.cr) AS full_amount,
            SUM(
                CASE
                    WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                    WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                    ELSE 0
                END
            ) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        JOIN corporate_cattree c ON c.id = it.cat_id
        JOIN corporate_cattree r
          ON r.parent_id IS NULL
         AND r.tree_id = c.tree_id
         AND c.lft >= r.lft
         AND c.rght <= r.rght
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY COALESCE(r.name, '—'), YEAR(s.`date`)
        ORDER BY root_category, year
    """
    return fetch_all_dict(q, params)




def get_manufacturer_category_item_counts(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Разбивка по производителю и категории:
    - количество уникальных SKU в категории у производителя
    - выручка категории у производителя
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            CASE
                WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer,
            COALESCE(c.name, '—') AS category,
            COUNT(DISTINCT it.id) AS item_count,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY manufacturer, category
        ORDER BY manufacturer, net_amount DESC, category
    """
    return fetch_all_dict(q, params)








def get_assortment_width_by_manufacturer(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    Анализ ширины ассортимента по производителям.

    Возвращает:
    - sku_count: количество уникальных SKU с ненулевым qty в периоде
    - qty_sold: количество проданных штук
    - net_amount: выручка
    по каждому производителю и году

    Если последний год не закрыт, в sheet будем сравнивать:
    YTD последнего года vs YTD предыдущего года на ту же дату.
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            x.manufacturer,
            x.year,
            COUNT(DISTINCT CASE WHEN x.full_qty <> 0 THEN x.item_id END) AS full_sku_count,
            COUNT(DISTINCT CASE WHEN x.ytd_qty <> 0 THEN x.item_id END) AS ytd_sku_count,
            SUM(x.full_qty) AS full_qty,
            SUM(x.ytd_qty) AS ytd_qty,
            SUM(x.full_amount) AS full_amount,
            SUM(x.ytd_amount) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM (
            SELECT
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END AS manufacturer,
                it.id AS item_id,
                YEAR(s.`date`) AS year,
                SUM(s.quant_dt - s.quant_cr) AS full_qty,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                        ELSE 0
                    END
                ) AS ytd_qty,
                SUM(s.dt - s.cr) AS full_amount,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                        ELSE 0
                    END
                ) AS ytd_amount
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            {mf_filter}
            GROUP BY
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END,
                it.id,
                YEAR(s.`date`)
        ) x
        GROUP BY x.manufacturer, x.year
        ORDER BY x.manufacturer, x.year
    """
    return fetch_all_dict(q, params)




def get_assortment_width_by_subcategory(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    Анализ ширины ассортимента по категориям / подкатегориям.

    Возвращает:
    - sku_count: количество уникальных SKU с ненулевым qty в периоде
    - qty_sold: количество проданных штук
    - net_amount: выручка
    по каждой категории / подкатегории и году

    Если последний год не закрыт, в sheet сравниваем:
    YTD последнего года vs YTD предыдущего года на ту же дату.
    """
    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            x.category,
            x.subcategory,
            x.year,
            COUNT(DISTINCT CASE WHEN x.full_qty <> 0 THEN x.item_id END) AS full_sku_count,
            COUNT(DISTINCT CASE WHEN x.ytd_qty <> 0 THEN x.item_id END) AS ytd_sku_count,
            SUM(x.full_qty) AS full_qty,
            SUM(x.ytd_qty) AS ytd_qty,
            SUM(x.full_amount) AS full_amount,
            SUM(x.ytd_amount) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM (
            SELECT
                COALESCE(c.name, 'Без категории') AS category,
                COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
                it.id AS item_id,
                YEAR(s.`date`) AS year,
                SUM(s.quant_dt - s.quant_cr) AS full_qty,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                        ELSE 0
                    END
                ) AS ytd_qty,
                SUM(s.dt - s.cr) AS full_amount,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                        ELSE 0
                    END
                ) AS ytd_amount
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_cattree c ON c.id = it.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            {mf_filter}
            GROUP BY
                COALESCE(c.name, 'Без категории'),
                COALESCE(sc.name, 'Нет подкатегории'),
                it.id,
                YEAR(s.`date`)
        ) x
        GROUP BY x.category, x.subcategory, x.year
        ORDER BY x.category, x.subcategory, x.year
    """
    return fetch_all_dict(q, params)








def get_new_lost_sku_by_manufacturer(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    New / Lost SKU по производителям.

    Сравниваем:
    - предыдущий год (или YTD)
    - текущий год (или YTD)
    """

    years = get_years(start_year=start_year)
    if len(years) < 2:
        return []

    prev_year = years[-2]
    last_year = years[-1]

    params = {
        "start_year": start_year,
        "prev_year": prev_year,
        "last_year": last_year,
    }

    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    q = f"""
        WITH base AS (
            SELECT
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END AS manufacturer,
                it.id AS item_id,
                YEAR(s.`date`) AS year,
                SUM(s.quant_dt - s.quant_cr) AS qty
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
            WHERE YEAR(s.`date`) IN (%(prev_year)s, %(last_year)s)
            {mf_filter}
            GROUP BY manufacturer, it.id, YEAR(s.`date`)
        )

        SELECT
            manufacturer,

            COUNT(DISTINCT CASE
                WHEN year = %(last_year)s AND qty <> 0 THEN item_id
            END) AS sku_last,

            COUNT(DISTINCT CASE
                WHEN year = %(prev_year)s AND qty <> 0 THEN item_id
            END) AS sku_prev,

            COUNT(DISTINCT CASE
                WHEN year = %(last_year)s AND qty <> 0
                     AND item_id NOT IN (
                         SELECT item_id FROM base b2
                         WHERE b2.year = %(prev_year)s AND b2.qty <> 0
                     )
                THEN item_id
            END) AS new_sku,

            COUNT(DISTINCT CASE
                WHEN year = %(prev_year)s AND qty <> 0
                     AND item_id NOT IN (
                         SELECT item_id FROM base b2
                         WHERE b2.year = %(last_year)s AND b2.qty <> 0
                     )
                THEN item_id
            END) AS lost_sku

        FROM base
        GROUP BY manufacturer
        ORDER BY manufacturer
    """

    return fetch_all_dict(q, params)




def get_new_lost_sku_by_manufacturer(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    New / Lost SKU по производителям.

    Логика:
    - определяем два последних года в данных
    - если последний год не закрыт, сравниваем YTD vs YTD
    - SKU считается активным, если qty != 0
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return {
            "rows": [],
            "compare_prev_year": None,
            "compare_last_year": None,
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
        }

    compare_prev_year = years[-2]
    compare_last_year = years[-1]

    params = {
        "start_year": start_year,
        "prev_year": compare_prev_year,
        "last_year": compare_last_year,
    }

    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return {
            "rows": [],
            "compare_prev_year": compare_prev_year,
            "compare_last_year": compare_last_year,
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
        }

    cutoff_year = int(cutoff_date.year)
    cutoff_month = int(cutoff_date.month)
    cutoff_day = int(cutoff_date.day)

    is_ytd_comparison = bool(
        compare_last_year == cutoff_year and (cutoff_month < 12 or cutoff_day < 31)
    )

    params["cutoff_month"] = cutoff_month
    params["cutoff_day"] = cutoff_day

    q = f"""
        WITH item_years AS (
            SELECT
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END AS manufacturer,
                it.id AS item_id,
                YEAR(s.`date`) AS year_num,
                SUM(s.quant_dt - s.quant_cr) AS full_qty,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                        ELSE 0
                    END
                ) AS ytd_qty
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
            WHERE YEAR(s.`date`) IN (%(prev_year)s, %(last_year)s)
            {mf_filter}
            GROUP BY
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END,
                it.id,
                YEAR(s.`date`)
        ),
        flags AS (
            SELECT
                manufacturer,
                item_id,
                MAX(
                    CASE
                        WHEN year_num = %(prev_year)s
                             AND (
                                 CASE WHEN %(last_year)s = %(cutoff_year)s AND (%(cutoff_month)s < 12 OR %(cutoff_day)s < 31)
                                      THEN ytd_qty
                                      ELSE full_qty
                                 END
                             ) <> 0
                        THEN 1 ELSE 0
                    END
                ) AS in_prev,
                MAX(
                    CASE
                        WHEN year_num = %(last_year)s
                             AND (
                                 CASE WHEN %(last_year)s = %(cutoff_year)s AND (%(cutoff_month)s < 12 OR %(cutoff_day)s < 31)
                                      THEN ytd_qty
                                      ELSE full_qty
                                 END
                             ) <> 0
                        THEN 1 ELSE 0
                    END
                ) AS in_last
            FROM item_years
            CROSS JOIN (
                SELECT
                    %(cutoff_year)s AS cutoff_year,
                    %(cutoff_month)s AS cutoff_month,
                    %(cutoff_day)s AS cutoff_day
            ) c
            GROUP BY manufacturer, item_id
        )
        SELECT
            manufacturer,
            SUM(in_prev) AS sku_prev,
            SUM(in_last) AS sku_last,
            SUM(CASE WHEN in_prev = 0 AND in_last = 1 THEN 1 ELSE 0 END) AS new_sku,
            SUM(CASE WHEN in_prev = 1 AND in_last = 0 THEN 1 ELSE 0 END) AS lost_sku
        FROM flags
        GROUP BY manufacturer
        ORDER BY sku_last DESC, manufacturer
    """
    rows = fetch_all_dict(q, {**params, "cutoff_year": cutoff_year})

    return {
        "rows": rows,
        "compare_prev_year": compare_prev_year,
        "compare_last_year": compare_last_year,
        "is_ytd_comparison": is_ytd_comparison,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "cutoff_day": cutoff_day,
    }


def get_new_lost_sku_by_manufacturer_subcategory(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    Детализация New / Lost SKU по производителю и подкатегории.
    """
    years = get_years(start_year=start_year)
    if len(years) < 2:
        return {
            "rows": [],
            "compare_prev_year": None,
            "compare_last_year": None,
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
        }

    compare_prev_year = years[-2]
    compare_last_year = years[-1]

    params = {
        "start_year": start_year,
        "prev_year": compare_prev_year,
        "last_year": compare_last_year,
    }

    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f" AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL) "

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return {
            "rows": [],
            "compare_prev_year": compare_prev_year,
            "compare_last_year": compare_last_year,
            "is_ytd_comparison": False,
            "cutoff_year": None,
            "cutoff_month": None,
            "cutoff_day": None,
        }

    cutoff_year = int(cutoff_date.year)
    cutoff_month = int(cutoff_date.month)
    cutoff_day = int(cutoff_date.day)

    is_ytd_comparison = bool(
        compare_last_year == cutoff_year and (cutoff_month < 12 or cutoff_day < 31)
    )

    params["cutoff_month"] = cutoff_month
    params["cutoff_day"] = cutoff_day

    q = f"""
        WITH item_years AS (
            SELECT
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END AS manufacturer,
                COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
                it.id AS item_id,
                YEAR(s.`date`) AS year_num,
                SUM(s.quant_dt - s.quant_cr) AS full_qty,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                        ELSE 0
                    END
                ) AS ytd_qty
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
            LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
            WHERE YEAR(s.`date`) IN (%(prev_year)s, %(last_year)s)
            {mf_filter}
            GROUP BY
                CASE
                    WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
                    ELSE COALESCE(m.report_name, m.name, '—')
                END,
                COALESCE(sc.name, 'Нет подкатегории'),
                it.id,
                YEAR(s.`date`)
        ),
        flags AS (
            SELECT
                manufacturer,
                subcategory,
                item_id,
                MAX(
                    CASE
                        WHEN year_num = %(prev_year)s
                             AND (
                                 CASE WHEN %(last_year)s = %(cutoff_year)s AND (%(cutoff_month)s < 12 OR %(cutoff_day)s < 31)
                                      THEN ytd_qty
                                      ELSE full_qty
                                 END
                             ) <> 0
                        THEN 1 ELSE 0
                    END
                ) AS in_prev,
                MAX(
                    CASE
                        WHEN year_num = %(last_year)s
                             AND (
                                 CASE WHEN %(last_year)s = %(cutoff_year)s AND (%(cutoff_month)s < 12 OR %(cutoff_day)s < 31)
                                      THEN ytd_qty
                                      ELSE full_qty
                                 END
                             ) <> 0
                        THEN 1 ELSE 0
                    END
                ) AS in_last
            FROM item_years
            CROSS JOIN (
                SELECT
                    %(cutoff_year)s AS cutoff_year,
                    %(cutoff_month)s AS cutoff_month,
                    %(cutoff_day)s AS cutoff_day
            ) c
            GROUP BY manufacturer, subcategory, item_id
        )
        SELECT
            manufacturer,
            subcategory,
            SUM(in_prev) AS sku_prev,
            SUM(in_last) AS sku_last,
            SUM(CASE WHEN in_prev = 0 AND in_last = 1 THEN 1 ELSE 0 END) AS new_sku,
            SUM(CASE WHEN in_prev = 1 AND in_last = 0 THEN 1 ELSE 0 END) AS lost_sku
        FROM flags
        GROUP BY manufacturer, subcategory
        HAVING SUM(in_prev) <> 0 OR SUM(in_last) <> 0
        ORDER BY manufacturer, sku_last DESC, subcategory
    """
    rows = fetch_all_dict(q, {**params, "cutoff_year": cutoff_year})

    return {
        "rows": rows,
        "compare_prev_year": compare_prev_year,
        "compare_last_year": compare_last_year,
        "is_ytd_comparison": is_ytd_comparison,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "cutoff_day": cutoff_day,
    }
    
    
    
    
    
    
    
    
def get_sku_productivity_by_subcategory(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    Эффективность SKU по категории / подкатегории и году.

    Логика SKU должна совпадать с листом
    'Ширина SKU по подкатегориям':
    - full_sku_count: количество SKU с full_qty != 0
    - ytd_sku_count: количество SKU с ytd_qty != 0
    - full_amount
    - ytd_amount
    """

    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f"""
            AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL)
        """

    cutoff_q = """
        SELECT MAX(`date`) AS cutoff_date
        FROM sales_salesdata
        WHERE YEAR(`date`) >= %(start_year)s
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    q = f"""
        SELECT
            x.category,
            x.subcategory,
            x.year,
            COUNT(DISTINCT CASE WHEN x.full_qty <> 0 THEN x.item_id END) AS full_sku_count,
            COUNT(DISTINCT CASE WHEN x.ytd_qty <> 0 THEN x.item_id END) AS ytd_sku_count,
            SUM(x.full_qty) AS full_qty,
            SUM(x.ytd_qty) AS ytd_qty,
            SUM(x.full_amount) AS full_amount,
            SUM(x.ytd_amount) AS ytd_amount,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day
        FROM (
            SELECT
                COALESCE(c.name, 'Без категории') AS category,
                COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
                it.id AS item_id,
                YEAR(s.`date`) AS year,
                SUM(s.quant_dt - s.quant_cr) AS full_qty,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s
                             AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                        ELSE 0
                    END
                ) AS ytd_qty,
                SUM(s.dt - s.cr) AS full_amount,
                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s
                             AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                        ELSE 0
                    END
                ) AS ytd_amount
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_cattree c ON c.id = it.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            {mf_filter}
            GROUP BY
                COALESCE(c.name, 'Без категории'),
                COALESCE(sc.name, 'Нет подкатегории'),
                it.id,
                YEAR(s.`date`)
        ) x
        GROUP BY
            x.category,
            x.subcategory,
            x.year
        ORDER BY
            x.category,
            x.subcategory,
            x.year
    """

    return fetch_all_dict(q, params)





# def get_price_segment_subcategory_yoy(
#     start_year: int = 2022,
#     manufacturer_ids: list[int] | None = None,
# ):
#     """
#     Анализ спроса по автоматическим ценовым диапазонам внутри каждой подкатегории.

#     Логика:
#     1. Считаем SKU-метрики по году:
#        - revenue
#        - qty
#        - avg_price = revenue / qty
#     2. Внутри каждой подкатегории автоматически делим SKU по цене на 3 группы:
#        - Низкий диапазон
#        - Средний диапазон
#        - Высокий диапазон
#     3. Затем агрегируем до уровня:
#        category / subcategory / price_band / year

#     Важно:
#     - "Без продаж" исключен
#     - в сегментацию попадают только SKU с qty > 0
#     """

#     params = {"start_year": start_year}
#     mf_filter = ""

#     if manufacturer_ids:
#         ph = []
#         for i, v in enumerate(manufacturer_ids):
#             k = f"mf{i}"
#             params[k] = int(v)
#             ph.append(f"%({k})s")
#         mf_filter = f"""
#             AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL)
#         """

#     cutoff_q = """
#         SELECT MAX(`date`) AS cutoff_date
#         FROM sales_salesdata
#         WHERE YEAR(`date`) >= %(start_year)s
#     """
#     cutoff_rows = fetch_all_dict(cutoff_q, params)
#     cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

#     if not cutoff_date:
#         return []

#     params["cutoff_year"] = int(cutoff_date.year)
#     params["cutoff_month"] = int(cutoff_date.month)
#     params["cutoff_day"] = int(cutoff_date.day)

#     q = f"""
#         WITH sku_base AS (
#             SELECT
#                 COALESCE(c.name, 'Без категории') AS category,
#                 COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
#                 it.id AS item_id,
#                 YEAR(s.`date`) AS year,

#                 SUM(s.dt - s.cr) AS revenue,
#                 SUM(s.quant_dt - s.quant_cr) AS qty,

#                 SUM(
#                     CASE
#                         WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
#                         WHEN MONTH(s.`date`) = %(cutoff_month)s
#                              AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
#                         ELSE 0
#                     END
#                 ) AS revenue_ytd,

#                 SUM(
#                     CASE
#                         WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
#                         WHEN MONTH(s.`date`) = %(cutoff_month)s
#                              AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
#                         ELSE 0
#                     END
#                 ) AS qty_ytd
#             FROM sales_salesdata s
#             JOIN corporate_items it ON it.id = s.item_id
#             LEFT JOIN corporate_cattree c ON c.id = it.cat_id
#             LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
#             WHERE YEAR(s.`date`) >= %(start_year)s
#             {mf_filter}
#             GROUP BY
#                 COALESCE(c.name, 'Без категории'),
#                 COALESCE(sc.name, 'Нет подкатегории'),
#                 it.id,
#                 YEAR(s.`date`)
#         ),
#         sku_priced AS (
#             SELECT
#                 category,
#                 subcategory,
#                 item_id,
#                 year,
#                 revenue,
#                 qty,
#                 revenue_ytd,
#                 qty_ytd,
#                 CASE
#                     WHEN qty <> 0 THEN revenue / qty
#                     ELSE NULL
#                 END AS avg_price
#             FROM sku_base
#         ),
#         sku_segmented AS (
#             SELECT
#                 category,
#                 subcategory,
#                 item_id,
#                 year,
#                 revenue,
#                 qty,
#                 revenue_ytd,
#                 qty_ytd,
#                 avg_price,
#                 CASE
#                     WHEN NTILE(3) OVER (
#                         PARTITION BY category, subcategory, year
#                         ORDER BY avg_price
#                     ) = 1 THEN 'Низкий диапазон'
#                     WHEN NTILE(3) OVER (
#                         PARTITION BY category, subcategory, year
#                         ORDER BY avg_price
#                     ) = 2 THEN 'Средний диапазон'
#                     ELSE 'Высокий диапазон'
#                 END AS price_band
#             FROM sku_priced
#             WHERE avg_price IS NOT NULL
#         )
#         SELECT
#             category,
#             subcategory,
#             price_band,
#             year,
#             SUM(revenue) AS revenue,
#             SUM(qty) AS qty,
#             SUM(revenue_ytd) AS revenue_ytd,
#             SUM(qty_ytd) AS qty_ytd,
#             MIN(avg_price) AS min_price,
#             MAX(avg_price) AS max_price,
#             %(cutoff_year)s AS cutoff_year,
#             %(cutoff_month)s AS cutoff_month,
#             %(cutoff_day)s AS cutoff_day
#         FROM sku_segmented
#         GROUP BY
#             category,
#             subcategory,
#             price_band,
#             year
#         ORDER BY
#             category,
#             subcategory,
#             FIELD(price_band, 'Низкий диапазон', 'Средний диапазон', 'Высокий диапазон'),
#             year
#     """

#     return fetch_all_dict(q, params)



def get_price_segment_subcategory_yoy(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
):
    """
    Управленческий анализ спроса по фиксированным ценовым сегментам внутри подкатегории.

    Логика:
    - если текущий год неполный -> режим YTD vs YTD
    - если текущий год полный -> режим Full Year vs Full Year

    В итоговую таблицу возвращаются period_revenue / period_qty:
    - в YTD-режиме это YTD
    - в full-year режиме это полный год

    Сегменты low / mid / high фиксируются по тем же period-данным
    последних 2 лет, чтобы сравнение было сопоставимым.
    """

    params = {"start_year": start_year}
    mf_filter = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        mf_filter = f"""
            AND (it.manufacturer_id IN ({', '.join(ph)}) OR it.manufacturer_id IS NULL)
        """

    cutoff_q = f"""
        SELECT MAX(s.`date`) AS cutoff_date
        FROM sales_salesdata s
        JOIN corporate_items it ON it.id = s.item_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
    """
    cutoff_rows = fetch_all_dict(cutoff_q, params)
    cutoff_date = cutoff_rows[0]["cutoff_date"] if cutoff_rows else None

    if not cutoff_date:
        return []

    params["cutoff_year"] = int(cutoff_date.year)
    params["cutoff_month"] = int(cutoff_date.month)
    params["cutoff_day"] = int(cutoff_date.day)

    # Если год не закрыт, весь отчет работает в YTD-режиме
    params["is_partial_year"] = int(
        cutoff_date.month < 12 or cutoff_date.day < 31
    )

    q = f"""
        WITH sku_base AS (
            SELECT
                COALESCE(c.name, 'Без категории') AS category,
                COALESCE(sc.name, 'Нет подкатегории') AS subcategory,
                it.id AS item_id,
                YEAR(s.`date`) AS year,

                SUM(s.dt - s.cr) AS revenue_full,
                SUM(s.quant_dt - s.quant_cr) AS qty_full,

                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.dt - s.cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s
                             AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.dt - s.cr)
                        ELSE 0
                    END
                ) AS revenue_ytd,

                SUM(
                    CASE
                        WHEN MONTH(s.`date`) < %(cutoff_month)s THEN (s.quant_dt - s.quant_cr)
                        WHEN MONTH(s.`date`) = %(cutoff_month)s
                             AND DAY(s.`date`) <= %(cutoff_day)s THEN (s.quant_dt - s.quant_cr)
                        ELSE 0
                    END
                ) AS qty_ytd
            FROM sales_salesdata s
            JOIN corporate_items it ON it.id = s.item_id
            LEFT JOIN corporate_cattree c ON c.id = it.cat_id
            LEFT JOIN corporate_subcategory sc ON sc.id = it.subcat_id
            WHERE YEAR(s.`date`) >= %(start_year)s
            {mf_filter}
            GROUP BY
                COALESCE(c.name, 'Без категории'),
                COALESCE(sc.name, 'Нет подкатегории'),
                it.id,
                YEAR(s.`date`)
        ),

        years_ranked AS (
            SELECT
                year,
                DENSE_RANK() OVER (ORDER BY year DESC) AS year_rank
            FROM (
                SELECT DISTINCT year
                FROM sku_base
            ) y
        ),

        comparison_years AS (
            SELECT year
            FROM years_ranked
            WHERE year_rank <= 2
        ),

        sku_periodized AS (
            SELECT
                sb.category,
                sb.subcategory,
                sb.item_id,
                sb.year,

                CASE
                    WHEN %(is_partial_year)s = 1 THEN sb.revenue_ytd
                    ELSE sb.revenue_full
                END AS period_revenue,

                CASE
                    WHEN %(is_partial_year)s = 1 THEN sb.qty_ytd
                    ELSE sb.qty_full
                END AS period_qty
            FROM sku_base sb
            JOIN comparison_years cy
              ON cy.year = sb.year
        ),

        sku_reference AS (
            SELECT
                sp.category,
                sp.subcategory,
                sp.item_id,
                CASE
                    WHEN SUM(sp.period_qty) <> 0 THEN SUM(sp.period_revenue) / SUM(sp.period_qty)
                    ELSE NULL
                END AS ref_price
            FROM sku_periodized sp
            GROUP BY
                sp.category,
                sp.subcategory,
                sp.item_id
        ),

        sku_reference_ranked AS (
            SELECT
                category,
                subcategory,
                item_id,
                ref_price,
                NTILE(3) OVER (
                    PARTITION BY category, subcategory
                    ORDER BY ref_price
                ) AS ref_tile
            FROM sku_reference
            WHERE ref_price IS NOT NULL
              AND ref_price > 0
        ),

        sku_reference_labeled AS (
            SELECT
                category,
                subcategory,
                item_id,
                ref_price,
                CASE
                    WHEN ref_tile = 1 THEN 'Низкий диапазон'
                    WHEN ref_tile = 2 THEN 'Средний диапазон'
                    ELSE 'Высокий диапазон'
                END AS price_band,
                MIN(ref_price) OVER (
                    PARTITION BY category, subcategory, ref_tile
                ) AS segment_low_bound,
                MAX(ref_price) OVER (
                    PARTITION BY category, subcategory, ref_tile
                ) AS segment_high_bound
            FROM sku_reference_ranked
        ),

        sku_segmented AS (
            SELECT
                sp.category,
                sp.subcategory,
                srl.price_band,
                sp.item_id,
                sp.year,
                sp.period_revenue,
                sp.period_qty,
                srl.segment_low_bound,
                srl.segment_high_bound
            FROM sku_periodized sp
            JOIN sku_reference_labeled srl
              ON srl.category = sp.category
             AND srl.subcategory = sp.subcategory
             AND srl.item_id = sp.item_id
        )

        SELECT
            category,
            subcategory,
            price_band,
            year,
            SUM(period_revenue) AS period_revenue,
            SUM(period_qty) AS period_qty,
            MIN(segment_low_bound) AS segment_low_bound,
            MAX(segment_high_bound) AS segment_high_bound,
            %(cutoff_year)s AS cutoff_year,
            %(cutoff_month)s AS cutoff_month,
            %(cutoff_day)s AS cutoff_day,
            %(is_partial_year)s AS is_partial_year
        FROM sku_segmented
        GROUP BY
            category,
            subcategory,
            price_band,
            year
        ORDER BY
            category,
            subcategory,
            FIELD(price_band, 'Низкий диапазон', 'Средний диапазон', 'Высокий диапазон'),
            year
    """

    return fetch_all_dict(q, params)