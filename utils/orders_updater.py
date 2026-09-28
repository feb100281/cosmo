# utils/orders_updater.py
import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from .db_engine import column_collation, get_duckdb_conn, get_mysql_conn, get_engine
from pprint import pprint
from .orders_reporter import main as final_mv

# Тестовый файл - УБРАТЬ ПОТОМ И ПЕРЕДАВАТЬ В MAIN ИЗ ДЖАНГО

file = '/Users/daria/Desktop/2026-04-15/Orders_2026-04-15.xlsx'


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
        df["Дата и время изменения"], dayfirst=True
    )
    df["Кол."] = (
        df["Кол."]
        .astype(str)
        .str.replace(r"\s+", "", regex=True)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    return df


# def update_orders(conn: DuckDBPyConnection):
#     orders = conn.sql(
#         """
#         SELECT DISTINCT
#             "GUID_ЗК" AS id,
#             "Номер Заказа" || ' от ' || strftime("ДатаИВремяСоздания", '%d.%m.%Y')::TEXT AS fullname,
#             "Номер Заказа"::TEXT AS number,
#             "ДатаИВремяСоздания"::DATE AS date_from,
#             MAX("Дата и время изменения")::DATE AS update_at,
#             CASE
#                 WHEN string_agg(DISTINCT "ПричинаОтмены", ', ' ORDER BY "ПричинаОтмены") IS NULL
#                 THEN FALSE
#                 ELSE TRUE
#             END AS is_cancelled,
#             string_agg(DISTINCT "ПричинаОтмены", ', ' ORDER BY "ПричинаОтмены") AS cancellation_reason,
#             string_agg(DISTINCT "Статус", ', ' ORDER BY "Статус") AS status,
#             string_agg(DISTINCT "Клиент", ', ' ORDER BY "Клиент") AS client,
#             string_agg(DISTINCT "Менеджер", ', ' ORDER BY "Менеджер") AS manager,
#             string_agg(DISTINCT "Тип операции", ', ' ORDER BY "Тип операции") AS oper_type,
#             string_agg(DISTINCT "Подразделение", ', ' ORDER BY "Подразделение") AS store
#         FROM raw
#         WHERE "GUID_ЗК" IS NOT NULL
#         GROUP BY
#             "GUID_ЗК",
#             "Номер Заказа",
#             "ДатаИВремяСоздания"
#         """
#     )

#     rows = orders.fetchall()
#     conn.register("orders", orders)

#     if not rows:
#         return "No orders found"

#     mysql_conn = get_mysql_conn()

#     with mysql_conn.cursor() as cur:
#         cur.execute("SET FOREIGN_KEY_CHECKS = 0")
#         cur.execute("TRUNCATE TABLE orders_orderitem")
#         cur.execute("TRUNCATE TABLE orders_order")
#         cur.execute("SET FOREIGN_KEY_CHECKS = 1")

#         cur.executemany(
#             """
#             INSERT INTO orders_order(
#                 id,
#                 fullname,
#                 number,
#                 date_from,
#                 update_at,
#                 is_cancelled,
#                 cancellation_reason,
#                 status,
#                 client,
#                 manager,
#                 oper_type,
#                 store
#             )
#             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             rows,
#         )

#     mysql_conn.commit()
#     return "Orders перезаписаны"



# Загрузка за любой период: заказы из файла заменяются целиком по GUID_ЗК
# (шапка, состав, raw_orders) в одной транзакции, остальные не меняются.

RAW_ORDERS_COLUMNS = [
    "order_id", "number", "date_from", "warehouse", "store", "manager",
    "client", "oper_type", "fullname", "article", "barcode", "qty", "price",
    "amount", "cancellation_reason", "update_at", "status",
]


def _df_rows(df: pd.DataFrame) -> list:
    """NaN/NaT -> None."""
    work = df.astype(object).where(pd.notna(df), None)
    return [tuple(r) for r in work.itertuples(index=False, name=None)]


def _refresh_dictionaries(conn: DuckDBPyConnection):
    """Справочники после добавления новых товаров и штрихкодов."""
    fullnames = conn.sql(
        """
        select min(id) as id, fullname
        from mysql_db.djangodb.corporate_items
        where fullname is not null
        group by fullname
        """
    ).df()
    conn.register("fullnames", fullnames)

    barcodes = conn.sql(
        """
        select min(id) as id, barcode
        from mysql_db.djangodb.corporate_barcode
        where barcode is not null
        group by barcode
        """
    ).df()
    conn.register("barcodes", barcodes)


def build_orders(conn: DuckDBPyConnection) -> pd.DataFrame:
    return conn.sql(
        """
        SELECT
            "GUID_ЗК" AS id,
            min("Номер Заказа") || ' от ' || strftime(min("ДатаИВремяСоздания"), '%d.%m.%Y')::TEXT AS fullname,
            min("Номер Заказа")::TEXT AS number,
            min("ДатаИВремяСоздания")::DATE AS date_from,
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
        GROUP BY "GUID_ЗК"
        """
    ).df()


def build_orders_items(conn: DuckDBPyConnection) -> pd.DataFrame:
    return conn.sql(
        """
        SELECT
            COALESCE(t."Кол."::double,0) as qty,
            COALESCE(t."Итоговая сумма"::double / NULLIF(t."Кол."::double, 0), 0) as price,
            COALESCE(t."Итоговая сумма"::double,0) as amount,
            i.id::bigint as item_id,
            t."GUID_ЗК" as order_id,
            b.id::bigint as barcode_id
        from raw t
        left join fullnames as i on i.fullname = t."РабочееНаименование"
        left join barcodes as b on b.barcode = t."Штрихкод"
        where t."GUID_ЗК" is not null
        """
    ).df()


def build_raw_orders(conn: DuckDBPyConnection) -> pd.DataFrame:
    return conn.sql("""
        select
            t."GUID_ЗК"::text as order_id,
            t."Номер Заказа"::text as number,
            t."ДатаИВремяСоздания"::date as date_from,
            t."Склад"::text as warehouse,
            t."Подразделение"::text as store,
            COALESCE(t."Менеджер"::text,'Менеджер не указан') as manager,
            COALESCE(t."Клиент"::text,'Клиент не указан') as client,
            t."Тип операции"::text as oper_type,
            COALESCE(t."РабочееНаименование"::text, 'Номенклатура не указана') as fullname,
            COALESCE(t."Артикул"::text,'Нет арт.') as article,
            COALESCE(t."Штрихкод"::text,'Нет ШК') as barcode,
            COALESCE(t."Кол."::double,0) as qty,
            COALESCE(
                t."Итоговая сумма"::double / NULLIF(t."Кол."::double, 0),
                0
            ) as price,
            COALESCE(t."Итоговая сумма"::double,0) as amount,
            t."ПричинаОтмены"::text as cancellation_reason,
            t."Дата и время изменения"::date as update_at,
            t."Статус"::text as status
        from raw t
        where t."GUID_ЗК" is not null
    """).df()[RAW_ORDERS_COLUMNS]


def _table_exists(cur, table: str) -> bool:
    cur.execute("SHOW TABLES LIKE %s", (table,))
    return cur.fetchone() is not None


def upsert_orders(conn: DuckDBPyConnection) -> str:
    """Замена заказов из файла по GUID."""
    orders = build_orders(conn)
    if orders.empty:
        return "В файле нет заказов с GUID_ЗК"

    items = build_orders_items(conn)
    raw_orders = build_raw_orders(conn)
    order_ids = [(x,) for x in orders["id"].tolist()]

    mysql_conn = get_mysql_conn()
    raw_orders_missing = False

    try:
        with mysql_conn.cursor() as cur:
            # Для каждой таблицы — свой список GUID в её collation:
            # сравнение без COLLATE, индексы используются с обеих сторон.
            def ids_table(name: str, table: str, column: str) -> str:
                coll = column_collation(cur, table, column)
                cur.execute(f"DROP TEMPORARY TABLE IF EXISTS {name}")
                cur.execute(
                    f"CREATE TEMPORARY TABLE {name} (id VARCHAR(64) NOT NULL PRIMARY KEY) "
                    f"CHARACTER SET {coll.split('_')[0]} COLLATE {coll}"
                )
                cur.executemany(f"INSERT IGNORE INTO {name} (id) VALUES (%s)", order_ids)
                return name

            t_order = ids_table("tmp_ids_order", "orders_order", "id")
            t_item = ids_table("tmp_ids_orderitem", "orders_orderitem", "order_id")

            cur.execute(f"SELECT COUNT(*) FROM {t_order} t JOIN orders_order o ON o.id = t.id")
            existed = cur.fetchone()[0]

            cur.execute(f"DELETE oi FROM {t_item} t STRAIGHT_JOIN orders_orderitem oi ON oi.order_id = t.id")
            cur.execute(f"DELETE o FROM {t_order} t STRAIGHT_JOIN orders_order o ON o.id = t.id")

            if _table_exists(cur, "raw_orders"):
                # У raw_orders нет индекса по order_id: один проход по таблице с поиском по PK списка
                t_raw = ids_table("tmp_ids_raw", "raw_orders", "order_id")
                cur.execute(f"DELETE r FROM raw_orders r STRAIGHT_JOIN {t_raw} t ON t.id = r.order_id")
            else:
                raw_orders_missing = True

            cur.executemany(
                """
                INSERT INTO orders_order(
                    id, fullname, number, date_from, update_at, is_cancelled,
                    cancellation_reason, status, client, manager, oper_type, store
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                _df_rows(orders[[
                    "id", "fullname", "number", "date_from", "update_at",
                    "is_cancelled", "cancellation_reason", "status", "client",
                    "manager", "oper_type", "store",
                ]]),
            )

            cur.executemany(
                """
                INSERT INTO orders_orderitem (
                    qty, price, amount, item_id, order_id, barcode_id
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                _df_rows(items[["qty", "price", "amount", "item_id", "order_id", "barcode_id"]]),
            )

            if not raw_orders_missing:
                placeholders = ",".join(["%s"] * len(RAW_ORDERS_COLUMNS))
                cur.executemany(
                    f"INSERT INTO raw_orders ({','.join(RAW_ORDERS_COLUMNS)}) "
                    f"VALUES ({placeholders})",
                    _df_rows(raw_orders),
                )

            cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_upload_order_ids")

        mysql_conn.commit()

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()

    # первый запуск: raw_orders ещё нет
    if raw_orders_missing:
        engine = get_engine()
        raw_orders.to_sql(
            "raw_orders", con=engine, if_exists="append", index=False,
            chunksize=5000, method="multi",
        )

    d_min = orders["date_from"].min()
    d_max = orders["date_from"].max()
    period = ""
    if pd.notna(d_min) and pd.notna(d_max):
        period = f" (даты создания {pd.Timestamp(d_min):%d.%m.%Y} – {pd.Timestamp(d_max):%d.%m.%Y})"

    return (
        f"Заказов в файле: {len(orders)}{period}: обновлено {existed}, новых {len(orders) - existed}; "
        f"строк состава загружено: {len(items)}; остальные заказы в базе не тронуты"
    )


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

    rows = list(df.itertuples(index=False, name=None))
    l_items = ", ".join(df["fullname"].astype(str).tolist())

    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT IGNORE INTO corporate_items (
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

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()


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

    l_stores = ", ".join(new_barcodes.df()["barcode"].tolist())

    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.executemany(
                """
                INSERT IGNORE INTO corporate_barcode (barcode)
                VALUES (%s)
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


def main(file, rebuild_mv: bool = True):
    conn: DuckDBPyConnection = get_duckdb_conn()
    log = []

    conn.register("raw", read_excel(file))

    log.append(update_items(conn))
    log.append(update_barcodes(conn))
    _refresh_dictionaries(conn)

    log.append(upsert_orders(conn))

    if rebuild_mv:
        log.append(final_mv())

    return "; \n".join(log)
