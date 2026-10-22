# utils/item_attrs.py
"""Дозаполнение карточек товаров из выгрузок 1С: производитель, артикул, штрихкоды."""
from __future__ import annotations

from typing import Iterable

from utils.db_engine import column_collation, get_mysql_conn

# Значения, которые считаются «не заполнено»
EMPTY_VALUES = {"", "-", "—", "нет", "нет производителя", "не указан", "<не указан>",
                "нет арт.", "нет артикля", "нет артикула", "без штрихкода", "нет штрихкода",
                "none", "nan", "null"}


def is_empty(value) -> bool:
    if value is None:
        return True
    return str(value).strip().casefold() in EMPTY_VALUES


def clean(value) -> str | None:
    return None if is_empty(value) else str(value).strip()


def _text_col(cur, table: str, column: str, size: int) -> str:
    """Тип колонки временной таблицы с той же кодировкой, что у колонки-источника."""
    coll = column_collation(cur, table, column)
    return f"VARCHAR({size}) CHARACTER SET {coll.split('_')[0]} COLLATE {coll}"


def _placeholder_sql(column: str) -> str:
    values = ", ".join(f"'{v}'" for v in sorted(EMPTY_VALUES))
    return f"({column} IS NULL OR LOWER(TRIM({column})) IN ({values}))"


def fill_item_attrs(rows: Iterable[tuple]) -> str:
    """
    rows: (item_id, производитель, артикул).
    Заполняет только пустые поля карточки; новые производители добавляются в справочник.
    """
    data = {}
    for item_id, manu, article in rows:
        if item_id is None:
            continue
        manu, article = clean(manu), clean(article)
        if manu is None and article is None:
            continue
        cur = data.setdefault(int(item_id), [None, None])
        cur[0] = cur[0] or manu
        cur[1] = cur[1] or article
    if not data:
        return "Производитель/артикул: нечего дозаполнять"

    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            names = sorted({m for m, _ in data.values() if m})
            if names:
                cur.executemany(
                    "INSERT INTO corporate_itemmanufacturer (name, country) "
                    "SELECT %s, 'RU' FROM DUAL WHERE NOT EXISTS "
                    "(SELECT 1 FROM corporate_itemmanufacturer WHERE name = %s)",
                    [(n, n) for n in names],
                )

            cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_item_fill")
            cur.execute(
                "CREATE TEMPORARY TABLE tmp_item_fill (id BIGINT PRIMARY KEY, "
                f"manu {_text_col(cur, 'corporate_itemmanufacturer', 'name', 255)}, "
                f"article {_text_col(cur, 'corporate_items', 'article', 250)})"
            )
            cur.executemany(
                "INSERT INTO tmp_item_fill VALUES (%s, %s, %s)",
                [(i, m, a) for i, (m, a) in data.items()],
            )

            cur.execute(
                f"""
                UPDATE corporate_items i
                JOIN tmp_item_fill t ON t.id = i.id
                JOIN corporate_itemmanufacturer m ON m.name = t.manu
                LEFT JOIN corporate_itemmanufacturer cm ON cm.id = i.manufacturer_id
                SET i.manufacturer_id = m.id
                WHERE t.manu IS NOT NULL AND {_placeholder_sql('cm.name')}
                """
            )
            manu_cnt = cur.rowcount

            cur.execute(
                f"""
                UPDATE corporate_items i
                JOIN tmp_item_fill t ON t.id = i.id
                SET i.article = t.article
                WHERE t.article IS NOT NULL AND {_placeholder_sql('i.article')}
                """
            )
            art_cnt = cur.rowcount
        conn.commit()
        return f"Дозаполнено: производитель у {manu_cnt} товаров, артикул у {art_cnt}"
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def link_barcodes(pairs: Iterable[tuple]) -> str:
    """pairs: (item_id, штрихкод). Добавляет штрихкоды в справочник и привязывает к карточкам."""
    data = {(int(i), str(b).strip()) for i, b in pairs
            if i is not None and not is_empty(b) and len(str(b).strip()) <= 50}
    if not data:
        return "Штрихкоды: нечего привязывать"

    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT IGNORE INTO corporate_barcode (barcode) VALUES (%s)",
                sorted({(b,) for _, b in data}),
            )
            new_codes = cur.rowcount

            cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_item_bc")
            cur.execute(
                "CREATE TEMPORARY TABLE tmp_item_bc (item_id BIGINT, "
                f"barcode {_text_col(cur, 'corporate_barcode', 'barcode', 50)})"
            )
            cur.executemany("INSERT INTO tmp_item_bc VALUES (%s, %s)", sorted(data))
            cur.execute(
                """
                INSERT IGNORE INTO corporate_items_barcode (items_id, barcode_id)
                SELECT t.item_id, b.id
                FROM tmp_item_bc t
                JOIN corporate_barcode b ON b.barcode = t.barcode
                """
            )
            linked = cur.rowcount
        conn.commit()
        return f"Штрихкоды: новых {new_codes}, новых привязок к товарам {linked}"
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
