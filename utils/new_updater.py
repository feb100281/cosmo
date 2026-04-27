# utils/new_updater.py
import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from .db_engine import get_duckdb_conn, get_mysql_conn
from pprint import pprint
from .orders_reporter import main as rebuild_orders_summary


file = '/Users/daria/Desktop/2026-04-15/Sales_2026-04-15.xlsx'

REGISTERED_COLUMNS = [
    "Регистратор",
    "Дата документа",
    "Заказ клиента",
    "Номер Заказа клиента",
    "Дата Заказа клиента",
    "Менеджер",
    "Подразделение",
    "Агент",
    "Склад",
    "Группа номенклатуры",
    "Вид номенклатуры",
    "Артикул",
    "Штрихкод",
    "Производитель",
    "Марка (бренд)",
    "Коллекция",
    "ID товара",
    "Номенклатура",
    "Название товара на сайте",
    "Характеристика",
    "УИД",
    "Количество",
    "Выручка",
]


# Чтение исходных данных из excel
def read_excel(file):
    df = pd.read_excel(file, dtype=str, skipfooter=1)
    df["Дата документа"] = pd.to_datetime(
        df["Дата документа"], dayfirst=True, errors="coerce"
    )
    df["Дата Заказа клиента"] = pd.to_datetime(
        df["Дата Заказа клиента"], dayfirst=True, errors="coerce"
    )
    df["Количество"] = df["Количество"].astype(float)
    df["Выручка"] = df["Выручка"].astype(float)
    return df


# # Обновление продаж
# def update_sales(conn: DuckDBPyConnection):
#     df = conn.sql('select "Дата документа" as date  from raw').df()
#     min_date = df["date"].min().date()
#     max_date = df["date"].max().date()

#     sales = conn.sql(
#         """
#         SELECT
#     t."Дата документа"::date as date,
#     case when COALESCE(t."Выручка", 0) > 0 then 'Sales' else 'Return' end as operation,
#     case when COALESCE(t."Выручка", 0) > 0 then COALESCE(t."Выручка", 0)::double else 0::double end as dt,
#     case when COALESCE(t."Выручка", 0) < 0 then abs(COALESCE(t."Выручка", 0))::double else 0::double end as cr,
#     case when COALESCE(t."Выручка", 0) > 0 then COALESCE(t."Количество", 0)::double else 0::double end as quant_dt,
#     case when COALESCE(t."Выручка", 0) < 0 then abs(COALESCE(t."Количество", 0))::double else 0::double end as quant_cr,
#         i.id::bigint as item_id,
#         s.id::bigint as store_id,
#         a.id::bigint as agent_id,
#         t."Заказ клиента"::text as client_order,
#         t."Дата Заказа клиента"::text as client_order_date,
#         t."Номер Заказа клиента"::text as client_order_number,
#         m.id::bigint as manager_id,
#         t."Склад"::text as warehouse,
#         b.id::bigint as barcode_id,
#         t."Характеристика"::text as spec,
#         t."УИД"::text as order_guid
#         FROM raw t
#         left join items as i on i.fullname = t."Номенклатура"
#         left join stores as s on LOWER(s.name) = LOWER(t."Подразделение")
#         left join agents as a on a.name = t."Агент"
#         left join managers as m on m.name = t."Менеджер"
#         left join barcodes as b on b.barcode = t."Штрихкод"
        
#     """
#     )

#     conn.register("sales", sales.df())

#     mysql_conn = get_mysql_conn()

#     rows = sales.fetchall()

#     with mysql_conn.cursor() as cur:

#         cur.execute(
#             "DELETE FROM sales_salesdata WHERE date BETWEEN %s AND %s",
#             (min_date, max_date),
#         )
#         mysql_conn.commit()

