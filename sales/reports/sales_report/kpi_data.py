# # sales/reports/sales_report/kpi_data.py
# from datetime import date
# from decimal import Decimal
# from django.db import connection


# def build_kpi_for_range(start: date, end: date) -> dict:
#     q_sales = """
#         SELECT
#             COALESCE(SUM(d.dt),0) AS dt,
#             COALESCE(SUM(d.cr),0) AS cr,

#             -- отгружено заказов в периоде: был хотя бы один dt>0 по заказу в периоде
#             COUNT(DISTINCT CASE
#                 WHEN d.orders_id IS NOT NULL AND d.dt > 0 THEN d.orders_id
#             END) AS orders_shipped,

#             -- продажи без заказа (сумма)
#             COALESCE(SUM(CASE
#                 WHEN d.orders_id IS NULL THEN d.dt ELSE 0
#             END),0) AS dt_without_order,

#             -- продажи без заказа (кол-во операций/строк)
#             COUNT(CASE
#                 WHEN d.orders_id IS NULL AND d.dt > 0 THEN 1
#             END) AS sales_wo_order_ops
#         FROM sales_salesdata d
#         WHERE d.date BETWEEN %(start)s AND %(end)s
#     """

#     q_created = """
#         SELECT COUNT(*)
#         FROM sales_salesorders
#         WHERE client_order_date BETWEEN %(start)s AND %(end)s
#     """

#     # закрыто заказов: последняя отгрузка в периоде
#     # (используем mv_orders, раз он у тебя уже есть и используется в админке)
#     q_closed = """
#         SELECT COUNT(*)
#         FROM mv_orders o
#         WHERE o.order_max_date BETWEEN %(start)s AND %(end)s
#           AND COALESCE(o.sales, 0) > 0
#     """

#     with connection.cursor() as cur:
#         cur.execute(q_sales, {"start": start, "end": end})
#         dt, cr, orders_shipped, dt_wo, sales_wo_order_ops = cur.fetchone()

#         cur.execute(q_created, {"start": start, "end": end})
#         orders_created = cur.fetchone()[0] or 0

#         cur.execute(q_closed, {"start": start, "end": end})
#         orders_closed = cur.fetchone()[0] or 0

#     dt = Decimal(dt)
#     cr = Decimal(cr)
#     dt_wo = Decimal(dt_wo)
#     amount = dt - cr

#     rtr_ratio = (cr / dt) if dt else None
#     ave_check = (amount / orders_shipped) if orders_shipped else None
#     sales_wo_ratio = (dt_wo / dt) if dt else None

#     return {
#         "dt": dt,
#         "cr": cr,
#         "amount": amount,

#         "orders_created": int(orders_created),

#         # вместо "реализовано" — две честные метрики
#         "orders_shipped": int(orders_shipped),   # отгружено в периоде (были отгрузки)
#         "orders_closed": int(orders_closed),     # закрыто в периоде (последняя отгрузка)

#         "dt_without_order": dt_wo,
#         "sales_wo_ratio": sales_wo_ratio,
#         "sales_wo_order_ops": int(sales_wo_order_ops),

#         "ave_check": ave_check,
#         "rtr_ratio": rtr_ratio,
#     }


# sales/reports/sales_report/kpi_data.py

from datetime import date
from decimal import Decimal
from django.db import connection


def _to_decimal(x) -> Decimal:
    return Decimal(str(x or 0))


