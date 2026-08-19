# # corporate/management/commands/import_stocks.py
# import os

# import duckdb
# import pandas as pd

# from django.core.management.base import BaseCommand
# from django.db import connection


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
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT *
#             FROM corporate_items
#         """)

#         columns = [
#             col[0]
#             for col in cursor.description
#         ]

#         rows = cursor.fetchall()

#     return pd.DataFrame(
#         rows,
#         columns=columns
#     )


# def import_stocks(file):

#     with duck_connection() as con:

#         # существующие товары
#         con.register(
#             "items",
#             get_items()
#         )

#         df = con.execute(
#             """
#             SELECT
#                 i.id AS item_id,

#                 x.fullname,
#                 x.name,

#                 CURRENT_DATE AS init_date,

#                 sum(available) AS tot_available,
#                 sum(ordered) AS tot_ordered,
#                 sum(available) + sum(ordered) AS total,


#                 list(
#                     DISTINCT
#                     barcode || ' - ' ||
#                     available::text ||
#                     ' шт.'
#                 ) AS barcode_stocks,


#                 list(
#                     DISTINCT
#                     barcode || ' - ' ||
#                     ordered::text ||
#                     ' шт.(дата поступления: ' ||
#                     date_arrival ||
#                     ')'
#                 ) AS barcode_ordered,


#                 list(
#                     DISTINCT
#                     warehouse || ' - ' ||
#                     available::text ||
#                     ' шт.'
#                 ) AS warehouse_stocks,


#                 list(
#                     DISTINCT
#                     warehouse || ' - ' ||
#                     ordered::text ||
#                     ' шт.'
#                 ) AS warehouse_ordered


#             FROM (

#                 SELECT

#                     "H" AS fullname,
#                     "N" AS name,

#                     "L" AS warehouse,
#                     "P" AS barcode,

#                     COALESCE("R",'0')::bigint AS available,
#                     COALESCE("T",'0')::bigint AS ordered,

#                     try_strptime(
#                         "V",
#                         '%d.%m.%Y'
#                     )::DATE AS date_arrival


#                 FROM (

#                     SELECT *

#                     FROM read_xlsx(
#                         ?,
#                         range='B3:V',
#                         header=false,
#                         all_varchar=true
#                     )

#                     WHERE "B" IS NOT NULL

#                 )

#             ) x


#             LEFT JOIN items i
#                 ON i.fullname = x.fullname


#             GROUP BY
#                 x.fullname,
#                 i.id,
#                 x.name,
#                 CURRENT_DATE

#             """,
#             [file]
#         ).df()


#         #
#         # новые товары
#         #
#         new_items = (
#             df[df["item_id"].isna()]
#             [
#                 [
#                     "fullname",
#                     "name",
#                     "init_date"
#                 ]
#             ]
#             .drop_duplicates()
#         )


#         if len(new_items) == 0:
#             return df


#         rows = [
#             tuple(x)
#             for x in new_items.to_numpy()
#         ]


#         #
#         # настоящий MySQL INSERT IGNORE
#         #
#         with connection.cursor() as cursor:

#             cursor.executemany(
#                 """
#                 INSERT IGNORE INTO corporate_items
#                 (
#                     fullname,
#                     name,
#                     init_date
#                 )
#                 VALUES
#                 (
#                     %s,
#                     %s,
#                     %s
#                 )
#                 """,
#                 rows
#             )


#         return df



# class Command(BaseCommand):

#     help = "Import stocks from XLSX"


#     def add_arguments(self, parser):

#         parser.add_argument(
#             "file",
#             type=str,
#             help="xlsx file path"
#         )


#     def handle(self, *args, **options):

#         file = options["file"]

#         self.stdout.write(
#             f"Importing: {file}"
#         )


#         df = import_stocks(file)


#         self.stdout.write(
#             self.style.SUCCESS(
#                 f"Done. Rows processed: {len(df)}"
#             )
#         )


# # corporate/management/commands/import_stocks.py

# import os

# import duckdb
# import pandas as pd