#         cur.executemany(
#             """
#             INSERT INTO sales_salesdata (
#                 date,
#                 operation,
#                 dt,
#                 cr,
#                 quant_dt,
#                 quant_cr,
#                 item_id,
#                 store_id,
#                 agent_id,
#                 client_order,
#                 client_order_date,
#                 client_order_number,
#                 manager_id,
#                 warehouse,
#                 barcode_id,
#                 spec,
#                 order_guid
                
#             )
#             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             rows,
#         )

#     mysql_conn.commit()
#     return f"добавлена реализация с {min_date} по {max_date}"




# Обновление продаж
def update_sales(conn: DuckDBPyConnection):
    df = conn.sql('select "Дата документа" as date  from raw').df()
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    sales = conn.sql(
        """
        SELECT
    t."Дата документа"::date as date,
    case when COALESCE(t."Выручка", 0) > 0 then 'Sales' else 'Return' end as operation,
    case when COALESCE(t."Выручка", 0) > 0 then COALESCE(t."Выручка", 0)::double else 0::double end as dt,
    case when COALESCE(t."Выручка", 0) < 0 then abs(COALESCE(t."Выручка", 0))::double else 0::double end as cr,
    case when COALESCE(t."Выручка", 0) > 0 then COALESCE(t."Количество", 0)::double else 0::double end as quant_dt,
    case when COALESCE(t."Выручка", 0) < 0 then abs(COALESCE(t."Количество", 0))::double else 0::double end as quant_cr,
        i.id::bigint as item_id,
        s.id::bigint as store_id,
        a.id::bigint as agent_id,
        t."Заказ клиента"::text as client_order,
        t."Дата Заказа клиента"::text as client_order_date,
        t."Номер Заказа клиента"::text as client_order_number,
        m.id::bigint as manager_id,
        t."Склад"::text as warehouse,
        b.id::bigint as barcode_id,
        t."Характеристика"::text as spec,
        t."УИД"::text as order_guid
        FROM raw t
        left join items as i on i.fullname = t."Номенклатура"
        left join stores as s on LOWER(s.name) = LOWER(t."Подразделение")
        left join agents as a on a.name = t."Агент"
        left join managers as m on m.name = t."Менеджер"
        left join barcodes as b on b.barcode = t."Штрихкод"
        where i.id is not null
    """
    )

    conn.register("sales", sales.df())

    rows = sales.fetchall()
    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.execute("SET SESSION innodb_lock_wait_timeout = 500")
            cur.execute(
                "DELETE FROM sales_salesdata WHERE date BETWEEN %s AND %s",
                (min_date, max_date),
            )

            cur.executemany(
                """
                INSERT INTO sales_salesdata (
                    date,
                    operation,
                    dt,
                    cr,
                    quant_dt,
                    quant_cr,
                    item_id,
                    store_id,
                    agent_id,
                    client_order,
                    client_order_date,
                    client_order_number,
                    manager_id,
                    warehouse,
                    barcode_id,
                    spec,
                    order_guid
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows,
            )

        mysql_conn.commit()
        return f"добавлена реализация с {min_date} по {max_date}"

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()


# Обновление справочника номенклатур
def update_items(conn: DuckDBPyConnection):
    fullnames = conn.sql(
        """
        select distinct id, fullname
        from mysql_db.djangodb.corporate_items
    """
    )

    conn.register("items", fullnames.df())

    new_items = conn.sql(
        """
        SELECT DISTINCT
            t."Номенклатура"::text as fullname,
            COALESCE(t."Название товара на сайте",t."Номенклатура")::text as name,
            t."Артикул"::text as article,
            min(t."Дата документа")::date as init_date,
            b.id::bigint as brend_id,
            m.id::bigint as manufacturer_id,
            t."ID товара" as im_id,
            t."Группа номенклатуры" as onec_cat,
            t."Вид номенклатуры" as onec_subcat
        from raw t
        left join brands as b on b.name = t."Марка (бренд)"
        left join manu as m on m.name = t."Производитель"
        where t."Номенклатура" not in (
            select distinct fullname from fullnames
        )
          and t."Номенклатура" is not null
        group by
            t."Номенклатура",
            t."Название товара на сайте",
            t."Артикул",
            b.id,
            m.id,
            t."ID товара",
            t."Группа номенклатуры",
            t."Вид номенклатуры"
    """
    )

    df = new_items.df()

    if df.empty:
        return "Нет новых номенклатур для добавления"

    mysql_conn = get_mysql_conn()
    rows = list(df.itertuples(index=False, name=None))
    l_items = ", ".join(df["name"].astype(str).tolist())

    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT IGNORE INTO corporate_items (
                    fullname,
                    name,
                    article,
                    init_date,
                    brend_id,
                    manufacturer_id,
                    im_id,
                    onec_cat,
                    onec_subcat
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(rows)} номенклатур было добавлено ({l_items})"

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()


# Обновление справочника бренда
def update_brand(conn: DuckDBPyConnection):
    brands = conn.sql(
        "select distinct id, name from mysql_db.djangodb.corporate_itembrend WHERE name IS NOT NULL"
    )

    conn.register("brands", brands.df())
    new_brands = conn.sql(
        'SELECT DISTINCT "Марка (бренд)" as name from raw where "Марка (бренд)" not in (SELECT name from brands) and "Марка (бренд)" is not null'
    )

    rows = new_brands.fetchall()

    if not rows:
        return "Нет новых брэндов для добавления"
    else:
        mysql_conn = get_mysql_conn()
        rows = new_brands.fetchall()
        l_stores = new_brands.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_itembrend (name)
                    VALUES (%s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} брендов было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление справочника бренда
def update_manufacturer(conn: DuckDBPyConnection):
    manu = conn.sql(
        "select distinct id, name from mysql_db.djangodb.corporate_itemmanufacturer WHERE name IS NOT NULL"
    )

    conn.register("manu", manu.df())
    new_manu = conn.sql(
        """ 
        SELECT DISTINCT
        "Производитель" as name,
        'RU' as country
        from raw 
        where 
        "Производитель" not in (SELECT name from manu) 
        and "Производитель" is not null        
        """
    )

    rows = new_manu.fetchall()

    if not rows:
        return "Нет новых производителей для добавления"
    else:
        mysql_conn = get_mysql_conn()
        rows = new_manu.fetchall()
        l_stores = new_manu.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_itemmanufacturer (name, country)
                    VALUES (%s, %s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} производителей было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление справочника коллекции
def update_collections(conn: DuckDBPyConnection):

    cols = conn.sql(
        "select distinct id, name from mysql_db.djangodb.corporate_itemcollections WHERE name IS NOT NULL"
    )

    conn.register("collections", cols.df())

    new_cols = conn.sql(
        'SELECT DISTINCT "Коллекция" as name from raw where "Коллекция" not in (SELECT name from cols) and "Коллекция" is not null'
    )

    rows = new_cols.fetchall()

    if not rows:
        return "Нет новых Колекций для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_cols.fetchall()
        l_stores = new_cols.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_itemcollections (name)
                    VALUES (%s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} коллекций было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление справочника менеджеров
def update_managers(conn: DuckDBPyConnection):

    managers = conn.sql(
        "select distinct id, name from mysql_db.djangodb.corporate_managers WHERE name IS NOT NULL"
    )

    conn.register("managers", managers.df())

    new_managers = conn.sql(
        """ 
        SELECT DISTINCT 
        "Менеджер" as name,
        "Менеджер" as report_name        
        from raw where "Менеджер" not in (SELECT name from managers) 
        and "Менеджер" is not null 
        """
    )

    rows = new_managers.fetchall()

    if not rows:
        return "Нет новых менеджеров для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_managers.fetchall()
        l_stores = new_managers.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_managers (name, report_name)
                    VALUES (%s, %s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} менеджеров было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление справочника агентов
def update_agents(conn: DuckDBPyConnection):

    agents = conn.sql(
        "select distinct id, name from mysql_db.djangodb.corporate_agents WHERE name IS NOT NULL"
    )

    conn.register("agents", agents.df())

    new_agents = conn.sql(
        """
        SELECT DISTINCT 
        "Агент" as name,
        "Агент" as report_name        
        from raw where "Агент" not in (SELECT name from agents) 
        and "Агент" is not null 
        """
    )

    rows = new_agents.fetchall()

    if not rows:
        return "Нет новых агентов для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_agents.fetchall()
        l_stores = new_agents.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_agents (name, report_name)
                    VALUES (%s, %s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} агентов было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление справочника магазинов
def update_stores(conn: DuckDBPyConnection):

    stores = conn.sql(
        "select distinct id, LOWER(name) as name from mysql_db.djangodb.corporate_stores WHERE name IS NOT NULL"
    )

    conn.register("stores", stores.df())

    new_stores = conn.sql(
        """ 
        select distinct 
        "Подразделение" as name,
        'RETAIL' as chanel,
        '' as adress,
        NULL as gr_id
        from raw
        where LOWER("Подразделение") not in (select name from stores) 
        and "Подразделение" is not null       
        """
    )

    rows = new_stores.fetchall()

    if not rows:
        return "Нет новых магазинов для добавления"

    else:

        mysql_conn = get_mysql_conn()
        rows = new_stores.fetchall()
        l_stores = new_stores.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_stores (name, chanel, adress, gr_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} магазинов было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление справочника баркодов
def update_barcodes(conn: DuckDBPyConnection):

    barcodes = conn.sql(
        "select distinct id, barcode from mysql_db.djangodb.corporate_barcode WHERE barcode IS NOT NULL"
    )

    conn.register("barcodes", barcodes.df())

    new_barcodes = conn.sql(
        """ 
        select distinct 
        "Штрихкод"::text as barcode,
        string_agg(DISTINCT "Характеристика", ', ' ORDER BY "Характеристика") as spec        
        from raw
        where "Штрихкод"::text not in (select barcode from barcodes) 
        and "Штрихкод" is not null    
        group by   barcode 
        """
    )

    rows = new_barcodes.fetchall()

    if not rows:
        return "Нет новых баркодов для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_barcodes.fetchall()
        l_stores = new_barcodes.df()
        l_stores = l_stores["barcode"].tolist()
        l_stores = ", ".join(l_stores)

        mysql_conn = get_mysql_conn()

        try:
            with mysql_conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT IGNORE INTO corporate_barcode (barcode, spec)
                    VALUES (%s, %s)
                    """,
                    rows,
                )

            mysql_conn.commit()
            return f"{len(rows)} баркодов было добавлено ({l_stores})"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()


