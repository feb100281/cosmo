# sales/reports/meeting_brief/fmt.py
"""Форматирование чисел и дат для текста и таблиц отчёта."""
from __future__ import annotations

from datetime import date

NBSP = " "
WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _num(v) -> float:
    try:
        x = float(v or 0)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if x != x else x


def _none(v) -> bool:
    if v is None:
        return True
    try:
        return float(v) != float(v)
    except (TypeError, ValueError):
        return True


def money(v, unit: bool = True) -> str:
    s = f"{_num(v):,.0f}".replace(",", NBSP)
    return f"{s}{NBSP}₽" if unit else s


def money_short(v) -> str:
    x = _num(v)
    a = abs(x)
    if a >= 1_000_000:
        s = f"{x / 1_000_000:.1f}".replace(".", ",")
        return f"{s}{NBSP}млн{NBSP}₽"
    if a >= 1_000:
        s = f"{x / 1_000:.1f}".replace(".", ",")
        return f"{s}{NBSP}тыс.{NBSP}₽"
    return money(x)


def qty(v) -> str:
    return f"{_num(v):,.0f}".replace(",", NBSP)


def pct(v, digits: int = 0) -> str:
    if _none(v):
        return "—"
    return f"{_num(v):.{digits}f}".replace(".", ",") + "%"


def signed_pct(v) -> str:
    if _none(v):
        return "—"
    x = _num(v)
    if abs(x) >= 999:
        return "×" + f"{x / 100 + 1:.1f}".replace(".", ",")
    sign = "+" if x > 0 else ("−" if x < 0 else "")
    return f"{sign}{abs(x):.0f}%"


def more_less(v, up: str = "больше", down: str = "меньше") -> str:
    """Изменение словами: «больше на 15%» / «меньше на 15%» — без знака минус."""
    if _none(v):
        return ""
    x = _num(v)
    if abs(x) < 0.5:
        return "без изменений"
    if abs(x) >= 999:
        return f"{up} в {x / 100 + 1:.1f} раза".replace(".", ",")
    return f"{up if x > 0 else down} на {abs(x):.0f}%"


def pp_words(v) -> str:
    if _none(v):
        return ""
    x = _num(v)
    return f"{'рост' if x > 0 else 'снижение'} на {abs(x):.1f}".replace(".", ",") + f"{NBSP}п.п."


def signed_pp(v) -> str:
    if _none(v):
        return "—"
    x = _num(v)
    sign = "+" if x > 0 else ("−" if x < 0 else "")
    return f"{sign}{abs(x):.1f}".replace(".", ",") + f"{NBSP}п.п."


def day(d: date | None) -> str:
    return d.strftime("%d.%m.%Y") if isinstance(d, date) else "—"


def day_short(d: date | None) -> str:
    return f"{d.strftime('%d.%m')} {WEEKDAYS[d.weekday()]}" if isinstance(d, date) else "—"


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def orders_word(n: int) -> str:
    return f"{n}{NBSP}{plural(n, 'заказ', 'заказа', 'заказов')}"


def sku_word(n: int) -> str:
    return f"{n}{NBSP}{plural(n, 'позиция', 'позиции', 'позиций')}"


def tone(v, good_when_up: bool = True, tol: float = 0.5) -> str:
    """CSS-класс для изменения: up / down / flat."""
    if _none(v):
        return "flat"
    x = _num(v)
    if abs(x) < tol:
        return "flat"
    return "up" if (x > 0) == good_when_up else "down"
