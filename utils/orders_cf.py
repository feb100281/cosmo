#  utils/orders_cf.py
"""
Загрузка CF в orders_orderscf за период файла: операции внутри
[мин. дата; макс. дата] заменяются, остальные не меняются.
"""
import pandas as pd
from duckdb import DuckDBPyConnection
from .db_engine import get_duckdb_conn, get_mysql_conn


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


def _parse_dates(series: pd.Series) -> pd.Series:
    """dd.mm.yy, запасной вариант — dayfirst."""
    parsed = pd.to_datetime(series, format="%d.%m.%y", errors="coerce")
    missing = parsed.isna() & series.notna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            series[missing], dayfirst=True, errors="coerce"
        )
    return parsed


def read_excel(file):
    fdf = pd.read_excel(file, skiprows=1, dtype=str)

    cols = [col for col in fdf.columns if not str(col).startswith("Unnamed")]
    df = fdf[cols].copy()

    missing_cols = [c for c in REGISTERED_COLS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            "В файле CF не найдены колонки: " + ", ".join(missing_cols)
        )

    df["Дата операции"] = _parse_dates(df["Дата операции"])

    df["Сумма операции"] = (
        df["Сумма операции"]
        .fillna("")
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Сумма операции"] = pd.to_numeric(df["Сумма операции"], errors="coerce")

    return df


def update_cashflow(conn: DuckDBPyConnection, df: pd.DataFrame):
    bad_dates = int(df["Дата операции"].isna().sum())
    df = df[df["Дата операции"].notna()].copy()

    if df.empty:
        raise ValueError("В файле CF нет ни одной строки с корректной датой операции")

    date_from = df["Дата операции"].min().date()
    date_to = df["Дата операции"].max().date()

    conn.register("raw", df)
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
    rows = cf.fetchall()

    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM orders_orderscf WHERE date BETWEEN %s AND %s",
                (date_from, date_to),
            )
            deleted = cur.rowcount

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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows,
            )

        mysql_conn.commit()

    except Exception:
        mysql_conn.rollback()
        raise

    finally:
        mysql_conn.close()

    log = [
        f"Период файла: {date_from:%d.%m.%Y} – {date_to:%d.%m.%Y}",
        f"Заменено операций за период: удалено {deleted}, загружено {len(rows)}",
        "Данные вне периода сохранены",
    ]
    if bad_dates:
        log.append(f"Пропущено строк без даты операции: {bad_dates}")
    return "; ".join(log)


def main(file):
    conn: DuckDBPyConnection = get_duckdb_conn()
    df = read_excel(file)
    return update_cashflow(conn, df)