# Обновление m2m
def m2m_update(conn: DuckDBPyConnection):
    item_barcode = conn.sql("select distinct item_id, barcode_id from sales").fetchall()
    item_collection = conn.sql(
        """ 
        SELECT distinct
        i.id as items_id,
        c.id as itemcollections_id
        from raw t
        join items as i on i.fullname = t."Номенклатура"
        join collections as c on c.name = t."Коллекция"
                
        """
    ).fetchall()

    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT IGNORE INTO corporate_items_barcode (items_id, barcode_id)
                VALUES (%s,%s)
                """,
                item_barcode,
            )

            cur.executemany(
                """
                INSERT IGNORE INTO corporate_items_collection (items_id, itemcollections_id)
                VALUES (%s,%s)
                """,
                item_collection,
            )

        mysql_conn.commit()
        return "M2M обновлены"

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()


# Обновление MV
def refresh_mv_daily_sales():
    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS mv_daily_sales")
            cur.execute("""
                CREATE TABLE mv_daily_sales AS
                SELECT * FROM daily_sales
            """)
            cur.execute("""
                ALTER TABLE mv_daily_sales
                ADD UNIQUE KEY ux_mv_daily_sales_date (`date`)
            """)

        mysql_conn.commit()
        return "MV UPDATED"

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()

def update_mv_orders():
        q = """
        CREATE TABLE IF NOT EXISTS mv_orders
            SELECT
            x.orders_id,
            ord.client_order_type,
            ord.client_order,
            ord.client_order_number,
            ord.client_order_date,    
            min(x.date) as order_min_date,
            max(x.date) as order_max_date,
            DATEDIFF(MAX(x.date), MIN(x.date)) + 1 AS realization_duration,
            DATEDIFF(MAX(x.date),ord.client_order_date) + 1 AS order_duration,
            sum(x.dt) as sales,
            sum(x.cr) as returns,
            sum(x.dt-x.cr) as amount,
            sum(case when parent_id != 86 then x.dt-x.cr else 0 end) as items_amount,
            sum(case when parent_id = 86 then x.dt-x.cr else 0 end) as service_amount,
            sum(case when parent_id != 86 then x.quant_dt-x.quant_cr else 0 end) as items_quant,
            count(distinct(case when parent_id != 86 then x.fullname  else NULL end)) as unique_items,
            GROUP_CONCAT(DISTINCT manager_name ORDER BY manager_name SEPARATOR ', ') as manager_name
            FROM (
            SELECT  
            d.orders_id,
            d.date,
            i.fullname,
            cat.parent_id,
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
            LEFT JOIN corporate_items as i on d.item_id = i.id
            LEFT JOIN corporate_cattree as cat on cat.id = i.cat_id
            LEFT JOIN corporate_barcode as b on d.barcode_id = b.id
            LEFT JOIN corporate_managers as mn on d.manager_id = mn.id
            LEFT JOIN corporate_agents as a on a.id = d.agent_id
            LEFT JOIN corporate_stores as store on store.id = d.store_id
            LEFT JOIN corporate_storegroups as sg on sg.id = store.gr_id
            ) x
            join sales_salesorders as ord on ord.id = x.orders_id
            group by x.orders_id
            order by ord.client_order_date desc;  
        
        """
        # mysql_conn = get_mysql_conn()
        # with mysql_conn.cursor() as cursor:
        #     cursor.execute("DROP TABLE IF EXISTS mv_orders")
        #     cursor.execute(q)
        #     cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_manager (manager_name(100));")
        #     cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_date (client_order_date);")
        #     cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_order_date (client_order, client_order_date);")
            
        # return 'all good'
        
        
        mysql_conn = get_mysql_conn()
        try:
            with mysql_conn.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS mv_orders")
                cursor.execute(q)
                cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_manager (manager_name(100));")
                cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_date (client_order_date);")
                cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_order_date (client_order, client_order_date);")

            mysql_conn.commit()
            return "all good"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()



# def update_salesorders():
        
#     q_update_salesorders = """
#     INSERT IGNORE INTO sales_salesorders
#     (client_order, client_order_date, client_order_number, client_order_type)
#     SELECT DISTINCT
#     client_order,
#     client_order_date,
#     client_order_number,

