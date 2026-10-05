# corporate/reports/receipts_xlsx.py
"""Выгрузка приходов из админки в Excel."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

from sales.reports.xl_brand import (
    FMT_DATE, FMT_MONEY, FMT_QTY, build_toc, finalize, set_number_format, style_table_sheet,
)

MONEY_COLS = ["Цена без НДС, ₽", "Сумма без НДС, ₽"]
QTY_COLS = ["Кол-во, шт.", "Строк", "Документов", "Позиций"]


def build_receipts_excel_bytes(queryset) -> bytes:
    rows = list(queryset.values_list(
        "receipt_date", "receipt_number", "warehouse", "fullname", "characteristic", "barcode",
        "qty", "price_purchase", "amount_purchase", "item_id",
    ))
    df = pd.DataFrame(rows, columns=["date", "number", "warehouse", "fullname", "characteristic", "barcode",
                                     "qty", "price", "amount", "item_id"])
    for c in ("qty", "price", "amount"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values(["date", "number", "fullname"], ascending=[False, False, True])

    wb = Workbook()
    wb.remove(wb.active)

    def sheet(name, frame, title, subtitle, widths, key, freeze=2):
        ws = wb.create_sheet(name)
        for row in dataframe_to_rows(frame, index=False, header=True):
            ws.append(row)
        hdr = style_table_sheet(ws, title=title, subtitle=subtitle, freeze_col=freeze, key_headers=(key,),
                                wrap_headers=("Характеристика",))
        set_number_format(ws, hdr, MONEY_COLS, FMT_MONEY)
        set_number_format(ws, hdr, QTY_COLS, FMT_QTY)
        set_number_format(ws, hdr, ["Дата прихода"], FMT_DATE)
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    detail = pd.DataFrame({
        "Дата прихода": df["date"], "№ прихода": df["number"], "Склад": df["warehouse"],
        "Номенклатура": df["fullname"], "Характеристика": df["characteristic"], "Штрихкод": df["barcode"],
        "Кол-во, шт.": df["qty"], "Цена без НДС, ₽": df["price"], "Сумма без НДС, ₽": df["amount"],
        "Был в продажах или остатках": df["item_id"].notna().map({True: "да", False: "нет, только приход"}),
    })
    sheet("Приходы", detail, "ПРИХОДЫ ТОВАРОВ", f"{len(df)} строк · от новых к старым",
          [14, 16, 24, 46, 40, 16, 12, 15, 17, 22], "Кол-во, шт.", freeze=5)

    docs = (df.groupby(["date", "number", "warehouse"], dropna=False)
            .agg(rows=("fullname", "count"), items=("fullname", "nunique"), qty=("qty", "sum"),
                 amount=("amount", lambda s: s.sum(min_count=1)))
            .reset_index().sort_values(["date", "number"], ascending=[False, False]))
    docs = docs.rename(columns={"date": "Дата прихода", "number": "№ прихода", "warehouse": "Склад",
                                "rows": "Строк", "items": "Позиций", "qty": "Кол-во, шт.",
                                "amount": "Сумма без НДС, ₽"})
    sheet("По документам", docs, "ПРИХОДЫ ПО ДОКУМЕНТАМ", "Один документ на склад — одна строка",
          [14, 16, 28, 10, 10, 14, 18], "Сумма без НДС, ₽", freeze=3)

    m = df.dropna(subset=["date"]).copy()
    m["month"] = pd.to_datetime(m["date"]).dt.strftime("%Y-%m")
    months = (m.groupby("month")
              .agg(docs=("number", "nunique"), rows=("fullname", "count"), qty=("qty", "sum"),
                   amount=("amount", lambda s: s.sum(min_count=1)))
              .reset_index().sort_values("month", ascending=False))
    months = months.rename(columns={"month": "Месяц", "docs": "Документов", "rows": "Строк",
                                    "qty": "Кол-во, шт.", "amount": "Сумма без НДС, ₽"})
    sheet("По месяцам", months, "ПРИХОДЫ ПО МЕСЯЦАМ", "Документы, количество и сумма закупки по месяцам",
          [12, 13, 10, 14, 18], "Сумма без НДС, ₽")

    d_min, d_max = df["date"].min(), df["date"].max()
    period = f"{d_min:%d.%m.%Y} – {d_max:%d.%m.%Y}" if pd.notna(d_min) else "нет дат"
    build_toc(
        wb,
        title="Приходы товаров",
        subtitle="Документы прихода из 1С · количество и закупочная цена без НДС",
        params=f"Период: {period} · выгружено {datetime.now():%d.%m.%Y %H:%M}",
        sheets=[
            ("Приходы", "Все строки приходов: товар, характеристика, количество, цена"),
            ("По документам", "Свод по каждому документу прихода"),
            ("По месяцам", "Свод по месяцам"),
        ],
        cards=[
            ("ДОКУМЕНТОВ", int(len(docs)), FMT_QTY, period),
            ("СТРОК", int(len(df)), FMT_QTY, "товар × характеристика"),
            ("ПРИШЛО, ШТ.", float(df["qty"].sum()), FMT_QTY, "за период"),
            ("СУММА БЕЗ НДС, ₽", float(df["amount"].sum()), FMT_MONEY, "прямая закупочная стоимость"),
        ],
    )
    finalize(wb, ["Оглавление", "Приходы", "По документам", "По месяцам"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
