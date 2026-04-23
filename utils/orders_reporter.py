# utils/orders_reporter.py
import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from .db_engine import get_duckdb_conn, get_mysql_conn, get_engine
from pprint import pprint

# Заисываем вьюхи в duck
def register_tables(conn:DuckDBPyConnection):
    my_sql = get_engine()
    orders = pd.read_sql("select * from orders_order",con=my_sql)
    items =  pd.read_sql("select * from corporate_items",con=my_sql)
    orders_items = pd.read_sql("select * from raw_orders",con=my_sql)
    orders_cf = pd.read_sql("select * from orders_orderscf",con=my_sql)
    cattree = pd.read_sql("select * from corporate_cattree",con=my_sql)
    sc = pd.read_sql("select * from corporate_subcategory",con=my_sql)
    barcodes = pd.read_sql("select * from corporate_barcode",con=my_sql)
    sales = pd.read_sql("select * from sales_salesdata",con=my_sql)
    
    conn.register("orders",orders)
    conn.register("items",items)
    conn.register("orders_items",orders_items)
    conn.register("orders_cf",orders_cf)
    conn.register("cattree",cattree)
    conn.register("sc",sc)
    conn.register("barcodes",barcodes)
    conn.register("sales",sales)
    
    return "Registation finished"

# Добавляем свистоперделки к таблице orders_items
def advance_items(conn:DuckDBPyConnection):
    items_joined = conn.sql(
        """ 
        SELECT
        t.*,        
        i.id as item_id,
        i.name,        
        pid_cat.id as pid_id,
        pid_cat.name as parent_cat,
        cat.id as cat_id,
        cat.name as cat,
        sub_cat.id as sc_id,
        sub_cat.name as subcat,
        bc.id as barcode_id,       
        from orders_items t        
        left join items as i on i.fullname = t.fullname
        left join cattree as cat on cat.id = i.cat_id
        left join cattree as pid_cat on pid_cat.id = cat.parent_id
        left join sc as sub_cat on sub_cat.id = i.subcat_id
        left join barcodes as bc on bc.barcode = t.barcode   
        """
    )
    my_sql = get_engine()
    items_joined_df = items_joined.df()
    items_joined_df['id'] = items_joined_df.index + 1
    items_joined_df.to_sql('mv_orders_items',con=my_sql,index=False,if_exists='replace')
    conn.register("items_joined",items_joined)
    return "all good"