#     CASE
#         WHEN client_order_number RLIKE '^(Реализация товаров и услуг|Возврат товаров от клиента)'
#         THEN 'Продажи без заказа'
#         WHEN client_order_number RLIKE '^Отчет комиссионера \\(агента\\) о продажах'
#         THEN 'Комиссионные продажи'
#         WHEN client_order_number RLIKE '^(Отчет о розничных возвратах|Отчет о розничных продажах)'
#         THEN 'Розничные продажи'
#         ELSE 'Заказ клиента'
#     END AS client_order_type
#     FROM sales_salesdata
#     WHERE client_order IS NOT NULL
#     AND client_order_number IS NOT NULL;  
#     """
        
#     q_update_relations = """
#     UPDATE sales_salesdata AS t
#         JOIN sales_salesorders AS s
#         ON t.client_order <=> s.client_order
#         AND t.client_order_date <=> s.client_order_date
#         AND t.client_order_number <=> s.client_order_number
#         SET t.orders_id = s.id;
#     """

#     mysql_conn = get_mysql_conn()

#     try:
#         with mysql_conn.cursor() as cursor:
#             cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
#             cursor.execute("TRUNCATE TABLE sales_salesorders;")
#             cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
#             cursor.execute(q_update_salesorders)
#             cursor.execute(q_update_relations)

