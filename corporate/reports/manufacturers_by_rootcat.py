from __future__ import annotations

from typing import Any
from django.db import connection


def get_rootcat_manufacturers_count_by_year(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:

    manufacturer_ids = manufacturer_ids or []

    params: dict[str, object] = {"start_year": int(start_year)}
    where_mf = ""

    if manufacturer_ids:
        ph = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        where_mf = f" AND i.manufacturer_id IN ({', '.join(ph)}) "

    # 1) по годам
    q = f"""
        SELECT
            r.id AS root_id,
            COALESCE(r.name, '—') AS root_name,
            YEAR(s.`date`) AS `year`,
            COUNT(DISTINCT i.manufacturer_id) AS mf_cnt
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        JOIN corporate_cattree c ON c.id = i.cat_id
        JOIN corporate_cattree r
          ON r.parent_id IS NULL
         AND r.tree_id = c.tree_id
         AND c.lft >= r.lft
         AND c.rght <= r.rght
        WHERE YEAR(s.`date`) >= %(start_year)s
          AND i.manufacturer_id IS NOT NULL
          {where_mf}
        GROUP BY r.id, r.name, YEAR(s.`date`)
        ORDER BY root_name, `year`
    """

    with connection.cursor() as cur:
        cur.execute(q, params)
        data = cur.fetchall()
        cols = [c[0] for c in cur.description]

    idx = {name: i for i, name in enumerate(cols)}

    years_set: set[int] = set()
    tmp: dict[int, dict[str, Any]] = {}

    for row in data:
        root_id = int(row[idx["root_id"]])
        root_name = (row[idx["root_name"]] or "—").strip() or "—"
        y_int = int(row[idx["year"]])
        y = str(y_int)
        cnt = int(row[idx["mf_cnt"]] or 0)

        years_set.add(y_int)

        payload = tmp.get(root_id)
        if payload is None:
            payload = {"root_id": root_id, "root_name": root_name, "counts": {}, "total": 0}
            tmp[root_id] = payload

        payload["counts"][y] = cnt  # total здесь НЕ суммируем

    years = [str(y) for y in sorted(y for y in years_set if y >= start_year)]

    # нормализуем: чтобы у всех были все годы
    rows = sorted(tmp.values(), key=lambda r: (r["root_name"] or "").lower())
    for r in rows:
        for y in years:
            r["counts"].setdefault(y, 0)

    # 2) уникальные производители за период (ИТОГО)
    q_total = f"""
        SELECT
            r.id AS root_id,
            COUNT(DISTINCT i.manufacturer_id) AS total_mf
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        JOIN corporate_cattree c ON c.id = i.cat_id
        JOIN corporate_cattree r
          ON r.parent_id IS NULL
         AND r.tree_id = c.tree_id
         AND c.lft >= r.lft
         AND c.rght <= r.rght
        WHERE YEAR(s.`date`) >= %(start_year)s
          AND i.manufacturer_id IS NOT NULL
          {where_mf}
        GROUP BY r.id
    """

    with connection.cursor() as cur:
        cur.execute(q_total, params)
        total_data = cur.fetchall()

    totals_map = {int(root_id): int(total_mf or 0) for (root_id, total_mf) in total_data}

    for r in rows:
        r["total"] = totals_map.get(r["root_id"], 0)

    return years, rows