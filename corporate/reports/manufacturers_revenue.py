# corporate/reports/manufacturers_revenue.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from django.db import connection


def get_manufacturers_net_by_year(
    start_year: int = 2022,
    ids: list[int] | None = None,
) -> tuple[list[int], list[dict[str, Any]], dict[str, Any]]:
    ids = ids or []

    params: dict[str, object] = {"start_year": int(start_year)}
    where_ids = ""

    # Если ids заданы — фильтруем по этим производителям
    # (строку "Производитель не указан" при этом НЕ показываем — логично для выбора)
    if ids:
        ph: list[str] = []
        for i, v in enumerate(ids):
            key = f"id{i}"
            params[key] = int(v)
            ph.append(f"%({key})s")
        where_ids = f" AND (i.manufacturer_id IN ({', '.join(ph)}) OR i.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            CASE
                WHEN i.manufacturer_id IS NULL THEN 0
                ELSE i.manufacturer_id
            END AS manufacturer_id,
            CASE
                WHEN i.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer_name,
            YEAR(s.`date`) AS `year`,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = i.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
          {where_ids}
        GROUP BY manufacturer_id, manufacturer_name, YEAR(s.`date`)
        ORDER BY manufacturer_name, `year`
    """

    with connection.cursor() as cur:
        cur.execute(q, params)
        data = cur.fetchall()
        cols = [c[0] for c in cur.description]

    idx = {name: i for i, name in enumerate(cols)}

    years_set: set[int] = set()
    tmp: dict[int, dict[str, Any]] = {}

    def to_decimal(x: Any) -> Decimal:
        if x is None:
            return Decimal("0")
        if isinstance(x, Decimal):
            return x
        try:
            return Decimal(str(x))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    def quant0(v: Decimal) -> Decimal:
        return v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def fmt_money_ru(v: Decimal) -> str:
        """
        Формат:
        12,3 млн ₽
        450 тыс ₽
        12 345 ₽

        Без копеек.
        Между числом, единицей и ₽ — неразрывный пробел.
        """
        vq = quant0(v)
        a = abs(vq)
        nbsp = "\u00A0"

        if a >= Decimal("1000000"):
            s = (vq / Decimal("1000000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            txt = f"{s}".replace(".", ",")
            return f"{txt}{nbsp}млн{nbsp}₽"

        if a >= Decimal("1000"):
            s = (vq / Decimal("1000")).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP)
            txt = f"{int(s):,}".replace(",", " ")
            return f"{txt}{nbsp}тыс{nbsp}₽"

        txt = f"{int(vq):,}".replace(",", " ")
        return f"{txt}{nbsp}₽"

    # --- сбор сырых данных ---
    for row in data:
        mf_id = int(row[idx["manufacturer_id"]])
        name = (row[idx["manufacturer_name"]] or "—").strip() or "—"
        y = int(row[idx["year"]])
        net = to_decimal(row[idx["net_amount"]])

        years_set.add(y)

        payload = tmp.get(mf_id)
        if payload is None:
            payload = {
                "manufacturer_id": mf_id,
                "name": name,
                "by_year": {},              # year -> Decimal
                "total": Decimal("0"),      # Decimal
            }
            tmp[mf_id] = payload

        payload["by_year"][y] = net
        payload["total"] = payload["total"] + net

    years = sorted([y for y in years_set if y >= start_year])
    rows = sorted(tmp.values(), key=lambda r: (r["name"] or "").lower())

    # --- подготовка для шаблона ---
    for r in rows:
        by_year: dict[int, Decimal] = r.get("by_year", {})

        vals = [to_decimal(by_year.get(y)) for y in years]
        r["values"] = vals  # если где-то ещё используется

        positives = [v for v in vals if v > 0]
        vmin = min(positives) if positives else Decimal("0")
        vmax = max(positives) if positives else Decimal("0")
        den = (vmax - vmin) if vmax > vmin else Decimal("0")

        cells: list[dict[str, Any]] = []
        for v in vals:
            if v <= 0 or den == 0:
                k = 0.0
            else:
                k = float((v - vmin) / den)  # 0..1
            cells.append({"v": v, "k": k, "disp": fmt_money_ru(v)})
        r["cells"] = cells


        # --- статусы (3 категории) ---
        last = vals[-1] if vals else Decimal("0")
        prev = vals[-2] if len(vals) >= 2 else Decimal("0")
        prev2 = vals[-3] if len(vals) >= 3 else Decimal("0")

        had_before = any(v > 0 for v in vals[:-2]) if len(vals) >= 2 else any(v > 0 for v in vals[:-1])

        if last > 0:
            status = "active"
        elif prev > 0 and last == 0:
            status = "pause"
        elif last == 0 and prev == 0 and (prev2 > 0 or had_before):
            status = "stopped"
        else:
            status = "stopped"

        r["status"] = status
        r["last"] = last
        r["prev"] = prev
        r["total_disp"] = fmt_money_ru(r["total"])

    # --- totals (строка Итого) ---
    totals_by_year: dict[int, Decimal] = {y: Decimal("0") for y in years}
    grand_total = Decimal("0")

    for r in rows:
        by_year = r.get("by_year", {})
        for y in years:
            v = to_decimal(by_year.get(y))
            totals_by_year[y] = totals_by_year[y] + v
            grand_total = grand_total + v

    revenue_totals = {
        "cells": [{"disp": fmt_money_ru(totals_by_year[y])} for y in years],
        "total_disp": fmt_money_ru(grand_total),
    }

    return years, rows, revenue_totals