# Саммари по заказам
def mv_orders_summary(conn: DuckDBPyConnection):    
    delivery_cats = conn.sql("select distinct id::bigint as id from cattree where parent_id = 86").df()['id'].to_list()
    delivery_cats = ', '.join(map(str, delivery_cats))
    if not delivery_cats:
        delivery_cats = "-1"

    deliveriy_items = conn.sql(f"select distinct id::bigint as id from items where cat_id in ({delivery_cats})").df()['id'].to_list()
    deliveriy_items = ', '.join(map(str, deliveriy_items))
    if not deliveriy_items:
        deliveriy_items = "-1"

    mv = conn.sql(
        f""" 
        
        SELECT
        t.order_id,
        t.number || ' от ' || strftime(t.date_from, '%d.%m.%Y')::TEXT AS order_name,
        t.number,
        t.date_from,
        max(t.update_at) as update_at,
        string_agg(DISTINCT t.status, ', ' ORDER BY t.status) AS status,
        COALESCE(string_agg(DISTINCT t.client, ', ' ORDER BY t.client),'Клиент не указан') AS client,
        COALESCE(string_agg(DISTINCT t.manager, ', ' ORDER BY t.manager),'Менеджер не указан') AS manager,
        COALESCE(string_agg(DISTINCT t.store, ', ' ORDER BY t.store),'Магазин не указан') AS store,        
        
        CASE 
            WHEN 
                COALESCE(sum(t.qty) FILTER (where t.pid_id != 86), 0) = 
                COALESCE(sum(t.qty) FILTER (where t.pid_id != 86 and cancellation_reason is not null), 0)
                AND COALESCE(sum(t.qty) FILTER (where t.pid_id != 86 and cancellation_reason is not null), 0) != 0
            THEN 'Отменен'

            WHEN
                COALESCE(sum(t.qty) FILTER (where t.pid_id != 86), 0) != 
                COALESCE(sum(t.qty) FILTER (where t.pid_id != 86 and cancellation_reason is not null), 0)
                AND COALESCE(sum(t.qty) FILTER (where t.pid_id != 86 and cancellation_reason is not null), 0) != 0
            THEN 'Уменьшен'

            ELSE 'Без изменений'
        END AS change_status,
        
        
        COALESCE(sum(t.qty) FILTER (where t.pid_id != 86), 0) as qty_ordered,
        COALESCE(sum(t.qty) FILTER (where t.pid_id != 86 and cancellation_reason is not null), 0) as qty_cancelled,
        
        COALESCE(sum(t.qty) FILTER (where t.pid_id != 86), 0) -
        COALESCE(sum(t.qty) FILTER (where t.pid_id != 86 and cancellation_reason is not null), 0)
        as order_qty,
        
        
        COALESCE(sum(t.amount) FILTER (where t.pid_id != 86), 0) +
            COALESCE(sum(t.amount) FILTER (where t.pid_id = 86), 0) as order_amount,

        COALESCE(sum(t.amount) FILTER (where t.pid_id = 86), 0) as amount_delivery,

        COALESCE(sum(t.amount) FILTER (
            where cancellation_reason is not null and t.pid_id != 86
        ), 0) as amount_cancelled,

    (
        COALESCE(sum(t.amount) FILTER (where t.pid_id != 86), 0) -
        COALESCE(sum(t.amount) FILTER (where cancellation_reason is not null and t.pid_id != 86), 0)
    ) + COALESCE(sum(t.amount) FILTER (where t.pid_id = 86), 0) as amount_active,
        
        max(COALESCE(ocf.cash_recieved)) as cash_recieved,
        max(COALESCE(ocf.cash_returned)) as cash_returned,
        max(COALESCE(ocf.cash_pmts)) as cash_pmts,       
        
        max(COALESCE(s.shiped, 0)) AS shiped,
        max(COALESCE(s.returned, 0)) AS returned,
        max(COALESCE(s.shiped_qty, 0)) AS shiped_qty,
        max(COALESCE(s.amount, 0)) AS shiped_amount,
        max(COALESCE(s.returned_amount, 0)) AS returned_amount,
        max(COALESCE(s.shiped_amount, 0)) as total_shiped_amount,
        max(COALESCE(s.delivery_amount,0)) as shiped_delivery_amount,
        
        max(COALESCE(ocf.payment_dates)) as payment_dates
        from items_joined t        
        
        LEFT JOIN (
            SELECT
                order_guid,
                COALESCE(SUM(quant_dt) filter (where item_id not in ({deliveriy_items})),0) AS shiped,
                COALESCE(SUM(quant_cr) filter (where item_id not in ({deliveriy_items})),0) AS returned,      
                COALESCE(SUM(quant_dt) filter (where item_id not in ({deliveriy_items})),0) -
                COALESCE(SUM(quant_cr) filter (where item_id not in ({deliveriy_items})),0)
                as shiped_qty,          
                SUM(dt) AS amount,
                SUM(cr) AS returned_amount,
                SUM(dt-cr) as shiped_amount,
                SUM(dt-cr) filter (where item_id in ({deliveriy_items})) as delivery_amount
            FROM sales
            GROUP BY order_guid            
        ) s on s.order_guid IS NOT DISTINCT FROM t.order_id
        
        LEFT JOIN (
            SELECT
                order_guid,
                SUM(amount) AS cash_pmts,
                COALESCE(SUM(amount) filter (where amount>0),0) as cash_recieved,
                COALESCE(SUM(amount) filter (where amount<0),0) as cash_returned,
                LIST(concat(date,': ',amount,' руб')) as payment_dates
            FROM orders_cf
            GROUP BY order_guid
        ) ocf
            ON ocf.order_guid IS NOT DISTINCT FROM t.order_id
        
        
        GROUP BY 
        t.order_id,
        t.number,
        t.date_from
        """
    )
    
    my_sql = get_engine()
    mv.df().to_sql('mv_orders_summary_table',con=my_sql,index=False,if_exists='replace')
    

    #  conn.register("orders_summary", orders_sum)
    return "orders_summary registered"

def get_summary_by_orders_status(conn:DuckDBPyConnection):
    return conn.sql(
        """ 
        SELECT
        t.status as "Статус заказа",
        count(t.*) as "Всего заказов",
        count(t.*) filter (where t.is_cancelled = true) as "в т.ч отменено", 
        count(t.*) filter (where t.is_cancelled = false) as "в т.ч выполнено / выполняется",
        sum(t.qty) as "Ед заказано",
        sum(t.qty) filter (where t.is_cancelled = true) as "в т.ч отменено",
        sum(t.qty) filter (where t.is_cancelled = false) as "в т.ч выполнено / выполняется",
        sum(t.amount) as "Сумма заказов",
        sum(t.amount) filter (where t.is_cancelled = true) as "в т.ч отменено",
        sum(t.amount) filter (where t.is_cancelled = false) as "в т.ч выполнено / выполняется",        
        sum(t.paid) as "Оплачено на дату",
        sum(t.shiped) as "Отгружено ед на дату",
        sum(t.returned) as "Возвраты ед на дату",
        sum(t.shiped_amount) as "Реализация на дату (руб)",
        sum(t.returned_amount) as "Возвращено на дату (руб)",
        sum(t.shiped_amount-t.returned_amount) as "Всего реализация"
        from orders_summary t
        group by t.status
        """
    )

def main():
    conn = get_duckdb_conn()
    log = []
    log.append(register_tables(conn))
    log.append(advance_items(conn))
    log.append(mv_orders_summary(conn))
    
    return "; \n".join(log)
   
    
