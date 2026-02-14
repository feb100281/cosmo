# sales/dash_apps/dailysales/data.py

# Данные для дневного отчета

from django.db import connection
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from datetime import timedelta

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