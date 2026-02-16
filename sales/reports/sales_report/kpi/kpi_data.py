# sales/reports/sales_report/kpi/kpi_data.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from utils.db_engine import get_engine  # ✅ singleton ENGINE из .env / DATABASE_URL


def _to_decimal(x) -> Decimal:
    return Decimal(str(x or 0))


def build_kpi_for_range(start: date, end: date) -> Dict[str, Any]:
    """
    KPI за период [start, end] включительно.
    Реализация СТРОГО через SQLAlchemy (engine берём из utils.db_engine.get_engine()).

    Логика:
    - Деньги: SUM(dt), SUM(cr) по d.date (дата реализации).
    - Заказы: COUNT(DISTINCT orders_id) по факту отгрузки в периоде (dt > 0).
    - Разрез по типам: безопасно через агрегацию sales_salesdata по orders_id,
      затем JOIN на mv_orders (так не будет "раздувания" сумм при потенциальных дублях витрины).
    - Магазины: только деньги (dt/cr) + учитываем "чистые возвраты" (dt=0, cr>0).
    - Max order: по net = dt-cr за период (dt>0), тоже через агрегацию по orders_id.
    - orders_net: список net по каждому заказу (для медианы/статистик).
    """

    engine = get_engine()
    params = {"start": start, "end": end}

    # 1) Деньги — по дате реализации
    q_sales_total = text("""
        SELECT
            COALESCE(SUM(d.dt), 0) AS dt,
            COALESCE(SUM(d.cr), 0) AS cr
        FROM sales_salesdata d
        WHERE d.date BETWEEN :start AND :end
    """)

    # 2) Заказы — по факту отгрузки в периоде
    q_orders_total = text("""
        SELECT
            COALESCE(COUNT(DISTINCT d.orders_id), 0) AS orders
        FROM sales_salesdata d
        WHERE d.date BETWEEN :start AND :end
          AND d.orders_id IS NOT NULL
          AND d.dt > 0
    """)

    # 3) Разрез по типам — через агрегацию по orders_id (стабильнее)
    # q_by_type = text("""
    #     SELECT
    #         COALESCE(ord.client_order_type, '—') AS client_order_type,
    #         COUNT(*) AS orders,
    #         COALESCE(SUM(x.dt), 0) AS dt,
    #         COALESCE(SUM(x.cr), 0) AS cr
    #     FROM (
    #         SELECT
    #             orders_id,
    #             SUM(dt) AS dt,
    #             SUM(cr) AS cr
    #         FROM sales_salesdata
    #         WHERE date BETWEEN :start AND :end
    #           AND orders_id IS NOT NULL

    #         GROUP BY orders_id
    #     ) x
    #     LEFT JOIN djangodb.mv_orders ord ON ord.orders_id = x.orders_id
    #     GROUP BY COALESCE(ord.client_order_type, '—')
    #     ORDER BY (COALESCE(SUM(x.dt),0) - COALESCE(SUM(x.cr),0)) DESC
    # """)

    # 4) Totals по магазинам — только деньги (dt/cr), учитываем чистые возвраты
    q_by_shop_total = text("""
        SELECT
            COALESCE(sg.name, '—') AS shop_name,
            COALESCE(SUM(d.dt), 0) AS dt,
            COALESCE(SUM(d.cr), 0) AS cr
        FROM sales_salesdata d
        LEFT JOIN corporate_stores store ON store.id = d.store_id
        LEFT JOIN corporate_storegroups sg ON sg.id = store.gr_id
        WHERE d.date BETWEEN :start AND :end
          AND d.orders_id IS NOT NULL
          AND (d.dt > 0 OR d.cr > 0)
        GROUP BY COALESCE(sg.name, '—')
        ORDER BY (COALESCE(SUM(d.dt),0) - COALESCE(SUM(d.cr),0)) DESC
    """)

    # 5) Максимальный отгруженный заказ за период (по net = dt-cr) — через агрегацию по orders_id
    # q_max_order = text("""
    #     SELECT
    #         x.orders_id AS orders_id,
    #         ord.client_order_number AS client_order_number,
    #         x.max_date AS last_ship_date,
    #         x.dt AS dt,
    #         x.cr AS cr
    #     FROM (
    #         SELECT
    #             orders_id,
    #             SUM(dt) AS dt,
    #             SUM(cr) AS cr,
    #             MAX(date) AS max_date
    #         FROM sales_salesdata
    #         WHERE date BETWEEN :start AND :end
    #           AND orders_id IS NOT NULL
    #           AND dt > 0
    #         GROUP BY orders_id
    #     ) x
    #     LEFT JOIN djangodb.mv_orders ord ON ord.orders_id = x.orders_id
    #     ORDER BY (x.dt - x.cr) DESC
    #     LIMIT 1
    # """)

    # 6) Нетто по заказам (для медианы/статистик)
    # q_orders_net = text("""
    #     SELECT
    #         COALESCE(SUM(d.dt), 0) - COALESCE(SUM(d.cr), 0) AS net_amount
    #     FROM sales_salesdata d
    #     WHERE d.date BETWEEN :start AND :end
    #       AND d.orders_id IS NOT NULL
    #       AND d.dt > 0
    #     GROUP BY d.orders_id
    # """)

    with engine.connect() as conn:
        dt, cr = conn.execute(q_sales_total, params).one()
        (orders,) = conn.execute(q_orders_total, params).one()

        # rows_type = conn.execute(q_by_type, params).all()
        rows_shop_total = conn.execute(q_by_shop_total, params).all()

        # max_row = conn.execute(q_max_order, params).first()
        # net_rows = conn.execute(q_orders_net, params).all()

    # --- постобработка ---
    dt_d = _to_decimal(dt)
    cr_d = _to_decimal(cr)
    amount = dt_d - cr_d

    orders_i = int(orders or 0)
    rtr_ratio = (cr_d / dt_d) if dt_d else None
    ave_check = (amount / orders_i) if orders_i else None

    # by type
    # sales_by_type: List[Dict[str, Any]] = []
    # for client_order_type, o_cnt, t_dt, t_cr in (rows_type or []):
    #     t_dt_d = _to_decimal(t_dt)
    #     t_cr_d = _to_decimal(t_cr)
    #     sales_by_type.append({
    #         "type": (client_order_type or "—").strip() or "—",
    #         "orders": int(o_cnt or 0),
    #         "dt": t_dt_d,
    #         "cr": t_cr_d,
    #         "amount": t_dt_d - t_cr_d,
    #     })

    # by shop (money only)
    sales_by_shop: List[Dict[str, Any]] = []
    for shop_name, s_dt, s_cr in (rows_shop_total or []):
        s_dt_d = _to_decimal(s_dt)
        s_cr_d = _to_decimal(s_cr)
        sales_by_shop.append({
            "shop": (shop_name or "—").strip() or "—",
            "dt": s_dt_d,
            "cr": s_cr_d,
            "amount": s_dt_d - s_cr_d,
        })

    # max order
    # max_order: Optional[Dict[str, Any]] = None
    # if max_row:
    #     o_id, client_order_number, last_ship_date, o_dt, o_cr = max_row
    #     o_dt_d = _to_decimal(o_dt)
    #     o_cr_d = _to_decimal(o_cr)
    #     max_order = {
    #         "order_id": o_id,
    #         "client_order_number": client_order_number,
    #         "date": last_ship_date,
    #         "dt": o_dt_d,
    #         "cr": o_cr_d,
    #         "amount": o_dt_d - o_cr_d,
    #     }

    # net amounts list
    # orders_net: List[Decimal] = [_to_decimal(net_amount) for (net_amount,) in (net_rows or [])]

    return {
        "dt": dt_d,
        "cr": cr_d,
        "amount": amount,
        "rtr_ratio": rtr_ratio,
        "orders": orders_i,
        "ave_check": ave_check,
        # "sales_by_type": sales_by_type,
        "sales_by_shop": sales_by_shop,  
        # "max_order": max_order,
        # "orders_net": orders_net,
    }
