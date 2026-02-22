# from __future__ import annotations

# from typing import Any
# from django.db import connection
# from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


# def get_rootcat_manufacturers_count_by_year(
#     start_year: int = 2022,
#     manufacturer_ids: list[int] | None = None,
# ) -> tuple[list[str], list[dict[str, Any]]]:

#     manufacturer_ids = manufacturer_ids or []

#     params: dict[str, object] = {"start_year": int(start_year)}
#     where_mf = ""

#     if manufacturer_ids:
#         ph = []
#         for i, v in enumerate(manufacturer_ids):
#             k = f"mf{i}"
#             params[k] = int(v)
#             ph.append(f"%({k})s")
#         where_mf = f" AND i.manufacturer_id IN ({', '.join(ph)}) "

#     # 1) по годам
#     q = f"""
#         SELECT
#             r.id AS root_id,
#             COALESCE(r.name, '—') AS root_name,
#             YEAR(s.`date`) AS `year`,
#             COUNT(DISTINCT i.manufacturer_id) AS mf_cnt
#         FROM sales_salesdata s
#         JOIN corporate_items i ON i.id = s.item_id
#         JOIN corporate_cattree c ON c.id = i.cat_id
#         JOIN corporate_cattree r
#           ON r.parent_id IS NULL
#          AND r.tree_id = c.tree_id
#          AND c.lft >= r.lft
#          AND c.rght <= r.rght
#         WHERE YEAR(s.`date`) >= %(start_year)s
#           AND i.manufacturer_id IS NOT NULL
#           {where_mf}
#         GROUP BY r.id, r.name, YEAR(s.`date`)
#         ORDER BY root_name, `year`
#     """

#     with connection.cursor() as cur:
#         cur.execute(q, params)
#         data = cur.fetchall()
#         cols = [c[0] for c in cur.description]

#     idx = {name: i for i, name in enumerate(cols)}

#     years_set: set[int] = set()
#     tmp: dict[int, dict[str, Any]] = {}

#     for row in data:
#         root_id = int(row[idx["root_id"]])
#         root_name = (row[idx["root_name"]] or "—").strip() or "—"
#         y_int = int(row[idx["year"]])
#         y = str(y_int)
#         cnt = int(row[idx["mf_cnt"]] or 0)

#         years_set.add(y_int)

#         payload = tmp.get(root_id)
#         if payload is None:
#             payload = {"root_id": root_id, "root_name": root_name, "counts": {}, "total": 0}
#             tmp[root_id] = payload

#         payload["counts"][y] = cnt  # total здесь НЕ суммируем

#     years = [str(y) for y in sorted(y for y in years_set if y >= start_year)]

#     # нормализуем: чтобы у всех были все годы
#     rows = sorted(tmp.values(), key=lambda r: (r["root_name"] or "").lower())
#     for r in rows:
#         for y in years:
#             r["counts"].setdefault(y, 0)

#     # 2) уникальные производители за период (ИТОГО)
#     q_total = f"""
#         SELECT
#             r.id AS root_id,
#             COUNT(DISTINCT i.manufacturer_id) AS total_mf
#         FROM sales_salesdata s
#         JOIN corporate_items i ON i.id = s.item_id
#         JOIN corporate_cattree c ON c.id = i.cat_id
#         JOIN corporate_cattree r
#           ON r.parent_id IS NULL
#          AND r.tree_id = c.tree_id
#          AND c.lft >= r.lft
#          AND c.rght <= r.rght
#         WHERE YEAR(s.`date`) >= %(start_year)s
#           AND i.manufacturer_id IS NOT NULL
#           {where_mf}
#         GROUP BY r.id
#     """

#     with connection.cursor() as cur:
#         cur.execute(q_total, params)
#         total_data = cur.fetchall()

#     totals_map = {int(root_id): int(total_mf or 0) for (root_id, total_mf) in total_data}

#     for r in rows:
#         r["total"] = totals_map.get(r["root_id"], 0)

#     return years, rows




from __future__ import annotations

from decimal import Decimal
from typing import Any
from django.db import connection

from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


def get_rootcat_manufacturers_metrics_by_year(
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

    # 1) по годам: count производителей + чистая выручка
    q = f"""
        SELECT
            r.id AS root_id,
            COALESCE(r.name, '—') AS root_name,
            YEAR(s.`date`) AS `year`,
            COUNT(DISTINCT i.manufacturer_id) AS mf_cnt,
            SUM(s.dt - s.cr) AS net_amount
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

        # net_amount может прийти как Decimal/float/int/None
        net_raw = row[idx["net_amount"]]
        try:
            net = Decimal(str(net_raw or "0"))
        except Exception:
            net = Decimal("0")

        years_set.add(y_int)

        payload = tmp.get(root_id)
        if payload is None:
            payload = {
                "root_id": root_id,
                "root_name": root_name,
                "counts": {},
                "revenue": {},
                "total_mf": 0,
                "total_rev": Decimal("0"),
            }
            tmp[root_id] = payload

        payload["counts"][y] = cnt
        payload["revenue"][y] = net

    years = [str(y) for y in sorted(y for y in years_set if y >= start_year)]

    rows = sorted(tmp.values(), key=lambda r: (r["root_name"] or "").lower())

    # нормализуем годы + готовим списки под шаблон
    for r in rows:
        for y in years:
            r["counts"].setdefault(y, 0)
            r["revenue"].setdefault(y, Decimal("0"))

        r["counts_list"] = [r["counts"][y] for y in years]
        r["revenue_list"] = [r["revenue"][y] for y in years]
        r["revenue_disp_list"] = [fmt_money_ru(v) if v else "0\u00A0₽" for v in r["revenue_list"]]
        
        r["pairs_list"] = list(zip(r["counts_list"], r["revenue_disp_list"]))

    # 2) итого за период: уникальные производители + net revenue total
    q_total = f"""
        SELECT
            r.id AS root_id,
            COUNT(DISTINCT i.manufacturer_id) AS total_mf,
            SUM(s.dt - s.cr) AS total_net
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

    totals_map: dict[int, dict[str, Any]] = {}
    for root_id, total_mf, total_net in total_data:
        rid = int(root_id)
        tmf = int(total_mf or 0)
        try:
            tnet = Decimal(str(total_net or "0"))
        except Exception:
            tnet = Decimal("0")
        totals_map[rid] = {"total_mf": tmf, "total_rev": tnet}

    for r in rows:
        t = totals_map.get(r["root_id"], {"total_mf": 0, "total_rev": Decimal("0")})
        r["total_mf"] = int(t["total_mf"])
        r["total_rev"] = t["total_rev"]
        r["total_rev_disp"] = fmt_money_ru(r["total_rev"]) if r["total_rev"] else "0\u00A0₽"

    return years, rows