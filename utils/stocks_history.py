# utils/stocks_history.py
"""
История остатков: срез на дату по товару и складу.

stocks_data — только текущие остатки (перезаписываются при каждой загрузке).
stocks_history — срезы по датам. За одну дату хранится ровно один срез:
повторная загрузка в тот же день заменяет срез, а не добавляет к нему.
Для итогов по дате суммировать только строки одного snapshot_date.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

import pandas as pd

from utils.db_engine import get_mysql_conn

TABLE = "stocks_history"
SOURCE_DAILY = "daily"
SOURCE_MONTHLY_1C = "1c_month"
BATCH = 2000

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    snapshot_date DATE NOT NULL,
    item_id BIGINT NOT NULL,
    warehouse VARCHAR(255) NOT NULL,
    available DECIMAL(14, 3) NOT NULL DEFAULT 0,
    ordered DECIMAL(14, 3) NOT NULL DEFAULT 0,
    cost_amount DECIMAL(16, 2) NULL,
    source VARCHAR(20) NOT NULL,
    loaded_at DATETIME NOT NULL,
    PRIMARY KEY (snapshot_date, item_id, warehouse),
    KEY idx_stocks_history_item (item_id, snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

NO_WAREHOUSE = "БЕЗ УКАЗАНИЯ СКЛАДА"
_ITEM_RE = re.compile(r"^(?P<wh>.*) - (?P<qty>-?\d+(?:[.,]\d+)?) шт\.")


def _parse_list(value) -> dict[str, float]:
    """["РигаМолл - 6 шт.", ...] -> {"РигаМолл": 6.0}."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    items = value
    if isinstance(value, str):
        try:
            items = json.loads(value)
        except ValueError:
            items = [value]
    out: dict[str, float] = {}
    for s in items or []:
        m = _ITEM_RE.match(str(s).strip())
        if not m:
            continue
        wh = m.group("wh").strip() or NO_WAREHOUSE
        out[wh] = out.get(wh, 0.0) + float(m.group("qty").replace(",", "."))
    return out


def snapshot_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Строки среза товар × склад из подготовленных остатков (как в stocks_data)."""
    recs = []
    for r in df.itertuples(index=False):
        item_id = getattr(r, "item_id", None)
        if item_id is None or pd.isna(item_id):
            continue
        avail = _parse_list(getattr(r, "warehouse_stocks", None))
        ordered = _parse_list(getattr(r, "warehouse_ordered", None))
        for wh in set(avail) | set(ordered):
            recs.append((int(item_id), wh[:255], avail.get(wh, 0.0), ordered.get(wh, 0.0)))
    out = pd.DataFrame(recs, columns=["item_id", "warehouse", "available", "ordered"])
    # Несколько строк файла могут указывать на одну карточку — складываем
    return out.groupby(["item_id", "warehouse"], as_index=False)[["available", "ordered"]].sum()


def save_snapshot(df: pd.DataFrame, snapshot_date: date, source: str = SOURCE_DAILY) -> str:
    """Записывает срез на дату. Существующий срез этой даты полностью заменяется (атомарно)."""
    rows = snapshot_rows(df)
    if rows.empty:
        return "История остатков: нет строк для сохранения"

    loaded_at = datetime.now().replace(microsecond=0)
    data = [
        (snapshot_date, int(r.item_id), r.warehouse, float(r.available), float(r.ordered), source, loaded_at)
        for r in rows.itertuples(index=False)
    ]

    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {TABLE} WHERE snapshot_date = %s", (snapshot_date,))
            for i in range(0, len(data), BATCH):
                cur.executemany(
                    f"INSERT INTO {TABLE} "
                    "(snapshot_date, item_id, warehouse, available, ordered, source, loaded_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    data[i:i + BATCH],
                )
            cur.execute(
                f"SELECT COUNT(*), COALESCE(SUM(available), 0) FROM {TABLE} WHERE snapshot_date = %s",
                (snapshot_date,),
            )
            n, avail = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    expected = float(rows["available"].sum())
    if abs(float(avail) - expected) > 0.5:
        raise ValueError(f"История остатков: сверка не сошлась ({avail} в базе против {expected} в файле)")
    return (f"История остатков: срез на {snapshot_date:%d.%m.%Y} сохранён "
            f"({n} строк, доступно {expected:,.0f} шт.)".replace(",", " "))
