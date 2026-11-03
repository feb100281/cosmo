# sales/reports/meeting_brief/orders_xlsx.py
"""Excel: заказы, созданные за период, в разрезе подразделений."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd

from .metrics import PAY_STATE_TITLE, created_orders, orders_by_store
from .orders_story import build_story, write_story
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
    stamp = f"оплата и отгрузка — на {p.end:%d.%m.%Y}"

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
        "Исключения (не долг)": r["ext"],
        "Закрыт без исполнения": r["void"],
        "Отгружено, ₽": r["shipped"],
        "Отгружено, не оплачено, ₽": r["shipped_unpaid"],
    } for r in stores], columns=["Подразделение", "Заказов", "Сумма заказов, ₽", "Средний чек, ₽",
                                 "Оплачено, ₽", "Оплачено, %", "Оплачены полностью", "Оплачены частично",
                                 "Без оплаты", "Без оплаты, ₽", "Исключения (не долг)", "Закрыт без исполнения", "Отгружено, ₽",
                                 "Отгружено, не оплачено, ₽"])
    if not sm.empty:
        tot = sm.sum(numeric_only=True)
        tot["Подразделение"] = "Итого"
        tot["Средний чек, ₽"] = tot["Сумма заказов, ₽"] / tot["Заказов"] if tot["Заказов"] else 0
        tot["Оплачено, %"] = tot["Оплачено, ₽"] / tot["Сумма заказов, ₽"] if tot["Сумма заказов, ₽"] else 0
        sm = pd.concat([sm, pd.DataFrame([tot])], ignore_index=True)
    money = ["Сумма заказов, ₽", "Средний чек, ₽", "Оплачено, ₽", "Без оплаты, ₽", "Отгружено, ₽", "Отгружено, не оплачено, ₽"]
    qty = ["Заказов", "Оплачены полностью", "Оплачены частично", "Без оплаты", "Исключения (не долг)",
           "Закрыт без исполнения"]

    ws = wb.create_sheet("По подразделениям")
    write(ws, sm)
    hdr = style_table_sheet(ws, title=f"ЗАКАЗЫ, СОЗДАННЫЕ {p.label.upper()}, ПО ПОДРАЗДЕЛЕНИЯМ",
                            subtitle=f"Без отменённых; {stamp}",
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
        hdr = style_table_sheet(ws, title=f"ЗАКАЗЫ, СОЗДАННЫЕ {p.label.upper()}, ПО МЕСЯЦАМ",
                                subtitle=f"Месяц — по дате создания заказа; {stamp}", freeze_col=3)
        set_number_format(ws, hdr, ["Сумма заказов, ₽", "Оплачено, ₽"], FMT_MONEY)
        set_number_format(ws, hdr, ["Заказов"], FMT_QTY)
        set_number_format(ws, hdr, ["Оплачено, %"], FMT_SHARE)
        widths(ws, [28, 10, 11, 16, 16, 12])
        sheets.append(("По месяцам", "То же по каждому месяцу периода"))

    # Список заказов
    cols = {"store_name": "Подразделение", "number": "Заказ", "date_from": "Дата создания",
            "manager_name": "Менеджер", "client": "Клиент", "status": "Статус",
            "pay_title": f"Оплата на {p.end:%d.%m}", "amount_active": "Сумма заказа, ₽",
            "paid": f"Оплачено на {p.end:%d.%m}, ₽",
            "left": "Не оплачено от суммы заказа, ₽", "total_shiped_amount": f"Отгружено на {p.end:%d.%m}, ₽",
            "ship_left": "Отгружено, не оплачено, ₽", "excluded": "Исключение (админка)",
            "order_id": "GUID заказа"}
    ex = created["is_excluded"] | (created["pay_state"] == "void")
    reason = created["excluded"].where(created["excluded"] != "", "Комиссионер")
    lst = created.assign(
        pay_title=created["pay_state"].map(PAY_STATE_TITLE).where(~created["is_excluded"], "Не долг"),
        paid=created["cash_pmts"],
        left=(created["amount_active"] - created["paid_clip"]).clip(lower=0).where(~ex, 0.0),
        ship_left=(created["total_shiped_amount"] - created["cash_pmts"]).clip(lower=0).where(~ex, 0.0),
        excluded=reason.where(created["is_excluded"], None),
    ).sort_values(["store_name", "date_from", "number"])
    ws = wb.create_sheet("Заказы")
    write(ws, lst[list(cols)].rename(columns=cols))
    hdr = style_table_sheet(ws, title=f"ЗАКАЗЫ, СОЗДАННЫЕ {p.label.upper()}",
                            subtitle=f"{len(lst)} заказов без отменённых; {stamp}. Фильтр — по подразделению "
                                     "или статусу оплаты", freeze_col=3, key_headers=(cols["pay_title"],),
                            wrap_headers=("Не оплачено от суммы заказа, ₽", "Отгружено, не оплачено, ₽"))
    set_number_format(ws, hdr, ["Сумма заказа, ₽", cols["paid"], "Не оплачено от суммы заказа, ₽",
                                cols["total_shiped_amount"], "Отгружено, не оплачено, ₽"], FMT_MONEY)
    set_number_format(ws, hdr, ["Дата создания"], FMT_DATE)
    widths(ws, [24, 16, 13, 22, 30, 22, 22, 15, 14, 16, 14, 16, 26, 40])
    sheets.append(("Заказы", "Все заказы периода: подразделение, менеджер, оплата, GUID"))

    write_story(wb, build_story(created, src, p))
    sheets.insert(0, ("Выводы", "Коротко и по-человечески: сколько создано, оплачено, что сделать"))

    amount = float(created["amount_active"].sum())
    paid = float(created["paid_clip"].sum())
    build_toc(
        wb,
        title="Заказы по подразделениям",
        subtitle=f"Созданы {p.label}",
        params=f"Заказы по дате создания, без отменённых и нулевых. Оплата и отгрузка — по {p.end:%d.%m.%Y}, "
               "без дизайнерского вознаграждения. Исключения (комиссионер, бартер и др.) — из админки, долгом не считаются. "
               "«Закрыт без исполнения» — статус «Закрыт», но ни оплаты, ни отгрузки на сегодня.",
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
