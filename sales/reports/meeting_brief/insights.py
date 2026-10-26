# sales/reports/meeting_brief/insights.py
"""Главное за период: достижения, проблемы и вопросы к совещанию (правила по метрикам)."""
from __future__ import annotations

from . import config as C
from . import fmt as F
from .periods import Periods


def _item(prio: float, title: str, text: str = "") -> dict:
    return {"prio": prio, "title": title, "text": text}


def _names(rows, key="name", value=None, limit=3, total=None) -> str:
    parts = []
    for r in rows[:limit]:
        parts.append(f"{r[key]} — {value(r)}" if value else str(r[key]))
    more = (total if total is not None else len(rows)) - min(limit, len(rows))
    return ", ".join(parts) + (f" и ещё {more}" if more > 0 else "")


def build_insights(m: dict, p: Periods) -> dict:
    cash, plan, orders, ctrl, sales, stock = (m["cash"], m["plan"], m["orders"], m["control"],
                                              m["sales"], m["stock"])
    good, bad, ask = [], [], []
    lim = C.CHANGE_ALERT_PCT
    pl = p.prev_label
    per = f"за {p.label}"

    # Деньги
    ch = cash["chg_prev"]
    money_txt = (f"Поступило {F.money_short(cash['cur']['cash_in'])} против "
                 f"{F.money_short(cash['prev']['cash_in'])} ({p.prev_range_label})")
    if ch is not None and ch >= lim:
        good.append(_item(9, f"Денег от клиентов {F.more_less(ch)} {pl}", money_txt))
    elif ch is not None and ch <= -lim:
        bad.append(_item(9, f"Денег от клиентов {F.more_less(ch)} {pl}", money_txt))

    # План месяца
    t = plan["total"]
    dp, dim = plan["days_passed"], plan["days_in_month"]
    month = p.month_label.split()[0].lower()
    if t["month_plan"] > 0:
        stores = [r for r in plan["rows"] if r["month_plan"] > 0]
        done = [r for r in stores if (r["month_exec"] or 0) >= 100]
        behind = [r for r in stores if r["month_fact"] < r["month_plan"] * dp / dim * 0.9]
        behind.sort(key=lambda r: r["month_fact"] / r["month_plan"])
        if done:
            good.append(_item(8, f"План на {month} уже выполнили: " +
                              _names(done, "store", lambda r: F.pct(r["month_exec"]), 3)))
        if behind:
            bad.append(_item(8.5, "Отстают от темпа плана месяца: " +
                             _names(behind, "store", lambda r: F.pct(r["month_exec"]), 3),
                             f"К {p.end:%d.%m} должно быть {F.pct(dp / dim * 100)} плана, "
                             f"по сети {F.pct(t['month_exec'])}"))
        fc = t["month_forecast_exec"]
        left = plan["days_left"]
        if fc is not None and left > 0:
            if fc >= 100:
                good.append(_item(6, f"Месяц идёт в план: прогноз {F.pct(fc)}",
                                  f"Собрано {F.money_short(t['month_fact'])} из {F.money_short(t['month_plan'])}"))
            elif t["month_left"] > 0:
                bad.append(_item(7, f"Прогноз на {month}: {F.pct(fc)} плана",
                                 f"Осталось собрать {F.money_short(t['month_left'])} за {left} дн.: нужно "
                                 f"{F.money_short(t['need_daily'])} в день, сейчас {F.money_short(t['avg_daily'])}"))
                ask.append(_item(7, f"Как добираем {F.money_short(t['month_left'])} до плана месяца за {left} дн.?",
                                 "Какие заказы можно довести до оплаты, какие магазины подтянуть"))

    # Заказы, созданные за период
    oc = orders["cur"]
    if orders["chg_prev_amount"] is not None and orders["chg_prev_amount"] >= lim:
        good.append(_item(7, f"Новых заказов на {F.money_short(oc['amount'])}: {F.more_less(orders['chg_prev_amount'])} {pl}",
                          f"{F.orders_word(oc['count'])} {per}, средний чек {F.money_short(oc['avg'])}"))
    elif orders["chg_prev_amount"] is not None and orders["chg_prev_amount"] <= -lim:
        bad.append(_item(7, f"Новых заказов на {F.money_short(oc['amount'])}: {F.more_less(orders['chg_prev_amount'])} {pl}",
                         f"{F.orders_word(oc['count'])} {per}"))
    best = orders["best"]
    if best:
        good.append(_item(8, f"Лучший менеджер — {best['name']}",
                          f"{F.orders_word(best['count'])} на {F.money_short(best['amount'])} {per}, "
                          f"оплачено {F.pct(best['paid_share'])}"))
    none = orders["none"]
    if none["count"]:
        sh = F.pct(none["amount"] / oc["amount"] * 100) if oc["amount"] else "—"
        bad.append(_item(6 + (2 if oc["amount"] and none["amount"] / oc["amount"] > 0.2 else 0),
                         f"Новые заказы без предоплаты: {F.orders_word(none['count'])} на {F.money_short(none['amount'])}",
                         f"Созданы {per}, оплат по ним нет — {sh} суммы новых заказов"))
        ask.append(_item(8, f"Взять предоплату: {F.orders_word(none['count'])} на {F.money_short(none['amount'])}",
                         f"Созданы {per}, ни одной оплаты — список на стр. 3 и в Excel по менеджерам"))

    # Контроль (на сегодня)
    rd = ctrl["ready"]
    if rd["count"]:
        ask.append(_item(6, f"Закрыть в 1С {F.orders_word(rd['count'])}: отгружены и оплачены полностью",
                         _names(rd["by_manager"], value=lambda r: str(r["count"]))))
    db = ctrl["debt"]
    if db["amount"] > 0:
        bad.append(_item(6.5, f"Клиенты должны за отгруженное: {F.money_short(db['amount'])}",
                         f"На сегодня, {F.orders_word(db['count'])} за последний год: отгружено больше, чем оплачено"))
        ask.append(_item(7.5, f"Долг по отгрузке {F.money_short(db['amount'])}: кто и когда собирает",
                         "Крупнейшие: " + _names(db["list"], "client", lambda r: F.money_short(r["debt"]), 3, db["count"])))
    if ctrl["reserve"]["count"]:
        r = ctrl["reserve"]
        bad.append(_item(5, f"Висят в резерве без отгрузки > {C.RESERVE_STUCK_DAYS} дн.: {F.orders_word(r['count'])}",
                         f"На сегодня, за всё время: на {F.money_short(r['amount'])}, оплачено "
                         f"{F.money_short(r['paid'])} — товар держим, денег нет. Отгрузить или снять резерв"))
    if ctrl["approval"]["count"]:
        r = ctrl["approval"]
        ask.append(_item(4, f"«На согласовании» дольше {C.APPROVAL_STUCK_DAYS} дн.: {F.orders_word(r['count'])}",
                         f"На {F.money_short(r['amount'])} — дожать или отменить"))

    # Продажи (отгрузки)
    if sales["growth"]:
        g = sales["growth"][0]
        good.append(_item(5, f"Продажи «{g['sub']}» ({g['root']}) выросли на {F.money_short(g['net'] - g['prev'])}",
                          f"Отгружено {F.money_short(g['net'])} против {F.money_short(g['prev'])} {pl}"))
    if sales["drops"]:
        d = sales["drops"][0]
        bad.append(_item(6, f"Продажи «{d['sub']}» ({d['root']}) упали на {F.money_short(d['prev'] - d['net'])}",
                         f"Отгружено {F.money_short(d['net'])} против {F.money_short(d['prev'])} {pl}"))
        ask.append(_item(5, f"Почему продажи «{d['sub']}» {F.more_less(d['chg'], 'выросли', 'упали')}?",
                         "Наличие, цены, выкладка, активность менеджеров"))
    rp = sales["ret_pp"]
    if rp is not None and rp >= C.RETURNS_ALERT_PP:
        bad.append(_item(5.5, f"Возвраты товара выросли до {F.pct(sales['cur']['ret_share'], 1)} ({F.pp_words(rp)})",
                         f"Возвратов на {F.money_short(sales['cur']['cr'])} {per}"))
    elif rp is not None and rp <= -C.RETURNS_ALERT_PP:
        good.append(_item(4, f"Возвратов товара меньше: {F.pct(sales['cur']['ret_share'], 1)} ({F.pp_words(rp)})"))

    # Остатки
    if stock.get("has_data"):
        df = stock["deficit"]
        if df["count"]:
            bad.append(_item(6, f"Хиты без остатка: {F.sku_word(df['count'])} из топ-{df['of']} продаж",
                             _names(df["list"], value=None, limit=2)))
            ask.append(_item(6, f"Дозаказ: {F.sku_word(df['count'])} продаются, но закончились",
                             "Список на стр. «Остатки»"))
        st = stock["stale"]
        if st["sku"]:
            bad.append(_item(4.5, f"Залежалось: {F.sku_word(st['sku'])}, {F.qty(st['qty'])} шт.",
                             f"В наличии, без продаж больше {C.STALE_NO_SALES_DAYS} дн."))
            ask.append(_item(5.5, "Что делаем с залежавшимся товаром?",
                             "Акции, комплекты, перенос в зал, уценка — см. стр. «Остатки»"))

    def top(lst, n):
        return sorted(lst, key=lambda x: -x["prio"])[:n]

    plan_txt = (f", план на {month} {F.pct(t['month_exec'])} (прогноз {F.pct(t['month_forecast_exec'])})"
                if t["month_plan"] > 0 else "")
    headline = (f"Поступило {F.money_short(cash['cur']['cash_in'])} ({F.more_less(cash['chg_prev'])} {pl})"
                f"{plan_txt}; создано {F.orders_word(oc['count'])} на {F.money_short(oc['amount'])}.")
    return {"good": top(good, 4), "bad": top(bad, 4), "ask": top(ask, 5), "headline": headline}
