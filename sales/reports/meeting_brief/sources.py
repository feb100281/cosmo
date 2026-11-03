# sales/reports/meeting_brief/sources.py
"""Выборка исходных данных из БД. Только чтение, без расчётов."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from django.db import connection

from . import config as C
from .periods import Periods


def _df(sql: str, params=None, columns=None) -> pd.DataFrame:
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        df = pd.DataFrame(list(cur.fetchall()), columns=cols)
    if columns:
        for c in columns:
            if c not in df.columns:
                df[c] = None
    return df


def _table_exists(name: str) -> bool:
    with connection.cursor() as cur:
        cur.execute("SHOW TABLES LIKE %s", [name])
        return cur.fetchone() is not None


def _num(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype(float)
    return df


def load_cash(d1: date, d2: date) -> pd.DataFrame:
    """Поступления и возвраты денег по дням, подразделениям и заказам."""
    df = _df(
        """
        SELECT date, LOWER(TRIM(COALESCE(store, ''))) AS store, order_guid,
               SUM(CASE WHEN oper_type = %s OR register LIKE %s THEN amount ELSE 0 END) AS cash_in,
               SUM(CASE WHEN oper_type = %s OR register LIKE %s THEN ABS(amount) ELSE 0 END) AS cash_ret
        FROM orders_orderscf
        WHERE date BETWEEN %s AND %s
        GROUP BY date, LOWER(TRIM(COALESCE(store, ''))), order_guid
        """,
        [C.CF_IN_TYPE, C.CF_IN_REGISTER, C.CF_RET_TYPE, C.CF_RET_REGISTER, d1, d2],
    )
    df = _num(df, ["cash_in", "cash_ret"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def load_plans(d1: date, d2: date) -> pd.DataFrame:
    from sales.models import StoreSalesPlan

    # План хранится по месяцу; день в дате может быть любым
    m1 = d1.replace(day=1)
    m_next = (d2.replace(day=1) + timedelta(days=32)).replace(day=1)
    rows = (StoreSalesPlan.objects
            .filter(plan_month__gte=m1, plan_month__lt=m_next)
            .select_related("store", "store__gr"))
    df = pd.DataFrame([{
        "plan_month": p.plan_month.replace(day=1),
        "store": str(p.store).strip().lower(),
        "store_name": str(p.store).strip(),
        "group": str(p.store.gr) if getattr(p.store, "gr", None) else "",
        "amount": float(p.amount or 0),
    } for p in rows], columns=["plan_month", "store", "store_name", "group", "amount"])
    return df


def load_item_sales(d1: date, d2: date) -> pd.DataFrame:
    df = _df(
        """
        SELECT item_id, SUM(dt) AS dt, SUM(cr) AS cr,
               SUM(quant_dt) AS qty, SUM(quant_cr) AS qty_ret
        FROM sales_salesdata
        WHERE date BETWEEN %s AND %s AND item_id IS NOT NULL
        GROUP BY item_id
        """,
        [d1, d2],
    )
    return _num(df, ["dt", "cr", "qty", "qty_ret"])


def load_items() -> pd.DataFrame:
    return _df(
        """
        SELECT i.id AS item_id, i.fullname, i.article, i.init_date,
               COALESCE(r.name, c.name) AS root, c.name AS cat, sc.name AS subcat,
               b.name AS brand, m.name AS manu
        FROM corporate_items i
        LEFT JOIN corporate_cattree c ON c.id = i.cat_id
        LEFT JOIN corporate_cattree r ON r.tree_id = c.tree_id AND r.level = 0
        LEFT JOIN corporate_subcategory sc ON sc.id = i.subcat_id
        LEFT JOIN corporate_itembrend b ON b.id = i.brend_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = i.manufacturer_id
        """
    )


ORDER_COLS = ("order_id, number, date_from, update_at, status, change_status, client, manager, store, "
              "order_amount, amount_delivery, amount_active, cash_pmts, total_shiped_amount")
ORDER_NUM = ["order_amount", "amount_delivery", "amount_active", "cash_pmts", "total_shiped_amount"]


def load_orders() -> pd.DataFrame:
    """Все заказы витрины (отменённые нужны для статистики отмен)."""
    df = _df(f"SELECT {ORDER_COLS} FROM mv_orders_summary_table")
    df = _num(df, ORDER_NUM)
    for c in ("date_from", "update_at"):
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    df["cancelled"] = (df["status"].eq(C.ST_CANCELLED) | df["change_status"].eq(C.ST_CANCELLED))

    df["cash_pmts"] = df["order_id"].astype(str).map(load_paid()).fillna(0.0).astype(float)
    return df


def load_paid(d2: date | None = None) -> dict:
    """Оплаты клиента по GUID заказа (без дизайнерского вознаграждения), по дату d2 включительно."""
    sql = """
        SELECT order_guid, SUM(amount) AS paid
        FROM orders_orderscf
        WHERE order_guid IS NOT NULL AND order_guid <> ''
          AND COALESCE(oper_type, '') NOT LIKE %s
    """
    params = [C.CF_DESIGNER_LIKE]
    if d2 is not None:
        sql += " AND date <= %s"
        params.append(d2)
    pay = _df(sql + " GROUP BY order_guid", params)
    return dict(zip(pay["order_guid"].astype(str), pd.to_numeric(pay["paid"], errors="coerce").fillna(0.0)))


def load_shipped(d2: date) -> dict:
    """Реализация по GUID заказа (отгрузки минус возвраты) по дату d2 включительно."""
    df = _df(
        """
        SELECT order_guid, SUM(dt - cr) AS shipped
        FROM sales_salesdata
        WHERE order_guid IS NOT NULL AND order_guid <> '' AND date <= %s
        GROUP BY order_guid
        """,
        [d2],
    )
    return dict(zip(df["order_guid"].astype(str), pd.to_numeric(df["shipped"], errors="coerce").fillna(0.0)))


def load_managers() -> dict:
    df = _df("SELECT name, report_name FROM corporate_managers")
    return {str(r.name).strip(): str(r.report_name or r.name).strip() for r in df.itertuples()}


def load_stocks() -> pd.DataFrame:
    if not _table_exists("stocks_data"):
        return pd.DataFrame(columns=["item_id", "available", "ordered", "stock_date"])
    df = _df(
        """
        SELECT item_id, SUM(tot_available) AS available, SUM(tot_ordered) AS ordered,
               MAX(init_date) AS stock_date
        FROM stocks_data
        WHERE item_id IS NOT NULL
        GROUP BY item_id
        """
    )
    return _num(df, ["available", "ordered"])


def load_sales_history(d2: date) -> pd.DataFrame:
    """По каждому товару: последняя продажа, продажи за 90 дней, средняя цена за год."""
    d90 = d2 - timedelta(days=C.STALE_NO_SALES_DAYS)
    d365 = d2 - timedelta(days=365)
    df = _df(
        """
        SELECT item_id,
               MAX(CASE WHEN quant_dt > 0 THEN date END) AS last_sale,
               SUM(CASE WHEN date > %s THEN quant_dt - quant_cr ELSE 0 END) AS qty_90,
               SUM(CASE WHEN date > %s THEN dt ELSE 0 END) AS dt_365,
               SUM(CASE WHEN date > %s THEN quant_dt ELSE 0 END) AS qty_365,
               SUM(dt) AS dt_all, SUM(quant_dt) AS qty_all
        FROM sales_salesdata
        WHERE date <= %s AND item_id IS NOT NULL
        GROUP BY item_id
        """,
        [d90, d365, d365, d2],
    )
    df = _num(df, ["qty_90", "dt_365", "qty_365", "dt_all", "qty_all"])
    df["last_sale"] = pd.to_datetime(df["last_sale"], errors="coerce").dt.date
    return df


def load_receipts() -> pd.DataFrame:
    if not _table_exists("stock_receipts"):
        return pd.DataFrame(columns=["item_id", "first_receipt", "last_receipt"])
    df = _df(
        """
        SELECT item_id, MIN(receipt_date) AS first_receipt, MAX(receipt_date) AS last_receipt
        FROM stock_receipts
        WHERE item_id IS NOT NULL AND qty > 0
        GROUP BY item_id
        """
    )
    for c in ("first_receipt", "last_receipt"):
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df


def norm_client(v) -> str:
    return " ".join(str(v or "").split()).casefold()


def load_exclusions() -> dict:
    """Клиенты и заказы, которые не считаются долгом (справочник в админке)."""
    out = {"clients": {}, "orders": {}, "commission": set(), "ok": True}
    try:
        from orders.models import DebtExclusion

        for x in DebtExclusion.objects.filter(is_active=True):
            label = x.get_reason_display() + (f": {x.comment}" if x.comment else "")
            if x.kind == DebtExclusion.KIND_CLIENT:
                out["clients"][norm_client(x.value)] = label
                if x.reason == "commission":
                    out["commission"].add(norm_client(x.value))
            else:
                out["orders"][x.value.strip().casefold()] = label
    except Exception:
        out["ok"] = False  # таблица ещё не создана: python manage.py migrate
    return out


def load_all(p: Periods) -> dict:
    return {
        "exclusions": load_exclusions(),
        "cash": load_cash(min(p.prev_start, p.month_start), p.end),
        "cash_ly": load_cash(p.ly_start, p.ly_end),
        "plans": load_plans(min(p.start, p.month_start), p.end),
        "sales": load_item_sales(p.start, p.end),
        "sales_prev": load_item_sales(p.prev_start, p.prev_end),
        "sales_ly": load_item_sales(p.ly_start, p.ly_end),
        "items": load_items(),
        "orders": load_orders(),
        "paid_end": load_paid(p.end),
        "shipped_end": load_shipped(p.end),
        "managers": load_managers(),
        "stocks": load_stocks(),
        "history": load_sales_history(p.end),
        "receipts": load_receipts(),
    }
