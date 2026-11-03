# sales/reports/meeting_brief/orders_xlsx.py
"""Excel: заказы, созданные за период, в разрезе подразделений."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd

from .metrics import PAY_STATE_TITLE, created_orders, orders_by_store
from .periods import Periods


def _month_key(d) -> str:
    return f"{d:%Y-%m}" if d is not None and d == d else ""


def build_orders_excel(src: dict, p: Periods) -> bytes:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.utils.dataframe import dataframe_to_rows

    from sales.reports.xl_brand import (
        FMT_DATE, FMT_MONEY, FMT_QTY, FMT_SHARE, build_toc, finalize, set_number_format, style_table_sheet,
    )

    created = created_orders(src, p.start, p.end)
    stores = orders_by_store(created)
    stamp = f"оплата и отгрузка — на {datetime.now():%d.%m.%Y}"

    wb = Workbook()
    wb.remove(wb.active)

    def write(ws, df):
        for row in dataframe_to_rows(df, index=False, header=True):
            ws.append([None if (isinstance(v, float) and v != v) else v for v in row])

    def widths(ws, values):
        for i, w in enumerate(values, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # По подразделениям
    sm = pd.DataFrame([{
        "Подразделение": r["store"],
        "Заказов": r["count"],
        "Сумма заказов, ₽": r["amount"],
        "Средний чек, ₽": r["avg"],
        "Оплачено, ₽": r["paid"],
        "Оплачено, %": (r["paid_share"] or 0) / 100,
        "Оплачены полностью": r["full"],
        "Оплачены частично": r["partial"],
        "Без оплаты": r["none"],
        "Без оплаты, ₽": r["none_amount"],
        "Комиссионер": r["ext"],
        "Отгружено, ₽": r["shipped"],
    } for r in stores], columns=["Подразделение", "Заказов", "Сумма заказов, ₽", "Средний чек, ₽",
                                 "Оплачено, ₽", "Оплачено, %", "Оплачены полностью", "Оплачены частично",
                                 "Без оплаты", "Без оплаты, ₽", "Комиссионер", "Отгружено, ₽"])
    if not sm.empty:
        tot = sm.sum(numeric_only=True)
        tot["Подразделение"] = "Итого"
        tot["Средний чек, ₽"] = tot["Сумма заказов, ₽"] / tot["Заказов"] if tot["Заказов"] else 0
        tot["Оплачено, %"] = tot["Оплачено, ₽"] / tot["Сумма заказов, ₽"] if tot["Сумма заказов, ₽"] else 0
        sm = pd.concat([sm, pd.DataFrame([tot])], ignore_index=True)
    money = ["Сумма заказов, ₽", "Средний чек, ₽", "Оплачено, ₽", "Без оплаты, ₽", "Отгружено, ₽"]
    qty = ["Заказов", "Оплачены полностью", "Оплачены частично", "Без оплаты", "Комиссионер"]

    ws = wb.create_sheet("По подразделениям")
    write(ws, sm)
    hdr = style_table_sheet(ws, title="ЗАКАЗЫ ПО ПОДРАЗДЕЛЕНИЯМ",
                            subtitle=f"Созданы за {p.label} (без отменённых); {stamp}",
                            freeze_col=2, key_headers=("Сумма заказов, ₽",),
                            wrap_headers=[c for c in sm.columns if c != "Подразделение"])
    set_number_format(ws, hdr, money, FMT_MONEY)
    set_number_format(ws, hdr, qty, FMT_QTY)
    set_number_format(ws, hdr, ["Оплачено, %"], FMT_SHARE)
    widths(ws, [28] + [14] * (len(sm.columns) - 1))
    sheets = [("По подразделениям", "Сколько заказов создано и оплачено в каждом подразделении")]

    # По месяцам, если период длиннее месяца
    months = created["date_from"].map(_month_key)
    if months.nunique() > 1:
        g = created.assign(month=months).groupby(["store_name", "month"])
        mm = g.agg(count=("amount_active", "size"), amount=("amount_active", "sum"),
                   paid=("paid_clip", "sum")).reset_index()
        mm["share"] = (mm["paid"] / mm["amount"]).where(mm["amount"] > 0, 0)
        mm = mm.sort_values(["store_name", "month"]).rename(columns={
            "store_name": "Подразделение", "month": "Месяц", "count": "Заказов",
            "amount": "Сумма заказов, ₽", "paid": "Оплачено, ₽", "share": "Оплачено, %"})
        ws = wb.create_sheet("По месяцам")
        write(ws, mm)
        hdr = style_table_sheet(ws, title="ЗАКАЗЫ ПО ПОДРАЗДЕЛЕНИЯМ И МЕСЯЦАМ",
                                subtitle=f"Месяц — по дате создания заказа; {stamp}", freeze_col=3)
        set_number_format(ws, hdr, ["Сумма заказов, ₽", "Оплачено, ₽"], FMT_MONEY)
        set_number_format(ws, hdr, ["Заказов"], FMT_QTY)
        set_number_format(ws, hdr, ["Оплачено, %"], FMT_SHARE)
        widths(ws, [28, 10, 11, 16, 16, 12])
        sheets.append(("По месяцам", "То же по каждому месяцу периода"))

    # Список заказов
    cols = {"store_name": "Подразделение", "number": "Заказ", "date_from": "Дата создания",
            "manager_name": "Менеджер", "client": "Клиент", "status": "Статус",
            "pay_title": "Оплата", "amount_active": "Сумма заказа, ₽", "paid": "Оплачено, ₽",
            "left": "Осталось оплатить, ₽", "total_shiped_amount": "Отгружено, ₽", "order_id": "GUID заказа"}
    lst = created.assign(
        pay_title=created["pay_state"].map(PAY_STATE_TITLE),
        paid=created["cash_pmts"],
        left=(created["amount_active"] - created["paid_clip"]).clip(lower=0),
    ).sort_values(["store_name", "date_from", "number"])
    ws = wb.create_sheet("Заказы")
    write(ws, lst[list(cols)].rename(columns=cols))
    hdr = style_table_sheet(ws, title="ЗАКАЗЫ ЗА ПЕРИОД",
                            subtitle=f"{len(lst)} заказов за {p.label}; {stamp}. Фильтр — по подразделению "
                                     "или статусу оплаты", freeze_col=3, key_headers=("Оплата",),
                            wrap_headers=("Осталось оплатить, ₽",))
    set_number_format(ws, hdr, ["Сумма заказа, ₽", "Оплачено, ₽", "Осталось оплатить, ₽", "Отгружено, ₽"],
                      FMT_MONEY)
    set_number_format(ws, hdr, ["Дата создания"], FMT_DATE)
    widths(ws, [24, 16, 13, 22, 30, 22, 22, 15, 14, 14, 14, 40])
    sheets.append(("Заказы", "Все заказы периода: подразделение, менеджер, оплата, GUID"))

    amount = float(created["amount_active"].sum())
    paid = float(created["paid_clip"].sum())
    build_toc(
        wb,
        title="Заказы по подразделениям",
        subtitle=f"За {p.label}",
        params="Заказы по дате создания, без отменённых и нулевых. Оплата — по кассе на сегодня, "
               "без дизайнерского вознаграждения. «Комиссионер» — клиенты, которые платят по отчёту.",
        sheets=sheets,
        cards=[
            ("ЗАКАЗОВ", int(len(created)), FMT_QTY, f"в {len(stores)} подразделениях"),
            ("СУММА, ₽", amount, FMT_MONEY, "созданных заказов"),
            ("ОПЛАЧЕНО, ₽", paid, FMT_MONEY, f"{paid / amount * 100:.0f}% суммы" if amount else ""),
            ("БЕЗ ОПЛАТЫ", int((created["pay_state"] == "none").sum()), FMT_QTY, "заказов"),
        ],
    )
    finalize(wb, ["Оглавление", *[s for s, _ in sheets]])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
