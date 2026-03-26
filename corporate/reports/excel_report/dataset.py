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


# def get_manufacturer_category_dependence(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
#     """
#     Для каждого производителя:
#     - общая выручка
#     - крупнейшая категория
#     - выручка крупнейшей категории
#     - доля крупнейшей категории в выручке производителя
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

#     q = f"""
#         SELECT
#             z.manufacturer,
#             z.category,
#             z.cat_revenue,
#             z.total_revenue,
#             CASE
#                 WHEN z.total_revenue = 0 OR z.total_revenue IS NULL THEN 0
#                 ELSE z.cat_revenue / z.total_revenue
#             END AS dependence_share
#         FROM (
#             SELECT
#                 x.manufacturer,
#                 x.category,
#                 x.cat_revenue,
#                 y.total_revenue,
#                 ROW_NUMBER() OVER (
#                     PARTITION BY x.manufacturer
#                     ORDER BY x.cat_revenue DESC, x.category
#                 ) AS rn
#             FROM (
#                 SELECT
#                     CASE
#                         WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
#                         ELSE COALESCE(m.report_name, m.name, '—')
#                     END AS manufacturer,
#                     COALESCE(c.name, '—') AS category,
#                     SUM(s.dt - s.cr) AS cat_revenue
#                 FROM sales_salesdata s
#                 JOIN corporate_items it ON it.id = s.item_id
#                 LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
#                 LEFT JOIN corporate_cattree c ON c.id = it.cat_id
#                 WHERE YEAR(s.`date`) >= %(start_year)s
#                 {mf_filter}
#                 GROUP BY manufacturer, category
#             ) x
#             JOIN (
#                 SELECT
#                     CASE
#                         WHEN it.manufacturer_id IS NULL THEN '!Производитель не указан'
#                         ELSE COALESCE(m.report_name, m.name, '—')
#                     END AS manufacturer,
#                     SUM(s.dt - s.cr) AS total_revenue
#                 FROM sales_salesdata s
#                 JOIN corporate_items it ON it.id = s.item_id
#                 LEFT JOIN corporate_itemmanufacturer m ON m.id = it.manufacturer_id
#                 WHERE YEAR(s.`date`) >= %(start_year)s
#                 {mf_filter}
#                 GROUP BY manufacturer
#             ) y ON y.manufacturer = x.manufacturer
#         ) z
#         WHERE z.rn = 1
#         ORDER BY
#             CASE
#                 WHEN z.total_revenue = 0 OR z.total_revenue IS NULL THEN 0
#                 ELSE z.cat_revenue / z.total_revenue
#             END DESC,
#             z.total_revenue DESC
#     """
#     return fetch_all_dict(q, params)




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
    
    
    
    
def get_categories_yoy_yearly(start_year: int = 2022, manufacturer_ids: list[int] | None = None):
    """
    Данные для листа Categories с поддержкой YTD для последнего незакрытого года.

    Возвращает по каждой категории и году:
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
        LEFT JOIN corporate_cattree c ON c.id = it.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
        {mf_filter}
        GROUP BY COALESCE(c.name, '—'), YEAR(s.`date`)
        ORDER BY category, year
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