# sales/reports/meeting_brief/render.py
"""HTML отчёта к совещанию. Один и тот же документ — для просмотра в браузере и для PDF."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from . import config as C
from . import fmt as F
from .charts import cash_by_day
from .periods import Periods

CSS_PATH = Path(__file__).resolve().parent / "report.css"


def e(v) -> str:
    return escape("" if v is None else str(v))


# ---------------------------------------------------------------- элементы

def delta(v, good_when_up: bool = True, label: str = "") -> str:
    if F._none(v):
        return f'<span class="d flat">— {e(label)}</span>' if label else '<span class="d flat">—</span>'
    cls = F.tone(v, good_when_up)
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "•")
    return f'<span class="d {cls}">{arrow} {e(F.signed_pct(v))}{(" " + e(label)) if label else ""}</span>'


def delta_pp(v, good_when_up: bool = True, label: str = "") -> str:
    if F._none(v):
        return '<span class="d flat">—</span>'
    cls = F.tone(v, good_when_up, tol=0.1)
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "•")
    return f'<span class="d {cls}">{arrow} {e(F.signed_pp(v))}{(" " + e(label)) if label else ""}</span>'


def kpi(title: str, value: str, sub: str = "", deltas: str = "", tone: str = "") -> str:
    return (f'<td class="kpi {tone}"><div class="kpi-t">{e(title)}</div>'
            f'<div class="kpi-v">{value}</div>'
            f'<div class="kpi-s">{sub}</div><div class="kpi-d">{deltas}</div></td>')


def bar(pct_value, cls: str = "", cap: float = 100) -> str:
    w = max(0.0, min(float(pct_value or 0), cap)) / cap * 100
    return f'<div class="bar {cls}"><span style="width:{w:.1f}%"></span></div>'


def exec_cell(v) -> str:
    if F._none(v):
        return '<td class="num muted">нет плана</td>'
    cls = "good" if v >= 100 else ("watch" if v >= 90 else "bad")
    return (f'<td class="num exec {cls}"><b>{e(F.pct(v))}</b>'
            f'{bar(v, cls, 120)}</td>')


def section(title: str, note: str = "") -> str:
    n = f'<span class="sec-note">{e(note)}</span>' if note else ""
    return f'<div class="sec"><h2>{e(title)}</h2>{n}</div>'


def page(num: int, title: str, body: str, p: Periods) -> str:
    return (f'<section class="page"><header class="page-h"><span class="page-n">{num}</span>'
            f'<span class="page-title">{e(title)}</span><span class="page-p">{e(p.label)}</span></header>'
            f'{body}</section>')


def table(head: list[tuple[str, str]], rows: list[str], cls: str = "", foot: str = "") -> str:
    th = "".join(f'<th class="{c}">{e(t)}</th>' for t, c in head)
    tf = f"<tfoot>{foot}</tfoot>" if foot else ""
    if not rows:
        rows = [f'<tr><td colspan="{len(head)}" class="empty">Нет данных за период</td></tr>']
    return f'<table class="t {cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody>{tf}</table>'


def notes(items: list[dict], cls: str, empty: str) -> str:
    if not items:
        return f'<p class="empty-note">{e(empty)}</p>'
    li = "".join(f'<li><b>{e(i["title"])}</b>{("<span>" + e(i["text"]) + "</span>") if i["text"] else ""}</li>'
                 for i in items)
    tag = "ol" if cls == "ask" else "ul"
    return f'<{tag} class="notes {cls}">{li}</{tag}>'


# ---------------------------------------------------------------- страницы

def cover(m: dict, ins: dict, p: Periods) -> str:
    cash, plan, orders, sales = m["cash"], m["plan"], m["orders"], m["sales"]
    t = plan["total"]
    pl, ly = "к пр. периоду", "к пр. году"

    cards = [
        kpi("Поступило денег", F.money_short(cash["cur"]["cash_in"]),
            f"возвраты {F.money_short(cash['cur']['cash_ret'])}",
            delta(cash["chg_prev"], label=pl) + delta(cash["chg_ly"], label=ly)),
        kpi("Долг клиентов по отгрузке", F.money_short(m["control"]["debt"]["amount"]),
            f"{F.orders_word(m['control']['debt']['count'])} · на сегодня",
            '<span class="d flat">отгружено, но не оплачено</span>', tone="bad" if m["control"]["debt"]["amount"] else ""),
        kpi("Новые заказы", F.money_short(orders["cur"]["amount"]),
            f"{F.orders_word(orders['cur']['count'])}, ср. чек {F.money_short(orders['cur']['avg'])}"
            + (f"; комиссионер {orders['commission']['count']} на {F.money_short(orders['commission']['amount'])}"
               if orders["commission"]["count"] else ""),
            delta(orders["chg_prev_amount"], label=pl) + delta(orders["chg_ly_amount"], label=ly)),
        kpi(f"План месяца · {p.month_label.split()[0].lower()}",
            F.pct(t["month_exec"]) if t["month_plan"] else "—",
            (f"{F.money_short(t['month_fact'])} из {F.money_short(t['month_plan'])} на {p.end:%d.%m}"
             if t["month_plan"] else "план не заведён"),
            (f'<span class="d {"up" if (t["month_forecast_exec"] or 0) >= 100 else "down"}">'
             f'прогноз {e(F.pct(t["month_forecast_exec"]))}</span>' if t["month_plan"] else ""),
            tone=("good" if (t["month_forecast_exec"] or 0) >= 100 else "bad" if t["month_plan"] else "")),
        kpi("Реализация (отгрузки)", F.money_short(sales["cur"]["net"]),
            "без услуг, за вычетом возвратов",
            delta(sales["chg_prev"], label=pl) + delta(sales["chg_ly"], label=ly)),
        kpi("Возвраты товара", F.pct(sales["cur"]["ret_share"], 1),
            f"{F.money_short(sales['cur']['cr'])} от отгрузок",
            delta_pp(sales["ret_pp"], good_when_up=False, label=pl)),
    ]
    cmp_txt = (f"Сравнение: {p.prev_range_label} и {p.ly_range_label}")
    return (
        f'<section class="page cover">'
        f'<div class="mast"><div class="mast-l"><div class="brand">{e(C.BRAND)}</div>'
        f'<div class="brand-sub">{e(C.REPORT_TITLE)}</div></div>'
        f'<div class="mast-r"><div class="period">{e(p.label)}</div>'
        f'<div class="period-sub">{e(p.kind.capitalize())} · {p.days} дн. · {e(cmp_txt)}</div></div></div>'
        f'<p class="headline">{e(ins["headline"])}</p>'
        f'<table class="kpis"><tr>{"".join(cards)}</tr></table>'
        f'<table class="three"><tr>'
        f'<td class="col good"><h3>Получилось</h3>{notes(ins["good"], "good", "Заметных улучшений нет")}</td>'
        f'<td class="col bad"><h3>Требует внимания</h3>{notes(ins["bad"], "bad", "Серьёзных отклонений нет")}</td>'
        f'<td class="col ask"><h3>Вопросы к совещанию</h3>{notes(ins["ask"], "ask", "Вопросов нет")}</td>'
        f'</tr></table>'
        f'<p class="foot-note">Деньги — поступления от клиентов по кассе и банку (розница и заказы). '
        f'Заказы — по дате создания. Реализация — отгрузки по данным продаж. '
        f'Состояние заказов и остатки — на дату формирования отчёта.</p>'
        f'</section>'
    )


def month_block(plan: dict, p: Periods) -> str:
    t = plan["total"]
    if not t["month_plan"]:
        return '<p class="empty-note">План на этот месяц не заведён</p>'
    dp, dim = plan["days_passed"], plan["days_in_month"]
    pace = dp / dim * 100
    fact_pct = t["month_exec"] or 0
    ahead = t["month_vs_expected"]
    cls = "good" if ahead >= 0 else "bad"
    need = t["need_daily"]
    need_txt = (f'{F.money_short(need)} в день' if need else ("план выполнен" if t["month_left"] <= 0 else "месяц закончился"))
    w = min(fact_pct, 100)
    return (
        f'<div class="month">'
        f'<div class="month-h"><b>{e(p.month_label)}</b><span>прошло {dp} из {dim} дн. · '
        f'осталось {plan["days_left"]} дн.</span></div>'
        f'<div class="month-bar"><span class="fill {cls}" style="width:{w:.1f}%"></span>'
        f'<span class="mark" style="left:{min(pace, 100):.1f}%"></span></div>'
        f'<div class="month-legend"><span>Выполнено {e(F.pct(fact_pct))}</span>'
        f'<span>черта — где должны быть к {p.end:%d.%m} при равномерном выполнении ({e(F.pct(pace))})</span></div>'
        f'<table class="month-n"><tr>'
        f'<td><i>План месяца</i><b>{e(F.money_short(t["month_plan"]))}</b></td>'
        f'<td><i>Факт на {p.end:%d.%m}</i><b>{e(F.money_short(t["month_fact"]))}</b></td>'
        f'<td><i>Должно быть к {p.end:%d.%m}</i><b>{e(F.money_short(t["month_expected"]))}</b></td>'
        f'<td class="{cls}"><i>{"Опережаем" if ahead >= 0 else "Отстаём"}</i><b>{e(F.money_short(abs(ahead)))}</b></td>'
        f'<td><i>Прогноз по темпу</i><b>{e(F.money_short(t["month_forecast"]))}</b><em>{e(F.pct(t["month_forecast_exec"]))} плана</em></td>'
        f'<td><i>Осталось собрать</i><b>{e(F.money_short(t["month_left"]))}</b>'
        f'<em>нужно {e(need_txt)}, сейчас {e(F.money_short(t["avg_daily"]))}</em></td>'
        f'</tr></table></div>'
    )


def how_block(plan: dict, p: Periods) -> str:
    ex = plan.get("example")
    example = ""
    if ex:
        dim = plan["days_in_month"]
        dp = plan["days_passed"]
        example = (f' Например, «{e(ex["store"])}»: {e(F.money_short(ex["month_plan"]))} ÷ {dim} × {dp} '
                   f'≈ {e(F.money_short(ex["month_plan"] / dim * dp))}.')
    return (
        '<div class="how"><b>Как считаем.</b> '
        '<u>Факт</u> — деньги от клиентов по дате оплаты: оплаты заказов (касса, банк) и розничная выручка, без возвратов. '
        '<u>План</u> — месячный план подразделения из раздела «Планы продаж магазинов», как в газете. '
        f'<u>Должно быть к дате</u> — план месяца ÷ дней в месяце × прошедшие дни.{example} '
        '<u>Прогноз месяца</u> — факт с 1-го числа ÷ прошедшие дни × дней в месяце, т.е. итог месяца при текущем темпе.</div>'
    )


def money_page(m: dict, p: Periods) -> str:
    cash, plan = m["cash"], m["plan"]
    best, worst = cash["best_day"], cash["worst_day"]
    marks = []
    if best:
        marks.append(f'<span class="tag good">лучший день: {e(F.day_short(best["date"]))} — {e(F.money_short(best["cash_in"]))}</span>')
    if worst:
        marks.append(f'<span class="tag bad">слабый день: {e(F.day_short(worst["date"]))} — {e(F.money_short(worst["cash_in"]))}</span>')
    marks.append('<span class="tag ghost">серые столбцы — тот же день прошлого периода</span>')
    chart = cash_by_day(cash, height_in=1.25)

    def ahead_cell(r):
        if not r["month_plan"]:
            return '<td class="num muted">—</td>'
        d = r["month_fact"] - r["month_expected"]
        return (f'<td class="num {"pos" if d >= 0 else "neg"}">{"+" if d >= 0 else "−"}'
                f'{e(F.money_short(abs(d)))}</td>')

    rows = []
    with_plan = [r for r in plan["rows"] if r["month_plan"] > 0]
    no_plan = [r for r in plan["rows"] if r["month_plan"] <= 0]
    for r in with_plan:
        rows.append(
            f'<tr><td class="name">{e(r["store"])}</td>'
            f'<td class="num">{e(F.money_short(r["month_plan"])) if r["month_plan"] else "—"}</td>'
            f'<td class="num"><b>{e(F.money_short(r["month_fact"]))}</b></td>'
            f'{exec_cell(r["month_exec"] if r["month_plan"] else None)}'
            f'{ahead_cell(r)}'
            f'{exec_cell(r["month_forecast_exec"] if r["month_plan"] else None)}'
            f'<td class="num">{e(F.money_short(r["fact"]))}</td>'
            f'<td class="num">{delta(r["chg_prev"])}</td></tr>')
    if no_plan:
        rows.append(
            f'<tr class="rest"><td class="name">Без плана: {e(", ".join(r["store"] for r in no_plan[:3]))}'
            f'{" и др." if len(no_plan) > 3 else ""}</td><td class="num">—</td>'
            f'<td class="num">{e(F.money_short(sum(r["month_fact"] for r in no_plan)))}</td>'
            f'<td></td><td></td><td></td>'
            f'<td class="num">{e(F.money_short(sum(r["fact"] for r in no_plan)))}</td><td></td></tr>')
    t = plan["total"]
    tot = {"month_plan": t["month_plan"], "month_fact": t["month_fact"], "month_expected": t["month_expected"]}
    foot = (f'<tr><td class="name">Итого</td><td class="num">{e(F.money_short(t["month_plan"]))}</td>'
            f'<td class="num"><b>{e(F.money_short(t["month_fact"]))}</b></td>'
            f'{exec_cell(t["month_exec"] if t["month_plan"] else None)}{ahead_cell(tot)}'
            f'{exec_cell(t["month_forecast_exec"] if t["month_plan"] else None)}'
            f'<td class="num">{e(F.money_short(t["fact"]))}</td><td class="num">{delta(cash["chg_prev"])}</td></tr>')
    head = [("Подразделение", ""), (f"План на {p.month_label.split()[0].lower()}", "num"),
            (f"Факт с 1 {p.month_gen} по {p.end:%d.%m}", "num"), ("Выполнено", "num w-exec"),
            (f"К темпу на {p.end:%d.%m}", "num"), ("Прогноз месяца", "num w-exec"),
            ("Факт за период", "num"), (p.prev_label.capitalize(), "num")]
    body = (
        section(f"План / факт за месяц: {p.month_label.lower()}", "все подразделения, деньги от клиентов")
        + month_block(plan, p)
        + section("Поступления по дням", f"{F.money_short(cash['cur']['cash_in'])} за период, "
                                        f"в среднем {F.money_short(cash['avg_day'])} в день")
        + f'<div class="chart">{chart}</div><div class="tags">{"".join(marks)}</div>'
        + section("План / факт по подразделениям", "месяц — главное; справа деньги за выбранный период")
        + table(head, rows, "plan compact", foot)
        + how_block(plan, p)
    )
    return page(2, "Деньги и план", body, p)


def orders_page(m: dict, p: Periods) -> str:
    o = m["orders"]
    cur = o["cur"]
    total = cur["amount"] or 1
    seg = "".join(
        f'<span class="seg {c}" style="width:{max(o[k]["amount"] / total * 100, 0):.1f}%"></span>'
        for k, c in (("full", "s-full"), ("partial", "s-part"), ("none", "s-none"), ("ext", "s-ext")))
    legend = "".join(
        f'<td><i class="dot {c}"></i><b>{e(t)}</b><br>{e(F.orders_word(o[k]["count"]))} · '
        f'{e(F.money_short(o[k]["amount"]))}</td>'
        for k, c, t in (("full", "s-full", "Оплачены полностью"), ("partial", "s-part", "Частично"),
                        ("none", "s-none", "Без предоплаты"), ("ext", "s-ext", "Комиссионер (оплата по отчёту)"))
        if k != "ext" or o["ext"]["count"])
    d = o["delivery"]
    side = (
        f'<table class="mini"><tr>'
        f'<td><div class="mini-t">Создано</div><div class="mini-v">{e(F.money_short(cur["amount"]))}</div>'
        f'<div class="mini-s">{e(F.orders_word(cur["count"]))} {delta(o["chg_prev_count"], label="по кол-ву")}</div></td>'
        f'<td><div class="mini-t">Оплачено по ним</div><div class="mini-v">{e(F.pct(o["paid_share"]))}</div>'
        f'<div class="mini-s">{e(F.money_short(cur["paid"]))}</div></td>'
        f'<td><div class="mini-t">Уже отгружено</div><div class="mini-v">{e(F.pct(o["shipped_share"]))}</div>'
        f'<div class="mini-s">{e(F.money_short(cur["shipped"]))}</div></td>'
        f'<td><div class="mini-t">С доставкой</div><div class="mini-v">{e(F.pct(d["orders_share"]))}</div>'
        f'<div class="mini-s">заказов · доставка {e(F.money_short(d["amount"]))} ({e(F.pct(d["amount_share"], 1))} суммы), '
        f'в среднем {e(F.money_short(d["avg"]))}</div></td>'
        f'<td><div class="mini-t">Отменено</div><div class="mini-v">{e(o["cancelled"]["count"])}</div>'
        f'<div class="mini-s">на {e(F.money_short(o["cancelled"]["amount"]))}</div></td>'
        f'</tr></table>'
        f'<div class="stack">{seg}</div><table class="legend"><tr>{legend}</tr></table>'
    )

    best = o["best"]["name"] if o["best"] else None
    best_cash = o["best_cash"]["name"] if o["best_cash"] else None
    rows = []
    top_n = C.MANAGER_ROWS
    shown = o["managers"][:top_n]
    rest = o["managers"][top_n:]
    for r in shown:
        badges = ""
        if r["name"] == best:
            badges += '<span class="badge">лучший по заказам</span>'
        if r["name"] == best_cash:
            badges += '<span class="badge alt">больше всех денег</span>'
        np_ = (f'{F.orders_word(r["no_pay_count"])} · {F.money_short(r["no_pay_amount"])}'
               if r["no_pay_count"] else "—")
        rows.append(
            f'<tr><td class="name">{e(r["name"])}{badges}</td>'
            f'<td class="num">{e(r["count"])}</td><td class="num"><b>{e(F.money(r["amount"], False))}</b></td>'
            f'<td class="num">{e(F.money(r["avg"], False)) if r["count"] else "—"}</td>'
            f'<td class="num">{e(F.pct(r["paid_share"]))}</td>'
            f'<td class="num {"warn" if r["no_pay_count"] else ""}">{e(np_)}</td>'
            f'<td class="num">{e(F.pct(r["delivery_share"], 1))}</td>'
            f'<td class="num"><b>{e(F.money(r["cash"], False))}</b></td></tr>')
    if rest:
        rc, ra = sum(r["count"] for r in rest), sum(r["amount"] for r in rest)
        rows.append(
            f'<tr class="rest"><td class="name">Остальные менеджеры ({len(rest)})</td>'
            f'<td class="num">{rc}</td><td class="num">{e(F.money(ra, False))}</td>'
            f'<td class="num">{e(F.money(ra / rc, False)) if rc else "—"}</td><td></td>'
            f'<td class="num">{e(F.orders_word(sum(r["no_pay_count"] for r in rest)))}</td><td></td>'
            f'<td class="num">{e(F.money(sum(r["cash"] for r in rest), False))}</td></tr>')
    head = [("Менеджер", ""), ("Заказов", "num"), ("Сумма, ₽", "num"), ("Ср. чек, ₽", "num"),
            ("Оплачено", "num"), ("Без предоплаты", "num"), ("Доставка", "num"), ("Собрано денег, ₽", "num")]

    np_rows = [
        f'<tr><td class="name">{e(r["number"])}</td><td>{e(F.day(r["date"]))}</td><td>{e(r["client"])}</td>'
        f'<td>{e(r["manager"])}</td><td>{e(r["status"])}</td><td class="num"><b>{e(F.money(r["amount"], False))}</b></td></tr>'
        for r in o["no_pay_list"][:5]]
    np_head = [("Заказ", ""), ("Создан", ""), ("Клиент", ""), ("Менеджер", ""), ("Статус", ""), ("Сумма, ₽", "num")]

    body = (
        section("Заказы, созданные за период", "по дате создания; оплата и отгрузка — на дату отчёта")
        + side
        + section("Менеджеры", "«Собрано денег» — оплаты за период по заказам менеджера, в т.ч. по старым заказам")
        + table(head, rows, "mgr compact")
        + section("Новые заказы без предоплаты", f"крупнейшие, всего {F.orders_word(o['none']['count'])} "
                                                  f"на {F.money_short(o['none']['amount'])}")
        + table(np_head, np_rows, "compact")
    )
    return page(3, "Заказы и менеджеры", body, p)


def stores_page(m: dict, p: Periods) -> str:
    o = m["orders"]
    rows, tot = [], {"count": 0, "amount": 0.0, "paid": 0.0, "full": 0, "partial": 0, "none": 0, "ext": 0,
                     "shipped": 0.0}
    has_ext = any(r["ext"] for r in o["stores"])
    for r in o["stores"]:
        for k in tot:
            tot[k] += r[k]
        ext = f'<td class="num">{e(r["ext"] or "—")}</td>' if has_ext else ""
        rows.append(
            f'<tr><td class="name">{e(r["store"])}</td><td class="num"><b>{e(r["count"])}</b></td>'
            f'<td class="num"><b>{e(F.money(r["amount"], False))}</b></td>'
            f'<td class="num">{e(F.money(r["avg"], False))}</td>'
            f'<td class="num">{e(F.money(r["paid"], False))}</td><td class="num">{e(F.pct(r["paid_share"]))}</td>'
            f'<td class="num">{e(r["full"] or "—")}</td><td class="num">{e(r["partial"] or "—")}</td>'
            f'<td class="num {"warn" if r["none"] else ""}">{e(r["none"] or "—")}</td>{ext}'
            f'<td class="num">{e(F.money(r["shipped"], False))}</td></tr>')
    head = [("Подразделение", ""), ("Заказов", "num"), ("Сумма, ₽", "num"), ("Ср. чек, ₽", "num"),
            ("Оплачено, ₽", "num"), ("Оплачено, %", "num"), ("Полностью", "num"), ("Частично", "num"),
            ("Без оплаты", "num")] + ([("Комиссионер", "num")] if has_ext else []) + [("Отгружено, ₽", "num")]
    foot = ""
    if rows:
        share = tot["paid"] / tot["amount"] * 100 if tot["amount"] else None
        ext = f'<td class="num">{e(tot["ext"] or "—")}</td>' if has_ext else ""
        foot = (f'<tr><td class="name">Итого</td><td class="num">{e(tot["count"])}</td>'
                f'<td class="num">{e(F.money(tot["amount"], False))}</td>'
                f'<td class="num">{e(F.money(tot["amount"] / tot["count"], False)) if tot["count"] else "—"}</td>'
                f'<td class="num">{e(F.money(tot["paid"], False))}</td><td class="num">{e(F.pct(share))}</td>'
                f'<td class="num">{e(tot["full"])}</td><td class="num">{e(tot["partial"])}</td>'
                f'<td class="num">{e(tot["none"])}</td>{ext}'
                f'<td class="num">{e(F.money(tot["shipped"], False))}</td></tr>')
    body = (
        section("Заказы, созданные за период, по подразделениям",
                "по дате создания, без отменённых; оплата и отгрузка — на дату отчёта")
        + table(head, rows, "compact", foot)
        + '<p class="empty-note">«Оплачено» — сумма оплат клиента по заказу, не больше суммы заказа. '
          'Полный список заказов — в Excel «Заказы по подразделениям».</p>'
    )
    return page(4, "Заказы по подразделениям", body, p)


def _chg_cell(v, good_when_up=True):
    return f'<td class="num">{delta(v, good_when_up)}</td>'


def sales_page(m: dict, p: Periods) -> str:
    s = m["sales"]
    max_share = max([r.get("share") or 0 for r in s["categories"]] + [1])
    rows = []
    for r in s["categories"]:
        rows.append(
            f'<tr class="{"rest" if r.get("is_rest") else ""}"><td class="name">{e(r["root"])}</td>'
            f'<td class="num"><b>{e(F.money(r["net"], False))}</b></td>'
            f'<td class="share">{bar((r.get("share") or 0) / max_share * 100, "neutral")}<em>{e(F.pct(r.get("share")))}</em></td>'
            f'{_chg_cell(r["chg"])}{_chg_cell(r["chg_ly"])}'
            f'<td class="num {"warn" if (r.get("ret_share") or 0) > 5 else ""}">{e(F.pct(r.get("ret_share"), 1))}</td></tr>')
    head = [("Категория", ""), ("Реализация, ₽", "num"), ("Доля", "w-share"), (p.prev_label.capitalize(), "num"),
            ("К году", "num"), ("Возвраты", "num")]
    foot = (f'<tr><td class="name">Итого</td><td class="num"><b>{e(F.money(s["cur"]["net"], False))}</b></td><td></td>'
            f'{_chg_cell(s["chg_prev"])}{_chg_cell(s["chg_ly"])}<td class="num">{e(F.pct(s["cur"]["ret_share"], 1))}</td></tr>')

    def movers(lst, sign):
        out = []
        for r in lst:
            dv = r["net"] - r["prev"]
            out.append(f'<tr><td class="name">{e(r["sub"])}<small>{e(r["root"])}</small></td>'
                       f'<td class="num">{e(F.money_short(r["net"]))}</td>'
                       f'<td class="num {"pos" if sign > 0 else "neg"}"><b>{"+" if dv > 0 else "−"}{e(F.money_short(abs(dv)))}</b></td>'
                       f'<td class="num">{delta(r["chg"])}</td></tr>')
        return out
    mv_head = [("Подкатегория", ""), ("Сейчас", "num"), ("Изменение", "num"), ("%", "num")]

    br = [f'<tr><td class="name">{e(r["brand"])}</td><td class="num">{e(F.money_short(r["net"]))}</td>'
          f'<td class="num">{e(F.pct(r.get("share")))}</td>{_chg_cell(r["chg"])}</tr>' for r in s["brands"][:6]]
    rt = [f'<tr><td class="name">{e(r["name"])}<small>{e(r["root"])}</small></td>'
          f'<td class="num">{e(F.money_short(r["cr"]))}</td><td class="num">{e(F.qty(r["qty"]))}</td></tr>'
          for r in s["returns"][:4]]

    body = (
        '<table class="cols"><tr>'
        + f'<td class="w58">{section("Реализация по категориям", "отгрузки минус возвраты, без услуг")}'
          f'{table(head, rows, "cats compact", foot)}</td>'
        + f'<td>{section("Бренды")}{table([("Бренд", ""), ("Реализация", "num"), ("Доля", "num"), ("%", "num")], br, "compact")}'
          f'{section("Больше всего возвратов")}{table([("Товар", ""), ("Сумма", "num"), ("Шт.", "num")], rt, "compact")}</td>'
        + '</tr></table>'
        + '<table class="cols"><tr>'
        + f'<td>{section("Растут сильнее всего", "в рублях " + p.prev_label)}{table(mv_head, movers(s["growth"], 1), "compact")}</td>'
        + f'<td>{section("Просели сильнее всего", "в рублях " + p.prev_label)}{table(mv_head, movers(s["drops"], -1), "compact")}</td>'
        + '</tr></table>'
    )
    return page(5, "Продажи по категориям и брендам", body, p)


def control_page(m: dict, p: Periods) -> str:
    c = m["control"]

    def card(title, block, sub, cls):
        return (f'<td class="kpi {cls}"><div class="kpi-t">{e(title)}</div>'
                f'<div class="kpi-v">{e(F.orders_word(block["count"]))}</div>'
                f'<div class="kpi-s">{e(sub)}</div></td>')

    cards = (
        card("Готовы к закрытию", c["ready"], f"на {F.money_short(c['ready']['amount'])} — отгружены и оплачены", "watch")
        + card("Отгружено без оплаты", c["debt"], f"долг {F.money_short(c['debt']['amount'])} (заказы за год)", "bad")
        + card(f"Резерв без отгрузки > {C.RESERVE_STUCK_DAYS} дн.", c["reserve"],
               f"на {F.money_short(c['reserve']['amount'])}, оплачено {F.money_short(c['reserve']['paid'])}", "")
        + card(f"На согласовании > {C.APPROVAL_STUCK_DAYS} дн.", c["approval"],
               f"на {F.money_short(c['approval']['amount'])}", "")
    )
    n = 6
    ready_mgr = [f'<tr><td class="name">{e(r["name"])}</td><td class="num">{e(r["count"])}</td>'
                 f'<td class="num">{e(F.money_short(r["amount"]))}</td></tr>' for r in c["ready"]["by_manager"][:n]]
    debt_mgr = [f'<tr><td class="name">{e(r["name"])}</td><td class="num">{e(r["count"])}</td>'
                f'<td class="num neg">{e(F.money_short(r["amount"]))}</td></tr>' for r in c["debt"]["by_manager"][:n]]
    debt_rows = [f'<tr><td class="name">{e(r["number"])}<small>{e(F.day(r["date"]))}</small></td><td>{e(r["client"])}</td>'
                 f'<td>{e(r["manager"])}</td><td class="num">{e(F.money_short(r["shipped"]))}</td>'
                 f'<td class="num">{e(F.money_short(r["paid"]))}</td>'
                 f'<td class="num neg"><b>{e(F.money_short(r["debt"]))}</b></td></tr>' for r in c["debt"]["list"][:n]]

    ex = c["debt_excluded"]
    ex_rows = [f'<tr><td class="name">{e(r["client"])}</td><td class="num">{e(r["count"])}</td>'
               f'<td>{e(r["reason"].split(": ", 1)[-1])}</td><td class="num">{e(F.money_short(r["amount"]))}</td></tr>'
               for r in ex["by_client"][:5]]
    ex_block = (section("Не считаются долгом", f"{F.orders_word(ex['count'])} на {F.money_short(ex['amount'])} · "
                                                   f"на сегодня, заказы с {p.end.replace(year=p.end.year - 1) if not (p.end.month == 2 and p.end.day == 29) else p.end.replace(year=p.end.year - 1, day=28):%d.%m.%Y}")
                + table([("Клиент", ""), ("Заказов", "num"), ("Почему", ""), ("Сумма", "num")], ex_rows, "compact")
                if ex["count"] else "")

    def stuck(block, k):
        return [f'<tr><td class="name">{e(r["number"])}</td><td>{e(r["client"])}</td><td>{e(r["manager"])}</td>'
                f'<td class="num">{e(r["days"])}</td><td class="num">{e(F.money_short(r["amount"]))}</td></tr>'
                for r in block["list"][:k]]
    st_head = [("Заказ", ""), ("Клиент", ""), ("Менеджер", ""), ("Дней", "num"), ("Сумма", "num")]

    body = (
        f'<table class="kpis small"><tr>{cards}</tr></table>'
        + '<p class="hint">Состояние на сегодня по всем открытым заказам, не только за выбранный период. '
          'Полные списки по каждому менеджеру — в Excel «Задачи менеджеров». '
          + ('' if c["exclusions_ok"] else ' <b>Раздел исключений ещё не создан — выполните python manage.py migrate.</b>')
          + '</p>'
        + '<table class="cols"><tr>'
        + f'<td class="w35">{section("Готовы к закрытию", "заказ = отгрузка = оплата, статус не «Закрыт»")}'
          f'{table([("Менеджер", ""), ("Заказов", "num"), ("Сумма", "num")], ready_mgr, "compact")}'
          f'{section("Долг по отгрузке по менеджерам")}'
          f'{table([("Менеджер", ""), ("Заказов", "num"), ("Долг", "num")], debt_mgr, "compact")}{ex_block}</td>'
        + f'<td>{section("Крупнейшие долги по отгрузке", "отгружено − оплачено; на сегодня, заказы за последний год")}'
          f'{table([("Заказ", ""), ("Клиент", ""), ("Менеджер", ""), ("Отгружено", "num"), ("Оплачено", "num"), ("Долг", "num")], debt_rows, "compact")}'
          f'{section("Резервы без отгрузки", "крупнейшие")}{table(st_head, stuck(c["reserve"], 3), "compact")}'
          f'{section("Долго на согласовании", "крупнейшие")}{table(st_head, stuck(c["approval"], 3), "compact")}</td>'
        + '</tr></table>'
    )
    return page(6, "Контроль заказов", body, p)


def stock_page(m: dict, p: Periods) -> str:
    s = m["stock"]
    if not s.get("has_data"):
        return page(7, "Остатки", '<p class="empty-note">Остатки не загружены</p>', p)
    st, df = s["stale"], s["deficit"]
    val = f"из них {st['never']} ни разу не продавались"
    cards = (
        kpi("Товаров в наличии", F.sku_word(s["sku"]), f"{F.qty(s['qty'])} шт. на {F.day(s['stock_date'])}")
        + kpi("Залежалось", F.sku_word(st["sku"]), f"{F.qty(st['qty'])} шт. · {val}",
              f'<span class="d down">это {e(F.pct(st["share"]))} товаров, которые сейчас в наличии</span>', "bad")
        + kpi("Хиты без остатка", F.sku_word(df["count"]), f"из топ-{df['of']} продаж периода", "",
              "watch" if df["count"] else "")
    )
    stale_rows = [
        f'<tr><td class="name">{e(r["name"])}<small>{e(r["root"])}{(" · " + e(r["article"])) if r["article"] else ""}</small></td>'
        f'<td class="num">{e(F.qty(r["available"]))}</td>'
        f'<td class="num">{e(F.qty(r["age_days"])) if not F._none(r["age_days"]) else "—"}</td>'
        f'<td class="num">{e(F.day(r["last_sale"])) if r["last_sale"] else "не было"}</td>'
        f'<td class="advice">{e(r["advice"])}</td></tr>' for r in st["list"][:8]]
    def_rows = [f'<tr><td class="name">{e(r["name"])}<small>{e(r["root"])}</small></td>'
                f'<td class="num">{e(F.qty(r["sold"]))}</td>'
                f'<td class="num">{e(F.qty(r["ordered"])) if r["ordered"] else "—"}</td></tr>' for r in df["list"][:6]]
    cat_rows = [f'<tr><td class="name">{e(r["root"])}</td><td class="num">{e(r["sku"])}</td>'
                f'<td class="num">{e(F.qty(r["qty"]))}</td><td class="num">{e(F.qty(r["sold"]))}</td>'
                f'<td class="num">{e(F.qty(r["cover_weeks"])) if r["cover_weeks"] is not None else "нет продаж"}</td>'
                f'<td class="num {"warn" if (r["stale_share"] or 0) >= 30 else ""}">{e(F.pct(r["stale_share"]))}</td></tr>'
                for r in s["categories"][:6]]
    body = (
        f'<table class="kpis small"><tr>{cards}</tr></table>'
        + section("Залежавшийся товар — что можно сделать",
                  f"есть в наличии, не продаётся больше {C.STALE_NO_SALES_DAYS} дн. и лежит на складе больше "
                  f"{C.STALE_MIN_AGE_DAYS} дн.; сверху — с самым большим остатком")
        + table([("Товар", ""), ("Остаток, шт.", "num"), ("Дней на складе", "num"), ("Посл. продажа", "num"),
                 ("Что можно сделать", "")], stale_rows, "stale compact")
        + '<table class="cols"><tr>'
        + f'<td class="w40">{section("Продаются, но закончились", "дозаказать")}'
          f'{table([("Товар", ""), ("Продано, шт.", "num"), ("В заказе", "num")], def_rows, "compact")}</td>'
        + f'<td>{section("Остатки по категориям", "запас — на сколько недель хватит при темпе периода")}'
          f'{table([("Категория", ""), ("SKU", "num"), ("Шт.", "num"), ("Продано", "num"), ("Запас, нед.", "num"), ("Залежалось", "num")], cat_rows, "compact")}</td>'
        + '</tr></table>'
    )
    return page(7, "Остатки", body, p)


def render_html(m: dict, ins: dict, p: Periods, standalone: bool = True, toolbar: str = "") -> str:
    css = CSS_PATH.read_text(encoding="utf-8")
    pages = "".join([cover(m, ins, p), money_page(m, p), orders_page(m, p), stores_page(m, p), sales_page(m, p),
                     control_page(m, p), stock_page(m, p)])
    gen = f'<div class="generated">Сформировано {datetime.now():%d.%m.%Y %H:%M}</div>'
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{e(C.REPORT_TITLE)} · {e(p.label)}</title><style>{css}</style></head>'
            f'<body>{toolbar}<main class="doc">{pages}{gen}</main></body></html>')
