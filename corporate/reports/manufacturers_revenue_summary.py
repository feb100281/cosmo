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
    top_n_concentration: int = 5,
    # === тренды (крупняк) ===
    trend_top_n: int = 8,
    trend_peak_threshold: Decimal = Decimal("10000000"),  # 10 млн ₽
    former_leaders_year_top_n: int = 3,                   # топ-3 года
    former_leaders_take: int = 5,                         # показать 5
    low_now_threshold: Decimal = Decimal("200000"),       # "сейчас низко" <= 200 тыс ₽
) -> dict[str, Any]:
    """
    Управленческая "Краткая справка" по производителям.

    Важно про "сейчас":
      - последний год в данных (cy) трактуем как YTD, если отчет строится в течение года.
      - тренды считаем по "закрытым годам": years_sorted[:-1] (например 2022–2025),
        а cy (например 2026) не используем для тренда.

    Ожидается, что revenue_rows содержит строки:
      manufacturer_id, name, values (list[Decimal]), last (Decimal), prev (Decimal), status (str)

    Добавлено:
      - Total revenue CY/PY + YoY
      - Avg/Median revenue per ACTIVE in CY
      - Concentration: leader share, top-5 share
      - Churn impact: lost_this_year prev revenue sum + share
      - Long-term trends (closed years only):
          * steady_decline (monotonic down 2022–2025)
          * former_leaders (top in a closed year, now low / stopped)
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
            "last_closed_year_str": "",
            "total_manufacturers": 0,
            "status_counts": {"active": 0, "pause": 0, "stopped": 0},
            "leader": None,
            "max_yoy": None,
            "totals": None,
            "concentration": None,
            "efficiency": None,
            "churn": None,
            "notes": {"cy_is_ytd": False},
            "lists": {
                "new": [],
                "revived": [],
                "lost_this_year": [],
                "steady_decline": [],
                "former_leaders": [],
            },
        }

    # --- helpers ---
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

    def last_val(r: dict[str, Any]) -> Decimal:
        if "last" in r:
            return to_dec(r.get("last"))
        vals = r.get("values") or []
        return to_dec(vals[-1]) if vals else Decimal("0")

    def prev_val(r: dict[str, Any]) -> Decimal:
        if "prev" in r:
            return to_dec(r.get("prev"))
        vals = r.get("values") or []
        return to_dec(vals[-2]) if len(vals) >= 2 else Decimal("0")

    def safe_pct(delta: Decimal, base: Decimal) -> float | None:
        if base <= 0:
            return None
        return float((delta / base) * Decimal("100"))

    # --- years ---
    years_sorted = sorted(int(y) for y in years)
    start_year = years_sorted[0]
    cy = years_sorted[-1]
    py = years_sorted[-2] if len(years_sorted) >= 2 else None

    closed_years = years_sorted[:-1]  # тренды только по закрытым
    last_closed_year = closed_years[-1] if closed_years else None

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

    # --- статусы ---
    status_counts = {"active": 0, "pause": 0, "stopped": 0}
    for r in rows:
        st = norm_name(r.get("status") or "stopped").lower()
        if st not in status_counts:
            st = "stopped"
        status_counts[st] += 1

    # --- лидер текущего года (cy / YTD) ---
    leader = None
    leader_row = max(rows, key=last_val, default=None)
    if leader_row is not None:
        lv = last_val(leader_row)
        if lv > 0:
            leader = {
                "name": norm_name(leader_row.get("name")) or "—",
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
            if prev <= 0:
                continue
            delta = last - prev
            if delta > best_delta:
                best_delta = delta
                best_r = r
                best_last = last
                best_prev = prev

        if best_r is not None and best_delta > 0:
            max_yoy = {
                "name": norm_name(best_r.get("name")) or "—",
                "last_disp": fmt_money_ru(best_last),
                "prev_disp": fmt_money_ru(best_prev),
                "delta_disp": fmt_money_ru(best_delta),
                "pct": safe_pct(best_delta, best_prev),
            }

    # --- новые / возобновившие / потерянные ---
    new_rows: list[dict[str, Any]] = []
    revived_rows: list[dict[str, Any]] = []
    lost_this_year_rows: list[dict[str, Any]] = []

    for r in rows:
        vals = vals_list(r)
        if not vals:
            continue

        last = vals[-1]
        prev = vals[-2] if len(vals) >= 2 else Decimal("0")
        before_current = vals[:-1]
        had_any_before = any(v > 0 for v in before_current)

        if last > 0 and not had_any_before:
            new_rows.append(r)

        if last > 0 and prev <= 0 and any(v > 0 for v in vals[:-2]):
            revived_rows.append(r)

        if prev > 0 and last <= 0:
            lost_this_year_rows.append(r)

    new_rows.sort(key=lambda rr: last_val(rr), reverse=True)
    revived_rows.sort(key=lambda rr: last_val(rr), reverse=True)
    lost_this_year_rows.sort(key=lambda rr: prev_val(rr), reverse=True)

    # --- итоги по выручке CY/PY + YoY ---
    total_cy = sum((last_val(r) for r in rows), Decimal("0"))
    total_py = sum((prev_val(r) for r in rows), Decimal("0")) if py is not None else Decimal("0")
    total_delta = total_cy - total_py
    total_pct = safe_pct(total_delta, total_py) if py is not None else None

    totals = {
        "cy": total_cy,
        "py": total_py,
        "delta": total_delta,
        "pct": total_pct,
        "cy_disp": fmt_money_ru(total_cy),
        "py_disp": fmt_money_ru(total_py) if py is not None else "",
        "delta_disp": fmt_money_ru(total_delta.copy_abs()),
        "sign": "+" if total_delta >= 0 else "−",
    }

    # --- эффективность: средняя/медианная выручка на активного в CY (YTD) ---
    active_rows = [r for r in rows if norm_name(r.get("status")).lower() == "active" and last_val(r) > 0]
    active_vals = sorted([last_val(r) for r in active_rows if last_val(r) > 0])

    avg_active = (sum(active_vals, Decimal("0")) / Decimal(len(active_vals))) if active_vals else Decimal("0")
    median_active = Decimal("0")
    if active_vals:
        n = len(active_vals)
        mid = n // 2
        if n % 2 == 1:
            median_active = active_vals[mid]
        else:
            median_active = (active_vals[mid - 1] + active_vals[mid]) / Decimal("2")

    efficiency = {
        "active_cnt": len(active_rows),
        "avg": avg_active,
        "median": median_active,
        "avg_disp": fmt_money_ru(avg_active) if avg_active else "0\u00A0₽",
        "median_disp": fmt_money_ru(median_active) if median_active else "0\u00A0₽",
    }

    # --- концентрация: доля лидера и доля топ-N в CY (YTD) ---
    concentration = None
    if total_cy > 0:
        sorted_by_last = sorted(rows, key=last_val, reverse=True)
        topn = sorted_by_last[: max(1, int(top_n_concentration))]
        topn_sum = sum((last_val(r) for r in topn), Decimal("0"))
        leader_share = float((leader["value"] / total_cy) * Decimal("100")) if leader and leader.get("value") else 0.0
        topn_share = float((topn_sum / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

        concentration = {
            "leader_share": leader_share,
            "topn": int(top_n_concentration),
            "topn_share": topn_share,
        }

    # --- churn impact: потерянные (их вклад в PY) ---
    churn = None
    if py is not None and total_py > 0:
        lost_prev_sum = sum((prev_val(r) for r in lost_this_year_rows), Decimal("0"))
        lost_prev_share = float((lost_prev_sum / total_py) * Decimal("100")) if total_py > 0 else 0.0

        churn = {
            "lost_cnt": len(lost_this_year_rows),
            "lost_prev_sum": lost_prev_sum,
            "lost_prev_sum_disp": fmt_money_ru(lost_prev_sum) if lost_prev_sum else "0\u00A0₽",
            "lost_prev_share": lost_prev_share,
        }

    # ============================================================
    #  ТРЕНДЫ ПО ЗАКРЫТЫМ ГОДАМ (например 2022–2025)
    # ============================================================

    # индекс года -> позиция в values
    # предполагаем, что values идут в порядке years_sorted
    # т.е. values[i] соответствует years_sorted[i]
    year_to_idx = {int(y): i for i, y in enumerate(years_sorted)}

    def get_year_value(r: dict[str, Any], year: int) -> Decimal:
        vals = vals_list(r)
        i = year_to_idx.get(int(year))
        if i is None or i < 0 or i >= len(vals):
            return Decimal("0")
        return vals[i]

    def peak_closed(r: dict[str, Any]) -> Decimal:
        if not closed_years:
            return Decimal("0")
        return max((get_year_value(r, y) for y in closed_years), default=Decimal("0"))

    # --- 1) Устойчивое снижение 2022–2025 (монотонно вниз, крупняк) ---
    steady_decline_candidates = []
    if len(closed_years) >= 3:
        for r in rows:
            pk = peak_closed(r)
            if pk < trend_peak_threshold:
                continue

            series = [get_year_value(r, y) for y in closed_years]
            # монотонно убывает и старт значимый
            is_down = all(series[i] >= series[i + 1] for i in range(len(series) - 1))
            if not is_down:
                continue

            first = series[0]
            last_closed = series[-1]
            if first <= 0:
                continue

            drop_abs = first - last_closed
            drop_pct = safe_pct(drop_abs, first)  # %

            # 2026 (YTD) для справки
            now_val = get_year_value(r, cy)
            steady_decline_candidates.append({
                "name": norm_name(r.get("name")) or "—",
                "first_year": str(closed_years[0]),
                "last_closed_year": str(closed_years[-1]),
                "first_disp": fmt_money_ru(first),
                "last_closed_disp": fmt_money_ru(last_closed),
                "drop_disp": fmt_money_ru(drop_abs.copy_abs()),
                "drop_pct": drop_pct,
                "now_year": str(cy),
                "now_disp": fmt_money_ru(now_val) if now_val else "0\u00A0₽",
                "score": drop_abs,  # сортировка по абсолютному падению
                "first_val": first,
                "last_closed_val": last_closed,
                "now_val": now_val,
            })

        steady_decline_candidates.sort(key=lambda x: (x["score"]), reverse=True)

    steady_decline = steady_decline_candidates[: max(0, int(trend_top_n))]

    # --- 2) Бывшие лидеры (топ года в закрытых годах, а сейчас низко/0/стоп) ---
    former_leaders = []
    if closed_years and last_closed_year is not None:
        # Соберем топ по каждому закрытому году
        top_per_year: dict[int, list[dict[str, Any]]] = {}
        for y in closed_years:
            ranked = sorted(rows, key=lambda r: get_year_value(r, y), reverse=True)
            top_per_year[y] = ranked[: max(1, int(former_leaders_year_top_n))]

        # Уникальные кандидаты
        seen = set()
        candidates = []
        for y, top_rows in top_per_year.items():
            for r in top_rows:
                mf_id = int(r.get("manufacturer_id", 0) or 0)
                if mf_id in seen:
                    continue
                seen.add(mf_id)

                peak_y = y
                peak_val = get_year_value(r, y)
                now_val = get_year_value(r, cy)
                st = norm_name(r.get("status") or "").lower()

                # условие "сейчас низко": либо <= порога, либо stopped
                if not (now_val <= low_now_threshold or st == "stopped"):
                    continue

                candidates.append({
                    "name": norm_name(r.get("name")) or "—",
                    "peak_year": str(peak_y),
                    "peak_disp": fmt_money_ru(peak_val),
                    "now_year": str(cy),
                    "now_disp": fmt_money_ru(now_val) if now_val else "0\u00A0₽",
                    "status": st or "—",
                    "delta_abs": (peak_val - now_val),
                    "delta_pct": safe_pct((peak_val - now_val), peak_val) if peak_val > 0 else None,
                })

        # сортируем по потере абсолютной (бывшие крупные)
        candidates.sort(key=lambda x: (x["delta_abs"]), reverse=True)
        former_leaders = candidates[: max(0, int(former_leaders_take))]

    # --- упаковка списков для шаблона ---
    def pack_list(rr: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for r in rr[: max(0, int(top_n_lists))]:
            out.append({"name": norm_name(r.get("name")) or "—", "value": fmt_money_ru(last_val(r))})
        return out

    def pack_lost(rr: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for r in rr[: max(0, int(top_n_lists))]:
            out.append({"name": norm_name(r.get("name")) or "—", "value": fmt_money_ru(prev_val(r))})
        return out

    return {
        "years": years_sorted,
        "start_year": start_year,
        "current_year": cy,
        "prev_year": py,
        "start_year_str": str(start_year),
        "current_year_str": str(cy),
        "prev_year_str": str(py) if py is not None else "",
        "last_closed_year_str": str(last_closed_year) if last_closed_year is not None else "",
        "notes": {
            "cy_is_ytd": True,  # трактуем последний год как YTD
        },
        "total_manufacturers": len(rows),
        "status_counts": status_counts,
        "leader": leader,
        "max_yoy": max_yoy,
        "totals": totals,
        "efficiency": efficiency,
        "concentration": concentration,
        "churn": churn,
        "lists": {
            "new": pack_list(new_rows),
            "revived": pack_list(revived_rows),
            "lost_this_year": pack_lost(lost_this_year_rows),
            "steady_decline": steady_decline,
            "former_leaders": former_leaders,
        },
    }