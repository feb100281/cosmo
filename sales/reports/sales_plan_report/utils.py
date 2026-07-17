from decimal import Decimal


def to_decimal(value):
    return Decimal(str(value or 0))


def fmt_money(value):
    value = to_decimal(value)
    return f"{float(value):,.0f}".replace(",", " ")


def fmt_money_short(value):
    """Короткий формат: млн, тыс."""
    value = to_decimal(value)

    if abs(value) >= Decimal("1000000"):
        return f"{float(value / Decimal('1000000')):.1f} млн"

    if abs(value) >= Decimal("1000"):
        return f"{float(value / Decimal('1000')):.0f} тыс."

    return f"{float(value):,.0f}".replace(",", " ")


def fmt_pct(value):
    value = to_decimal(value)
    return f"{float(value):.0f}%"


def safe_div(a, b):
    a = to_decimal(a)
    b = to_decimal(b)
    if b == 0:
        return Decimal("0")
    return a / b


def normalize_store_name(value):
    if not value:
        return ""
    return str(value).strip().lower()