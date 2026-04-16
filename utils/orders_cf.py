#  utils/orders_cf.py
import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from .db_engine import get_duckdb_conn, get_mysql_conn
from pprint import pprint


# Тестовый файл - УБРАТЬ ПОТОМ И ПЕРЕДАВАТЬ В MAIN ИЗ ДЖАНГО

file = "/Users/daria/Desktop/2026-04-14/Pay_2026_04_14.xlsx"

REGISTERED_COLS = [
    "GUID_ЗК",
    "Дата операции",
    "Тип операции",
    "Назначение операции",
    "Касса",
    "Номер документа",
    "Сумма операции",
    "Подразделение",
    "Регистратор",
]


def read_excel(file):
    fdf = pd.read_excel(file, skiprows=1, dtype=str)

    cols = [col for col in fdf.columns if not str(col).startswith("Unnamed")]
    df = fdf[cols].copy()

    df["Дата операции"] = pd.to_datetime(
        df["Дата операции"],
        format="%d.%m.%y",
        errors="coerce",
    )

    df["Сумма операции"] = (
        df["Сумма операции"]
        .fillna("")
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Сумма операции"] = pd.to_numeric(df["Сумма операции"], errors="coerce")

    return df

def update_cashflow(conn:DuckDBPyConnection):
    cf = conn.sql(
        """ 
        SELECT
        "GUID_ЗК"::text as order_guid,
        "Дата операции"::date as date,
        "Тип операции"::text as oper_type,
        "Назначение операции"::text as oper_name,
        "Касса"::text as cash_deck,
        "Номер документа"::text as doc_number,
        "Сумма операции"::double as amount,
        "Подразделение"::text as store,
        "Регистратор"::text as register
        from raw            
        """
    )
    conn.register("order_cf",cf)
    rows = cf.fetchall()  
    
    mysql_conn = get_mysql_conn()

    with mysql_conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        cur.execute("TRUNCATE TABLE orders_orderscf")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")

        cur.executemany(
            """ 
            INSERT INTO orders_orderscf(
                order_guid,
                date,
                oper_type,
                oper_name,
                cash_deck,
                doc_number,
                amount,
                store,
                register
                )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)               
            
            """,
            rows,
        )
    mysql_conn.commit()
    return "ALL DONE"

def main(file):
    conn: DuckDBPyConnection = get_duckdb_conn()
    log = []
    conn.register("raw", read_excel(file))
    log.append(update_cashflow(conn))
    return "; \n".join(log)


# print(main(file))


