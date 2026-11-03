# sales/reports/meeting_brief/orders_story.py
"""Лист «Выводы»: заказы периода связным текстом."""
from __future__ import annotations

import pandas as pd

from . import config as C
from . import fmt as F
from .metrics import _in_range, _txt, orders_by_store
from .periods import Periods

TOL = C.MONEY_TOL


def _share(part: float, total: float) -> str:
    return F.pct(part / total * 100) if total else "—"


def _cancelled(src: dict, p: Periods) -> pd.DataFrame:
    df = _in_range(src["orders"], p.start, p.end, "date_from")
    df = df[df["cancelled"]].copy()
    df["store_name"] = df["store"].map(lambda v: _txt(v, "Без подразделения"))
    return df


def _parts(g: pd.DataFrame) -> list[str]:
    """Хвост фразы о проблемных заказах группы."""
    out = []
    none = g[g["pay_state"] == "none"]
    if len(none):
        out.append(f"без оплаты {F.orders_word(len(none))} на {F.money_short(none['amount_active'].sum())}")
    void = g[g["pay_state"] == "void"]
    if len(void):
        out.append(f"закрыто без оплаты и отгрузки — {len(void)}")
    ex = g[g["is_excluded"]]
    if len(ex):
        out.append(f"исключений (не долг) — {len(ex)}")
    return out


