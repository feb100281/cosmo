# utils/import_receipts.py
"""
Загрузка приходов товаров в stock_receipts.
Приходы из файла заменяются целиком по GUID_Прихода.
Цена/сумма закупки подхватываются, если колонки есть в файле.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import openpyxl

from utils.db_engine import column_collation, get_mysql_conn


TABLE = "stock_receipts"

REQUIRED = {
    "GUID_Прихода": "receipt_guid",
    "Номенклатура": "fullname",
    "Дата прихода": "receipt_date",
    "Приход": "qty",
}
OPTIONAL = {
    "GUID_Номенклатуры": "item_guid",
    "GUID_Характеристики": "char_guid",
    "GUID_Склада": "warehouse_guid",
    "Характеристика": "characteristic",
    "Склад": "warehouse",
    "Номер прихода": "receipt_number",
    "Штрихкод": "barcode",
}
# Суммы с НДС не используются: закупка учитывается без НДС.
PRICE_KEYS = ("цена", "себестоимость")
AMOUNT_KEYS = ("сумма",)


def _find_money_column(names, keys):
    """
    Колонка цены/суммы по вхождению ключевых слов; «без НДС» в приоритете,
    колонки «с НДС» пропускаются, если есть вариант без НДС.
    """
    found = [n for n in names if any(k in n.lower() for k in keys)]
    if not found:
        return None
    no_vat = [n for n in found if "без ндс" in n.lower()]
    if no_vat:
        return no_vat[0]
    plain = [n for n in found if "ндс" not in n.lower()]
    return plain[0] if plain else None

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    receipt_guid VARCHAR(64) NOT NULL,
    receipt_number VARCHAR(100) NULL,
    receipt_date DATE NULL,
    item_id BIGINT NULL,
    item_guid VARCHAR(64) NULL,
    char_guid VARCHAR(64) NULL,
    warehouse_guid VARCHAR(64) NULL,
    fullname VARCHAR(500) NULL,
    characteristic TEXT NULL,
    warehouse VARCHAR(255) NULL,
    barcode VARCHAR(100) NULL,
    qty DECIMAL(14,3) NOT NULL DEFAULT 0,
    price_purchase DECIMAL(14,2) NULL,
    amount_purchase DECIMAL(16,2) NULL,
    loaded_at DATETIME NOT NULL,
    KEY ix_receipt_guid (receipt_guid),
    KEY ix_receipt_date (receipt_date),
    KEY ix_item_id (item_id),
    KEY ix_barcode (barcode)
) DEFAULT CHARSET=utf8mb4
"""

COLUMNS = [
    "receipt_guid", "receipt_number", "receipt_date", "item_id", "item_guid",
    "char_guid", "warehouse_guid", "fullname", "characteristic", "warehouse",
    "barcode", "qty", "price_purchase", "amount_purchase", "loaded_at",
]


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    for a, b in ((" ", " "), (" ", " "), ("​", ""), ("﻿", "")):
        text = text.replace(a, b)
    return " ".join(text.split()).strip()


