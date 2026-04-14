import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from .db_engine import get_duckdb_conn, get_mysql_conn
from pprint import pprint


file = "/Users/pavelustenko/Downloads/ПРОДАЖИ 2026-04-05.xlsx"

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
    df = pd.read_excel(file,dtype=str)
    df["Дата документа"] = pd.to_datetime(df["Дата документа"], errors="coerce")
    df["Количество"] = df["Количество"].astype(float)
    df["Выручка"] = df["Выручка"].astype(float)
    return df


# Обновление справочника номенклатур
def get_new_items(conn: DuckDBPyConnection):
    fullnames = conn.sql(
        "select distinct fullname from mysql_db.djangodb.corporate_items"
    )
    new_items = conn.sql(
        """ 
        SELECT * from raw where "Марка (бренд)" not in (SELECT name from brands)
        """
    )
    if len(new_items) == 0:
        return "Нет новых брэндов для добавления"
    else:
        pass


# Обновление справочника бренда
def update_brand(conn: DuckDBPyConnection):
    brands = conn.sql(
        "select distinct name from mysql_db.djangodb.corporate_itembrend WHERE name IS NOT NULL"
    )
    new_brands = conn.sql(
        'SELECT DISTINCT * from raw where "Марка (бренд)" not in (SELECT name from brands) and "Марка (бренд)" is not null'
    )
    if len(new_brands) == 0:
        return "Нет новых брэндов для добавления"
    else:
        mysql_conn = get_mysql_conn()
        rows = new_brands.fetchall()
        l_stores = new_brands.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_itemcollections (name)
                VALUES (%s,)
                
            """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(new_brands)} брендов было добавлено ({(l_stores)})"


# Обновление справочника бренда
def update_manufacturer(conn: DuckDBPyConnection):
    manu = conn.sql(
        "select distinct name from mysql_db.djangodb.corporate_itemmanufacturer WHERE name IS NOT NULL"
    )
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
    if len(new_manu) == 0:
        return "Нет новых производителей для добавления"
    else:
        mysql_conn = get_mysql_conn()
        rows = new_manu.fetchall()
        l_stores = new_manu.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_itemmanufacturer (name, country)
                VALUES (%s, %s )
                
            """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(new_manu)} производителей было добавлено ({(l_stores)})"


# Обновление справочника коллекции
def update_collections(conn: DuckDBPyConnection):

    cols = conn.sql(
        "select distinct name from mysql_db.djangodb.corporate_itemcollections WHERE name IS NOT NULL"
    )

    new_cols = conn.sql(
        'SELECT DISTINCT "Коллекция" as name from raw where "Коллекция" not in (SELECT name from cols) and "Коллекция" is not null'
    )

    if len(new_cols) == 0:
        return "Нет новых Колекций для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_cols.fetchall()
        l_stores = new_cols.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_itemcollections (name)
                VALUES (%s,)
                
            """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(new_cols)} коллекций было добавлено ({(l_stores)})"


# Обновление справочника менеджеров
def update_managers(conn: DuckDBPyConnection):

    managers = conn.sql(
        "select distinct name from mysql_db.djangodb.corporate_managers WHERE name IS NOT NULL"
    )

    new_managers = conn.sql(
        """ 
        SELECT DISTINCT 
        "Менеджер" as name,
        "Менеджер" as report_name        
        from raw where "Менеджер" not in (SELECT name from managers) 
        and "Менеджер" is not null 
        """
    )

    if len(new_managers) == 0:
        return "Нет новых менеджеров для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_managers.fetchall()
        l_stores = new_managers.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_managers (name, report_name)
                VALUES (%s, %s )
                
            """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(new_managers)} менеджеров было добавлено ({(l_stores)})"


# Обновление справочника агентов
def update_agents(conn: DuckDBPyConnection):

    agents = conn.sql(
        "select distinct name from mysql_db.djangodb.corporate_agents WHERE name IS NOT NULL"
    )

    new_agents = conn.sql(
        """
        SELECT DISTINCT 
        "Агент" as name,
        "Агент" as report_name        
        from raw where "Агент" not in (SELECT name from agents) 
        and "Агент" is not null 
        """
    )

    if len(new_agents) == 0:
        return "Нет новых агентов для добавления"

    else:
        mysql_conn = get_mysql_conn()
        rows = new_agents.fetchall()
        l_stores = new_agents.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_agents (name, report_name)
                VALUES (%s, %s )
                
            """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(new_agents)} агентов было добавлено ({(l_stores)})"


# Обновление справочника магазинов
def update_stores(conn: DuckDBPyConnection):

    stores = conn.sql(
        "select distinct LOWER(name) as name from mysql_db.djangodb.corporate_stores WHERE name IS NOT NULL"
    )

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

    if len(new_stores) == 0:
        return "Нет новых магазинов для добавления"

    else:

        mysql_conn = get_mysql_conn()
        rows = new_stores.fetchall()
        l_stores = new_stores.df()
        l_stores = l_stores["name"].tolist()
        l_stores = ", ".join(l_stores)

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_stores (name, chanel, adress, gr_id)
                VALUES (%s, %s, %s, %s )
                
            """,
                rows,
            )

        mysql_conn.commit()
        return f"{len(new_stores)} магазинов было добавлено ({(l_stores)})"


# Обновление справочника баркодов
def update_barcodes(conn: DuckDBPyConnection):

    barcodes = conn.sql(
        "select distinct as barcode from mysql_db.djangodb.corporate_barcode WHERE barcode IS NOT NULL"
    )

    new_barcodes = conn.sql(
        """ 
        select distinct 
        "Штрихкод"::text as barcode,
        'RETAIL' as chanel,
        '' as adress,
        NULL as gr_id
        from raw
        where LOWER("Подразделение") not in (select name from stores) 
        and "Подразделение" is not null       
        """
    )

    if len(new_stores) == 0:
        return "Нет новых магазинов для добавления"
    
    
    
    
    mysql_conn = get_mysql_conn()

    barcode_with_spec = conn.sql(
        """ 
        SELECT DISTINCT
        "Штрихкод"::text as barcode,
        string_agg(DISTINCT "Характеристика", ', ' ORDER BY "Характеристика") as spec
        from raw
        where "Штрихкод" is not null
        group by "Штрихкод"
        """
    )
    rows = barcode_with_spec.fetchall()

    with mysql_conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO corporate_barcode (barcode, spec)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                spec = VALUES(spec)
        """,
            rows,
        )

    mysql_conn.commit()


def main(file):
    conn: DuckDBPyConnection = get_duckdb_conn()

    # conn.sql("USE mysql_db.djangodb")
    # conn.sql("SELECT * FROM sales_salesdata LIMIT 10").show()
    conn.register("raw", read_excel(file))
    conn.sql('select "Штрихкод" from raw').show()
    # print(update_brand(conn))
    # print(update_manufacturer(conn))
    # print(update_collections(conn))
    # print(update_managers(conn))
    # print(update_agents(conn))
    # print(update_stores(conn))
    # update_barcodes(conn)


main(file)
