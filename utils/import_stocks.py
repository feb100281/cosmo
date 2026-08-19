# # utils/import_stocks.py
# import duckdb
# from conns import get_engine
# import pandas as pd
# import os

# from dotenv import load_dotenv
# from sqlalchemy import text
# load_dotenv()

# db_user = os.getenv("DB_USER")
# db_pass = os.getenv("DB_PASSWORD")
# db_host = os.getenv("DB_HOST", "localhost")
# db_port = os.getenv("DB_PORT", "3306")
# db_name = os.getenv("DB_NAME")
# db_driver = os.getenv("DB_DRIVER", "mysql+pymysql")

# def duck_connection():
#     con = duckdb.connect(":memory:")
#     con.execute("INSTALL mysql")
#     con.execute("LOAD mysql")
#     con.execute(f"""
#         ATTACH '
#             host={os.getenv("DB_HOST", "localhost")}
#             port={os.getenv("DB_PORT", "3306")}
#             user={os.getenv("DB_USER")}
#             password={os.getenv("DB_PASSWORD")}
#             database={os.getenv("DB_NAME")}
#         '
#         AS mysql
#         (TYPE mysql);
#     """)

#     return con    
    

# def get_items():
#     eng =  get_engine() 
#     df = pd.read_sql("SELECT * FROM corporate_items",eng)
#     return df

# def get_file_data(file):
#     with duck_connection() as con:
#         con.register("items",get_items())
#         df = con.execute(
#             """ 
#             select
#             i.id as item_id,
#             x.fullname,
#             x.name,
#             CURRENT_DATE as init_date,
#             sum(available) as tot_available,
#             sum(ordered) as tot_ordered,
#             sum(available) + sum(ordered) as total,
#             list(DISTINCT barcode || ' - ' || available::text || ' шт.') as barcode_stocks,
#             list(DISTINCT barcode || ' - ' || ordered::text || ' шт.(дата поступления: '|| date_arrival ||')') as barcode_ordered,
#             list(DISTINCT warehouse || ' - ' || available::text || ' шт.') as warehouse_stocks,
#             list(DISTINCT warehouse || ' - ' || ordered::text || ' шт.') as warehouse_ordered
#             from(
#             SELECT 
#             "H" as fullname,
#             "N" as name,
#             "L" as warehouse,
#             "P" as barcode,
#             COALESCE("R",'0')::bigint as available,
#             COALESCE("T",'0')::bigint as ordered,
#             try_strptime("V", '%d.%m.%Y')::DATE as date_arrival
#             from(
#             SELECT *
#             FROM read_xlsx(
#                 ?,
#                 range='B3:V',
#                 header=false,
#                 all_varchar=true
#             )
#             where "B" is not null
#             )
#             ) x
#             left join items i on i.fullname = x.fullname
#             group by x.fullname, i.id, x.name,
#             CURRENT_DATE
#             ;            
#             """,parameters=[file,]
#         ).df()
#         con.register("stocks",df)     
        
#         mysql_con = get_engine()         
             
#         df.to_sql('stocks_data',mysql_con,index=False,if_exists='replace')
        
#         with mysql_con.begin() as conn:
#             conn.execute(text("""
#             INSERT IGNORE INTO corporate_items (
#                 fullname,
#                 name,
#                 init_date
#             )
#             SELECT
#                 fullname,
#                 name,
#                 init_date
#             FROM stocks_data
#             WHERE item_id IS NULL
#         """))

# file = '/Users/pavelustenko/Downloads/test.xlsx'  
# get_file_data(file)



# # utils/import_stocks.py

# from __future__ import annotations

# from datetime import date
# from typing import Any
# import json

# import duckdb
# import pandas as pd
# from dotenv import load_dotenv
# from sqlalchemy import text
# from sqlalchemy.types import BigInteger, Date, Text

# from conns import get_engine


# load_dotenv()


# # ============================================================================
# # Нормализация текста
# # ============================================================================

# def normalize_text(value: Any) -> str:
#     """
#     Нормализует текст для надежного сопоставления номенклатуры.

#     Убираем:
#     - None / NaN;
#     - пробелы по краям;
#     - неразрывные пробелы;
#     - narrow NBSP;
#     - zero-width space;
#     - BOM;
#     - табы и переносы;
#     - повторяющиеся пробелы.
#     """
#     if value is None:
#         return ""

#     try:
#         if pd.isna(value):
#             return ""
#     except (TypeError, ValueError):
#         pass

#     text_value = str(value)

#     replacements = {
#         "\u00a0": " ",
#         "\u202f": " ",
#         "\u2007": " ",
#         "\u200b": "",
#         "\ufeff": "",
#         "\t": " ",
#         "\r": " ",
#         "\n": " ",
#     }

#     for old, new in replacements.items():
#         text_value = text_value.replace(old, new)

#     return " ".join(text_value.split()).strip()


# def normalize_key(value: Any) -> str:
#     """Ключ сопоставления fullname."""
#     return normalize_text(value).casefold()


# # ============================================================================
# # corporate_items
# # ============================================================================

# def get_items() -> pd.DataFrame:
#     engine = get_engine()

#     return pd.read_sql(
#         """
#         SELECT
#             id,
#             fullname
#         FROM corporate_items
#         """,
#         engine,
#     )


