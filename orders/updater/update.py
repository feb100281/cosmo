import duckdb
from duckdb import DuckDBPyConnection
import pandas as pd
from conns import get_engine
from sqlalchemy import engine, text


# Тестовый файл - УБРАТЬ ПОТОМ И ПЕРЕДАВАТЬ В MAIN ИЗ ДЖАНГО

file = '/Users/pavelustenko/Downloads/ЗАКАЗЫ 2026-04-05.xlsx'

def get_excel_data(file):
    fdf = pd.read_excel(file,skiprows=1)
    cols = []
    for col in fdf.columns:
        if col.startswith('Unnamed'):
            continue
        else:
            cols.append(col)

    df = fdf[cols].copy()
    df['ДатаИВремяСоздания'] = pd.to_datetime(df['ДатаИВремяСоздания'],dayfirst=True)
    df['Дата и время изменения'] = pd.to_datetime(df['ДатаИВремяСоздания'],dayfirst=True)
    df['Кол.'] = (
    df['Кол.']
    .astype(str)
    .str.replace(r'\s+', '', regex=True)
    .str.replace(',', '.', regex=False)
    .astype(float)
    )
    
    
    return df

def get_items(mysql_conn):
    return pd.read_sql("select * from corporate_items",mysql_conn)

def chunked(seq, size=2000):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def register_orders(conn:DuckDBPyConnection):
    rel = conn.sql("""
        SELECT
            "GUID_ЗК" AS id,
            "Номер Заказа" || ' от ' || strftime("ДатаИВремяСоздания"::date, '%d.%m.%Y') AS fullname,
            "Номер Заказа" AS number,
            "ДатаИВремяСоздания"::date AS date_from,
            max("Дата и время изменения")::date AS update_at,
            CASE
                WHEN string_agg(DISTINCT "ПричинаОтмены", ', ') IS NULL THEN FALSE
                ELSE TRUE
            END AS is_cancelled,
            string_agg(DISTINCT "ПричинаОтмены", ', ' ORDER BY "ПричинаОтмены") AS cancellation_reason,
            string_agg(DISTINCT "Статус", ', ' ORDER BY "Статус") AS status
        FROM raw
        GROUP BY
            "GUID_ЗК",
            "Номер Заказа" || ' от ' || strftime("ДатаИВремяСоздания"::date, '%d.%m.%Y'),
            "Номер Заказа",
            "ДатаИВремяСоздания"::date
    """)
    return rel

def register_orders_items(conn:DuckDBPyConnection):
    rel = conn.sql(
        """ 
        SELECT
        x.order_id::text as order_id,
        x.fullname::text as fullname,
        x.order_article::text as order_article,
        x.order_barcode::text as order_barcode,
        x.qty::double as qty,
        x.price::double as price,
        x.amount::double as amount,
        i.id::bigint as item_id
        FROM(
        SELECT
        r."GUID_ЗК" as order_id,
        r.GUID_Номенклатуры as order_item_guid,
        r."РабочееНаименование" as fullname,        
        r."Штрихкод"  as order_barcode,     
        r."Артикул" as order_article,
        r."Кол." as qty,
        r."Итоговая сумма"::double / r."Кол."::double as price,
        r."Итоговая сумма" as amount
        from raw as r) x
        left join items as i on i.fullname = x.fullname  
        """
    )
    return rel
    

def import_orders(conn, mysql_conn):
    rel = conn.sql("""
        SELECT
            * from orders
    """)
    

    rows = rel.fetchall()
    if not rows:
        return 0

    data = [
        (
            str(row[0]) if row[0] is not None else None,  # id
            row[1],  # fullname
            row[2],  # number
            row[3],  # date_from
            row[4],  # update_at
            1 if row[5] else 0,  # is_cancelled
            row[6],  # cancellation_reason
            row[7],  # status
        )
        for row in rows
    ]

    sql = """
        INSERT INTO orders_order (
            id,
            fullname,
            number,
            date_from,
            update_at,
            is_cancelled,
            cancellation_reason,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            fullname = VALUES(fullname),
            number = VALUES(number),
            date_from = VALUES(date_from),
            update_at = VALUES(update_at),
            is_cancelled = VALUES(is_cancelled),
            cancellation_reason = VALUES(cancellation_reason),
            status = VALUES(status)
    """

    raw = mysql_conn.raw_connection()
    cursor = raw.cursor()
    try:
        total = 0
        for batch in chunked(data, 2000):
            cursor.executemany(sql, batch)
            total += len(batch)
        raw.commit()
        return total
    except Exception:
        raw.rollback()
        raise
    finally:
        cursor.close()
        raw.close()


def import_orders_items(conn:DuckDBPyConnection,mysql_conn):
    rel = conn.sql(
        """ 
        select * from orders
        
        """
    ).show()


def main(file):
    ddb_conn = duckdb.connect()
    mysql_conn = get_engine()
    ddb_conn.register("raw", get_excel_data(file))
    ddb_conn.register("items", get_items(mysql_conn))
    ddb_conn.register("orders", register_orders(ddb_conn))
    ddb_conn.register("orders_items",register_orders_items(ddb_conn))
    ddb_conn.sql("select t.order_id, t.fullname, o.status, o.is_cancelled from orders_items t join orders as o on o.id = t.order_id where item_id is null").show()
    # import_orders_items(ddb_conn, mysql_conn)
    # print("Total rows",import_orders(ddb_conn, mysql_conn))
    

main(file)
