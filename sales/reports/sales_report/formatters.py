import numpy as np


NBSP = "\u00A0"


def pct_change(curr, prev):
    try:
        curr = float(curr)
        prev = float(prev)
    except Exception:
        return None
    if prev == 0:
        return None
    return (curr - prev) / prev * 100

def fmt_pp(pct, digits: int = 1) -> str:
    if pct is None:
        return "—"
    s = f"{pct:+.{digits}f}".replace(".", ",")
    return f"{s}%"


def fmt_delta_money(v):
    """
    Δ деньги со знаком. Минус НЕ теряем.
    """
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    sign = "+" if v > 0 else "−" if v < 0 else ""
    # если ровно 0 — показываем 0 ₽ (без плюса/минуса)
    if sign == "":
        return fmt_money(0)
    return f"{sign}{fmt_money(abs(v))}"


def fmt_delta_int(v):
    """
    Δ int со знаком.
    """
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    sign = "+" if v > 0 else "−" if v < 0 else ""
    if sign == "":
        return fmt_int(0)
    return f"{sign}{fmt_int(abs(v))}"



def fmt_money_0(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "—"
        return f"{float(v):,.0f} ₽".replace(",", " ").replace(".", ",")


def fmt_delta_short(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    sign = "−" if v < 0 else "+"
    av = abs(float(v))

    if av >= 1_000_000:
        return f"{sign}{av/1_000_000:,.1f} млн ₽".replace(",", " ").replace(".", ",")
    if av >= 1_000:
        return f"{sign}{av/1_000:,.0f} тыс ₽".replace(",", " ").replace(".", ",")
    return f"{sign}{av:,.0f} ₽".replace(",", " ").replace(".", ",")


def fmt_money_chart(v) -> str:
    if v is None:
        return "—"
    v = float(v)
    av = abs(v)
    nbsp = "\u00A0"

    if av >= 1_000_000:
        return f"{v/1_000_000:,.1f}".replace(",", nbsp).replace(".", ",") + f"{nbsp}млн"
    if av >= 1_000:
        return f"{v/1_000:,.0f}".replace(",", nbsp) + f"{nbsp}тыс"
    return f"{v:,.0f}".replace(",", nbsp)


def fmt_delta_short_chart(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    sign = "−" if v < 0 else "+"
    av = abs(float(v))

    if av >= 1_000_000:
        return f"{sign}{av/1_000_000:,.1f} млн".replace(",", " ").replace(".", ",")
    if av >= 1_000:
        return f"{sign}{av/1_000:,.0f} тыс".replace(",", " ").replace(".", ",")
    return f"{sign}{av:,.0f}".replace(",", " ").replace(".", ",")



def fmt_delta_money_signed(v):
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    sign = "+" if v > 0 else "−" if v < 0 else ""
    # fmt_money уже умеет форматировать число с ₽ и неразрывными пробелами
    return f"{sign}{fmt_money(abs(v))}" if sign else fmt_money(0)


def fmt_delta_int_signed(v):
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{fmt_int(abs(v))}" if sign else fmt_int(0)






def fmt_money(v, mln_digits: int = 1) -> str:
    """
    Денежный формат с сокращениями (тыс/млн) и НЕРАЗРЫВНЫМИ пробелами,
    чтобы "₽" и единицы не уезжали на новую строку.
    """
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    av = abs(v)

    if av >= 1_000_000:
        s = f"{v / 1_000_000:,.{mln_digits}f}".replace(",", NBSP).replace(".", ",")
        return f"{s}{NBSP}млн{NBSP}₽"

    if av >= 1_000:
        s = f"{v / 1_000:,.0f}".replace(",", NBSP)
        return f"{s}{NBSP}тыс{NBSP}₽"

    s = f"{v:,.0f}".replace(",", NBSP)
    return f"{s}{NBSP}₽"


def fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(v):,}".replace(",", NBSP)
    except Exception:
        return "—"


def fmt_pct(v, digits=1) -> str:
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    s = f"{v:.{digits}f}".replace(".", ",")
    return f"{s}%"



def fmt_rub(v, digits: int = 0) -> str:
    """
    Рубли БЕЗ сокращений (всегда полная сумма), с NBSP и неразрывным "₽".
    Пример: 95 235 ₽
    """
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    s = f"{v:,.{digits}f}".replace(",", NBSP).replace(".", ",")
    return f"{s}{NBSP}₽"


def fmt_delta_rub(v, digits: int = 0) -> str:
    """
    Δ рубли со знаком, БЕЗ сокращений.
    """
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    sign = "+" if v > 0 else "−" if v < 0 else ""
    if sign == "":
        return fmt_rub(0, digits=digits)
    return f"{sign}{fmt_rub(abs(v), digits=digits)}"


def fmt_money_0(v):
    """
    Оставляю для совместимости, но делаю NBSP и неразрывный ₽.
    (Если где-то используется как "точная сумма" — лучше заменить на fmt_rub)
    """
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    s = f"{v:,.0f}".replace(",", NBSP).replace(".", ",")
    return f"{s}{NBSP}₽"


def fmt_delta_pct(v, digits=1):
    if v is None:
        return "—"
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.{digits}f}%".replace(".", ",")