def build_kpi_for_range(start: date, end: date) -> dict:
    # Деньги — по дате реализации (истина)
    q_sales_total = """
        SELECT
            COALESCE(SUM(d.dt), 0) AS dt,
            COALESCE(SUM(d.cr), 0) AS cr
        FROM sales_salesdata d
        WHERE d.date BETWEEN %(start)s AND %(end)s
    """

    # Заказы — по факту отгрузки в периоде (стабильно для дня/недели/месяца)
    q_orders_total = """
        SELECT
            COALESCE(COUNT(DISTINCT d.orders_id), 0) AS orders
        FROM sales_salesdata d
        WHERE d.date BETWEEN %(start)s AND %(end)s
          AND d.orders_id IS NOT NULL
          AND d.dt > 0
    """

    # Разрез по типам — по факту отгрузки в периоде, тип из mv_orders
    q_by_type = """
        SELECT
            COALESCE(o.client_order_type, '—') AS client_order_type,
            COALESCE(COUNT(DISTINCT d.orders_id), 0) AS orders,
            COALESCE(SUM(d.dt), 0) AS dt,
            COALESCE(SUM(d.cr), 0) AS cr
        FROM sales_salesdata d
        LEFT JOIN djangodb.mv_orders o ON o.orders_id = d.orders_id
        WHERE d.date BETWEEN %(start)s AND %(end)s
          AND d.orders_id IS NOT NULL
          AND d.dt > 0
        GROUP BY COALESCE(o.client_order_type, '—')
        ORDER BY (COALESCE(SUM(d.dt),0) - COALESCE(SUM(d.cr),0)) DESC
    """

    # totals по магазинам — ТОЛЬКО ДЕНЬГИ (без заказов по магазинам)
    # важно: учитываем "чистые возвраты" (dt=0, cr>0)
    q_by_shop_total = """
        SELECT
            COALESCE(sg.name, '—') AS shop_name,
            COALESCE(SUM(d.dt), 0) AS dt,
            COALESCE(SUM(d.cr), 0) AS cr
        FROM sales_salesdata d
        LEFT JOIN corporate_stores store ON store.id = d.store_id
        LEFT JOIN corporate_storegroups sg ON sg.id = store.gr_id
        WHERE d.date BETWEEN %(start)s AND %(end)s
          AND d.orders_id IS NOT NULL
          AND (d.dt > 0 OR d.cr > 0)
        GROUP BY COALESCE(sg.name, '—')
        ORDER BY (COALESCE(SUM(d.dt),0) - COALESCE(SUM(d.cr),0)) DESC
    """

    # Максимальный отгруженный заказ (по чистой выручке = dt-cr) за период
    q_max_order = """
        SELECT
            d.orders_id AS orders_id,
            MAX(d.date) AS last_ship_date,
            COALESCE(SUM(d.dt), 0) AS dt,
            COALESCE(SUM(d.cr), 0) AS cr
        FROM sales_salesdata d
        WHERE d.date BETWEEN %(start)s AND %(end)s
          AND d.orders_id IS NOT NULL
          AND d.dt > 0
        GROUP BY d.orders_id
        ORDER BY (COALESCE(SUM(d.dt),0) - COALESCE(SUM(d.cr),0)) DESC
        LIMIT 1
    """

    # Нетто по заказам (для медианы/статистик)
    q_orders_net = """
        SELECT
            COALESCE(SUM(d.dt), 0) - COALESCE(SUM(d.cr), 0) AS net_amount
        FROM sales_salesdata d
        WHERE d.date BETWEEN %(start)s AND %(end)s
          AND d.orders_id IS NOT NULL
          AND d.dt > 0
        GROUP BY d.orders_id
    """

    with connection.cursor() as cur:
        cur.execute(q_sales_total, {"start": start, "end": end})
        dt, cr = cur.fetchone()

        cur.execute(q_orders_total, {"start": start, "end": end})
        (orders,) = cur.fetchone()

        cur.execute(q_by_type, {"start": start, "end": end})
        rows_type = cur.fetchall()

        cur.execute(q_by_shop_total, {"start": start, "end": end})
        rows_shop_total = cur.fetchall()

        cur.execute(q_max_order, {"start": start, "end": end})
        max_row = cur.fetchone()

        cur.execute(q_orders_net, {"start": start, "end": end})
        net_rows = cur.fetchall()

    dt = _to_decimal(dt)
    cr = _to_decimal(cr)
    amount = dt - cr

    orders = int(orders or 0)
    rtr_ratio = (cr / dt) if dt else None
    ave_check = (amount / orders) if orders else None

    # by type
    sales_by_type = []
    for t, o_cnt, t_dt, t_cr in (rows_type or []):
        t_dt = _to_decimal(t_dt)
        t_cr = _to_decimal(t_cr)
        sales_by_type.append({
            "type": (t or "—").strip() or "—",
            "orders": int(o_cnt or 0),
            "dt": t_dt,
            "cr": t_cr,
            "amount": t_dt - t_cr,
        })

    # by shop (money only)
    sales_by_shop = []
    for shop_name, s_dt, s_cr in (rows_shop_total or []):
        s_dt = _to_decimal(s_dt)
        s_cr = _to_decimal(s_cr)
        sales_by_shop.append({
            "shop": (shop_name or "—").strip() or "—",
            "dt": s_dt,
            "cr": s_cr,
            "amount": s_dt - s_cr,
        })

    # max order
    max_order = None
    if max_row:
        o_id, o_date, o_dt, o_cr = max_row
        o_dt = _to_decimal(o_dt)
        o_cr = _to_decimal(o_cr)
        max_order = {
            "order_id": o_id,
            "date": o_date,
            "dt": o_dt,
            "cr": o_cr,
            "amount": o_dt - o_cr,
        }

    # net amounts list
    orders_net = []
    for (net_amount,) in (net_rows or []):
        orders_net.append(_to_decimal(net_amount))

    return {
        "dt": dt,
        "cr": cr,
        "amount": amount,
        "rtr_ratio": rtr_ratio,
        "orders": orders,
        "ave_check": ave_check,
        "sales_by_type": sales_by_type,
        "sales_by_shop": sales_by_shop,  # ✅ магазины: только деньги
        "max_order": max_order,
        "orders_net": orders_net,
    }
