# utils/price_changes.py
"""Изменение закупочных цен между приходами одного товара (номенклатура + характеристика)."""
from __future__ import annotations

from io import BytesIO

import pandas as pd

from utils.db_engine import get_mysql_conn
from utils.item_match import normalize_key

MIN_CHANGE = 0.01      # изменения меньше 1% считаются округлением
RECENT_DAYS = 30
MAX_NAMES = 10
SUSPECT_UP = 1.0       # рост больше чем вдвое — вероятна ошибка в одном из документов
SUSPECT_DOWN = -0.5


def load_price_history() -> pd.DataFrame:
    """Строка на (товар, характеристика, документ прихода) с ценой и изменением к предыдущему приходу."""
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'stock_receipts'")
            if not cur.fetchone():
                return pd.DataFrame()
            cur.execute(
                "SELECT fullname, characteristic, receipt_guid, receipt_number, receipt_date, "
                "qty, amount_purchase FROM stock_receipts "
                "WHERE qty > 0 AND amount_purchase > 0"
            )
            rows = list(cur.fetchall())
            stock = {}
            cur.execute("SHOW TABLES LIKE 'stocks_data'")
            if cur.fetchone():
                cur.execute("SELECT fullname, COALESCE(tot_available, 0) FROM stocks_data")
                for name, qty in cur.fetchall():
                    k = normalize_key(name)
                    stock[k] = stock.get(k, 0.0) + float(qty or 0)
    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=["fullname", "characteristic", "receipt_guid", "receipt_number",
                                     "receipt_date", "qty", "amount"])
    if df.empty:
        return df
    df["receipt_date"] = pd.to_datetime(df["receipt_date"]).dt.date
    for c in ("qty", "amount"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["characteristic"] = df["characteristic"].fillna("").astype(str).str.strip()
    df["key"] = df["fullname"].map(normalize_key) + "|" + df["characteristic"].map(normalize_key)

    # Один документ — одна цена товара (средневзвешенная по строкам документа)
    g = (df.groupby(["key", "receipt_guid"], as_index=False)
         .agg(fullname=("fullname", "first"), characteristic=("characteristic", "first"),
              receipt_number=("receipt_number", "first"), receipt_date=("receipt_date", "max"),
              qty=("qty", "sum"), amount=("amount", "sum")))
    g["price"] = g["amount"] / g["qty"]
    g = g.sort_values(["key", "receipt_date", "receipt_number"]).reset_index(drop=True)

    prev = g.groupby("key")
    g["prev_price"] = prev["price"].shift(1)
    g["prev_date"] = prev["receipt_date"].shift(1)
    g["prev_number"] = prev["receipt_number"].shift(1)
    g["delta"] = g["price"] - g["prev_price"]
    g["delta_pct"] = g["delta"] / g["prev_price"]
    g["extra_cost"] = g["delta"] * g["qty"]
    g["is_last"] = ~g.duplicated("key", keep="last")
    g["note"] = [
        "проверить цену в документах" if pd.notna(p) and (p >= SUSPECT_UP or p <= SUSPECT_DOWN) else ""
        for p in g["delta_pct"]
    ]
    g["doc"] = [f"{n} от {d:%d.%m.%Y}" for n, d in zip(g["receipt_number"], g["receipt_date"])]
    g["prev_doc"] = [
        f"{n} от {d:%d.%m.%Y}" if pd.notna(p) else ""
        for n, d, p in zip(g["prev_number"], g["prev_date"], g["prev_price"])
    ]
    g["stock"] = g["fullname"].map(lambda n: stock.get(normalize_key(n)))
    return g


def last_changes(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Товары, у которых последний приход дороже / дешевле предыдущего."""
    if history.empty:
        return history, history
    last = history[history["is_last"] & history["prev_price"].notna()]
    up = last[last["delta_pct"] >= MIN_CHANGE].sort_values("extra_cost", ascending=False)
    down = last[last["delta_pct"] <= -MIN_CHANGE].sort_values("extra_cost")
    return up.reset_index(drop=True), down.reset_index(drop=True)


def price_messages() -> list[str]:
    """Строки для вывода после загрузки приходов."""
    try:
        history = load_price_history()
    except Exception as exc:
        return [f"Сверка закупочных цен не выполнена: {exc}"]
    if history.empty:
        return []
    up, _ = last_changes(history)
    if up.empty:
        return ["Закупочные цены: в последних приходах роста цены нет"]

    last_date = history["receipt_date"].max()
    recent = up[up["receipt_date"].map(lambda d: (last_date - d).days <= RECENT_DAYS)]
    extra = f"{up['extra_cost'].sum():,.0f}".replace(",", " ")
    suspect = int((up["note"] != "").sum())
    out = [
        f"ВНИМАНИЕ. Последний приход дороже предыдущего: {len(up)} поз., разница на последних партиях "
        f"{extra} ₽. Из них пришло за последние {RECENT_DAYS} дн.: {len(recent)} поз."
        + (f" Рост больше чем вдвое (возможна ошибка в документе): {suspect} поз." if suspect else "")
        + " Подробности — в файле «Изменение закупочных цен»"
    ]
    top = (recent if not recent.empty else up).head(MAX_NAMES)
    def money(v):
        return f"{v:,.0f}".replace(",", " ")

    names = [
        f"{r.fullname} — {money(r.prev_price)} → {money(r.price)} ₽ (+{r.delta_pct:.0%}), {r.doc}"
        for r in top.itertuples()
    ]
    out.append("Рост цены: " + " | ".join(names).replace(";", ","))
    return out


def build_price_excel_bytes() -> bytes:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.utils.dataframe import dataframe_to_rows

    from sales.reports.xl_brand import (
        FMT_DATE, FMT_MONEY, FMT_QTY, FMT_SHARE, build_toc, finalize, set_number_format, style_table_sheet,
    )

    history = load_price_history()
    up, down = last_changes(history)

    wb = Workbook()
    wb.remove(wb.active)

    def changes_frame(df: pd.DataFrame) -> pd.DataFrame:
        cols = ["Номенклатура", "Характеристика", "Предыдущий приход", "Цена была, ₽", "Последний приход",
                "Цена стала, ₽", "Изменение, ₽", "Изменение, %", "Пришло, шт.", "Влияние на партию, ₽",
                "Остаток сейчас, шт.", "Примечание"]
        if df.empty:
            return pd.DataFrame(columns=cols)
        return pd.DataFrame({
            "Номенклатура": df["fullname"], "Характеристика": df["characteristic"],
            "Предыдущий приход": df["prev_doc"], "Цена была, ₽": df["prev_price"],
            "Последний приход": df["doc"], "Цена стала, ₽": df["price"],
            "Изменение, ₽": df["delta"], "Изменение, %": df["delta_pct"],
            "Пришло, шт.": df["qty"], "Влияние на партию, ₽": df["extra_cost"],
            "Остаток сейчас, шт.": df["stock"],
            "Примечание": df["note"],
        })

    def sheet(name, df, title, subtitle, widths, key, freeze=2):
        ws = wb.create_sheet(name)
        for row in dataframe_to_rows(df, index=False, header=True):
            ws.append(row)
        hdr = style_table_sheet(ws, title=title, subtitle=subtitle, freeze_col=freeze, key_headers=(key,),
                                wrap_headers=("Характеристика",))
        set_number_format(ws, hdr, ["Цена была, ₽", "Цена стала, ₽", "Изменение, ₽", "Влияние на партию, ₽",
                                    "Цена, ₽", "Сумма без НДС, ₽", "Изменение к пред., ₽"], FMT_MONEY)
        set_number_format(ws, hdr, ["Изменение, %", "Изменение к пред., %"], FMT_SHARE)
        set_number_format(ws, hdr, ["Пришло, шт.", "Остаток сейчас, шт."], FMT_QTY)
        set_number_format(ws, hdr, ["Дата прихода"], FMT_DATE)
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    widths = [46, 40, 26, 14, 26, 14, 14, 13, 12, 18, 16, 28]
    sheet("Цена выросла", changes_frame(up), "ПОСЛЕДНИЙ ПРИХОД ДОРОЖЕ ПРЕДЫДУЩЕГО",
          "Сравнение двух последних приходов одного товара (номенклатура + характеристика). "
          "Влияние на партию = изменение цены × количество в последнем приходе",
          widths, "Изменение, %")
    sheet("Цена снизилась", changes_frame(down), "ПОСЛЕДНИЙ ПРИХОД ДЕШЕВЛЕ ПРЕДЫДУЩЕГО",
          "Сравнение двух последних приходов одного товара (номенклатура + характеристика)",
          widths, "Изменение, %")

    if not history.empty:
        h = history.sort_values(["fullname", "characteristic", "receipt_date"])
        hist = pd.DataFrame({
            "Номенклатура": h["fullname"], "Характеристика": h["characteristic"],
            "Дата прихода": h["receipt_date"], "№ прихода": h["receipt_number"],
            "Пришло, шт.": h["qty"], "Цена, ₽": h["price"], "Сумма без НДС, ₽": h["amount"],
            "Изменение к пред., ₽": h["delta"], "Изменение к пред., %": h["delta_pct"],
        })
    else:
        hist = pd.DataFrame(columns=["Номенклатура", "Характеристика", "Дата прихода", "№ прихода",
                                     "Пришло, шт.", "Цена, ₽", "Сумма без НДС, ₽",
                                     "Изменение к пред., ₽", "Изменение к пред., %"])
    sheet("История цен", hist, "ИСТОРИЯ ЗАКУПОЧНЫХ ЦЕН",
          "Все приходы с ценой: по каждому товару от старого к новому, с изменением к предыдущему приходу",
          [46, 40, 14, 16, 12, 14, 16, 18, 18], "Цена, ₽")

    compared = int((history["is_last"] & history["prev_price"].notna()).sum()) if not history.empty else 0
    build_toc(
        wb,
        title="Изменение закупочных цен",
        subtitle="Сравнение цен последнего и предыдущего прихода по каждому товару",
        params="Цена = сумма без НДС / количество · без доставки, ГТД и прочих допрасходов · "
               "изменения меньше 1% не учитываются",
        sheets=[
            ("Цена выросла", "Товары, у которых последний приход дороже предыдущего"),
            ("Цена снизилась", "Товары, у которых последний приход дешевле предыдущего"),
            ("История цен", "Все приходы с ценой и изменением к предыдущему"),
        ],
        cards=[
            ("ЦЕНА ВЫРОСЛА, ПОЗ.", len(up), FMT_QTY, f"из {compared} с двумя и более приходами"),
            ("РОСТ СТОИМОСТИ, ₽", float(up["extra_cost"].sum()) if not up.empty else 0, FMT_MONEY,
             "на последних партиях"),
            ("ЦЕНА СНИЗИЛАСЬ, ПОЗ.", len(down), FMT_QTY, "последний приход дешевле"),
            ("ЭКОНОМИЯ, ₽", float(-down["extra_cost"].sum()) if not down.empty else 0, FMT_MONEY,
             "на последних партиях"),
        ],
    )
    finalize(wb, ["Оглавление", "Цена выросла", "Цена снизилась", "История цен"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
