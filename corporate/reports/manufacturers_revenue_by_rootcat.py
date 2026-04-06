from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from django.db import connection


def _to_dec(x: Any) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def fmt_money_ru(v: Decimal) -> str:
    vq = v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    a = abs(vq)
    nbsp = "\u00A0"

    if a >= Decimal("1000000"):
        s = (vq / Decimal("1000000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{str(s).replace('.', ',')}{nbsp}млн{nbsp}₽"

    if a >= Decimal("1000"):
        s = (vq / Decimal("1000")).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP)
        txt = f"{int(s):,}".replace(",", " ")
        return f"{txt}{nbsp}тыс{nbsp}₽"

    txt = f"{int(vq):,}".replace(",", " ")
    return f"{txt}{nbsp}₽"


def get_manufacturer_net_by_rootcat_total(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
) -> dict[int, dict[str, Any]]:
    """
    root_id -> {
      "root_name": str,
      "root_icon": str,
      "by_mf": { mf_name: {"net": Decimal, "disp": str} }
    }

    Корень определяется как r.parent_id IS NULL (nested set), как у тебя в рабочем отчёте.
    Фильтр: r.id <> 0.
    """
    manufacturer_ids = manufacturer_ids or []
    params: dict[str, object] = {"start_year": int(start_year)}
    where_mf = ""

    if manufacturer_ids:
        ph: list[str] = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        where_mf = f" AND (i.manufacturer_id IN ({', '.join(ph)}) OR i.manufacturer_id IS NULL) "

    q = f"""
        SELECT
            r.id AS root_id,
            COALESCE(r.name, '—') AS root_name,
            COALESCE(r.icon, '') AS root_icon,
            COALESCE(i.manufacturer_id, 0) AS manufacturer_id,
            CASE
                WHEN i.manufacturer_id IS NULL THEN '!Производитель не указан'
                ELSE COALESCE(m.report_name, m.name, '—')
            END AS manufacturer_name,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        JOIN corporate_cattree c ON c.id = i.cat_id
        JOIN corporate_cattree r
          ON r.parent_id IS NULL
         AND r.tree_id = c.tree_id
         AND c.lft >= r.lft
         AND c.rght <= r.rght
        LEFT JOIN corporate_itemmanufacturer m ON m.id = i.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
          AND r.id <> 0
          {where_mf}
        GROUP BY r.id, r.name, r.icon, manufacturer_id, manufacturer_name
        ORDER BY root_name, manufacturer_name
    """

    with connection.cursor() as cur:
        cur.execute(q, params)
        data = cur.fetchall()
        cols = [c[0] for c in cur.description]

    idx = {name: i for i, name in enumerate(cols)}

    out: dict[int, dict[str, Any]] = {}
    for row in data:
        root_id = int(row[idx["root_id"]])
        root_name = (row[idx["root_name"]] or "—").strip() or "—"
        root_icon = (row[idx["root_icon"]] or "")
        mf_name = (row[idx["manufacturer_name"]] or "—").strip() or "—"
        net = _to_dec(row[idx["net_amount"]])

        payload = out.get(root_id)
        if payload is None:
            payload = {"root_name": root_name, "root_icon": root_icon, "by_mf": {}}
            out[root_id] = payload

        payload["by_mf"][mf_name] = {"net": net, "disp": fmt_money_ru(net)}

    return out