#         mysql_conn.commit()
#         return "sales_salesorders updated"

#     except Exception:
#         mysql_conn.rollback()
#         raise

#     finally:
#         mysql_conn.close()




def update_salesorders():
        
        """
        mysql_conn = get_mysql_conn()
        try:
            with mysql_conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                cursor.execute("TRUNCATE TABLE sales_salesorders;")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
                cursor.execute(q_update_salesorders)
                cursor.execute(q_update_relations)

            mysql_conn.commit()
            return "all good"

        except Exception:
            mysql_conn.rollback()
            raise

        finally:
            mysql_conn.close()

def update_sales_with_client_orders():
    q = """
        UPDATE sales_salesdata
            SET
            client_order = CASE
                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Реализация товаров и услуг'
                THEN TRIM(REPLACE(client_order_number, 'Реализация товаров и услуг', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Возврат товаров от клиента'
                THEN TRIM(REPLACE(client_order_number, 'Возврат товаров от клиента', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Отчет комиссионера \\(агента\\) о продажах'
                THEN TRIM(REPLACE(client_order_number, 'Отчет комиссионера (агента) о продажах', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Отчет о розничных возвратах'
                THEN TRIM(REPLACE(client_order_number, 'Отчет о розничных возвратах', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Отчет о розничных продажах'
                THEN TRIM(REPLACE(client_order_number, 'Отчет о розничных продажах', ''))

                ELSE client_order
            END,

            client_order_date = CASE
                WHEN client_order_date IS NULL THEN
                DATE(
                    STR_TO_DATE(
                    SUBSTRING_INDEX(client_order_number, 'от ', -1),
                    '%d.%m.%Y %H:%i:%s'
                    )
                )
                ELSE client_order_date
            END
            WHERE client_order_number IS NOT NULL
            AND (
                client_order IS NULL OR client_order = '<Продажи без заказа>'
                OR client_order_date IS NULL
            );
        """
        mysql_conn = get_mysql_conn()
        try:
            with mysql_conn.cursor() as cursor:
                cursor.execute(q)
            mysql_conn.commit()
            return "all good"
        except Exception:
            mysql_conn.rollback()
            raise
        finally:
            mysql_conn.close()


# Запускаем халабуду
def main(file):
    conn: DuckDBPyConnection = get_duckdb_conn()
    log = []

    
    conn.register("raw", read_excel(file))

    log.append(update_brand(conn))
    log.append(update_manufacturer(conn))
    log.append(update_collections(conn))
    log.append(update_managers(conn))
    log.append(update_agents(conn))
    log.append(update_stores(conn))
    log.append(update_barcodes(conn))
    log.append(update_items(conn))

    # 2. Основная загрузка продаж
    log.append(update_sales(conn))
    log.append(m2m_update(conn))

    # 3. Обновление заказов
    print("Продажи загружены. Обновляем заказы...")
    log.append(update_sales_with_client_orders())
    log.append(update_salesorders())

    # 4. Перестройка витрин
    print("Заказы обновлены. Перестраиваем витрины...")
    log.append(refresh_mv_daily_sales())
    log.append(update_mv_orders())

    print("Перестраиваем mv_orders_summary_table...")
    log.append(rebuild_orders_summary())

    return "; \n".join(log)

   


# print(main(file))
