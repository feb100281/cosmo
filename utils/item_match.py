# utils/item_match.py
"""Единое сопоставление номенклатуры 1С с corporate_items.

Ключ — нормализованное «Номенклатура» (регистр, пробелы, NBSP).
Если на один ключ приходится несколько карточек, берётся заполненная:
сначала с категорией, затем с производителем, затем с минимальным id.
Правило общее для продаж, остатков и приходов.
"""
from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

ITEMS_SQL = "SELECT id, fullname, cat_id, manufacturer_id FROM corporate_items"

_REPLACEMENTS = {
    " ": " ",
    " ": " ",
    " ": " ",
    "​": "",
    "﻿": "",
    "\t": " ",
    "\r": " ",
    "\n": " ",
}


def normalize_key(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value)
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return " ".join(text.split()).casefold()


def canonical_items(items: pd.DataFrame) -> pd.DataFrame:
    """Возвращает key → id (одна карточка на ключ)."""
    if items is None or items.empty:
        return pd.DataFrame({"key": pd.Series(dtype=str), "id": pd.Series(dtype="int64")})

    work = items.copy()
    for col in ("cat_id", "manufacturer_id"):
        if col not in work.columns:
            work[col] = None
    work["id"] = pd.to_numeric(work["id"], errors="coerce")
    work = work.dropna(subset=["id"])
    work["key"] = work["fullname"].map(normalize_key)
    work = work[work["key"] != ""]
    work["_rank"] = work["cat_id"].isna().astype(int) * 2 + work["manufacturer_id"].isna().astype(int)
    work = work.sort_values(["key", "_rank", "id"]).drop_duplicates("key")
    work["id"] = work["id"].astype("int64")
    return work[["key", "id"]].reset_index(drop=True)


def item_map(items: pd.DataFrame) -> dict[str, int]:
    df = canonical_items(items)
    return dict(zip(df["key"], df["id"]))


def item_map_from_rows(rows: Iterable[tuple]) -> dict[str, int]:
    """rows: (id, fullname, cat_id, manufacturer_id)."""
    df = pd.DataFrame(list(rows), columns=["id", "fullname", "cat_id", "manufacturer_id"])
    return item_map(df)


def duplicate_groups(items: pd.DataFrame) -> pd.DataFrame:
    """Карточки, у которых нормализованное имя совпадает с другой карточкой."""
    work = items.copy()
    work["key"] = work["fullname"].map(normalize_key)
    work = work[work["key"] != ""]
    dup = work[work.duplicated("key", keep=False)]
    if dup.empty:
        return dup.assign(canonical_id=pd.Series(dtype="int64"))
    canon = canonical_items(dup).rename(columns={"id": "canonical_id"})
    return dup.merge(canon, on="key").sort_values(["key", "id"])
