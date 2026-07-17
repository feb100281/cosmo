import os

import duckdb
import pandas as pd

from django.core.management.base import BaseCommand
from django.db import connection


def duck_connection():
    con = duckdb.connect(":memory:")

    con.execute("INSTALL mysql")
    con.execute("LOAD mysql")

    con.execute(f"""
        ATTACH '
            host={os.getenv("DB_HOST", "localhost")}
            port={os.getenv("DB_PORT", "3306")}
            user={os.getenv("DB_USER")}
            password={os.getenv("DB_PASSWORD")}
            database={os.getenv("DB_NAME")}
        '
        AS mysql
        (TYPE mysql);
    """)

    return con


def get_items():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM corporate_items
        """)

        columns = [
            col[0]
            for col in cursor.description
        ]

        rows = cursor.fetchall()

    return pd.DataFrame(
        rows,
        columns=columns
    )


def import_stocks(file):

    with duck_connection() as con:

        # существующие товары
        con.register(
            "items",
            get_items()
        )

        df = con.execute(
            """
            SELECT
                i.id AS item_id,

                x.fullname,
                x.name,

                CURRENT_DATE AS init_date,

                sum(available) AS tot_available,
                sum(ordered) AS tot_ordered,
                sum(available) + sum(ordered) AS total,


                list(
                    DISTINCT
                    barcode || ' - ' ||
                    available::text ||
                    ' шт.'
                ) AS barcode_stocks,


                list(
                    DISTINCT
                    barcode || ' - ' ||
                    ordered::text ||
                    ' шт.(дата поступления: ' ||
                    date_arrival ||
                    ')'
                ) AS barcode_ordered,


                list(
                    DISTINCT
                    warehouse || ' - ' ||
                    available::text ||
                    ' шт.'
                ) AS warehouse_stocks,


                list(
                    DISTINCT
                    warehouse || ' - ' ||
                    ordered::text ||
                    ' шт.'
                ) AS warehouse_ordered


            FROM (

                SELECT

                    "H" AS fullname,
                    "N" AS name,

                    "L" AS warehouse,
                    "P" AS barcode,

                    COALESCE("R",'0')::bigint AS available,
                    COALESCE("T",'0')::bigint AS ordered,

                    try_strptime(
                        "V",
                        '%d.%m.%Y'
                    )::DATE AS date_arrival


                FROM (

                    SELECT *

                    FROM read_xlsx(
                        ?,
                        range='B3:V',
                        header=false,
                        all_varchar=true
                    )

                    WHERE "B" IS NOT NULL

                )

            ) x


            LEFT JOIN items i
                ON i.fullname = x.fullname


            GROUP BY
                x.fullname,
                i.id,
                x.name,
                CURRENT_DATE

            """,
            [file]
        ).df()


        #
        # новые товары
        #
        new_items = (
            df[df["item_id"].isna()]
            [
                [
                    "fullname",
                    "name",
                    "init_date"
                ]
            ]
            .drop_duplicates()
        )


        if len(new_items) == 0:
            return df


        rows = [
            tuple(x)
            for x in new_items.to_numpy()
        ]


        #
        # настоящий MySQL INSERT IGNORE
        #
        with connection.cursor() as cursor:

            cursor.executemany(
                """
                INSERT IGNORE INTO corporate_items
                (
                    fullname,
                    name,
                    init_date
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                rows
            )


        return df



class Command(BaseCommand):

    help = "Import stocks from XLSX"


    def add_arguments(self, parser):

        parser.add_argument(
            "file",
            type=str,
            help="xlsx file path"
        )


    def handle(self, *args, **options):

        file = options["file"]

        self.stdout.write(
            f"Importing: {file}"
        )


        df = import_stocks(file)


        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Rows processed: {len(df)}"
            )
        )