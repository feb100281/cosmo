# # corporate/reports/manufacturers_by_rootcat.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any
# from django.db import connection

# from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


# def get_rootcat_manufacturers_metrics_by_year(
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

#     # 1) по годам: count производителей + чистая выручка
#     q = f"""
#         SELECT
#             r.id AS root_id,
#             COALESCE(r.name, '—') AS root_name,
#             YEAR(s.`date`) AS `year`,
#             COUNT(DISTINCT i.manufacturer_id) AS mf_cnt,
#             SUM(s.dt - s.cr) AS net_amount
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

#         # net_amount может прийти как Decimal/float/int/None
#         net_raw = row[idx["net_amount"]]
#         try:
#             net = Decimal(str(net_raw or "0"))
#         except Exception:
#             net = Decimal("0")

#         years_set.add(y_int)

#         payload = tmp.get(root_id)
#         if payload is None:
#             payload = {
#                 "root_id": root_id,
#                 "root_name": root_name,
#                 "counts": {},
#                 "revenue": {},
#                 "total_mf": 0,
#                 "total_rev": Decimal("0"),
#             }
#             tmp[root_id] = payload

#         payload["counts"][y] = cnt
#         payload["revenue"][y] = net

#     years = [str(y) for y in sorted(y for y in years_set if y >= start_year)]

#     rows = sorted(tmp.values(), key=lambda r: (r["root_name"] or "").lower())

#     # нормализуем годы + готовим списки под шаблон
#     for r in rows:
#         for y in years:
#             r["counts"].setdefault(y, 0)
#             r["revenue"].setdefault(y, Decimal("0"))

#         r["counts_list"] = [r["counts"][y] for y in years]
#         r["revenue_list"] = [r["revenue"][y] for y in years]
#         r["revenue_disp_list"] = [fmt_money_ru(v) if v else "0\u00A0₽" for v in r["revenue_list"]]
        
#         r["pairs_list"] = list(zip(r["counts_list"], r["revenue_disp_list"]))

#     # 2) итого за период: уникальные производители + net revenue total
#     q_total = f"""
#         SELECT
#             r.id AS root_id,
#             COUNT(DISTINCT i.manufacturer_id) AS total_mf,
#             SUM(s.dt - s.cr) AS total_net
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

#     totals_map: dict[int, dict[str, Any]] = {}
#     for root_id, total_mf, total_net in total_data:
#         rid = int(root_id)
#         tmf = int(total_mf or 0)
#         try:
#             tnet = Decimal(str(total_net or "0"))
#         except Exception:
#             tnet = Decimal("0")
#         totals_map[rid] = {"total_mf": tmf, "total_rev": tnet}

#     for r in rows:
#         t = totals_map.get(r["root_id"], {"total_mf": 0, "total_rev": Decimal("0")})
#         r["total_mf"] = int(t["total_mf"])
#         r["total_rev"] = t["total_rev"]
#         r["total_rev_disp"] = fmt_money_ru(r["total_rev"]) if r["total_rev"] else "0\u00A0₽"

#     return years, rows





# corporate/reports/manufacturers_by_rootcat.py

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import connection

from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


