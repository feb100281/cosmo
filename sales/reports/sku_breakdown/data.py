# sales/reports/sku_breakdown/data.py
"""
Слой данных для отчёта "Разбивка по номенклатуре и штрихкодам" (SKU breakdown).

Берёт продажи из sales_salesdata за произвольный период [start, end]
(включительно с обеих сторон) и агрегирует их до уровня "номенклатура +
штрихкод", подтягивая категорию/подкатегорию и производителя из
справочников corporate_* — теми же таблицами и полями, что уже использует
sales_report/categories_data.py (corporate_cattree/corporate_subcategory)
и sales_report/kpi/manufacturers_period_data.py (corporate_itemmanufacturer),
плюс corporate_barcode, как в dash_apps/orders/data.py.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from django.db import connection

NO_CATEGORY = "Без категории"
NO_SUBCATEGORY = "Без подкатегории"
NO_MANUFACTURER = "Производитель не указан"
NO_BARCODE = "Без штрихкода"
NO_ARTICLE = "Без артикула"
NO_NAME = "—"

_METRIC_COLS = ("sales_amount", "sales_qty", "returns_amount", "returns_qty")


def get_sku_barcode_breakdown(start: date, end: date) -> pd.DataFrame:
    """
    Возвращает DataFrame — одна строка на уникальную комбинацию
    (номенклатура, штрихкод, категория/подкатегория, производитель) за
    период [start, end] включительно, со столбцами:

        cat_name, subcat_name, manufacturer_name, article, fullname, barcode,
        sales_amount, sales_qty, returns_amount, returns_qty,
        net_amount, net_qty

    Строки, по которым за период не было ни продаж, ни возвратов,
    отбрасываются.
    """
    q = """
        SELECT
            i.id AS item_id,
            COALESCE(i.article, %(no_article)s) AS article,
            COALESCE(i.fullname, %(no_name)s) AS fullname,
            b.id AS barcode_id,
            COALESCE(b.barcode, %(no_barcode)s) AS barcode,
            i.cat_id AS cat_id,
            COALESCE(cat.name, %(no_category)s) AS cat_name,
            i.subcat_id AS subcat_id,
            COALESCE(sc.name, %(no_subcategory)s) AS subcat_name,
            i.manufacturer_id AS manufacturer_id,
            COALESCE(m.report_name, m.name, %(no_manufacturer)s) AS manufacturer_name,
            SUM(s.dt) AS sales_amount,
            SUM(s.quant_dt) AS sales_qty,
            SUM(s.cr) AS returns_amount,
            SUM(s.quant_cr) AS returns_qty
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        LEFT JOIN corporate_barcode b ON b.id = s.barcode_id
        LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
        LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = i.manufacturer_id
        WHERE s.`date` BETWEEN %(start)s AND %(end)s
        GROUP BY
            i.id, article, fullname,
            b.id, barcode,
            i.cat_id, cat_name,
            i.subcat_id, subcat_name,
            i.manufacturer_id, manufacturer_name
        ORDER BY cat_name, subcat_name, fullname, barcode
    """

    params = {
        "start": start,
        "end": end,
        "no_article": NO_ARTICLE,
        "no_name": NO_NAME,
        "no_barcode": NO_BARCODE,
        "no_category": NO_CATEGORY,
        "no_subcategory": NO_SUBCATEGORY,
        "no_manufacturer": NO_MANUFACTURER,
    }

    with connection.cursor() as cur:
        cur.execute(q, params)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    for col in _METRIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["net_amount"] = df["sales_amount"] - df["returns_amount"]
    df["net_qty"] = df["sales_qty"] - df["returns_qty"]

    # убираем строки, по которым за период вообще ничего не произошло
    # (SUM по LEFT JOIN может дать формально нулевую комбинацию)
    mask = (
        (df["sales_amount"] != 0)
        | (df["sales_qty"] != 0)
        | (df["returns_amount"] != 0)
        | (df["returns_qty"] != 0)
    )
    df = df[mask].reset_index(drop=True)

    return df