# def build_item_map(items: pd.DataFrame) -> dict[str, int]:
#     """
#     normalized fullname -> item_id.

#     Если исторически есть несколько ID для одного нормализованного fullname,
#     используем минимальный ID — самый старый товар.
#     """
#     if items.empty:
#         return {}

#     work = items[["id", "fullname"]].copy()

#     work["_key"] = work["fullname"].map(normalize_key)
#     work["id"] = pd.to_numeric(work["id"], errors="coerce")

#     work = work.dropna(subset=["id"])
#     work = work[work["_key"] != ""].copy()

#     work["id"] = work["id"].astype(int)

#     mapping = (
#         work.groupby("_key", as_index=False)
#         .agg(id=("id", "min"))
#     )

#     return dict(zip(mapping["_key"], mapping["id"]))


# def assign_item_ids(df: pd.DataFrame) -> pd.DataFrame:
#     result = df.copy()

#     item_map = build_item_map(get_items())

#     result["_fullname_key"] = result["fullname"].map(normalize_key)
#     result["item_id"] = result["_fullname_key"].map(item_map)

#     return result


# # ============================================================================
# # XLSX
# # ============================================================================

# def read_file_data(file: str) -> pd.DataFrame:
#     """
#     Читает XLSX и агрегирует данные до уровня номенклатуры.
#     item_id здесь не присваиваем.
#     """
#     with duckdb.connect(":memory:") as con:
#         raw = con.execute(
#             """
#             SELECT
#                 "H" AS fullname,
#                 "N" AS name,
#                 "L" AS warehouse,
#                 "P" AS barcode,

#                 COALESCE(
#                     TRY_CAST(NULLIF(TRIM("R"), '') AS BIGINT),
#                     0
#                 ) AS available,

#                 COALESCE(
#                     TRY_CAST(NULLIF(TRIM("T"), '') AS BIGINT),
#                     0
#                 ) AS ordered,

#                 TRY_STRPTIME(
#                     NULLIF(TRIM("V"), ''),
#                     '%d.%m.%Y'
#                 )::DATE AS date_arrival

#             FROM read_xlsx(
#                 ?,
#                 range='B3:V',
#                 header=false,
#                 all_varchar=true
#             )

#             WHERE "B" IS NOT NULL
#             """,
#             [file],
#         ).df()

#     if raw.empty:
#         return raw

#     # ------------------------------------------------------------------
#     # Нормализация
#     # ------------------------------------------------------------------

#     for column in ["fullname", "name", "warehouse", "barcode"]:
#         raw[column] = raw[column].map(normalize_text)

#     raw = raw[raw["fullname"] != ""].copy()

#     raw["_fullname_key"] = raw["fullname"].map(normalize_key)

#     # ------------------------------------------------------------------
#     # Суммы
#     # ------------------------------------------------------------------

#     totals = (
#         raw.groupby("_fullname_key", as_index=False)
#         .agg(
#             fullname=("fullname", "first"),
#             name=("name", "first"),
#             tot_available=("available", "sum"),
#             tot_ordered=("ordered", "sum"),
#         )
#     )

#     totals["total"] = totals["tot_available"] + totals["tot_ordered"]
#     totals["init_date"] = pd.Timestamp(date.today())

#     # ------------------------------------------------------------------
#     # Детализация
#     # ------------------------------------------------------------------

#     detail_rows: list[dict[str, Any]] = []

#     for key, group in raw.groupby("_fullname_key", sort=False):
#         barcode_stocks: list[str] = []
#         barcode_ordered: list[str] = []
#         warehouse_stocks: list[str] = []
#         warehouse_ordered: list[str] = []

#         for _, row in group.iterrows():
#             barcode = normalize_text(row["barcode"])
#             warehouse = normalize_text(row["warehouse"])

#             available = int(row["available"] or 0)
#             ordered = int(row["ordered"] or 0)

#             if barcode:
#                 value = f"{barcode} - {available} шт."
#                 if value not in barcode_stocks:
#                     barcode_stocks.append(value)

#             if barcode and ordered != 0:
#                 value = f"{barcode} - {ordered} шт."

#                 if pd.notna(row["date_arrival"]):
#                     arrival = pd.Timestamp(
#                         row["date_arrival"]
#                     ).strftime("%Y-%m-%d")

#                     value += f"(дата поступления: {arrival})"

#                 if value not in barcode_ordered:
#                     barcode_ordered.append(value)

#             if warehouse:
#                 value = f"{warehouse} - {available} шт."
#                 if value not in warehouse_stocks:
#                     warehouse_stocks.append(value)

#                 value = f"{warehouse} - {ordered} шт."
#                 if value not in warehouse_ordered:
#                     warehouse_ordered.append(value)

#         detail_rows.append(
#             {
#                 "_fullname_key": key,
#                 "barcode_stocks": barcode_stocks,
#                 "barcode_ordered": barcode_ordered,
#                 "warehouse_stocks": warehouse_stocks,
#                 "warehouse_ordered": warehouse_ordered,
#             }
#         )

#     details = pd.DataFrame(detail_rows)

#     return totals.merge(
#         details,
#         on="_fullname_key",
#         how="left",
#         validate="one_to_one",
#     )


# # ============================================================================
# # Создание отсутствующих товаров
# # ============================================================================

