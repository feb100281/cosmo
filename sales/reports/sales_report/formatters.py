import numpy as np

def fmt_money(v) -> str:
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    abs_v = abs(v)

    nbsp = "\u00A0"   # неразрывный пробел

    if abs_v >= 1_000_000:
        s = f"{v / 1_000_000:,.1f}".replace(",", nbsp).replace(".", ",")
        return f"{s}{nbsp}млн{nbsp}₽"

    if abs_v >= 1_000:
        s = f"{v / 1_000:,.0f}".replace(",", nbsp)
        return f"{s}{nbsp}тыс{nbsp}₽"

    s = f"{v:,.0f}".replace(",", nbsp)
    return f"{s}{nbsp}₽"


def fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        nbsp = "\u00A0"   # неразрывный пробел
        return f"{int(v):,}".replace(",", nbsp)
    except Exception:
        return "—"


def fmt_pct(v, digits: int = 1) -> str:
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    if -1.0 <= v <= 1.0:
        v *= 100
    s = f"{v:.{digits}f}".replace(".", ",")
    return f"{s}%"

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
    if v is None:
        return "—"
    return fmt_money(abs(v))


def fmt_delta_int(v):
    if v is None:
        return "—"
    return fmt_int(abs(v))

def fmt_delta_pct(v, digits=1):
    if v is None:
        return "—"
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.{digits}f}%".replace(".", ",")


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