def build_story(created: pd.DataFrame, src: dict, p: Periods) -> list[tuple[str, str]]:
    """Список абзацев (стиль, текст). Стили: h1, sub, h2, p, li, note."""
    S: list[tuple[str, str]] = []
    n = len(created)
    amount = float(created["amount_active"].sum())
    paid = float(created["paid_clip"].sum())
    shipped = float(created["total_shiped_amount"].sum())
    canc = _cancelled(src, p)
    st = created["pay_state"]

    def bucket(key):
        part = created[st == key]
        return len(part), float(part["amount_active"].sum())

    full, part, none, void = bucket("full"), bucket("partial"), bucket("none"), bucket("void")
    ex = created[created["is_excluded"]]
    debt = (created["total_shiped_amount"] - created["cash_pmts"]).clip(lower=0).where(~created["is_excluded"], 0.0)
    debt_n = int((debt > TOL).sum())

    S.append(("h1", f"Заказы, созданные {p.label}"))
    S.append(("sub", f"Оплата и отгрузка — на {p.end:%d.%m.%Y}. Отменённые заказы и заказы с нулевой суммой "
                     "в расчёт не входят."))

    # Коротко
    S.append(("h2", "Коротко"))
    S.append(("p", f"За период создано {F.orders_word(n)} на {F.money_short(amount)}, "
                   f"средний чек {F.money_short(amount / n if n else 0)}."
                   + (f" Ещё {F.orders_word(len(canc))} на {F.money_short(canc['order_amount'].sum())} "
                      "отменены." if len(canc) else "")))
    S.append(("p", f"Клиенты оплатили {F.money_short(paid)} — {_share(paid, amount)} суммы заказов. "
                   f"Отгружено {F.money_short(shipped)} — {_share(shipped, amount)}."))
    S.append(("li", f"Оплачены полностью: {F.orders_word(full[0])} на {F.money_short(full[1])}"))
    S.append(("li", f"Оплачены частично: {F.orders_word(part[0])} на {F.money_short(part[1])}"))
    S.append(("li", f"Без оплаты: {F.orders_word(none[0])} на {F.money_short(none[1])}"
                    + (f" ({_share(none[1], amount)} суммы)" if none[0] else "")))
    if len(ex):
        S.append(("li", f"Исключения из админки (комиссионер, бартер и др.): {F.orders_word(len(ex))} "
                        f"на {F.money_short(ex['amount_active'].sum())} — долгом не считаются"))
    if void[0]:
        S.append(("li", f"Закрыты без оплаты и отгрузки: {F.orders_word(void[0])} на {F.money_short(void[1])} — "
                        "по сути не исполнены, нужно проверить"))

    # Подразделения
    stores = orders_by_store(created)
    if stores:
        S.append(("h2", "По подразделениям"))
        top = stores[0]
        best = max(stores, key=lambda r: r["paid_share"] or 0)
        worst = min(stores, key=lambda r: r["paid_share"] or 0)
        S.append(("p", f"Больше всего заказов на сумму — «{top['store']}»: {F.money_short(top['amount'])}, "
                       f"{_share(top['amount'], amount)} всех заказов периода."
                       + (f" Лучше всех оплачены заказы «{best['store']}» ({F.pct(best['paid_share'])}), "
                          f"хуже всех — «{worst['store']}» ({F.pct(worst['paid_share'])})."
                          if len(stores) > 1 and best is not worst else "")))
        canc_by = canc.groupby("store_name").size().to_dict() if len(canc) else {}
        for r in stores:
            g = created[created["store_name"] == r["store"]]
            tail = _parts(g)
            if canc_by.get(r["store"]):
                tail.append(f"отменено ещё {canc_by[r['store']]}")
            S.append(("li", f"{r['store']} — {F.orders_word(r['count'])} на {F.money_short(r['amount'])}, "
                            f"средний чек {F.money_short(r['avg'])}, оплачено {F.pct(r['paid_share'])}"
                            + (f"; {', '.join(tail)}" if tail else "")))

    # Менеджеры
    if n:
        S.append(("h2", "По менеджерам"))
        rows = []
        for name, g in created.groupby("manager_name"):
            a = float(g["amount_active"].sum())
            rows.append((a, name, g))
        rows.sort(key=lambda x: -x[0])
        a0, name0, g0 = rows[0]
        S.append(("p", f"Больше всех заказов на сумму оформил(а) {name0}: {F.orders_word(len(g0))} "
                       f"на {F.money_short(a0)} ({_share(a0, amount)} всех)."))
        for a, name, g in rows:
            pd_ = float(g["paid_clip"].sum())
            tail = _parts(g)
            S.append(("li", f"{name} — {F.orders_word(len(g))} на {F.money_short(a)}, оплачено {_share(pd_, a)}"
                            + (f"; {', '.join(tail)}" if tail else "")))

    # Что сделать
    todo = []
    if none[0]:
        todo.append(f"Взять предоплату: {F.orders_word(none[0])} на {F.money_short(none[1])}. "
                    f"На листе «Заказы» — фильтр «Оплата на {p.end:%d.%m}» = «Без оплаты».")
    if void[0]:
        todo.append(f"Проверить закрытые без оплаты и отгрузки: {F.orders_word(void[0])} на {F.money_short(void[1])}. "
                    "Перевести в «Отменен» или указать, в какой заказ или чек ушла продажа. "
                    f"Фильтр «Оплата на {p.end:%d.%m}» = «Закрыт без исполнения».")
    if debt_n:
        todo.append(f"Получить оплату за отгруженное: {F.orders_word(debt_n)} на {F.money_short(debt.sum())}. "
                    "Фильтр по колонке «Отгружено, не оплачено».")
    if todo:
        S.append(("h2", "Что сделать"))
        S.extend(("li", t) for t in todo)
    S.append(("note", "Если заказ на самом деле не долг (бартер, свои клиенты, ошибка в 1С), его добавляют в "
                      "админке: Заказы → Исключения из долгов. Тогда он перестаёт считаться долгом и "
                      "«без оплаты» во всех отчётах."))
    return S


def write_story(wb, story: list[tuple[str, str]], sheet: str = "Выводы") -> None:
    from openpyxl.styles import Alignment

    from sales.reports.xl_brand import MUTED, NAVY, TEXT, TEXT_2, font, page_setup, toc_button

    ws = wb.create_sheet(sheet)
    page_setup(ws, landscape=False)
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 110
    toc_button(ws, 1, 2)
    styles = {
        "h1": (font(16, True, NAVY), 26, 0),
        "sub": (font(10, color=MUTED, italic=True), 16, 0),
        "h2": (font(12, True, NAVY), 22, 0),
        "p": (font(10.5, color=TEXT), 16, 0),
        "li": (font(10.5, color=TEXT_2), 16, 1),
        "note": (font(9.5, color=MUTED, italic=True), 15, 0),
    }
    r = 2
    for kind, text in story:
        if kind in ("h1", "h2"):
            r += 1
        f, line_h, indent = styles[kind]
        value = f"•  {text}" if kind == "li" else text
        c = ws.cell(row=r, column=2, value=value)
        c.font = f
        c.alignment = Alignment(wrap_text=True, vertical="top", indent=indent)
        lines = max(1, -(-len(value) // 95))
        ws.row_dimensions[r].height = line_h * lines + 2
        r += 1