def _to_number(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _norm(value).replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _to_date(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    text = _norm(value)
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def read_receipts_file(file) -> pd.DataFrame:
    """Значение поля ищется от колонки заголовка до следующего заголовка (объединённые ячейки)."""
    wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    header_idx = None
    for i, row in enumerate(rows[:30]):
        if any(_norm(c) == "GUID_Прихода" for c in row):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Не найдена строка заголовков (колонка «GUID_Прихода»)")

    header = rows[header_idx]
    positions = [(i, _norm(h)) for i, h in enumerate(header) if _norm(h)]
    spans = {}
    for n, (col, name) in enumerate(positions):
        end = positions[n + 1][0] if n + 1 < len(positions) else len(header) + 1
        spans[name] = (col, end)

    missing = [h for h in REQUIRED if h not in spans]
    if missing:
        raise ValueError("В файле приходов не найдены колонки: " + ", ".join(missing))

    price_col = _find_money_column(list(spans), PRICE_KEYS)
    amount_col = _find_money_column(list(spans), AMOUNT_KEYS)

    def cell(row, name):
        start, end = spans[name]
        for j in range(start, min(end, len(row))):
            if row[j] not in (None, ""):
                return row[j]
        return None

    fields = {**REQUIRED, **{k: v for k, v in OPTIONAL.items() if k in spans}}
    records = []
    for row in rows[header_idx + 1:]:
        if row is None or all(c in (None, "") for c in row):
            continue
        rec = {field: cell(row, src) for src, field in fields.items()}
        rec["price_purchase"] = _to_number(cell(row, price_col)) if price_col else None
        rec["amount_purchase"] = _to_number(cell(row, amount_col)) if amount_col else None
        records.append(rec)

    df = pd.DataFrame(records)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None
    if df.empty:
        return df[COLUMNS]

    for c in ("receipt_guid", "item_guid", "char_guid", "warehouse_guid",
              "fullname", "characteristic", "warehouse", "receipt_number", "barcode"):
        df[c] = df[c].map(lambda v: _norm(v) or None)

    df["receipt_date"] = df["receipt_date"].map(_to_date)
    df["qty"] = df["qty"].map(_to_number).fillna(0.0)

    df = df[df["receipt_guid"].notna()].copy()

    df["price_purchase"] = pd.to_numeric(df["price_purchase"], errors="coerce").astype(float)
    df["amount_purchase"] = pd.to_numeric(df["amount_purchase"], errors="coerce").astype(float)
    has_price = df["price_purchase"].notna()
    has_amount = df["amount_purchase"].notna()
    df.loc[has_price & ~has_amount, "amount_purchase"] = (
        df.loc[has_price & ~has_amount, "price_purchase"] * df.loc[has_price & ~has_amount, "qty"]
    )
    fill_price = ~has_price & has_amount & (df["qty"] != 0)
    df.loc[fill_price, "price_purchase"] = df.loc[fill_price, "amount_purchase"] / df.loc[fill_price, "qty"]

    return df


def assign_items(df: pd.DataFrame, cur) -> pd.DataFrame:
    from utils.import_stocks import normalize_key

    cur.execute("SELECT id, fullname, guid FROM corporate_items")
    items = cur.fetchall()

    by_name: dict[str, int] = {}
    by_guid: dict[str, int] = {}
    for item_id, fullname, guid in items:
        key = normalize_key(fullname)
        if key and (key not in by_name or item_id < by_name[key]):
            by_name[key] = item_id
        if guid:
            g = str(guid).strip().lower()
            if g and (g not in by_guid or item_id < by_guid[g]):
                by_guid[g] = item_id

    def match(row):
        item = by_name.get(normalize_key(row["fullname"]))
        if item is None and row.get("item_guid"):
            item = by_guid.get(str(row["item_guid"]).lower())
        return item

    df = df.copy()
    df["item_id"] = df.apply(match, axis=1) if not df.empty else None
    return df


def _rows(df: pd.DataFrame) -> list[tuple]:
    work = df[COLUMNS].astype(object).where(pd.notna(df[COLUMNS]), None)
    return [tuple(r) for r in work.itertuples(index=False, name=None)]


def import_receipts(file) -> str:
    df = read_receipts_file(file)
    if df.empty:
        return "В файле нет строк приходов"

    df["loaded_at"] = datetime.now().replace(microsecond=0)
    guids = sorted(df["receipt_guid"].unique().tolist())

    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_SQL)
            conn.commit()

            df = assign_items(df, cur)

            cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_upload_receipts")
            cur.execute("CREATE TEMPORARY TABLE tmp_upload_receipts (guid VARCHAR(64) NOT NULL PRIMARY KEY)")
            cur.executemany("INSERT IGNORE INTO tmp_upload_receipts (guid) VALUES (%s)", [(g,) for g in guids])
            coll = column_collation(cur, TABLE, "receipt_guid")

            cur.execute(
                f"SELECT COUNT(DISTINCT r.receipt_guid) FROM {TABLE} r "
                f"JOIN tmp_upload_receipts t ON t.guid COLLATE {coll} = r.receipt_guid"
            )
            existed = cur.fetchone()[0]

            cur.execute(
                f"DELETE r FROM {TABLE} r JOIN tmp_upload_receipts t ON t.guid COLLATE {coll} = r.receipt_guid"
            )
            deleted = cur.rowcount

            placeholders = ",".join(["%s"] * len(COLUMNS))
            cur.executemany(
                f"INSERT INTO {TABLE} ({','.join(COLUMNS)}) VALUES ({placeholders})",
                _rows(df),
            )
            cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_upload_receipts")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    d_min, d_max = df["receipt_date"].dropna().min(), df["receipt_date"].dropna().max()
    unmatched = df[df["item_id"].isna()]
    log = [
        f"Период приходов в файле: {d_min:%d.%m.%Y} – {d_max:%d.%m.%Y}" if d_min else "Даты приходов не распознаны",
        f"Документов прихода: {len(guids)} (обновлено {existed}, новых {len(guids) - existed})",
        f"Строк загружено: {len(df)} (заменено старых строк: {deleted}), штук: {df['qty'].sum():,.0f}".replace(",", " "),
    ]
    if df["price_purchase"].notna().any():
        log.append(f"Закупочная цена без НДС есть у {int(df['price_purchase'].notna().sum())} строк")
    else:
        log.append("Закупочной цены в файле нет — загружены только количества")
    if not unmatched.empty:
        names = ", ".join(unmatched["fullname"].dropna().unique()[:10])
        log.append(f"Не сопоставлено с номенклатурой: {unmatched['fullname'].nunique()} поз. ({names}…)")
    return "; ".join(log)
