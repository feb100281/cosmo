import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from .db_engine import get_duckdb_conn, get_mysql_conn
from pprint import pprint


# Тестовый файл - УБРАТЬ ПОТОМ И ПЕРЕДАВАТЬ В MAIN ИЗ ДЖАНГО

file = '/Users/pavelustenko/Downloads/заказы 2026-04-13.xlsx'

REGISTERED_COLUMS = [
    "GUID_ЗК",
    "GUID_Номенклатуры",
    "GUID_Характеристики",
    "Номер Заказа",
    "ДатаИВремяСоздания",
    "Склад",
    "Подразделение",
    "Менеджер",
    "Клиент",
    "Тип операции",
    "РабочееНаименование",
    "Артикул",
    "Штрихкод",
    "Кол.",
    "Цена полная",
    "СуммаРучнойСкидки",
    "% РучнойСкидки",
    "СуммаАвтоСкидки",
    "% Авто скидки",
    "СуммаАгентскойСкидки",
    "% АгентскойСкидки",
    "Итоговая цена",
    "Итоговая сумма",
    "ПричинаОтмены",
    "Дата и время изменения",
    "Статус",
]


def read_excel(file):
    fdf = pd.read_excel(file, skiprows=1, dtype=str)
    cols = []
    for col in fdf.columns:
        if col.startswith("Unnamed"):
            continue
        else:
            cols.append(col)

    df = fdf[cols].copy()
    df["ДатаИВремяСоздания"] = pd.to_datetime(df["ДатаИВремяСоздания"], dayfirst=True)
    df["Дата и время изменения"] = pd.to_datetime(
        df["ДатаИВремяСоздания"], dayfirst=True
    )
    df["Кол."] = (
        df["Кол."]
        .astype(str)
        .str.replace(r"\s+", "", regex=True)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    return df


def update_orders(conn: DuckDBPyConnection):
    orders = conn.sql(
        """
        SELECT DISTINCT
            "GUID_ЗК" AS id,
            "Номер Заказа" || ' от ' || strftime("ДатаИВремяСоздания", '%d.%m.%Y')::TEXT AS fullname,
            "Номер Заказа"::TEXT AS number,
            "ДатаИВремяСоздания"::DATE AS date_from,
            MAX("Дата и время изменения")::DATE AS update_at,
            CASE
                WHEN string_agg(DISTINCT "ПричинаОтмены", ', ' ORDER BY "ПричинаОтмены") IS NULL
                THEN FALSE
                ELSE TRUE
            END AS is_cancelled,
            string_agg(DISTINCT "ПричинаОтмены", ', ' ORDER BY "ПричинаОтмены") AS cancellation_reason,
            string_agg(DISTINCT "Статус", ', ' ORDER BY "Статус") AS status,
            string_agg(DISTINCT "Клиент", ', ' ORDER BY "Клиент") AS client,
            string_agg(DISTINCT "Менеджер", ', ' ORDER BY "Менеджер") AS manager,
            string_agg(DISTINCT "Тип операции", ', ' ORDER BY "Тип операции") AS oper_type,
            string_agg(DISTINCT "Подразделение", ', ' ORDER BY "Подразделение") AS store
        FROM raw
        WHERE "GUID_ЗК" IS NOT NULL
        GROUP BY
            "GUID_ЗК",
            "Номер Заказа",
            "ДатаИВремяСоздания"
        """
    )

    rows = orders.fetchall()
    conn.register("orders", orders)

    if not rows:
        return "No orders found"

    mysql_conn = get_mysql_conn()

    with mysql_conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        cur.execute("TRUNCATE TABLE orders_orderitem")
        cur.execute("TRUNCATE TABLE orders_order")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")

        cur.executemany(
            """
            INSERT INTO orders_order(
                id,
                fullname,
                number,
                date_from,
                update_at,
                is_cancelled,
                cancellation_reason,
                status,
                client,
                manager,
                oper_type,
                store
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            rows,
        )

    mysql_conn.commit()
    return "Orders перезаписаны"


def update_items(conn: DuckDBPyConnection):
    fullnames = conn.sql(
        """
        select distinct id, fullname
        from mysql_db.djangodb.corporate_items
        where fullname is not null
    """
    ).df()

    conn.register("fullnames", fullnames)

    new_items = conn.sql(
        """
        SELECT
            t."РабочееНаименование"::text as fullname,
            'Не указано'::text as name,
            min(t."Артикул"::text) as article,
            min(t."ДатаИВремяСоздания"::date) as init_date
        from raw t
        left join fullnames f
            on f.fullname = t."РабочееНаименование"
        where t."РабочееНаименование" is not null
          and trim(t."РабочееНаименование"::text) <> ''
          and f.fullname is null
        group by t."РабочееНаименование"
    """
    )

    df = new_items.df()

    if df.empty:
        return "Нет новых номенклатур для добавления"

    mysql_conn = get_mysql_conn()
    rows = list(df.itertuples(index=False, name=None))
    l_items = ", ".join(df["fullname"].astype(str).tolist())

    with mysql_conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO corporate_items (
                fullname,
                name,
                article,
                init_date
            )
            VALUES (%s, %s, %s, %s)
            """,
            rows,
        )

    mysql_conn.commit()
    return f"{len(rows)} номенклатур было добавлено ({l_items})"


def update_barcodes(conn: DuckDBPyConnection):

    barcodes = conn.sql(
        "select distinct id, barcode from mysql_db.djangodb.corporate_barcode WHERE barcode IS NOT NULL"
    )

    conn.register("barcodes", barcodes.df())

    new_barcodes = conn.sql(
        """ 
        select distinct 
        "Штрихкод"::text as barcode             
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

        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO corporate_barcode (barcode)
                VALUES (%s)
                
            """,
                rows,
            )
        mysql_conn.commit()
        return f"{len(rows)} баркодов было добавлено ({(l_stores)})"


def update_orders_items(conn: DuckDBPyConnection):

    orders_items = conn.sql(
        """ 
        SELECT
        COALESCE(t."Кол."::double,0) as qty,
        COALESCE(t."Итоговая сумма"::double,0) / COALESCE(t."Кол."::double,1) as price,
        COALESCE(t."Итоговая сумма"::double,0) as amount,
        i.id::bigint as item_id,
        t."GUID_ЗК" as order_id,
        b.id::bigint as barcode_id
        from raw t
        left join fullnames as i on i.fullname = t."РабочееНаименование"
        left join barcodes as b on b.barcode = t."Штрихкод"  
        """
    )
    conn.register("orders_items", orders_items)

    rows = orders_items.fetchall()

    mysql_conn = get_mysql_conn()

    with mysql_conn.cursor() as cur:
        cur.executemany(
            """
                INSERT INTO orders_orderitem (
                    qty,
                    price,
                    amount,
                    item_id,
                    order_id,
                    barcode_id                    
                )
                VALUES (%s,%s,%s,%s,%s,%s)                
            """,
            rows,
        )

    mysql_conn.commit()
    return "НОМЕНКЛАТУРЫ В ЗАКАЗАХ ОБНОВЛЕНЫ"


def main(file):
    conn: DuckDBPyConnection = get_duckdb_conn()
    log = []
    conn.register("raw", read_excel(file))
    log.append(update_orders(conn))
    log.append(update_items(conn))
    log.append(update_barcodes(conn))
    log.append(update_orders_items(conn))

    return "; \n".join(log)


print(main(file))
