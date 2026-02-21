# corporate/reports/manufacturers_revenue_summary.py
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


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



def build_manufacturers_brief(
    years: list[int],
    revenue_rows: list[dict[str, Any]],
    *,
    exclude_unknown: bool = True,
    top_n_lists: int = 8,
) -> dict[str, Any]:
    """
    Возвращает параметры для краткой справки:
    - итого производителей
    - статусы (active/pause/stopped)
    - лидер текущего года
    - максимальный рост YoY (текущий год vs прошлый)
    - новые / возобновившие / переставшие в текущем году

    ВАЖНО:
    - годы возвращаются также строками, чтобы в шаблоне не появлялись запятые: 2026, а не 2,026
    - ожидается, что в revenue_rows у каждой строки есть:
        manufacturer_id, name, values (list[Decimal]), last (Decimal), prev (Decimal), status (str)
    - fmt_money_ru должна быть доступна в этом модуле (та же, что в manufacturers_revenue.py)
    """
    # --- пустой кейс ---
    if not years:
        return {
            "years": [],
            "start_year": None,
            "current_year": None,
            "prev_year": None,
            "start_year_str": "",
            "current_year_str": "",
            "prev_year_str": "",
            "total_manufacturers": 0,
            "status_counts": {"active": 0, "pause": 0, "stopped": 0},
            "leader": None,
            "max_yoy": None,
            "lists": {"new": [], "revived": [], "lost_this_year": []},
        }

    years_sorted = sorted(int(y) for y in years)
    start_year = years_sorted[0]
    cy = years_sorted[-1]
    py = years_sorted[-2] if len(years_sorted) >= 2 else None

    # --- фильтр строк ---
    rows = list(revenue_rows or [])
    if exclude_unknown:
        filtered = []
        for r in rows:
            mf_id = int(r.get("manufacturer_id", 0) or 0)
            name = (r.get("name") or "").strip()
            if mf_id == 0:
                continue
            if not name:
                continue
            # твой маркер неизвестного производителя: "!Производитель не указан"
            if name.startswith("!"):
                continue
            filtered.append(r)
        rows = filtered

    # --- статусы ---
    status_counts = {"active": 0, "pause": 0, "stopped": 0}
    for r in rows:
        st = (r.get("status") or "stopped").strip().lower()
        if st not in status_counts:
            st = "stopped"
        status_counts[st] += 1

    # --- helpers ---
    def to_dec(x: Any) -> Decimal:
        if isinstance(x, Decimal):
            return x
        try:
            return Decimal(str(x or "0"))
        except Exception:
            return Decimal("0")

    def last_val(r: dict[str, Any]) -> Decimal:
        # предпочтение готовому полю last, иначе берём последний из values
        if "last" in r:
            return to_dec(r.get("last"))
        vals = r.get("values") or []
        return to_dec(vals[-1]) if vals else Decimal("0")

    def prev_val(r: dict[str, Any]) -> Decimal:
        if "prev" in r:
            return to_dec(r.get("prev"))
        vals = r.get("values") or []
        return to_dec(vals[-2]) if len(vals) >= 2 else Decimal("0")

    # --- лидер текущего года ---
    leader = None
    leader_row = max(rows, key=last_val, default=None)
    if leader_row is not None:
        lv = last_val(leader_row)
        if lv > 0:
            leader = {
                "name": leader_row.get("name", "—"),
                "value": lv,
                "disp": fmt_money_ru(lv),
            }

    # --- максимальный рост YoY (cy vs py) ---
    max_yoy = None
    if py is not None:
        best_r = None
        best_delta = Decimal("0")
        best_last = Decimal("0")
        best_prev = Decimal("0")

        for r in rows:
            last = last_val(r)
            prev = prev_val(r)

            # считаем рост только если есть база сравнения
            if prev <= 0:
                continue

            delta = last - prev
            if delta > best_delta:
                best_delta = delta
                best_r = r
                best_last = last
                best_prev = prev

        if best_r is not None and best_delta > 0:
            pct = float((best_delta / best_prev) * Decimal("100")) if best_prev > 0 else None
            max_yoy = {
                "name": best_r.get("name", "—"),
                "last_disp": fmt_money_ru(best_last),
                "prev_disp": fmt_money_ru(best_prev),
                "delta_disp": fmt_money_ru(best_delta),
                "pct": pct,
            }

    # --- новые / возобновившие / потерянные ---
    new_rows: list[dict[str, Any]] = []
    revived_rows: list[dict[str, Any]] = []
    lost_this_year_rows: list[dict[str, Any]] = []

    for r in rows:
        vals_raw = r.get("values") or []
        vals: list[Decimal] = [to_dec(v) for v in vals_raw]
        if not vals:
            continue

        last = vals[-1]
        prev = vals[-2] if len(vals) >= 2 else Decimal("0")

        # “история до текущего года”
        before_current = vals[:-1]
        had_any_before = any(v > 0 for v in before_current)

        # новый = в текущем году >0, раньше всегда 0
        if last > 0 and not had_any_before:
            new_rows.append(r)

        # восстановился = в текущем >0, в прошлом 0, но когда-то раньше было >0
        if last > 0 and prev <= 0 and any(v > 0 for v in vals[:-2]):
            revived_rows.append(r)

        # перестали в текущем = в прошлом >0, в текущем 0
        if prev > 0 and last <= 0:
            lost_this_year_rows.append(r)

    # сортировки
    new_rows.sort(key=lambda rr: last_val(rr), reverse=True)
    revived_rows.sort(key=lambda rr: last_val(rr), reverse=True)
    lost_this_year_rows.sort(key=lambda rr: prev_val(rr), reverse=True)

    # упаковка списков для шаблона
    def pack_list(rr: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for r in rr[: max(0, int(top_n_lists))]:
            out.append(
                {
                    "name": (r.get("name") or "—").strip() or "—",
                    "value": fmt_money_ru(last_val(r)),
                }
            )
        return out

    def pack_lost(rr: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for r in rr[: max(0, int(top_n_lists))]:
            out.append(
                {
                    "name": (r.get("name") or "—").strip() or "—",
                    "value": fmt_money_ru(prev_val(r)),
                }
            )
        return out

    return {
        "years": years_sorted,
        "start_year": start_year,
        "current_year": cy,
        "prev_year": py,
        # строки для гарантированного вывода без “2,026”
        "start_year_str": str(start_year),
        "current_year_str": str(cy),
        "prev_year_str": str(py) if py is not None else "",
        "total_manufacturers": len(rows),
        "status_counts": status_counts,
        "leader": leader,
        "max_yoy": max_yoy,
        "lists": {
            "new": pack_list(new_rows),
            "revived": pack_list(revived_rows),
            "lost_this_year": pack_lost(lost_this_year_rows),
        },
    }