def get_rootcat_manufacturers_metrics_by_year(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """
    Возвращает:
      - years: список лет (строки), например ["2022","2023",...]
      - rows: список строк по root category (группа), в каждой:
          - pairs_list: [(cnt, rev_disp), ...] по годам
          - total_mf, total_rev_disp: итого уникальных производителей + выручка за период
      - totals: итоги "всего по всем группам":
          - by_year: список по годам в том же порядке, что years: mf + net_disp
          - period_total_mf: уникальные производители за весь период
          - period_total_net_disp: выручка за весь период
    """
    manufacturer_ids = manufacturer_ids or []
    params: dict[str, object] = {"start_year": int(start_year)}
    where_mf = ""

    # ВАЖНО:
    #  - когда фильтруем по выбранным производителям, мы НЕ теряем строки с manufacturer_id IS NULL,
    #    чтобы "не указан" продолжал входить в выручку/итоги.
    if manufacturer_ids:
        ph: list[str] = []
        for i, v in enumerate(manufacturer_ids):
            k = f"mf{i}"
            params[k] = int(v)
            ph.append(f"%({k})s")
        where_mf = f" AND (i.manufacturer_id IN ({', '.join(ph)}) OR i.manufacturer_id IS NULL) "

    # 1) по группам и годам: count производителей + чистая выручка
    # manufacturer_id IS NULL НЕ исключаем.
    # mf_cnt: считаем distinct по COALESCE(..., 0), чтобы NULL считался отдельным "производителем 0"
    q = f"""
        SELECT
            r.id AS root_id,
            COALESCE(r.name, '—') AS root_name,
            YEAR(s.`date`) AS `year`,
            COUNT(DISTINCT COALESCE(i.manufacturer_id, 0)) AS mf_cnt,
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
        r["revenue_disp_list"] = [
            fmt_money_ru(v) if v else "0\u00A0₽" for v in r["revenue_list"]
        ]
        r["pairs_list"] = list(zip(r["counts_list"], r["revenue_disp_list"]))

    # 2) итого за период ПО КАЖДОЙ группе: уникальные производители + net revenue total
    q_total = f"""
        SELECT
            r.id AS root_id,
            COUNT(DISTINCT COALESCE(i.manufacturer_id, 0)) AS total_mf,
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

    # 3) ИТОГО "всего по всем группам" ПОД КАЖДЫМ ГОДОМ (tfoot)
    # Важно: это корректный distinct по всему массиву, а не сумма "уникальных внутри групп" (которая завышает)
    q_year_totals = f"""
        SELECT
            YEAR(s.`date`) AS `year`,
            COUNT(DISTINCT COALESCE(i.manufacturer_id, 0)) AS mf_cnt,
            SUM(s.dt - s.cr) AS net_amount
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        JOIN corporate_cattree c ON c.id = i.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
          {where_mf}
        GROUP BY YEAR(s.`date`)
        ORDER BY `year`
    """

    with connection.cursor() as cur:
        cur.execute(q_year_totals, params)
        yt = cur.fetchall()

    totals_by_year_map: dict[str, dict[str, Any]] = {}
    for y, mf_cnt, net_amount in yt:
        y_str = str(int(y))
        mf = int(mf_cnt or 0)
        try:
            net = Decimal(str(net_amount or "0"))
        except Exception:
            net = Decimal("0")
        totals_by_year_map[y_str] = {"mf": mf, "net": net}

    totals_by_year: list[dict[str, Any]] = []
    for y in years:
        rec = totals_by_year_map.get(y, {"mf": 0, "net": Decimal("0")})
        net_val: Decimal = rec["net"]
        totals_by_year.append(
            {
                "year": y,
                "mf": rec["mf"],
                "net": net_val,
                "net_disp": fmt_money_ru(net_val) if net_val else "0\u00A0₽",
            }
        )

    # 4) ИТОГО "всего по всем группам" за период (правый нижний угол)
    q_period_total = f"""
        SELECT
            COUNT(DISTINCT COALESCE(i.manufacturer_id, 0)) AS total_mf,
            SUM(s.dt - s.cr) AS total_net
        FROM sales_salesdata s
        JOIN corporate_items i ON i.id = s.item_id
        JOIN corporate_cattree c ON c.id = i.cat_id
        WHERE YEAR(s.`date`) >= %(start_year)s
          {where_mf}
    """

    with connection.cursor() as cur:
        cur.execute(q_period_total, params)
        row = cur.fetchone()

    total_mf_all = 0
    total_net_all = Decimal("0")
    if row:
        total_mf_all = int((row[0] or 0))
        try:
            total_net_all = Decimal(str(row[1] or "0"))
        except Exception:
            total_net_all = Decimal("0")

    totals_payload = {
        "by_year": totals_by_year,
         "by_year_pairs": [(t["year"], t["mf"], t["net_disp"]) for t in totals_by_year],
        "period_total_mf": total_mf_all,
        "period_total_net_disp": fmt_money_ru(total_net_all) if total_net_all else "0\u00A0₽",
    }
    


    return years, rows, totals_payload