# def create_missing_items(df: pd.DataFrame) -> int:
#     missing = df[df["item_id"].isna()].copy()

#     if missing.empty:
#         return 0

#     new_items = (
#         missing[
#             [
#                 "fullname",
#                 "name",
#                 "init_date",
#                 "_fullname_key",
#             ]
#         ]
#         .loc[lambda x: x["_fullname_key"] != ""]
#         .drop_duplicates(subset=["_fullname_key"], keep="first")
#     )

#     if new_items.empty:
#         return 0

#     engine = get_engine()

#     with engine.begin() as conn:
#         for _, row in new_items.iterrows():
#             conn.execute(
#                 text(
#                     """
#                     INSERT IGNORE INTO corporate_items
#                     (
#                         fullname,
#                         name,
#                         init_date
#                     )
#                     VALUES
#                     (
#                         :fullname,
#                         :name,
#                         :init_date
#                     )
#                     """
#                 ),
#                 {
#                     "fullname": row["fullname"],
#                     "name": row["name"],
#                     "init_date": row["init_date"],
#                 },
#             )

#     return len(new_items)


# # ============================================================================
# # Проверка
# # ============================================================================

# def validate_result(df: pd.DataFrame) -> None:
#     if df.empty:
#         return

#     missing = df[df["item_id"].isna()].copy()

#     if not missing.empty:
#         raise ValueError(
#             "Есть остатки без item_id:\n\n"
#             + missing[
#                 [
#                     "fullname",
#                     "name",
#                     "tot_available",
#                     "tot_ordered",
#                     "total",
#                 ]
#             ].to_string(index=False)
#         )

#     duplicates = df.groupby("item_id").size()
#     duplicates = duplicates[duplicates > 1]

#     if not duplicates.empty:
#         bad_ids = duplicates.index.tolist()

#         raise ValueError(
#             "Одному item_id соответствует несколько строк остатков:\n\n"
#             + df[
#                 df["item_id"].isin(bad_ids)
#             ][
#                 [
#                     "item_id",
#                     "fullname",
#                     "name",
#                     "tot_available",
#                     "tot_ordered",
#                     "total",
#                 ]
#             ].sort_values(["item_id", "fullname"]).to_string(index=False)
#         )


# # ============================================================================
# # MySQL serialization
# # ============================================================================

# def serialize_list_value(value: Any) -> str:
#     """
#     MySQL/PyMySQL не умеет писать Python list напрямую.

#     Храним списки как JSON-строку.
#     Пример:
#         ["РигаМолл - 6 шт.", "ОСНОВНОЙ склад - 1 шт."]
#     """
#     if value is None:
#         return "[]"

#     if isinstance(value, (list, tuple)):
#         clean_values = [
#             str(item)
#             for item in value
#             if item is not None
#             and str(item).strip()
#             and str(item).lower() != "none"
#         ]

#         return json.dumps(
#             clean_values,
#             ensure_ascii=False,
#         )

#     if isinstance(value, float) and pd.isna(value):
#         return "[]"

#     return str(value)


# def prepare_for_mysql(df: pd.DataFrame) -> pd.DataFrame:
#     result = df.copy()

#     list_columns = [
#         "barcode_stocks",
#         "barcode_ordered",
#         "warehouse_stocks",
#         "warehouse_ordered",
#     ]

#     for column in list_columns:
#         if column in result.columns:
#             result[column] = result[column].map(serialize_list_value)

#     return result


# # ============================================================================
# # Основная функция
# # ============================================================================

# def get_file_data(file: str) -> pd.DataFrame:
#     # ------------------------------------------------------------------
#     # 1. Excel
#     # ------------------------------------------------------------------

#     df = read_file_data(file)

#     if df.empty:
#         return df

#     # ------------------------------------------------------------------
#     # 2. Существующие item_id
#     # ------------------------------------------------------------------

#     df = assign_item_ids(df)

#     # ------------------------------------------------------------------
#     # 3. Новые товары
#     # ------------------------------------------------------------------

#     created = create_missing_items(df)

#     # ------------------------------------------------------------------
#     # 4. ВАЖНО: повторное присвоение item_id после INSERT
#     # ------------------------------------------------------------------

#     df = assign_item_ids(df)

#     # ------------------------------------------------------------------
#     # 5. Проверка качества
#     # ------------------------------------------------------------------

#     validate_result(df)

#     # ------------------------------------------------------------------
#     # 6. Типы
#     # ------------------------------------------------------------------

#     df["item_id"] = pd.to_numeric(
#         df["item_id"],
#         errors="raise",
#     ).astype("int64")

#     for column in [
#         "tot_available",
#         "tot_ordered",
#         "total",
#     ]:
#         df[column] = pd.to_numeric(
#             df[column],
#             errors="coerce",
#         ).fillna(0).astype("int64")

#     # Проверяем конкретно AV 337 для диагностики.
#     av337 = df[
#         df["fullname"].str.contains(
#             "AV 337",
#             case=False,
#             na=False,
#         )
#     ]

#     if not av337.empty:
#         print("\nCHECK AV 337:")
#         print(
#             av337[
#                 [
#                     "item_id",
#                     "fullname",
#                     "tot_available",
#                     "tot_ordered",
#                     "total",
#                 ]
#             ].to_string(index=False)
#         )

