# sales/reports/newspaper/data/turnover.py
"""
Оборачиваемость остатков для газеты.

Неликвид        — есть доступный остаток, нет продаж за окно и последний приход
                  старше TURNOVER_NEW_RECEIPT_DAYS (или приходов нет).
Очень медленные — остатка больше чем на TURNOVER_VERY_SLOW_DAYS при текущем темпе.
Заморожено      — доля доступного остатка в неликвиде и очень медленных.
Суммы по закупке — остаток × цена последнего прихода без НДС (если цена загружена).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import connection

from ..config import (
    TURNOVER_NEW_RECEIPT_DAYS,
    TURNOVER_TOP_N,
    TURNOVER_VERY_SLOW_DAYS,
    TURNOVER_WINDOW_DAYS,
)

STATUS_DEAD = "Неликвид"
STATUS_VERY_SLOW = "Очень медленный"


def _fetch(sql: str, params=None) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _latest_stocks() -> list[dict]:
    return _fetch("""
        WITH ranked AS (
            SELECT item_id, tot_available,
                   ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY init_date DESC) AS rn
            FROM stocks_data
        )
        SELECT r.item_id, r.tot_available,
               i.fullname, i.article,
               COALESCE(cat.name, 'Без категории') AS cat_name
        FROM ranked r
        LEFT JOIN corporate_items i ON i.id = r.item_id
        LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
        WHERE r.rn = 1 AND r.tot_available > 0
    """)


def _sales(date_from, date_to) -> dict:
    rows = _fetch("""
        SELECT item_id, SUM(quant_dt - quant_cr) AS sold
        FROM sales_salesdata
        WHERE date BETWEEN %s AND %s AND item_id IS NOT NULL
        GROUP BY item_id
    """, [date_from, date_to])
    return {r["item_id"]: float(r["sold"] or 0) for r in rows}


def _receipts(report_date) -> dict:
    """item_id -> (дата последнего прихода, цена последнего прихода без НДС)."""
    try:
        rows = _fetch("""
            WITH r AS (
                SELECT item_id, receipt_date, price_purchase,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY receipt_date DESC) AS rn
                FROM stock_receipts
                WHERE item_id IS NOT NULL AND receipt_date <= %s
            ),
            p AS (
                SELECT item_id, price_purchase,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY receipt_date DESC) AS rn
                FROM stock_receipts
                WHERE item_id IS NOT NULL AND receipt_date <= %s AND price_purchase > 0
            )
            SELECT r.item_id, r.receipt_date, p.price_purchase
            FROM r LEFT JOIN p ON p.item_id = r.item_id AND p.rn = 1
            WHERE r.rn = 1
        """, [report_date, report_date])
    except Exception:
        return {}
    return {r["item_id"]: (r["receipt_date"], r["price_purchase"]) for r in rows}


def get_turnover_data(report_date) -> dict:
    date_from = report_date - timedelta(days=TURNOVER_WINDOW_DAYS - 1)
    stocks = _latest_stocks()
    sales = _sales(date_from, report_date)
    receipts = _receipts(report_date)

    total_units = 0.0
    total_daily = 0.0
    dead_units = slow_units = 0.0
    dead_sku = slow_sku = 0
    total_value = frozen_value = Decimal("0")
    has_price = False
    problem = []

    for row in stocks:
        qty = float(row["tot_available"] or 0)
        sold = max(sales.get(row["item_id"], 0.0), 0.0)
        daily = sold / TURNOVER_WINDOW_DAYS
        last_date, price = receipts.get(row["item_id"], (None, None))
        days_since = (report_date - last_date).days if last_date else None

        total_units += qty
        total_daily += daily

        value = None
        if price:
            has_price = True
            value = Decimal(str(price)) * Decimal(str(qty))
            total_value += value

        status = None
        turnover_days = qty / daily if daily > 0 else None
        if sold <= 0:
            if days_since is None or days_since > TURNOVER_NEW_RECEIPT_DAYS:
                status = STATUS_DEAD
                dead_units += qty
                dead_sku += 1
        elif turnover_days and turnover_days > TURNOVER_VERY_SLOW_DAYS:
            status = STATUS_VERY_SLOW
            slow_units += qty
            slow_sku += 1

        if status:
            if value is not None:
                frozen_value += value
            problem.append({
                "name": row["fullname"] or f"item {row['item_id']}",
                "article": row["article"] or "",
                "cat_name": row["cat_name"],
                "qty": qty,
                "status": status,
                "turnover_days": turnover_days,
                "days_since_receipt": days_since,
                "value": value,
            })

    problem.sort(key=lambda r: r["qty"], reverse=True)
    frozen_units = dead_units + slow_units

    return {
        "window_days": TURNOVER_WINDOW_DAYS,
        "date_from": date_from,
        "total_units": total_units,
        "company_turnover_days": (total_units / total_daily) if total_daily > 0 else None,
        "dead_units": dead_units,
        "dead_sku": dead_sku,
        "dead_share": dead_units / total_units if total_units else 0.0,
        "slow_units": slow_units,
        "slow_sku": slow_sku,
        "frozen_units": frozen_units,
        "frozen_share": frozen_units / total_units if total_units else 0.0,
        "has_price": has_price,
        "total_value": total_value if has_price else None,
        "frozen_value": frozen_value if has_price else None,
        "top": problem[:TURNOVER_TOP_N],
        "has_receipts": bool(receipts),
    }
