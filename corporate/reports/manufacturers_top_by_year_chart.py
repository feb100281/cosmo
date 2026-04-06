# corporate/reports/manufacturers_top_by_year_chart.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

# Если хочешь переиспользовать fmt_money_ru из твоего файла — можно импортом.
# from .manufacturers_revenue_summary import fmt_money_ru

def _quant0(v: Decimal) -> Decimal:
    return v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

def fmt_money_ru(v: Decimal) -> str:
    """
    12,3 млн ₽
    450 тыс ₽
    12 345 ₽
    """
    vq = _quant0(v)
    a = abs(vq)
    nbsp = "\u00A0"

    if a >= Decimal("1000000"):
        s = (vq / Decimal("1000000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{str(s).replace('.', ',')}{nbsp}млн{nbsp}₽"

    if a >= Decimal("1000"):
        s = (vq / Decimal("1000")).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP)
        txt = f"{int(s):,}".replace(",", " ")
        return f"{txt}{nbsp}тыс{nbsp}₽"

    txt = f"{int(vq):,}".replace(",", " ")
    return f"{txt}{nbsp}₽"


def build_top_manufacturers_by_year(
    years: list[int],
    revenue_rows: list[dict[str, Any]],
    *,
    start_year: int = 2022,
    top_n: int = 5,
    exclude_unknown: bool = False,
    include_share: bool = True,
) -> dict[str, Any]:
    """
    Топ-N производителей по каждому году.

    Важно:
    - предполагаем, что r["values"][i] соответствует years_sorted[i]
      (как и в твоем текущем коде).
    - start_year=2022: берем годы >= 2022, которые есть в years.
    """

    def to_dec(x: Any) -> Decimal:
        if isinstance(x, Decimal):
            return x
        try:
            return Decimal(str(x or "0"))
        except Exception:
            return Decimal("0")

    def norm_name(s: Any) -> str:
        return (str(s or "")).strip()

    def vals_list(r: dict[str, Any]) -> list[Decimal]:
        raw = r.get("values") or []
        return [to_dec(v) for v in raw]

    # --- years ---
    years_sorted = sorted(int(y) for y in (years or []))
    years_use = [y for y in years_sorted if y >= int(start_year)]
    if not years_use:
        return {
            "years": [],
            "top_n": int(top_n),
            "per_year": [],
            "notes": {"start_year": int(start_year)},
        }

    year_to_idx = {int(y): i for i, y in enumerate(years_sorted)}

    def get_year_value(r: dict[str, Any], year: int) -> Decimal:
        vals = vals_list(r)
        i = year_to_idx.get(int(year))
        if i is None or i < 0 or i >= len(vals):
            return Decimal("0")
        return vals[i]

    # --- фильтр строк ---
    rows = list(revenue_rows or [])
    if exclude_unknown:
        filtered = []
        for r in rows:
            mf_id = int(r.get("manufacturer_id", 0) or 0)
            name = norm_name(r.get("name"))
            if mf_id == 0:
                continue
            if not name:
                continue
            if name.startswith("!"):
                continue
            filtered.append(r)
        rows = filtered

    # --- расчет топов по годам ---
    per_year: list[dict[str, Any]] = []

    for y in years_use:
        ranked = sorted(rows, key=lambda r: get_year_value(r, y), reverse=True)

        # total по году (для долей)
        total_y = sum((get_year_value(r, y) for r in rows), Decimal("0"))

        top_rows = []
        place = 0
        for r in ranked:
            val = get_year_value(r, y)
            if val <= 0:
                continue
            place += 1
            if place > int(top_n):
                break

            share = None
            if include_share and total_y > 0:
                share = float((val / total_y) * Decimal("100"))

            top_rows.append({
                "rank": place,
                "manufacturer_id": int(r.get("manufacturer_id", 0) or 0),
                "name": norm_name(r.get("name")) or "—",
                "value": val,
                "value_disp": fmt_money_ru(val),
                "share_pct": share,  # float | None
            })

        per_year.append({
            "year": int(y),
            "total": total_y,
            "total_disp": fmt_money_ru(total_y) if total_y else "0\u00A0₽",
            "items": top_rows,
        })

    return {
        "years": years_use,
        "top_n": int(top_n),
        "per_year": per_year,
        "notes": {"start_year": int(start_year)},
    }


# -------------------------------
# (опционально) matplotlib plot
# -------------------------------
def render_top_by_year_matplotlib(
    top_data: dict[str, Any],
    *,
    max_name_len: int = 26,
):
    """
    Рендер "small multiples": по одному горизонтальному барчарту на год.
    Возвращает (fig, ax_list).
    """
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        raise RuntimeError("matplotlib is required for rendering") from e

    per_year = top_data.get("per_year") or []
    if not per_year:
        fig = plt.figure()
        return fig, []

    n = len(per_year)
    # один столбец, n строк — читабельно и очень управленчески
    fig_h = max(2.6, n * 2.2)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(10, fig_h))
    if n == 1:
        axes = [axes]

    for ax, block in zip(axes, per_year):
        y = block["year"]
        items = block.get("items") or []

        names = [i["name"] for i in items]
        vals = [i["value"] for i in items]

        # укоротим длинные названия
        def cut(s: str) -> str:
            s = s or ""
            return s if len(s) <= max_name_len else s[: max_name_len - 1] + "…"

        names = [cut(s) for s in names]

        ax.barh(names[::-1], vals[::-1])  # top-1 сверху
        ax.set_title(f"Топ-{top_data.get('top_n', 5)} производителей — {y}")
        ax.grid(True, axis="x", linestyle=":", linewidth=0.6)
        ax.tick_params(axis="y", labelsize=9)

        # подписи значений справа
        for nme, v in zip(names[::-1], vals[::-1]):
            ax.text(v, nme, f"  {fmt_money_ru(v)}", va="center", fontsize=9)

    fig.tight_layout()
    return fig, axes