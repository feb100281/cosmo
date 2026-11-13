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
NO_STORE = "Без подразделения"

_METRIC_COLS = ("sales_amount", "sales_qty", "returns_amount", "returns_qty")


def _fetch(q: str, params) -> pd.DataFrame:
    with connection.cursor() as cur:
        cur.execute(q, params)
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def _names(table: str, ids, name_sql: str = "name") -> dict:
    ids = sorted({int(i) for i in ids if i is not None and i == i})
    if not ids:
        return {}
    marks = ", ".join(["%s"] * len(ids))
    df = _fetch(f"SELECT id, {name_sql} AS name FROM {table} WHERE id IN ({marks})", ids)
    return dict(zip(df["id"], df["name"]))


def get_sku_barcode_breakdown(start: date, end: date, by_store: bool = False) -> pd.DataFrame:
    """
    Продажи за [start, end] на уровне «номенклатура + штрихкод» (by_store=True — ещё и подразделение).
    Сначала агрегируем по id (быстро), затем подставляем названия из справочников.
    Колонки: [store_name], item_id, article, fullname, barcode, cat_name, subcat_name, manufacturer_name,
    sales_amount, sales_qty, returns_amount, returns_qty, net_amount, net_qty.
    """
    store = ", s.store_id" if by_store else ""
    df = _fetch(
        f"""
        SELECT s.item_id, s.barcode_id{store},
               SUM(s.dt) AS sales_amount, SUM(s.quant_dt) AS sales_qty,
               SUM(s.cr) AS returns_amount, SUM(s.quant_cr) AS returns_qty
        FROM sales_salesdata s
        WHERE s.`date` BETWEEN %s AND %s AND s.item_id IS NOT NULL
        GROUP BY s.item_id, s.barcode_id{store}
        """,
        [start, end],
    )
    if df.empty:
        return df
    for col in _METRIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df[(df[list(_METRIC_COLS)] != 0).any(axis=1)].reset_index(drop=True)
    if df.empty:
        return df

    ids = sorted({int(i) for i in df["item_id"]})
    marks = ", ".join(["%s"] * len(ids))
    items = _fetch(
        f"SELECT id AS item_id, article, fullname, cat_id, subcat_id, manufacturer_id "
        f"FROM corporate_items WHERE id IN ({marks})",
        ids,
    )
    df = df.merge(items, on="item_id", how="left")
    cats = _names("corporate_cattree", df["cat_id"])
    subcats = _names("corporate_subcategory", df["subcat_id"])
    manus = _names("corporate_itemmanufacturer", df["manufacturer_id"], "COALESCE(report_name, name)")
    barcodes = _names("corporate_barcode", df["barcode_id"], "barcode")

    df["article"] = df["article"].fillna(NO_ARTICLE)
    df["fullname"] = df["fullname"].fillna(NO_NAME)
    df["barcode"] = df["barcode_id"].map(barcodes).fillna(NO_BARCODE)
    df["cat_name"] = df["cat_id"].map(cats).fillna(NO_CATEGORY)
    df["subcat_name"] = df["subcat_id"].map(subcats).fillna(NO_SUBCATEGORY)
    df["manufacturer_name"] = df["manufacturer_id"].map(manus).fillna(NO_MANUFACTURER)
    if by_store:
        stores = _names("corporate_stores", df["store_id"])
        df["store_name"] = df["store_id"].map(stores).fillna(NO_STORE)

    df["net_amount"] = df["sales_amount"] - df["returns_amount"]
    df["net_qty"] = df["sales_qty"] - df["returns_qty"]
    keep = (["store_name"] if by_store else []) + [
        "item_id", "article", "fullname", "barcode", "cat_name", "subcat_name", "manufacturer_name",
        *_METRIC_COLS, "net_amount", "net_qty"]
    return df[keep]


def without_store(df: pd.DataFrame) -> pd.DataFrame:
    """Сворачивает разбивку по подразделениям до уровня «номенклатура + штрихкод»."""
    if df.empty or "store_name" not in df.columns:
        return df.drop(columns=["store_name"], errors="ignore")
    keys = [c for c in df.columns if c not in _METRIC_COLS + ("net_amount", "net_qty", "store_name")]
    out = df.groupby(keys, dropna=False, as_index=False)[list(_METRIC_COLS)].sum()
    out["net_amount"] = out["sales_amount"] - out["returns_amount"]
    out["net_qty"] = out["sales_qty"] - out["returns_qty"]
    return out