# from django.core.management.base import BaseCommand
# from django.db import connection


# def duck_connection():
#     con = duckdb.connect(":memory:")

#     con.execute("INSTALL mysql")
#     con.execute("LOAD mysql")

#     con.execute(
#         f"""
#         ATTACH '
#             host={os.getenv("DB_HOST", "localhost")}
#             port={os.getenv("DB_PORT", "3306")}
#             user={os.getenv("DB_USER")}
#             password={os.getenv("DB_PASSWORD")}
#             database={os.getenv("DB_NAME")}
#         '
#         AS mysql
#         (TYPE mysql);
#         """
#     )

#     return con


# def get_items() -> pd.DataFrame:
#     """
#     Получаем текущий справочник товаров.

#     Для сопоставления остатков достаточно:
#     - id
#     - fullname
#     """

#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT
#                 id,
#                 fullname
#             FROM corporate_items
#             """
#         )

#         columns = [
#             col[0]
#             for col in cursor.description
#         ]

#         rows = cursor.fetchall()

#     return pd.DataFrame(
#         rows,
#         columns=columns,
#     )


# def normalize_text_series(series: pd.Series) -> pd.Series:
#     """
#     Нормализация текстовых полей для сопоставления.

#     Убираем:
#     - NULL
#     - пробелы по краям
#     - неразрывные пробелы
#     - повторяющиеся пробелы
#     """

#     return (
#         series
#         .fillna("")
#         .astype(str)
#         .str.replace("\u00a0", " ", regex=False)
#         .str.replace(r"\s+", " ", regex=True)
#         .str.strip()
#     )


# def refresh_item_ids(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Повторно сопоставляет fullname с corporate_items.

#     Используется после INSERT новых товаров,
#     потому что первоначальный df уже был построен
#     до создания этих товаров.
#     """

#     if df.empty:
#         return df

#     items = get_items()

#     if items.empty:
#         return df

#     items = items.copy()
#     df = df.copy()

#     items["_fullname_key"] = normalize_text_series(
#         items["fullname"]
#     )

#     df["_fullname_key"] = normalize_text_series(
#         df["fullname"]
#     )

#     # На случай, если в corporate_items вдруг есть
#     # несколько одинаковых fullname.
#     item_map = (
#         items[
#             items["_fullname_key"] != ""
#         ]
#         .drop_duplicates(
#             subset=["_fullname_key"],
#             keep="last",
#         )
#         .set_index("_fullname_key")["id"]
#     )

#     df["item_id"] = (
#         df["_fullname_key"]
#         .map(item_map)
#     )

#     df = df.drop(
#         columns=["_fullname_key"],
#         errors="ignore",
#     )

#     return df


# def import_stocks(file: str) -> pd.DataFrame:

#     # ==================================================================
#     # 1. Читаем Excel и сопоставляем с существующими товарами
#     # ==================================================================

#     with duck_connection() as con:

#         items = get_items()

#         # Нормализуем fullname ещё до передачи в DuckDB.
#         # Это помогает не ловить пробелы/nbsp в самом справочнике.
#         if not items.empty:
#             items = items.copy()

#             items["fullname"] = normalize_text_series(
#                 items["fullname"]
#             )

#         con.register(
#             "items",
#             items,
#         )

#         df = con.execute(
#             """
#             WITH source AS (
#                 SELECT
#                     TRIM(
#                         REGEXP_REPLACE(
#                             REPLACE("H", CHR(160), ' '),
#                             '\\s+',
#                             ' '
#                         )
#                     ) AS fullname,

#                     TRIM(
#                         REGEXP_REPLACE(
#                             REPLACE("N", CHR(160), ' '),
#                             '\\s+',
#                             ' '
#                         )
#                     ) AS name,

#                     TRIM(
#                         REGEXP_REPLACE(
#                             REPLACE("L", CHR(160), ' '),
#                             '\\s+',
#                             ' '
#                         )
#                     ) AS warehouse,

#                     TRIM(
#                         REPLACE("P", CHR(160), ' ')
#                     ) AS barcode,