#     # ------------------------------------------------------------------
#     # 7. Удаляем служебный ключ
#     # ------------------------------------------------------------------

#     df = df.drop(
#         columns=["_fullname_key"],
#         errors="ignore",
#     )

#     preferred_columns = [
#         "item_id",
#         "fullname",
#         "name",
#         "init_date",
#         "tot_available",
#         "tot_ordered",
#         "total",
#         "barcode_stocks",
#         "barcode_ordered",
#         "warehouse_stocks",
#         "warehouse_ordered",
#     ]

#     df = df[
#         [c for c in preferred_columns if c in df.columns]
#         + [c for c in df.columns if c not in preferred_columns]
#     ]

#     print(
#         "\nStocks prepared:",
#         f"rows={len(df)}",
#         f"available={int(df['tot_available'].sum())}",
#         f"ordered={int(df['tot_ordered'].sum())}",
#         f"total={int(df['total'].sum())}",
#         f"null_ids={int(df['item_id'].isna().sum())}",
#         f"created_items={created}",
#     )

#     # ------------------------------------------------------------------
#     # 8. Сериализуем list-колонки для MySQL
#     # ------------------------------------------------------------------

#     db_df = prepare_for_mysql(df)

#     # ------------------------------------------------------------------
#     # 9. Только теперь записываем stocks_data
#     # ------------------------------------------------------------------

#     engine = get_engine()

#     db_df.to_sql(
#         "stocks_data",
#         engine,
#         index=False,
#         if_exists="replace",
#         chunksize=500,
#         method=None,
#         dtype={
#             "item_id": BigInteger(),
#             "fullname": Text(),
#             "name": Text(),
#             "init_date": Date(),
#             "tot_available": BigInteger(),
#             "tot_ordered": BigInteger(),
#             "total": BigInteger(),
#             "barcode_stocks": Text(),
#             "barcode_ordered": Text(),
#             "warehouse_stocks": Text(),
#             "warehouse_ordered": Text(),
#         },
#     )

#     # ------------------------------------------------------------------
#     # 10. Контроль уже записанной MySQL-таблицы
#     # ------------------------------------------------------------------

#     with engine.connect() as conn:
#         check = conn.execute(
#             text(
#                 """
#                 SELECT
#                     COUNT(*) AS rows_count,
#                     SUM(CASE WHEN item_id IS NULL THEN 1 ELSE 0 END) AS null_ids,
#                     SUM(tot_available) AS available,
#                     SUM(tot_ordered) AS ordered,
#                     SUM(total) AS total
#                 FROM stocks_data
#                 """
#             )
#         ).mappings().one()

#     print(
#         "\nStocks written:",
#         f"rows={check['rows_count']}",
#         f"available={int(check['available'] or 0)}",
#         f"ordered={int(check['ordered'] or 0)}",
#         f"total={int(check['total'] or 0)}",
#         f"null_ids={int(check['null_ids'] or 0)}",
#     )

#     return df



# utils/import_stocks.py

from __future__ import annotations

from datetime import date
from typing import Any
import json
import re

import duckdb
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.types import BigInteger, Date, Text

from conns import get_engine


load_dotenv()


# ============================================================================
# Нормализация текста
# ============================================================================

def normalize_text(value: Any) -> str:
    """
    Нормализует текст для надежного сопоставления номенклатуры.

    Убираем:
    - None / NaN;
    - пробелы по краям;
    - неразрывные пробелы;
    - narrow NBSP;
    - zero-width space;
    - BOM;
    - табы и переносы;
    - повторяющиеся пробелы.
    """
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text_value = str(value)

    replacements = {
        "\u00a0": " ",
        "\u202f": " ",
        "\u2007": " ",
        "\u200b": "",
        "\ufeff": "",
        "\t": " ",
        "\r": " ",
        "\n": " ",
    }

    for old, new in replacements.items():
        text_value = text_value.replace(old, new)

    return " ".join(text_value.split()).strip()


def normalize_key(value: Any) -> str:
    """Ключ сопоставления fullname."""
    return normalize_text(value).casefold()


# ============================================================================
# corporate_items
# ============================================================================

def get_items() -> pd.DataFrame:
    engine = get_engine()

    return pd.read_sql(
        """
        SELECT
            id,
            fullname
        FROM corporate_items
        """,
        engine,
    )


def build_item_map(items: pd.DataFrame) -> dict[str, int]:
    """
    normalized fullname -> item_id.

    Если исторически есть несколько ID для одного нормализованного fullname,
    используем минимальный ID — самый старый товар.
    """
    if items.empty:
        return {}

    work = items[["id", "fullname"]].copy()

    work["_key"] = work["fullname"].map(normalize_key)
    work["id"] = pd.to_numeric(work["id"], errors="coerce")

    work = work.dropna(subset=["id"])
    work = work[work["_key"] != ""].copy()

    work["id"] = work["id"].astype(int)

    mapping = (
        work.groupby("_key", as_index=False)
        .agg(id=("id", "min"))
    )

    return dict(zip(mapping["_key"], mapping["id"]))


