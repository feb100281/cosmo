# sales/reports/meeting_brief/tasks.py
"""Задачи менеджерам по заказам и Excel с листом на каждого менеджера."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd

from . import config as C
from .periods import Periods

TOL = C.MONEY_TOL

ACTIONS = [
    ("close", "Закрыть заказ в 1С", "отгружен и оплачен полностью, а статус не «Закрыт»"),
    ("collect", "Получить оплату", "отгружено больше, чем оплачено"),
    ("void", "Проверить закрытый заказ",
     "создан за выбранный период, статус «Закрыт», но ни оплаты, ни отгрузки — отменить или указать, "
     "куда ушла продажа"),
    ("prepay", "Взять предоплату", "создан за выбранный период, ни одной оплаты (кроме исключений)"),
    ("reserve", "Отгрузить или снять резерв", f"в резерве дольше {C.RESERVE_STUCK_DAYS} дн., ничего не отгружено"),
    ("approval", "Согласовать или отменить", f"на согласовании дольше {C.APPROVAL_STUCK_DAYS} дн."),
]
ACTION_TITLE = {k: t for k, t, _ in ACTIONS}
ACTION_ORDER = {k: i for i, (k, _, _) in enumerate(ACTIONS)}


def _txt(v, default="") -> str:
    if v is None or (isinstance(v, float) and v != v):
        return default
    return str(v).strip() or default


COLUMNS = ["action", "manager", "number", "date_from", "client", "store", "status",
           "amount", "shipped", "paid", "debt", "days", "guid", "excluded"]


def build_tasks(orders: pd.DataFrame, managers: dict, p: Periods, exclusions: dict | None = None,
                only_excluded: bool = False) -> pd.DataFrame:
    """Одна строка — один заказ с одним действием (по приоритету из ACTIONS).
    only_excluded=True — долги по отгрузке, которые исключены из расчёта (бартер и т.п.)."""
    from .metrics import exclusion_reason

    o = orders[~orders["cancelled"] & (orders["amount_active"] > TOL)].copy()
    if o.empty:
        return pd.DataFrame(columns=COLUMNS)
    o["excluded"] = exclusion_reason(o, exclusions)
    is_ex = o["excluded"] != ""
    ref = p.end
    has_date = o["date_from"].map(lambda d: d is not None and d == d)
    open_ = o["status"] != C.ST_CLOSED
    debt = (o["total_shiped_amount"] - o["cash_pmts"]).clip(lower=0)
    dates = o["date_from"].where(has_date)

    def since(days):
        return has_date & dates.map(lambda d: d is not None and d == d and d <= ref - timedelta(days=days))

    rules = {
        "close": open_ & ((o["total_shiped_amount"] - o["amount_active"]).abs() <= TOL)
                 & (o["cash_pmts"] >= o["amount_active"] - TOL),
        "collect": (debt > TOL) & has_date & dates.map(
            lambda d: d is not None and d == d and d >= ref - timedelta(days=365)),
        "prepay": has_date & dates.map(lambda d: d is not None and d == d and p.start <= d <= p.end)
                  & (o["cash_pmts"] <= TOL),
        "void": has_date & dates.map(lambda d: d is not None and d == d and p.start <= d <= p.end)
                & (o["status"] == C.ST_CLOSED) & (o["cash_pmts"].abs() <= TOL)
                & (o["total_shiped_amount"].abs() <= TOL) & ~is_ex,
        "reserve": open_ & (o["status"] == C.ST_RESERVE) & (o["total_shiped_amount"] <= TOL)
                   & since(C.RESERVE_STUCK_DAYS),
        "approval": open_ & (o["status"] == C.ST_APPROVAL) & since(C.APPROVAL_STUCK_DAYS),
    }
    commission = (exclusions or {}).get("commission", set())
    ext = o["client"].map(lambda c: " ".join(_txt(c).split()).casefold() in commission)
    rules["prepay"] = rules["prepay"] & ~ext & ~is_ex
    if only_excluded:
        rules = {"collect": rules["collect"] & is_ex}
    else:
        rules["collect"] = rules["collect"] & ~is_ex
    o["action"] = None
    for key, _, _ in reversed(ACTIONS):
        if key in rules:
            o.loc[rules[key].fillna(False).astype(bool), "action"] = key
    o = o[o["action"].notna()].copy()

    o["manager"] = o["manager"].map(lambda m: managers.get(_txt(m), _txt(m)) or "Без менеджера")
    o["debt"] = debt.loc[o.index]
    o["days"] = o["date_from"].map(lambda d: (ref - d).days if d is not None and d == d else None)
    out = pd.DataFrame({
        "action": o["action"], "manager": o["manager"], "number": o["number"].map(_txt),
        "date_from": o["date_from"], "client": o["client"].map(_txt), "store": o["store"].map(_txt),
        "status": o["status"].map(_txt), "amount": o["amount_active"], "shipped": o["total_shiped_amount"],
        "paid": o["cash_pmts"], "debt": o["debt"], "days": o["days"],
        "guid": o["order_id"].map(_txt), "excluded": o["excluded"],
    })
    out["_ord"] = out["action"].map(ACTION_ORDER)
    out = out.sort_values(["manager", "_ord", "debt", "amount"], ascending=[True, True, False, False])
    return out.drop(columns="_ord").reset_index(drop=True)


def summary(tasks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, g in tasks.groupby("manager"):
        r = {"Менеджер": name}
        for key, title, _ in ACTIONS:
            part = g[g["action"] == key]
            r[f"{title}, шт."] = len(part)
            r[f"{title}, ₽"] = float((part["debt"] if key == "collect" else part["amount"]).sum())
        r["Всего задач"] = len(g)
        rows.append(r)
    df = pd.DataFrame(rows)
    return df.sort_values("Всего задач", ascending=False) if not df.empty else df


def _sheet_name(name: str, used: set) -> str:
    base = re.sub(r"[\[\]\*\?/\\:]", " ", name).strip()[:28] or "Менеджер"
    candidate, i = base, 2
    while candidate.lower() in used:
        candidate = f"{base[:25]} {i}"
        i += 1
    used.add(candidate.lower())
    return candidate


def build_tasks_excel(tasks: pd.DataFrame, p: Periods, excluded: pd.DataFrame | None = None) -> bytes:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.utils.dataframe import dataframe_to_rows

    from sales.reports.xl_brand import (
        FMT_DATE, FMT_MONEY, FMT_QTY, build_toc, finalize, set_number_format, style_table_sheet,
    )

    wb = Workbook()
    wb.remove(wb.active)

    def write(ws, df):
        for row in dataframe_to_rows(df, index=False, header=True):
            ws.append([None if (isinstance(v, float) and v != v) else v for v in row])

    def widths(ws, values):
        for i, w in enumerate(values, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # Сводка
    sm = summary(tasks)
    ws = wb.create_sheet("Сводка")
    write(ws, sm if not sm.empty else pd.DataFrame(columns=["Менеджер", "Всего задач"]))
    hdr = style_table_sheet(ws, title="ЗАДАЧИ МЕНЕДЖЕРОВ ПО ЗАКАЗАМ",
                            subtitle=f"Состояние на {datetime.now():%d.%m.%Y}; новые заказы — за {p.label}",
                            freeze_col=2, key_headers=("Всего задач",),
                            wrap_headers=[c for c in sm.columns if c != "Менеджер"])
    set_number_format(ws, hdr, [c for c in sm.columns if c.endswith("₽")], FMT_MONEY)
    set_number_format(ws, hdr, [c for c in sm.columns if c.endswith("шт.")] + ["Всего задач"], FMT_QTY)
    widths(ws, [26] + [14] * (len(sm.columns) - 1))

    # Лист на менеджера
    cols = {
        "action": "Что сделать", "number": "Заказ", "date_from": "Дата создания", "client": "Клиент",
        "store": "Магазин", "status": "Статус", "amount": "Сумма заказа, ₽", "shipped": "Отгружено, ₽",
        "paid": "Оплачено, ₽", "debt": "Не оплачено отгруженное, ₽", "days": "Дней с создания",
        "guid": "GUID заказа",
    }
    hint = ("Если по заказу на самом деле нет долга (бартер, зачёт, ошибка в 1С) — "
            "пришлите GUID заказа и причину, его исключат из долгов")
    used = {"сводка", "оглавление"}
    sheets = []
    for name, g in tasks.groupby("manager", sort=False):
        sheet = _sheet_name(name, used)
        df = g.drop(columns=["manager", "excluded"]).rename(columns=cols)
        df["Что сделать"] = g["action"].map(ACTION_TITLE).values
        ws = wb.create_sheet(sheet)
        write(ws, df[list(cols.values())])
        counts = ", ".join(f"{ACTION_TITLE[k]} — {int((g['action'] == k).sum())}"
                           for k, _, _ in ACTIONS if (g["action"] == k).any())
        hdr = style_table_sheet(ws, title=name.upper(), subtitle=f"{len(g)} заказов: {counts}. {hint}",
                                freeze_col=3, key_headers=("Что сделать",),
                                wrap_headers=("Клиент", "Не оплачено отгруженное, ₽"))
        set_number_format(ws, hdr, ["Сумма заказа, ₽", "Отгружено, ₽", "Оплачено, ₽",
                                    "Не оплачено отгруженное, ₽"], FMT_MONEY)
        set_number_format(ws, hdr, ["Дней с создания"], FMT_QTY)
        set_number_format(ws, hdr, ["Дата создания"], FMT_DATE)
        widths(ws, [26, 16, 13, 30, 22, 22, 15, 14, 14, 16, 11, 40])
        sheets.append(sheet)

    # Исключённые из долгов
    ex_sheet = []
    if excluded is not None and not excluded.empty:
        ex_cols = {"reason": "Почему не долг", "manager": "Менеджер", "number": "Заказ", "date_from": "Дата создания",
                   "client": "Клиент", "shipped": "Отгружено, ₽", "paid": "Оплачено, ₽",
                   "debt": "Не оплачено отгруженное, ₽", "guid": "GUID заказа"}
        df = excluded.rename(columns={"excluded": "reason"})[list(ex_cols)].rename(columns=ex_cols)
        ws = wb.create_sheet("Не считаются долгом")
        write(ws, df)
        hdr = style_table_sheet(ws, title="НЕ СЧИТАЮТСЯ ДОЛГОМ",
                                subtitle=f"{len(df)} заказов на {excluded['debt'].sum():,.0f} ₽ — исключены "
                                         "в админке (Исключения из долгов)".replace(",", " "),
                                freeze_col=3, key_headers=("Почему не долг",))
        set_number_format(ws, hdr, ["Отгружено, ₽", "Оплачено, ₽", "Не оплачено отгруженное, ₽"], FMT_MONEY)
        set_number_format(ws, hdr, ["Дата создания"], FMT_DATE)
        widths(ws, [30, 22, 16, 13, 30, 14, 14, 16, 40])
        ex_sheet = ["Не считаются долгом"]

    def total(key, col="amount"):
        part = tasks[tasks["action"] == key]
        return len(part), float(part[col].sum())

    n_close, s_close = total("close")
    n_debt, s_debt = total("collect", "debt")
    n_pre, s_pre = total("prepay")
    rules = " · ".join(f"{t}: {d}" for _, t, d in ACTIONS)
    build_toc(
        wb,
        title="Задачи менеджеров по заказам",
        subtitle=f"К совещанию за {p.label}",
        params=rules,
        sheets=[("Сводка", "Сколько задач у каждого менеджера")] +
               [(s, "Заказы менеджера и что по ним сделать") for s in sheets] +
               [(s, "Долги, исключённые из расчёта: бартер, свои клиенты и т.п.") for s in ex_sheet],
        cards=[
            ("ЗАКРЫТЬ В 1С", n_close, FMT_QTY, f"заказов на {s_close:,.0f} ₽".replace(",", " ")),
            ("ПОЛУЧИТЬ ОПЛАТУ, ₽", s_debt, FMT_MONEY, f"по {n_debt} заказам"),
            ("ВЗЯТЬ ПРЕДОПЛАТУ", n_pre, FMT_QTY, f"заказов на {s_pre:,.0f} ₽".replace(",", " ")),
            ("МЕНЕДЖЕРОВ", int(tasks["manager"].nunique()), FMT_QTY, "с задачами"),
        ],
    )
    finalize(wb, ["Оглавление", "Сводка", *sheets, *ex_sheet])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