#                     COALESCE(
#                         NULLIF(TRIM("R"), ''),
#                         '0'
#                     )::BIGINT AS available,

#                     COALESCE(
#                         NULLIF(TRIM("T"), ''),
#                         '0'
#                     )::BIGINT AS ordered,

#                     TRY_STRPTIME(
#                         NULLIF(TRIM("V"), ''),
#                         '%d.%m.%Y'
#                     )::DATE AS date_arrival

#                 FROM read_xlsx(
#                     ?,
#                     range='B3:V',
#                     header=false,
#                     all_varchar=true
#                 )

#                 WHERE "B" IS NOT NULL
#             )

#             SELECT
#                 i.id AS item_id,

#                 x.fullname,
#                 x.name,

#                 CURRENT_DATE AS init_date,

#                 SUM(x.available) AS tot_available,
#                 SUM(x.ordered) AS tot_ordered,

#                 SUM(x.available)
#                     + SUM(x.ordered)
#                     AS total,

#                 LIST(
#                     DISTINCT
#                     CASE
#                         WHEN x.barcode IS NOT NULL
#                              AND x.barcode <> ''
#                         THEN
#                             x.barcode
#                             || ' - '
#                             || x.available::TEXT
#                             || ' шт.'
#                     END
#                 ) AS barcode_stocks,

#                 LIST(
#                     DISTINCT
#                     CASE
#                         WHEN x.barcode IS NOT NULL
#                              AND x.barcode <> ''
#                              AND x.ordered <> 0
#                         THEN
#                             x.barcode
#                             || ' - '
#                             || x.ordered::TEXT
#                             || ' шт.'
#                             || CASE
#                                 WHEN x.date_arrival IS NOT NULL
#                                 THEN
#                                     '(дата поступления: '
#                                     || x.date_arrival::TEXT
#                                     || ')'
#                                 ELSE ''
#                             END
#                     END
#                 ) AS barcode_ordered,

#                 LIST(
#                     DISTINCT
#                     CASE
#                         WHEN x.warehouse IS NOT NULL
#                              AND x.warehouse <> ''
#                         THEN
#                             x.warehouse
#                             || ' - '
#                             || x.available::TEXT
#                             || ' шт.'
#                     END
#                 ) AS warehouse_stocks,

#                 LIST(
#                     DISTINCT
#                     CASE
#                         WHEN x.warehouse IS NOT NULL
#                              AND x.warehouse <> ''
#                         THEN
#                             x.warehouse
#                             || ' - '
#                             || x.ordered::TEXT
#                             || ' шт.'
#                     END
#                 ) AS warehouse_ordered

#             FROM source AS x

#             LEFT JOIN items AS i
#                 ON i.fullname = x.fullname

#             WHERE x.fullname IS NOT NULL
#               AND x.fullname <> ''

#             GROUP BY
#                 x.fullname,
#                 i.id,
#                 x.name,
#                 CURRENT_DATE
#             """,
#             [file],
#         ).df()

#     if df.empty:
#         return df

#     # ==================================================================
#     # 2. Дополнительная нормализация после DuckDB
#     # ==================================================================

#     df["fullname"] = normalize_text_series(
#         df["fullname"]
#     )

#     df["name"] = normalize_text_series(
#         df["name"]
#     )

#     # ==================================================================
#     # 3. Ищем товары, которых ещё нет в corporate_items
#     # ==================================================================

#     new_items = (
#         df.loc[
#             df["item_id"].isna(),
#             [
#                 "fullname",
#                 "name",
#                 "init_date",
#             ],
#         ]
#         .copy()
#     )

#     # пустые fullname создавать нельзя
#     new_items = new_items[
#         new_items["fullname"] != ""
#     ]

#     new_items = new_items.drop_duplicates(
#         subset=["fullname"],
#         keep="first",
#     )

#     # ==================================================================
#     # 4. Создаём новые товары
#     # ==================================================================

#     if not new_items.empty:

