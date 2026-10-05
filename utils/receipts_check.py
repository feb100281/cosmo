# utils/receipts_check.py
"""Сверка приходов с остатками: что пришло недавно, не продано и в остатках отсутствует."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from utils.db_engine import get_mysql_conn
from utils.item_match import normalize_key

WINDOW_DAYS = None  # None — вся история приходов
MAX_NAMES = 15


def _table_exists(cur, name: str) -> bool:
    cur.execute("SHOW TABLES LIKE %s", (name,))
    return cur.fetchone() is not None


def find_receipts_without_stock(window_days: int | None = WINDOW_DAYS) -> dict:
    """
    Возвращает {"stock_date", "missing": DataFrame, "after_stock": int}.
    missing — позиции с приходом за window_days до даты остатков,
    у которых расчётный остаток (пришло − продано) больше остатка в файле.
    """
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            if not (_table_exists(cur, "stocks_data") and _table_exists(cur, "stock_receipts")):
                return {"stock_date": None, "missing": pd.DataFrame(), "after_stock": 0, "after": pd.DataFrame(), "checked": 0}

            cur.execute("SELECT MAX(init_date) FROM stocks_data")
            stock_date = cur.fetchone()[0]
            if stock_date is None:
                return {"stock_date": None, "missing": pd.DataFrame(), "after_stock": 0, "after": pd.DataFrame(), "checked": 0}
            date_from = stock_date - timedelta(days=window_days) if window_days else date(1900, 1, 1)

            # Остаток на складе — «доступно»; товар в пути (заказано) показывается отдельно.
            # Сопоставление: по названию, затем по item_id.
            cur.execute("SELECT fullname, item_id, COALESCE(tot_available, 0), COALESCE(tot_ordered, 0) "
                        "FROM stocks_data")
            stock_by_key: dict[str, list[float]] = {}
            stock_by_id: dict[int, list[float]] = {}
            for name, iid, avail, ordered in cur.fetchall():
                for bucket, k in ((stock_by_key, normalize_key(name)),
                                  (stock_by_id, int(iid) if iid is not None else None)):
                    if k in (None, ""):
                        continue
                    acc = bucket.setdefault(k, [0.0, 0.0])
                    acc[0] += float(avail or 0)
                    acc[1] += float(ordered or 0)

            cur.execute(
                "SELECT fullname, item_id, receipt_date, qty, warehouse, receipt_number FROM stock_receipts "
                "WHERE receipt_date >= %s",
                (date_from,),
            )
            rec = pd.DataFrame(list(cur.fetchall()),
                               columns=["fullname", "item_id", "receipt_date", "qty", "warehouse", "receipt_number"])
            if rec.empty:
                return {"stock_date": stock_date, "missing": rec, "after_stock": 0, "after": pd.DataFrame(), "checked": 0}

            # Продажи считаются с даты первого прихода товара в выбранном окне
            cur.execute(
                "SELECT s.item_id, SUM(s.quant_dt - s.quant_cr) FROM sales_salesdata s "
                "JOIN (SELECT item_id, MIN(receipt_date) AS d FROM stock_receipts "
                "      WHERE item_id IS NOT NULL AND receipt_date >= %s GROUP BY item_id) r "
                "  ON r.item_id = s.item_id AND s.date >= r.d "
                "GROUP BY s.item_id",
                (date_from,),
            )
            sold = {int(r[0]): float(r[1] or 0) for r in cur.fetchall()}
            cur.execute("SELECT MAX(date) FROM sales_salesdata")
            sales_date = cur.fetchone()[0]
    finally:
        conn.close()

    rec["receipt_date"] = pd.to_datetime(rec["receipt_date"]).dt.date
    rec["qty"] = pd.to_numeric(rec["qty"], errors="coerce").fillna(0)
    rec["key"] = rec["fullname"].map(normalize_key)
    rec["doc"] = [
        f"{n} от {d:%d.%m.%Y}" if n else f"без номера от {d:%d.%m.%Y}"
        for n, d in zip(rec["receipt_number"], rec["receipt_date"])
    ]

    after = rec[rec["receipt_date"] > stock_date]
    rec = rec[rec["receipt_date"] <= stock_date]

    g = (rec.groupby("key")
         .agg(fullname=("fullname", "first"), item_id=("item_id", "first"), qty=("qty", "sum"),
              first_date=("receipt_date", "min"), last_date=("receipt_date", "max"),
              docs=("doc", lambda s: ", ".join(dict.fromkeys(s))),
              warehouse=("warehouse", lambda s: ", ".join(sorted({str(x) for x in s if x}))))
         .reset_index())
    def _stock(row):
        hit = stock_by_key.get(row["key"])
        if hit is None and pd.notna(row["item_id"]):
            hit = stock_by_id.get(int(row["item_id"]))
        return hit

    hits = g.apply(_stock, axis=1)
    g["stock"] = hits.map(lambda h: h[0] if h else 0.0)
    g["ordered"] = hits.map(lambda h: h[1] if h else 0.0)
    g["in_file"] = [
        "нет в файле" if h is None else ("есть, количество 0" if h[0] <= 0 else "есть, меньше расчётного")
        for h in hits
    ]
    g["age_days"] = g["last_date"].map(lambda d: (stock_date - d).days)
    g["sold"] = g["item_id"].map(lambda v: sold.get(int(v), 0.0) if pd.notna(v) else 0.0)
    g["left"] = g["qty"] - g["sold"].clip(lower=0)
    g["no_card"] = g["item_id"].isna()
    # Недостача: расчётный остаток (пришло − продано) больше фактического.
    # Излишек не считается расхождением: у товара могли быть остатки до начала истории приходов.
    g["shortage"] = g["left"] - g["stock"]
    missing = g[g["shortage"] > 0].sort_values(["last_date", "shortage"], ascending=[False, False])

    after_df = (after.groupby("key")
                .agg(fullname=("fullname", "first"), qty=("qty", "sum"), last_date=("receipt_date", "max"),
                     docs=("doc", lambda s: ", ".join(dict.fromkeys(s))),
                     warehouse=("warehouse", lambda s: ", ".join(sorted({str(x) for x in s if x}))))
                .reset_index().sort_values("last_date", ascending=False))

    return {
        "stock_date": stock_date,
        "missing": missing.reset_index(drop=True),
        "after_stock": int(after["key"].nunique()),
        "after": after_df.reset_index(drop=True),
        "checked": int(rec["key"].nunique()),
        "sales_date": sales_date,
    }


def find_receipts_without_card() -> pd.DataFrame:
    """Товары из приходов, которые ни разу не встречались в продажах и остатках."""
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            if not _table_exists(cur, "stock_receipts"):
                return pd.DataFrame()
            cur.execute(
                "SELECT fullname, receipt_date, receipt_number, qty, warehouse, amount_purchase "
                "FROM stock_receipts WHERE item_id IS NULL"
            )
            rows = list(cur.fetchall())
            cur.execute("SELECT fullname FROM corporate_items")
            card_names = [r[0] for r in cur.fetchall() if r[0]]
            stock_keys = {}
            if _table_exists(cur, "stocks_data"):
                cur.execute("SELECT fullname, COALESCE(total, 0) FROM stocks_data")
                stock_keys = {normalize_key(r[0]): float(r[1] or 0) for r in cur.fetchall()}
    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=["fullname", "receipt_date", "receipt_number", "qty", "warehouse", "amount"])
    if df.empty:
        return df
    df["receipt_date"] = pd.to_datetime(df["receipt_date"]).dt.date
    for c in ("qty", "amount"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["key"] = df["fullname"].map(normalize_key)
    df["doc"] = [f"{n} от {d:%d.%m.%Y}" if n else f"без номера от {d:%d.%m.%Y}"
                 for n, d in zip(df["receipt_number"], df["receipt_date"])]
    g = (df.groupby("key")
         .agg(fullname=("fullname", "first"), qty=("qty", "sum"), amount=("amount", lambda s: s.sum(min_count=1)),
              docs=("receipt_number", "nunique"), first_date=("receipt_date", "min"),
              doc_list=("doc", lambda s: ", ".join(dict.fromkeys(s))),
              last_date=("receipt_date", "max"),
              warehouse=("warehouse", lambda s: ", ".join(sorted({str(x) for x in s if x}))))
         .reset_index())
    g["in_file"] = g["key"].map(
        lambda k: "нет в файле" if k not in stock_keys else ("есть" if stock_keys[k] > 0 else "есть, количество 0")
    )
    # Похожие названия в базе: возможное расхождение написания между приходом и продажами/остатками
    import difflib

    by_key = {normalize_key(n): n for n in card_names}
    keys = list(by_key)

    def similar(key):
        hit = difflib.get_close_matches(key, keys, n=1, cutoff=0.82)
        if not hit:
            return "", None
        return by_key[hit[0]], difflib.SequenceMatcher(None, key, hit[0]).ratio()

    found = g["key"].map(similar)
    g["similar"] = found.map(lambda x: x[0])
    g["similarity"] = found.map(lambda x: x[1])
    return g.sort_values(["last_date", "qty"], ascending=[False, False]).reset_index(drop=True)


def find_sales_without_receipts() -> dict:
    """Товары, которые продавались с начала истории приходов, но ни одного прихода по ним нет."""
    empty = {"start": None, "rows": pd.DataFrame()}
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            if not _table_exists(cur, "stock_receipts"):
                return empty
            cur.execute("SELECT MIN(receipt_date) FROM stock_receipts")
            start = cur.fetchone()[0]
            if start is None:
                return empty
            cur.execute(
                "SELECT s.item_id, i.fullname, cat.name, "
                "       SUM(s.quant_dt - s.quant_cr), SUM(s.dt - s.cr), MIN(s.date), MAX(s.date) "
                "FROM sales_salesdata s "
                "JOIN corporate_items i ON i.id = s.item_id "
                "LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id "
                "LEFT JOIN corporate_cattree root ON root.tree_id = cat.tree_id AND root.level = 0 "
                "WHERE s.date >= %s "
                # услуги и логистика — не товар, приходов по ним не бывает
                "  AND COALESCE(root.id, 0) <> 86 "
                "  AND LOWER(COALESCE(cat.name, '')) NOT LIKE '%%услуг%%' "
                "  AND LOWER(COALESCE(cat.name, '')) NOT LIKE '%%логист%%' "
                "  AND LOWER(COALESCE(root.name, '')) NOT LIKE '%%услуг%%' "
                "  AND LOWER(COALESCE(root.name, '')) NOT LIKE '%%логист%%' "
                "  AND NOT EXISTS (SELECT 1 FROM stock_receipts r WHERE r.item_id = s.item_id) "
                "GROUP BY s.item_id, i.fullname, cat.name "
                "HAVING SUM(s.quant_dt - s.quant_cr) > 0",
                (start,),
            )
            rows = list(cur.fetchall())
            ids = [int(r[0]) for r in rows]
            first_sale, stock = {}, {}
            if ids:
                marks = ",".join(["%s"] * len(ids))
                cur.execute(
                    f"SELECT item_id, MIN(date) FROM sales_salesdata "
                    f"WHERE quant_dt > 0 AND item_id IN ({marks}) GROUP BY item_id", ids,
                )
                first_sale = {int(r[0]): r[1] for r in cur.fetchall()}
                if _table_exists(cur, "stocks_data"):
                    cur.execute(
                        f"SELECT item_id, SUM(COALESCE(tot_available, 0)) FROM stocks_data "
                        f"WHERE item_id IN ({marks}) GROUP BY item_id", ids,
                    )
                    stock = {int(r[0]): float(r[1] or 0) for r in cur.fetchall()}
    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=["item_id", "fullname", "cat", "sold", "revenue", "first_in_period", "last_sale"])
    if df.empty:
        return {"start": start, "rows": df}
    for c in ("sold", "revenue"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["first_sale"] = df["item_id"].map(lambda v: first_sale.get(int(v)))
    df["stock"] = df["item_id"].map(lambda v: stock.get(int(v), 0.0))
    # Впервые продан уже после начала истории приходов — приход по нему должен был быть
    df["new_item"] = df["first_sale"].map(lambda d: d is not None and d >= start)
    df["note"] = df["new_item"].map({
        True: "первая продажа позже начала истории приходов — прихода нет",
        False: "продавался и раньше — возможно, старый запас",
    })
    df = df.sort_values(["new_item", "sold"], ascending=[False, False]).reset_index(drop=True)
    return {"start": start, "rows": df}


def check_messages(window_days: int | None = WINDOW_DAYS) -> list[str]:
    """Строки для вывода после загрузки приходов или остатков."""
    try:
        res = find_receipts_without_stock(window_days)
    except Exception as exc:
        return [f"Сверка приходов с остатками не выполнена: {exc}"]

    stock_date, missing = res["stock_date"], res["missing"]
    if stock_date is None:
        return []

    scope = f"за {window_days} дн. до даты остатков" if window_days else "за всю историю"
    out = []
    if missing.empty:
        out.append(f"Сверка с остатками на {stock_date:%d.%m.%Y}: по приходам {scope} "
                   f"недостачи нет")
    else:
        units = f"{missing['shortage'].sum():,.0f}".replace(",", " ")
        recent = int((missing["age_days"] <= 90).sum())
        absent = int((missing["stock"] <= 0).sum())
        out.append(
            f"ВНИМАНИЕ. Остатков на {stock_date:%d.%m.%Y} меньше, чем должно быть по приходам и продажам "
            f"({scope}): {len(missing)} поз., не хватает {units} шт. Из них совсем нет в остатках: {absent} поз., "
            f"с приходом за последние 90 дн.: {recent} поз. Подробности — в файле сверки"
        )
        names = [
            f"{r.fullname} — должно быть {r.left:,.0f}, в остатках {r.stock:,.0f}, "
            f"приход {r.last_date:%d.%m.%Y}"
            + (" (нет ни в продажах, ни в остатках)" if r.no_card else "")
            for r in missing.head(MAX_NAMES).itertuples()
        ]
        tail = f" … и ещё {len(missing) - MAX_NAMES}" if len(missing) > MAX_NAMES else ""
        out.append("Расхождения: " + " | ".join(names).replace(";", ",") + tail)
    try:
        nr = find_sales_without_receipts()
        if not nr["rows"].empty:
            new = nr["rows"][nr["rows"]["new_item"]]
            out.append(
                f"Продажи без приходов (с {nr['start']:%d.%m.%Y}): {len(nr['rows'])} поз. Из них впервые проданы "
                f"уже после этой даты, а прихода нет: {len(new)} поз., "
                + f"{new['sold'].sum():,.0f}".replace(",", " ") + " шт. — см. лист «Продажи без приходов»"
            )
    except Exception as exc:
        out.append(f"Сверка приходов с остатками не выполнена (продажи без приходов): {exc}")
    sales_date = res.get("sales_date")
    if sales_date and sales_date < stock_date:
        out.append(f"Продажи отстают: продажи загружены только по {sales_date:%d.%m.%Y}, а остатки на "
                   f"{stock_date:%d.%m.%Y} — проданное за эти дни в сверке не учтено, загрузите свежие продажи")
    if res["after_stock"]:
        out.append(f"Приходы позже даты остатков: {res['after_stock']} поз. — не сверялись, "
                   f"загрузите свежие остатки")
    return out


def build_check_excel_bytes(window_days: int | None = WINDOW_DAYS) -> bytes:
    """Excel со сверкой приходов и остатков."""
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.utils.dataframe import dataframe_to_rows

    from sales.reports.xl_brand import (
        FMT_DATE, FMT_MONEY, FMT_QTY, build_toc, finalize, set_number_format, style_table_sheet,
    )

    res = find_receipts_without_stock(window_days)
    stock_date, missing, after = res["stock_date"], res["missing"], res["after"]
    stock_label = f"{stock_date:%d.%m.%Y}" if stock_date else "нет данных"
    scope = f"за {window_days} дн. до даты остатков" if window_days else "за всю историю"

    wb = Workbook()
    wb.remove(wb.active)

    def sheet(name, df, title, subtitle, widths, key):
        ws = wb.create_sheet(name)
        for row in dataframe_to_rows(df, index=False, header=True):
            ws.append(row)
        hdr = style_table_sheet(ws, title=title, subtitle=subtitle, freeze_col=2, key_headers=(key,),
                                wrap_headers=("Документы прихода",))
        set_number_format(ws, hdr, ["Пришло, шт.", "Продано, шт.", "Должно быть, шт.", "Документов", "Дней с прихода", "В остатках, шт.", "Не хватает, шт.", "В пути, шт."], FMT_QTY)
        set_number_format(ws, hdr, ["Сумма без НДС, ₽", "Выручка, ₽"], FMT_MONEY)
        set_number_format(ws, hdr, ["Последний приход", "Первый приход", "Первая продажа", "Последняя продажа"], FMT_DATE)
        set_number_format(ws, hdr, ["Сходство"], "0%")
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    if not missing.empty:
        m = pd.DataFrame({
            "Номенклатура": missing["fullname"],
            "Пришло, шт.": missing["qty"],
            "Продано, шт.": missing["sold"],
            "Должно быть, шт.": missing["left"],
            "В остатках, шт.": missing["stock"],
            "Не хватает, шт.": missing["shortage"],
            "В пути, шт.": missing["ordered"],
            "Документы прихода": missing["docs"],
            "Первый приход": missing["first_date"],
            "Последний приход": missing["last_date"],
            "Дней с прихода": missing["age_days"],
            "Склад прихода": missing["warehouse"],
            "В файле остатков": missing["in_file"],
            "Был в продажах или остатках": missing["no_card"].map({True: "нет, только приход", False: "да"}),
            "item_id": missing["item_id"],
        })
    else:
        m = pd.DataFrame(columns=["Номенклатура", "Пришло, шт.", "Продано, шт.", "Должно быть, шт.",
                                  "В остатках, шт.", "Не хватает, шт.", "В пути, шт.",
                                  "Документы прихода", "Первый приход", "Последний приход", "Дней с прихода",
                                  "Склад прихода", "В файле остатков",
                                  "Был в продажах или остатках", "item_id"])
    sheet("Расхождения", m, "ОСТАТКОВ МЕНЬШЕ, ЧЕМ ДОЛЖНО БЫТЬ",
          f"Приходы {scope}, остатки на {stock_label}. Должно быть = пришло − продано с первого прихода. "
          f"Излишки не показываются",
          [52, 13, 13, 16, 15, 15, 12, 44, 14, 16, 14, 30, 24, 16, 10], "Не хватает, шт.")

    if after is not None and not after.empty:
        a = pd.DataFrame({
            "Номенклатура": after["fullname"],
            "Пришло, шт.": after["qty"],
            "Документы прихода": after["docs"],
            "Последний приход": after["last_date"],
            "Склад прихода": after["warehouse"],
        })
        sheet("Позже даты остатков", a, "ПРИХОДЫ ПОЗЖЕ ДАТЫ ОСТАТКОВ",
              f"Не сверялись: остатки загружены на {stock_label}", [52, 13, 44, 16, 30], "Пришло, шт.")

    no_card_df = find_receipts_without_card()
    if not no_card_df.empty:
        n = pd.DataFrame({
            "Номенклатура": no_card_df["fullname"],
            "Пришло, шт.": no_card_df["qty"],
            "Сумма без НДС, ₽": no_card_df["amount"],
            "Документов": no_card_df["docs"],
            "Документы прихода": no_card_df["doc_list"],
            "Первый приход": no_card_df["first_date"],
            "Последний приход": no_card_df["last_date"],
            "Склад прихода": no_card_df["warehouse"],
            "В файле остатков": no_card_df["in_file"],
            "Похожее название в базе": no_card_df["similar"],
            "Сходство": no_card_df["similarity"],
        })
        sheet("Только в приходах", n, "ТОВАРЫ, КОТОРЫЕ ЕСТЬ ТОЛЬКО В ПРИХОДАХ",
              "За всю историю: приход из 1С был, но товар ни разу не встречался ни в загруженных продажах, ни в остатках",
              [52, 13, 16, 12, 44, 14, 16, 30, 20, 52, 11], "Пришло, шт.")

    nr = find_sales_without_receipts()
    if not nr["rows"].empty:
        r = nr["rows"]
        sn = pd.DataFrame({
            "Номенклатура": r["fullname"],
            "Категория": r["cat"],
            "Продано, шт.": r["sold"],
            "Выручка, ₽": r["revenue"],
            "Первая продажа": r["first_sale"],
            "Последняя продажа": r["last_sale"],
            "В остатках, шт.": r["stock"],
            "Примечание": r["note"],
            "item_id": r["item_id"],
        })
        sheet("Продажи без приходов", sn, "ПРОДАЖИ ЕСТЬ, ПРИХОДОВ НЕТ",
              f"Товары, проданные с {nr['start']:%d.%m.%Y} (начало истории приходов), по которым нет ни одного прихода. Услуги и логистика исключены",
              [52, 24, 13, 16, 15, 17, 15, 52, 10], "Продано, шт.")

    units = float(missing["shortage"].sum()) if not missing.empty else 0
    no_card = int(missing["no_card"].sum()) if not missing.empty else 0
    build_toc(
        wb,
        title="Сверка приходов и остатков",
        subtitle="Что пришло на склад, не продано и отсутствует в выгрузке остатков",
        params=f"Остатки на {stock_label} · приходы {scope}"
               + (f" · продажи по {res['sales_date']:%d.%m.%Y}" if res.get("sales_date") else ""),
        sheets=[
            ("Расхождения", "Позиции, где остаток меньше расчётного или товара нет совсем"),
            ("Позже даты остатков", "Приходы после даты остатков — сверить после загрузки свежих остатков"),
            ("Только в приходах", "Товары, которые были в приходах, но ни разу не встречались ни в продажах, ни в остатках"),
            ("Продажи без приходов", "Товары, которые продавались, но ни одного прихода по ним нет"),
        ],
        cards=[
            ("РАСХОЖДЕНИЙ, ПОЗ.", len(missing), FMT_QTY, f"из {res['checked']} проверенных"),
            ("НЕ ХВАТАЕТ, ШТ.", units, FMT_QTY, "должно быть минус остаток"),
            ("ТОЛЬКО В ПРИХОДАХ", len(no_card_df), FMT_QTY, "нет ни в продажах, ни в остатках"),
            ("ПОЗЖЕ ДАТЫ ОСТАТКОВ", res["after_stock"], FMT_QTY, "не сверялись"),
        ],
    )
    finalize(wb, ["Оглавление", "Расхождения", "Позже даты остатков", "Только в приходах", "Продажи без приходов"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
