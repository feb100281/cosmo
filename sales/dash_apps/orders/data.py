# sales/dash_apps/dailysales/data.py

# Данные для дневного отчета


from django.db import connection
import pandas as pd

def get_orders_by_period(sd=None, ed=None, order_type=None):
    if not sd or not ed:
        return None

    start_date = pd.to_datetime(sd).strftime("%Y-%m-%d")
    end_date = pd.to_datetime(ed).strftime("%Y-%m-%d")

    where_clause = ""
    if order_type == 1:
        where_clause = "WHERE ord.client_order_type != 'Розничные продажи'"
    elif order_type == 2:
        where_clause = "WHERE ord.client_order_type = 'Розничные продажи'"

    q = f"""
    SELECT
        ord.client_order_type,
        ord.client_order,
        ord.client_order_date,
        ord.sales as total_sales,
        x.dt as sales_period,
        ord.returns,
        x.cr as returns_period,
        ord.amount,
        x.dt - x.cr as amount_period,
        ord.items_amount,
        ord.service_amount,
        ord.items_quant,
        ord.unique_items,
        ord.order_duration,
        DATEDIFF(x.max_date, ord.client_order_date) + 1 AS current_order_duration
    FROM (
        SELECT
            orders_id,
            SUM(dt) as dt,
            SUM(cr) as cr,
            MAX(`date`) as max_date
        FROM sales_salesdata
        WHERE `date` BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY orders_id
    ) x
    JOIN mv_orders as ord on ord.orders_id = x.orders_id
    {where_clause}
    """

    with connection.cursor() as cur:
        cur.execute(q, {"start_date": start_date, "end_date": end_date})
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
    return pd.DataFrame(rows, columns=cols)


def get_orders_details(orders_id):
    q = """
    SELECT 
    d.date,
    i.fullname,
    coalesce(i.article,'нет артикля') as article,
    coalesce(b.barcode,'нет баркода') as barcode,
    d.dt,
    d.cr,
    d.quant_dt,
    d.quant_cr,
    coalesce(mn.name, 'Менеджер не указан') as manager_name,
    coalesce(a.name,'Нет агента') as agent_name,
    coalesce(d.warehouse,'Склад не указан') as warehouse,
    coalesce(sg.name,'') as store_group,
    d.spec
    FROM sales_salesdata d
    JOIN sales_salesorders m ON m.id = d.orders_id
    LEFT JOIN corporate_items as i on d.item_id = i.id
    LEFT JOIN corporate_barcode as b on d.barcode_id = b.id
    LEFT JOIN corporate_managers as mn on d.manager_id = mn.id
    LEFT JOIN corporate_agents as a on a.id = d.agent_id
    LEFT JOIN corporate_stores as store on store.id = d.store_id
    LEFT JOIN corporate_storegroups as sg on sg.id = store.gr_id
    where orders_id = %(orders_id)s;   
    """
    with connection.cursor() as cur:
        cur.execute(q, {'orders_id':orders_id})            
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]  # самый совместимый вариант
    return pd.DataFrame(rows, columns=cols)

