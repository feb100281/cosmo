# corporate/reports/manufacturers_revenue.py
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import connection


def get_manufacturers_net_by_year(
    start_year: int = 2022,
    ids: list[int] | None = None,
) -> tuple[list[int], list[dict[str, Any]]]:

    ids = ids or []

    where_ids = ""
    params: dict[str, object] = {"start_year": int(start_year)}

    if ids:
        ph = []
        for i, v in enumerate(ids):
            key = f"id{i}"
            params[key] = int(v)
            ph.append(f"%({key})s")
        where_ids = f" AND i.manufacturer_id IN ({', '.join(ph)}) "

    q = f"""
        SELECT
            i.manufacturer_id AS manufacturer_id,
            COALESCE(m.report_name, m.name, '—') AS manufacturer_name,
            YEAR(s.`date`) AS `year`,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        LEFT JOIN corporate_itemmanufacturer m ON m.id = i.manufacturer_id
        WHERE YEAR(s.`date`) >= %(start_year)s
          AND i.manufacturer_id IS NOT NULL
          {where_ids}
        GROUP BY i.manufacturer_id, manufacturer_name, YEAR(s.`date`)
        ORDER BY manufacturer_name, `year`
    """

    with connection.cursor() as cur:
        cur.execute(q, params)
        data = cur.fetchall()
        cols = [c[0] for c in cur.description]

    idx = {name: i for i, name in enumerate(cols)}

    years_set: set[int] = set()
    tmp: dict[int, dict[str, Any]] = {}

    def to_float(x: Any) -> float:
        if x is None:
            return 0.0
        if isinstance(x, Decimal):
            return float(x)
        try:
            return float(x)
        except Exception:
            return 0.0

    for row in data:
        mf_id = int(row[idx["manufacturer_id"]])
        name = (row[idx["manufacturer_name"]] or "—").strip() or "—"
        y = int(row[idx["year"]])
        net = to_float(row[idx["net_amount"]])

        years_set.add(y)

        payload = tmp.get(mf_id)
        if payload is None:
            payload = {"manufacturer_id": mf_id, "name": name, "by_year": {}, "total": 0.0}
            tmp[mf_id] = payload

        payload["by_year"][y] = net
        payload["total"] = float(payload["total"]) + net

    years = sorted([y for y in years_set if y >= start_year])

    rows = sorted(tmp.values(), key=lambda r: (r["name"] or "").lower())

    # чтобы в шаблоне было просто: {% for v in r.values %}...
    for r in rows:
        by_year = r.get("by_year", {})
        r["values"] = [to_float(by_year.get(y)) for y in years]

    return years, rows