#         rows = [
#             tuple(row)
#             for row in new_items.to_numpy()
#         ]

#         with connection.cursor() as cursor:
#             cursor.executemany(
#                 """
#                 INSERT IGNORE INTO corporate_items
#                 (
#                     fullname,
#                     name,
#                     init_date
#                 )
#                 VALUES
#                 (
#                     %s,
#                     %s,
#                     %s
#                 )
#                 """,
#                 rows,
#             )

#     # ==================================================================
#     # 5. КРИТИЧЕСКИ ВАЖНО:
#     #    после INSERT заново присваиваем item_id
#     # ==================================================================

#     df = refresh_item_ids(df)

#     # ==================================================================
#     # 6. Проверяем, что НИ ОДИН товар не остался без item_id
#     # ==================================================================

#     missing = df[
#         df["item_id"].isna()
#     ].copy()

#     if not missing.empty:

#         bad_rows = (
#             missing[
#                 [
#                     "fullname",
#                     "name",
#                     "tot_available",
#                     "tot_ordered",
#                     "total",
#                 ]
#             ]
#             .drop_duplicates()
#             .to_dict("records")
#         )

#         raise ValueError(
#             "Импорт остановлен: после создания новых товаров "
#             "часть номенклатуры всё ещё не получила item_id.\n"
#             f"Проблемные строки: {bad_rows}"
#         )

#     # ==================================================================
#     # 7. Финальные типы
#     # ==================================================================

#     df["item_id"] = (
#         pd.to_numeric(
#             df["item_id"],
#             errors="raise",
#         )
#         .astype("int64")
#     )

#     for column in [
#         "tot_available",
#         "tot_ordered",
#         "total",
#     ]:
#         df[column] = (
#             pd.to_numeric(
#                 df[column],
#                 errors="coerce",
#             )
#             .fillna(0)
#             .astype("int64")
#         )

#     return df


# class Command(BaseCommand):

#     help = "Import stocks from XLSX"

#     def add_arguments(self, parser):

#         parser.add_argument(
#             "file",
#             type=str,
#             help="xlsx file path",
#         )

#     def handle(self, *args, **options):

#         file = options["file"]

#         self.stdout.write(
#             f"Importing: {file}"
#         )

#         df = import_stocks(file)

#         # --------------------------------------------------------------
#         # Контроль импорта
#         # --------------------------------------------------------------

#         total_available = int(
#             df["tot_available"].sum()
#         )

#         total_ordered = int(
#             df["tot_ordered"].sum()
#         )

#         total_stock = int(
#             df["total"].sum()
#         )

#         self.stdout.write(
#             self.style.SUCCESS(
#                 "\n".join(
#                     [
#                         f"Done. Rows processed: {len(df)}",
#                         f"Available: {total_available}",
#                         f"Ordered: {total_ordered}",
#                         f"Total: {total_stock}",
#                     ]
#                 )
#             )
#         )




# corporate/management/commands/import_stocks.py

from django.core.management.base import BaseCommand, CommandError

from utils.import_stocks import get_file_data


class Command(BaseCommand):
    help = "Import stocks from XLSX"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="xlsx file path",
        )

    def handle(self, *args, **options):
        file = options["file"]

        self.stdout.write(
            f"Importing: {file}"
        )

        try:
            df = get_file_data(file)

        except Exception as exc:
            raise CommandError(
                f"Stocks import failed:\n{exc}"
            ) from exc

        if df.empty:
            self.stdout.write(
                self.style.WARNING(
                    "No stock rows found."
                )
            )
            return

        available = int(
            df["tot_available"].sum()
        )

        ordered = int(
            df["tot_ordered"].sum()
        )

        total = int(
            df["total"].sum()
        )

        null_ids = int(
            df["item_id"].isna().sum()
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n".join(
                    [
                        "Stocks imported successfully.",
                        f"Rows: {len(df)}",
                        f"Available: {available}",
                        f"Ordered: {ordered}",
                        f"Total: {total}",
                        f"NULL item_id: {null_ids}",
                    ]
                )
            )
        )