def assign_item_ids(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    item_map = build_item_map(get_items())

    result["_fullname_key"] = result["fullname"].map(normalize_key)
    result["item_id"] = result["_fullname_key"].map(item_map)

    return result


# ============================================================================
# XLSX
# ============================================================================

def read_file_data(file: str) -> pd.DataFrame:
    """
    Читает XLSX и агрегирует данные до уровня номенклатуры.

    Важно:
    - tot_available / tot_ordered считаются по всем исходным строкам товара;
    - warehouse_stocks агрегируется по складу;
    - barcode_stocks агрегируется по штрихкоду;
    - одинаковые строки НЕ дедуплицируются, а суммируются;
    - остаток без склада попадает в "БЕЗ УКАЗАНИЯ СКЛАДА";
    - остаток без штрихкода попадает в "БЕЗ ШТРИХКОДА";
    - item_id здесь не присваиваем.
    """
    with duckdb.connect(":memory:") as con:
        raw = con.execute(
            """
            SELECT
                "H" AS fullname,
                "N" AS name,
                "L" AS warehouse,
                "P" AS barcode,

                COALESCE(
                    TRY_CAST(NULLIF(TRIM("R"), '') AS BIGINT),
                    0
                ) AS available,

                COALESCE(
                    TRY_CAST(NULLIF(TRIM("T"), '') AS BIGINT),
                    0
                ) AS ordered,

                TRY_STRPTIME(
                    NULLIF(TRIM("V"), ''),
                    '%d.%m.%Y'
                )::DATE AS date_arrival

            FROM read_xlsx(
                ?,
                range='B3:V',
                header=false,
                all_varchar=true
            )

            WHERE "B" IS NOT NULL
            """,
            [file],
        ).df()

    if raw.empty:
        return raw

    # ------------------------------------------------------------------
    # Нормализация
    # ------------------------------------------------------------------

    for column in ["fullname", "name", "warehouse", "barcode"]:
        raw[column] = raw[column].map(normalize_text)

    raw = raw[raw["fullname"] != ""].copy()

    raw["_fullname_key"] = raw["fullname"].map(normalize_key)

    # Числовые поля на всякий случай нормализуем повторно.
    raw["available"] = pd.to_numeric(
        raw["available"],
        errors="coerce",
    ).fillna(0).astype("int64")

    raw["ordered"] = pd.to_numeric(
        raw["ordered"],
        errors="coerce",
    ).fillna(0).astype("int64")

    # ------------------------------------------------------------------
    # Общие суммы по номенклатуре
    # ------------------------------------------------------------------

    totals = (
        raw.groupby("_fullname_key", as_index=False)
        .agg(
            fullname=("fullname", "first"),
            name=("name", "first"),
            tot_available=("available", "sum"),
            tot_ordered=("ordered", "sum"),
        )
    )

    totals["total"] = (
        totals["tot_available"]
        + totals["tot_ordered"]
    )

    totals["init_date"] = pd.Timestamp(date.today())

    # ------------------------------------------------------------------
    # Детализация по складам и штрихкодам
    # ------------------------------------------------------------------

    detail_rows: list[dict[str, Any]] = []

    for key, group in raw.groupby(
        "_fullname_key",
        sort=False,
    ):
        # ==============================================================
        # Накопители
        # ==============================================================

        barcode_available_map: dict[str, int] = {}

        # Для заказов по штрихкодам сохраняем дату поступления.
        # Один и тот же barcode + одна дата должны суммироваться.
        barcode_ordered_map: dict[
            tuple[str, str | None],
            int,
        ] = {}

        warehouse_available_map: dict[str, int] = {}
        warehouse_ordered_map: dict[str, int] = {}

        # ==============================================================
        # Агрегация исходных строк
        # ==============================================================

        for _, row in group.iterrows():
            barcode = normalize_text(row["barcode"])
            warehouse = normalize_text(row["warehouse"])

            available = int(row["available"] or 0)
            ordered = int(row["ordered"] or 0)

            # ----------------------------------------------------------
            # Доступный остаток по штрихкоду
            # ----------------------------------------------------------

            if barcode:
                barcode_available_map[barcode] = (
                    barcode_available_map.get(barcode, 0)
                    + available
                )

            # ----------------------------------------------------------
            # Заказ по штрихкоду + дата поступления
            # ----------------------------------------------------------

            if barcode and ordered != 0:
                arrival: str | None = None

                if pd.notna(row["date_arrival"]):
                    arrival = pd.Timestamp(
                        row["date_arrival"]
                    ).strftime("%Y-%m-%d")

                order_key = (
                    barcode,
                    arrival,
                )

                barcode_ordered_map[order_key] = (
                    barcode_ordered_map.get(order_key, 0)
                    + ordered
                )

            # ----------------------------------------------------------
            # Доступный остаток по складу
            # ----------------------------------------------------------

            if warehouse:
                warehouse_available_map[warehouse] = (
                    warehouse_available_map.get(warehouse, 0)
                    + available
                )

            # ----------------------------------------------------------
            # Заказ по складу
            # ----------------------------------------------------------

            if warehouse:
                warehouse_ordered_map[warehouse] = (
                    warehouse_ordered_map.get(warehouse, 0)
                    + ordered
                )

        # ==============================================================
        # Контроль полноты доступного остатка
        # ==============================================================

        total_available = int(
            group["available"].sum()
        )

        total_ordered = int(
            group["ordered"].sum()
        )

        warehouse_available_total = sum(
            warehouse_available_map.values()
        )

        barcode_available_total = sum(
            barcode_available_map.values()
        )

        warehouse_ordered_total = sum(
            warehouse_ordered_map.values()
        )

        barcode_ordered_total = sum(
            barcode_ordered_map.values()
        )

        # Если в исходном Excel у строки с остатком нет склада,
        # не теряем количество, а явно относим его в отдельную группу.
        warehouse_available_diff = (
            total_available
            - warehouse_available_total
        )

        if warehouse_available_diff != 0:
            warehouse_available_map[
                "БЕЗ УКАЗАНИЯ СКЛАДА"
            ] = (
                warehouse_available_map.get(
                    "БЕЗ УКАЗАНИЯ СКЛАДА",
                    0,
                )
                + warehouse_available_diff
            )

        # То же самое для штрихкода.
        barcode_available_diff = (
            total_available
            - barcode_available_total
        )

        if barcode_available_diff != 0:
            barcode_available_map[
                "БЕЗ ШТРИХКОДА"
            ] = (
                barcode_available_map.get(
                    "БЕЗ ШТРИХКОДА",
                    0,
                )
                + barcode_available_diff
            )

        # Если заказ есть, а склад не заполнен.
        warehouse_ordered_diff = (
            total_ordered
            - warehouse_ordered_total
        )

        if warehouse_ordered_diff != 0:
            warehouse_ordered_map[
                "БЕЗ УКАЗАНИЯ СКЛАДА"
            ] = (
                warehouse_ordered_map.get(
                    "БЕЗ УКАЗАНИЯ СКЛАДА",
                    0,
                )
                + warehouse_ordered_diff
            )

        # Если заказ есть, а штрихкод не заполнен.
        barcode_ordered_diff = (
            total_ordered
            - barcode_ordered_total
        )

        if barcode_ordered_diff != 0:
            order_key = (
                "БЕЗ ШТРИХКОДА",
                None,
            )

            barcode_ordered_map[order_key] = (
                barcode_ordered_map.get(
                    order_key,
                    0,
                )
                + barcode_ordered_diff
            )

        # ==============================================================
        # Формируем JSON-совместимые списки
        # ==============================================================

        barcode_stocks = [
            f"{barcode} - {qty} шт."
            for barcode, qty in sorted(
                barcode_available_map.items(),
                key=lambda item: item[0].casefold(),
            )
            if qty != 0
        ]

        barcode_ordered: list[str] = []

        for (
            barcode,
            arrival,
        ), qty in sorted(
            barcode_ordered_map.items(),
            key=lambda item: (
                item[0][0].casefold(),
                item[0][1] or "",
            ),
        ):
            if qty == 0:
                continue

            value = (
                f"{barcode} - {qty} шт."
            )

            if arrival:
                value += (
                    f" (дата поступления: {arrival})"
                )

            barcode_ordered.append(value)

        warehouse_stocks = [
            f"{warehouse} - {qty} шт."
            for warehouse, qty in sorted(
                warehouse_available_map.items(),
                key=lambda item: item[0].casefold(),
            )
            if qty != 0
        ]

        warehouse_ordered = [
            f"{warehouse} - {qty} шт."
            for warehouse, qty in sorted(
                warehouse_ordered_map.items(),
                key=lambda item: item[0].casefold(),
            )
            if qty != 0
        ]

        # ==============================================================
        # Жёсткая сверка до формирования итогового DataFrame
        # ==============================================================

        check_warehouse_available = sum(
            warehouse_available_map.values()
        )

        check_barcode_available = sum(
            barcode_available_map.values()
        )

        check_warehouse_ordered = sum(
            warehouse_ordered_map.values()
        )

        check_barcode_ordered = sum(
            barcode_ordered_map.values()
        )

        if check_warehouse_available != total_available:
            raise ValueError(
                "Ошибка агрегации доступного остатка по складам: "
                f"{group['fullname'].iloc[0]!r}; "
                f"общий={total_available}; "
                f"по складам={check_warehouse_available}"
            )

        if check_barcode_available != total_available:
            raise ValueError(
                "Ошибка агрегации доступного остатка по штрихкодам: "
                f"{group['fullname'].iloc[0]!r}; "
                f"общий={total_available}; "
                f"по штрихкодам={check_barcode_available}"
            )

        if check_warehouse_ordered != total_ordered:
            raise ValueError(
                "Ошибка агрегации заказанного товара по складам: "
                f"{group['fullname'].iloc[0]!r}; "
                f"общий={total_ordered}; "
                f"по складам={check_warehouse_ordered}"
            )

        if check_barcode_ordered != total_ordered:
            raise ValueError(
                "Ошибка агрегации заказанного товара по штрихкодам: "
                f"{group['fullname'].iloc[0]!r}; "
                f"общий={total_ordered}; "
                f"по штрихкодам={check_barcode_ordered}"
            )

        detail_rows.append(
            {
                "_fullname_key": key,
                "barcode_stocks": barcode_stocks,
                "barcode_ordered": barcode_ordered,
                "warehouse_stocks": warehouse_stocks,
                "warehouse_ordered": warehouse_ordered,
            }
        )

    details = pd.DataFrame(detail_rows)

    return totals.merge(
        details,
        on="_fullname_key",
        how="left",
        validate="one_to_one",
    )

# ============================================================================
# Создание отсутствующих товаров
# ============================================================================

def create_missing_items(df: pd.DataFrame) -> int:
    missing = df[df["item_id"].isna()].copy()

    if missing.empty:
        return 0

    new_items = (
        missing[
            [
                "fullname",
                "name",
                "init_date",
                "_fullname_key",
            ]
        ]
        .loc[lambda x: x["_fullname_key"] != ""]
        .drop_duplicates(subset=["_fullname_key"], keep="first")
    )

    if new_items.empty:
        return 0

    engine = get_engine()

    with engine.begin() as conn:
        for _, row in new_items.iterrows():
            conn.execute(
                text(
                    """
                    INSERT IGNORE INTO corporate_items
                    (
                        fullname,
                        name,
                        init_date
                    )
                    VALUES
                    (
                        :fullname,
                        :name,
                        :init_date
                    )
                    """
                ),
                {
                    "fullname": row["fullname"],
                    "name": row["name"],
                    "init_date": row["init_date"],
                },
            )

    return len(new_items)


# ============================================================================
# Проверка
# ============================================================================

def validate_result(df: pd.DataFrame) -> None:
    if df.empty:
        return

    missing = df[df["item_id"].isna()].copy()

    if not missing.empty:
        raise ValueError(
            "Есть остатки без item_id:\n\n"
            + missing[
                [
                    "fullname",
                    "name",
                    "tot_available",
                    "tot_ordered",
                    "total",
                ]
            ].to_string(index=False)
        )

    duplicates = df.groupby("item_id").size()
    duplicates = duplicates[duplicates > 1]

    if not duplicates.empty:
        bad_ids = duplicates.index.tolist()

        raise ValueError(
            "Одному item_id соответствует несколько строк остатков:\n\n"
            + df[
                df["item_id"].isin(bad_ids)
            ][
                [
                    "item_id",
                    "fullname",
                    "name",
                    "tot_available",
                    "tot_ordered",
                    "total",
                ]
            ].sort_values(["item_id", "fullname"]).to_string(index=False)
        )


def _sum_qty_list(values: Any) -> int:
    """
    Суммирует количества из list-колонки вида:

        ["Европарк - 2 шт.", "ОСНОВНОЙ склад - 1364 шт."]

    Работает и с Python list, и с JSON-строкой.
    """
    if values is None:
        return 0

    if isinstance(values, float) and pd.isna(values):
        return 0

    parsed_values: list[Any]

    if isinstance(values, (list, tuple)):
        parsed_values = list(values)
    else:
        text_value = str(values).strip()

        if not text_value:
            return 0

        try:
            parsed = json.loads(text_value)
            parsed_values = (
                parsed
                if isinstance(parsed, list)
                else [parsed]
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            parsed_values = [text_value]

    total = 0

    for value in parsed_values:
        match = re.search(
            r"\s-\s(-?\d+)\s*шт\.",
            str(value),
            flags=re.IGNORECASE,
        )

        if match:
            total += int(match.group(1))

    return total


def validate_stock_details(df: pd.DataFrame) -> None:
    """
    Проверяет, что детализация полностью сходится с итогами.

    Для каждой номенклатуры должны выполняться равенства:

        sum(warehouse_stocks) == tot_available
        sum(barcode_stocks) == tot_available
        sum(warehouse_ordered) == tot_ordered
        sum(barcode_ordered) == tot_ordered

    Если хотя бы один товар не сходится — импорт останавливается
    ДО записи stocks_data.
    """
    if df.empty:
        return

    problems: list[str] = []

    for _, row in df.iterrows():
        fullname = str(
            row.get("fullname", "")
        )

        total_available = int(
            row.get("tot_available", 0) or 0
        )

        total_ordered = int(
            row.get("tot_ordered", 0) or 0
        )

        warehouse_available = _sum_qty_list(
            row.get("warehouse_stocks")
        )

        barcode_available = _sum_qty_list(
            row.get("barcode_stocks")
        )

        warehouse_ordered = _sum_qty_list(
            row.get("warehouse_ordered")
        )

        barcode_ordered = _sum_qty_list(
            row.get("barcode_ordered")
        )

        row_problems: list[str] = []

        if warehouse_available != total_available:
            row_problems.append(
                "склады доступно "
                f"{warehouse_available} != {total_available}"
            )

        if barcode_available != total_available:
            row_problems.append(
                "штрихкоды доступно "
                f"{barcode_available} != {total_available}"
            )

        if warehouse_ordered != total_ordered:
            row_problems.append(
                "склады заказано "
                f"{warehouse_ordered} != {total_ordered}"
            )

        if barcode_ordered != total_ordered:
            row_problems.append(
                "штрихкоды заказано "
                f"{barcode_ordered} != {total_ordered}"
            )

        if row_problems:
            problems.append(
                f"{fullname}: "
                + "; ".join(row_problems)
            )

    if problems:
        preview = "\n".join(
            problems[:50]
        )

        extra = (
            ""
            if len(problems) <= 50
            else (
                "\n..."
                f"\nЕщё ошибок: {len(problems) - 50}"
            )
        )

        raise ValueError(
            "Детализация остатков не сходится "
            "с итоговыми значениями:\n\n"
            + preview
            + extra
        )


# ============================================================================
# MySQL serialization
# ============================================================================

def serialize_list_value(value: Any) -> str:
    """
    MySQL/PyMySQL не умеет писать Python list напрямую.

    Храним списки как JSON-строку.
    Пример:
        ["РигаМолл - 6 шт.", "ОСНОВНОЙ склад - 1 шт."]
    """
    if value is None:
        return "[]"

    if isinstance(value, (list, tuple)):
        clean_values = [
            str(item)
            for item in value
            if item is not None
            and str(item).strip()
            and str(item).lower() != "none"
        ]

        return json.dumps(
            clean_values,
            ensure_ascii=False,
        )

    if isinstance(value, float) and pd.isna(value):
        return "[]"

    return str(value)


def prepare_for_mysql(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    list_columns = [
        "barcode_stocks",
        "barcode_ordered",
        "warehouse_stocks",
        "warehouse_ordered",
    ]

    for column in list_columns:
        if column in result.columns:
            result[column] = result[column].map(serialize_list_value)

    return result


# ============================================================================
# Основная функция
# ============================================================================

def get_file_data(file: str) -> pd.DataFrame:
    # ------------------------------------------------------------------
    # 1. Excel
    # ------------------------------------------------------------------

    df = read_file_data(file)

    if df.empty:
        return df

    # ------------------------------------------------------------------
    # 2. Существующие item_id
    # ------------------------------------------------------------------

    df = assign_item_ids(df)

    # ------------------------------------------------------------------
    # 3. Новые товары
    # ------------------------------------------------------------------

    created = create_missing_items(df)

    # ------------------------------------------------------------------
    # 4. ВАЖНО: повторное присвоение item_id после INSERT
    # ------------------------------------------------------------------

    df = assign_item_ids(df)

    # ------------------------------------------------------------------
    # 5. Проверка качества
    # ------------------------------------------------------------------

    validate_result(df)

    # ------------------------------------------------------------------
    # 6. Типы
    # ------------------------------------------------------------------

    df["item_id"] = pd.to_numeric(
        df["item_id"],
        errors="raise",
    ).astype("int64")

    for column in [
        "tot_available",
        "tot_ordered",
        "total",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0).astype("int64")

    # ------------------------------------------------------------------
    # 7. Жёсткая сверка детализации до записи в БД
    # ------------------------------------------------------------------

    validate_stock_details(df)

    # Проверяем конкретно AV 337 для диагностики.
    av337 = df[
        df["fullname"].str.contains(
            "AV 337",
            case=False,
            na=False,
        )
    ]

    if not av337.empty:
        print("\nCHECK AV 337:")
        print(
            av337[
                [
                    "item_id",
                    "fullname",
                    "tot_available",
                    "tot_ordered",
                    "total",
                ]
            ].to_string(index=False)
        )

    # ------------------------------------------------------------------
    # 8. Удаляем служебный ключ
    # ------------------------------------------------------------------

    df = df.drop(
        columns=["_fullname_key"],
        errors="ignore",
    )

    preferred_columns = [
        "item_id",
        "fullname",
        "name",
        "init_date",
        "tot_available",
        "tot_ordered",
        "total",
        "barcode_stocks",
        "barcode_ordered",
        "warehouse_stocks",
        "warehouse_ordered",
    ]

    df = df[
        [c for c in preferred_columns if c in df.columns]
        + [c for c in df.columns if c not in preferred_columns]
    ]

    print(
        "\nStocks prepared:",
        f"rows={len(df)}",
        f"available={int(df['tot_available'].sum())}",
        f"ordered={int(df['tot_ordered'].sum())}",
        f"total={int(df['total'].sum())}",
        f"null_ids={int(df['item_id'].isna().sum())}",
        f"created_items={created}",
    )

    # ------------------------------------------------------------------
    # 9. Сериализуем list-колонки для MySQL
    # ------------------------------------------------------------------

    db_df = prepare_for_mysql(df)

    # ------------------------------------------------------------------
    # 10. Только теперь записываем stocks_data
    # ------------------------------------------------------------------

    engine = get_engine()

    db_df.to_sql(
        "stocks_data",
        engine,
        index=False,
        if_exists="replace",
        chunksize=500,
        method=None,
        dtype={
            "item_id": BigInteger(),
            "fullname": Text(),
            "name": Text(),
            "init_date": Date(),
            "tot_available": BigInteger(),
            "tot_ordered": BigInteger(),
            "total": BigInteger(),
            "barcode_stocks": Text(),
            "barcode_ordered": Text(),
            "warehouse_stocks": Text(),
            "warehouse_ordered": Text(),
        },
    )

    # ------------------------------------------------------------------
    # 11. Контроль уже записанной MySQL-таблицы
    # ------------------------------------------------------------------

    with engine.connect() as conn:
        check = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS rows_count,
                    SUM(CASE WHEN item_id IS NULL THEN 1 ELSE 0 END) AS null_ids,
                    SUM(tot_available) AS available,
                    SUM(tot_ordered) AS ordered,
                    SUM(total) AS total
                FROM stocks_data
                """
            )
        ).mappings().one()

    print(
        "\nStocks written:",
        f"rows={check['rows_count']}",
        f"available={int(check['available'] or 0)}",
        f"ordered={int(check['ordered'] or 0)}",
        f"total={int(check['total'] or 0)}",
        f"null_ids={int(check['null_ids'] or 0)}",
    )

    return df

