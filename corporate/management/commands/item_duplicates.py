# corporate/management/commands/item_duplicates.py
import pandas as pd
from django.core.management.base import BaseCommand

from utils.db_engine import get_mysql_conn
from utils.item_match import ITEMS_SQL, duplicate_groups, normalize_key

FACT_TABLES = [
    ("sales_salesdata", "item_id"),
    ("orders_orderitem", "item_id"),
    ("stocks_data", "item_id"),
    ("stock_receipts", "item_id"),
]


class Command(BaseCommand):
    help = "Дубли номенклатуры (одно имя с точностью до регистра и пробелов) и перенос фактов на основную карточку"

    def add_arguments(self, parser):
        parser.add_argument("--name", help="Проверить одну номенклатуру")
        parser.add_argument("--merge", action="store_true", help="Перенести продажи/заказы/остатки на основную карточку")

    def handle(self, *args, **opts):
        conn = get_mysql_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(ITEMS_SQL)
                items = pd.DataFrame(list(cur.fetchall()), columns=["id", "fullname", "cat_id", "manufacturer_id"])

                if opts.get("name"):
                    self._show_one(cur, items, opts["name"])
                    return

                dup = duplicate_groups(items)
                if dup.empty:
                    self.stdout.write(self.style.SUCCESS("Дублей нет"))
                    return

                for key, grp in dup.groupby("key"):
                    self.stdout.write(f"\n{key}")
                    for r in grp.itertuples():
                        mark = "*" if r.id == r.canonical_id else " "
                        self.stdout.write(
                            f"  {mark} id={r.id} cat={r.cat_id} manu={r.manufacturer_id} «{r.fullname}»"
                        )
                self.stdout.write(f"\nГрупп: {dup['key'].nunique()}; * — основная карточка")

                if not opts["merge"]:
                    self.stdout.write("Для переноса фактов запустите с --merge")
                    return

                pairs = [
                    (int(r.canonical_id), int(r.id))
                    for r in dup.itertuples()
                    if r.id != r.canonical_id
                ]
                for table, col in FACT_TABLES:
                    cur.execute("SHOW TABLES LIKE %s", (table,))
                    if not cur.fetchone():
                        continue
                    cur.executemany(f"UPDATE {table} SET {col} = %s WHERE {col} = %s", pairs)
                    self.stdout.write(f"{table}: перенесено строк {cur.rowcount}")
            conn.commit()
            self.stdout.write(self.style.SUCCESS("Готово. Пересоберите витрины продаж (или перезагрузите файл продаж)."))
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _show_one(self, cur, items, name):
        key = normalize_key(name)
        hits = items[items["fullname"].map(normalize_key) == key]
        if hits.empty:
            self.stdout.write(self.style.WARNING(f"В corporate_items нет «{name}»"))
            return
        for r in hits.itertuples():
            cur.execute(
                "SELECT COUNT(*), MIN(date), MAX(date), SUM(quant_dt) FROM sales_salesdata WHERE item_id = %s",
                (int(r.id),),
            )
            n, d1, d2, q = cur.fetchone()
            self.stdout.write(
                f"id={r.id} cat={r.cat_id} manu={r.manufacturer_id} «{r.fullname}»: "
                f"продаж строк {n}, шт {q or 0}, {d1} — {d2}"
            )
