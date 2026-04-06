# # corporate/reports/manufacturers_lost_chart.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any

# def build_lost_manufacturers_svg(
#     revenue_rows: list[dict[str, Any]],
#     years: list[int],
#     *,
#     top_n: int = 15,
#     exclude_unknown: bool = True,   # исключить manufacturer_id=0
# ) -> str | None:
#     """
#     Горизонтальный бар-чарт (SVG): топ производителей с большими продажами раньше,
#     но сейчас статус pause/stopped.

#     revenue_rows — то, что возвращает get_manufacturers_net_by_year (rows)
#     years — список лет из get_manufacturers_net_by_year
#     """

#     if not revenue_rows or not years:
#         return None

#     # ---- настройки периода ----
#     last_year = years[-1]
#     prev_year = years[-2] if len(years) >= 2 else None

#     # ---- собрать кандидатов ----
#     items: list[dict[str, Any]] = []

#     for r in revenue_rows:
#         mf_id = int(r.get("manufacturer_id") or 0)
#         if exclude_unknown and mf_id == 0:
#             continue

#         status = r.get("status")
#         if status not in ("pause", "stopped"):
#             continue

#         by_year: dict[int, Decimal] = r.get("by_year", {}) or {}

#         # “раньше” = всё, кроме последнего года (и, по желанию, включая prev)
#         last = Decimal("0")
#         prev = Decimal("0")
#         past = Decimal("0")

#         for y, v in by_year.items():
#             v = v if isinstance(v, Decimal) else Decimal(str(v or 0))
#             if y == last_year:
#                 last += v
#             elif prev_year is not None and y == prev_year:
#                 prev += v
#                 past += v   # ← прошлый год включаем в “раньше” (так логичнее для потерь)
#             else:
#                 past += v

#         # sanity: если “раньше” было мало — не интересно
#         if past <= 0:
#             continue

#         items.append(
#             {
#                 "name": r.get("name") or "—",
#                 "status": status,
#                 "past": past,
#                 "prev": prev,
#                 "last": last,
#             }
#         )

#     if not items:
#         return None

#     items.sort(key=lambda x: x["past"], reverse=True)
#     items = items[:top_n]

#     # ---- SVG chart ----
#     import matplotlib
#     matplotlib.use("Agg")
#     import matplotlib.pyplot as plt
#     from matplotlib.ticker import FuncFormatter

#     def fmt_axis(v, _pos=None):
#         # деловой формат для оси: млн / тыс / ₽
#         v = float(v or 0)
#         a = abs(v)
#         if a >= 1_000_000:
#             return f"{v/1_000_000:.1f} млн"
#         if a >= 1_000:
#             return f"{v/1_000:.0f} тыс"
#         return f"{v:.0f}"

#     # размеры: под top_n
#     # (высота зависит от строк — чтобы не слипалось)
#     h = max(3.2, 0.32 * len(items) + 1.4)
#     fig = plt.figure(figsize=(12.2, h), dpi=150)
#     ax = fig.add_subplot(111)
#     fig.patch.set_facecolor("white")
#     ax.set_facecolor("white")

#     names = [it["name"] for it in items][::-1]
#     vals = [float(it["past"]) for it in items][::-1]
#     statuses = [it["status"] for it in items][::-1]

#     # один базовый цвет + различие по статусу (делово)
#     # pause — оранжевый, stopped — красноватый
#     colors = []
#     for st in statuses:
#         if st == "pause":
#             colors.append((0.96, 0.62, 0.11, 0.85))   # amber-ish
#         else:
#             colors.append((0.94, 0.27, 0.27, 0.80))   # red-ish

#     y = list(range(len(names)))
#     ax.barh(y, vals, height=0.62, color=colors, edgecolor=(0, 0, 0, 0.08), linewidth=0.8)

#     ax.set_yticks(y)
#     ax.set_yticklabels(names, fontsize=9, fontweight="bold")
#     ax.xaxis.set_major_formatter(FuncFormatter(fmt_axis))

#     title = f"Топ производителей (потерянные): большие продажи раньше, сейчас пауза/перестали"
#     subtitle = f"Период анализа: {years[0]}–{years[-1]} | Исключён: «Производитель не указан»"
#     ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=14)

#     # “подзаголовок” мелким текстом
#     ax.text(
#         0.0, 1.01, subtitle,
#         transform=ax.transAxes,
#         fontsize=9,
#         color="#6b7280",
#         ha="left",
#         va="bottom"
#     )

#     # сетка по X деловая
#     ax.grid(axis="x", alpha=0.15)
#     ax.set_axisbelow(True)

#     # подписи справа от баров (Past значение)
#     maxv = max(vals) or 1.0
#     for yi, v in enumerate(vals):
#         ax.text(
#             v + maxv * 0.01,
#             yi,
#             fmt_axis(v),
#             va="center",
#             ha="left",
#             fontsize=9,
#             color="#111827",
#         )

#     # убрать рамки
#     for spine in ["top", "right", "left"]:
#         ax.spines[spine].set_visible(False)
#     ax.spines["bottom"].set_alpha(0.2)

#     ax.tick_params(axis="x", labelsize=9)
#     ax.tick_params(axis="y", length=0)

#     fig.tight_layout(pad=1.0)

#     import io
#     buf = io.StringIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight")
#     plt.close(fig)

#     svg = buf.getvalue()

#     # лёгкая чистка: иногда matplotlib вставляет <?xml ...> — можно оставить, но HTML норм и без него
#     # svg = svg.replace('<?xml version="1.0" encoding="utf-8" standalone="no"?>', '')
#     return svg





# corporate/reports/manufacturers_lost_chart.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any


# def build_lost_manufacturers_svg(
#     revenue_rows: list[dict[str, Any]],
#     years: list[int],
#     *,
#     top_n: int = 15,
#     exclude_unknown: bool = True,
# ) -> str | None:
#     if not revenue_rows or not years:
#         return None

#     last_year = years[-1]
#     prev_year = years[-2] if len(years) >= 2 else None

#     items: list[dict[str, Any]] = []

#     for r in revenue_rows:
#         mf_id = int(r.get("manufacturer_id") or 0)
#         if exclude_unknown and mf_id == 0:
#             continue

#         status = r.get("status")
#         if status not in ("pause", "stopped"):
#             continue

#         by_year: dict[int, Decimal] = r.get("by_year", {}) or {}

#         last = Decimal("0")
#         prev = Decimal("0")
#         past = Decimal("0")

#         for y, v in by_year.items():
#             v = v if isinstance(v, Decimal) else Decimal(str(v or 0))
#             if y == last_year:
#                 last += v
#             elif prev_year is not None and y == prev_year:
#                 prev += v
#                 past += v
#             else:
#                 past += v

#         if past <= 0:
#             continue

#         items.append(
#             {
#                 "name": r.get("name") or "—",
#                 "status": status,
#                 "past": past,
#                 "prev": prev,
#                 "last": last,
#             }
#         )

#     if not items:
#         return None

#     items.sort(key=lambda x: x["past"], reverse=True)
#     items = items[:top_n]

#     # ---- plotting to SVG ----
#     import matplotlib
#     matplotlib.use("Agg")
#     import matplotlib.pyplot as plt
#     from matplotlib.ticker import FuncFormatter

#     def fmt_axis(v, _pos=None):
#         v = float(v or 0)
#         a = abs(v)
#         if a >= 1_000_000:
#             return f"{v/1_000_000:.1f} млн"
#         if a >= 1_000:
#             return f"{v/1_000:.0f} тыс"
#         return f"{v:.0f}"

#     def fmt_value(v: float) -> str:
#         a = abs(v)
#         if a >= 1_000_000:
#             return f"{v/1_000_000:.1f} млн"
#         if a >= 1_000:
#             return f"{v/1_000:.0f} тыс"
#         return f"{v:.0f}"

#     # summary (по всем items в топе)
#     pause_cnt = sum(1 for it in items if it["status"] == "pause")
#     stop_cnt = sum(1 for it in items if it["status"] == "stopped")
#     pause_sum = float(sum(it["past"] for it in items if it["status"] == "pause"))
#     stop_sum = float(sum(it["past"] for it in items if it["status"] == "stopped"))

#     # figure size
#     h = max(3.4, 0.34 * len(items) + 1.7)
#     fig = plt.figure(figsize=(12.2, h), dpi=150)
#     ax = fig.add_subplot(111)
#     fig.patch.set_facecolor("white")
#     ax.set_facecolor("white")

#     names = [it["name"] for it in items][::-1]
#     vals = [float(it["past"]) for it in items][::-1]
#     prev_vals = [float(it["prev"]) for it in items][::-1]
#     last_vals = [float(it["last"]) for it in items][::-1]
#     statuses = [it["status"] for it in items][::-1]

#     # цвета (деловые)
#     colors = []
#     for st in statuses:
#         if st == "pause":
#             colors.append((0.96, 0.62, 0.11, 0.85))  # amber
#         else:
#             colors.append((0.94, 0.27, 0.27, 0.80))  # red

#     y = list(range(len(names)))
#     ax.barh(y, vals, height=0.62, color=colors, edgecolor=(0, 0, 0, 0.08), linewidth=0.8)

#     ax.set_yticks(y)
#     ax.set_yticklabels(names, fontsize=9, fontweight="bold")
#     ax.xaxis.set_major_formatter(FuncFormatter(fmt_axis))

#     title = "Топ потерянных производителей: большие продажи раньше, сейчас пауза/перестали"
#     subtitle = f"Период: {years[0]}–{years[-1]} | Исключён: «Производитель не указан»"
#     ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=18)
#     ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, fontsize=9, color="#6b7280",
#             ha="left", va="bottom")

#     # мини-сводка (очень помогает руководству)
#     sumline = f"Пауза: {pause_cnt} (≈ {fmt_value(pause_sum)})   •   Перестали: {stop_cnt} (≈ {fmt_value(stop_sum)})"
#     ax.text(0.0, 0.985, sumline, transform=ax.transAxes, fontsize=9, color="#111827",
#             ha="left", va="bottom")

#     ax.grid(axis="x", alpha=0.15)
#     ax.set_axisbelow(True)

#     maxv = max(vals) or 1.0

#     # подписи справа + “когда отвалились” (prev/last)
#     for yi, v in enumerate(vals):
#         ax.text(
#             v + maxv * 0.012,
#             yi + 0.10,
#             fmt_value(v),
#             va="center",
#             ha="left",
#             fontsize=9,
#             color="#111827",
#             fontweight="bold",
#         )
#         # мелко: прошлый/текущий год
#         if prev_year is not None:
#             tail = f"{prev_year}: {fmt_value(prev_vals[yi])} | {last_year}: {fmt_value(last_vals[yi])}"
#         else:
#             tail = f"{last_year}: {fmt_value(last_vals[yi])}"
#         ax.text(
#             v + maxv * 0.012,
#             yi - 0.18,
#             tail,
#             va="center",
#             ha="left",
#             fontsize=8,
#             color="#6b7280",
#         )

#     for spine in ["top", "right", "left"]:
#         ax.spines[spine].set_visible(False)
#     ax.spines["bottom"].set_alpha(0.2)

#     ax.tick_params(axis="x", labelsize=9)
#     ax.tick_params(axis="y", length=0)

#     fig.tight_layout(pad=1.0)

#     import io
#     buf = io.StringIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight")
#     plt.close(fig)

#     return buf.getvalue()


# corporate/reports/manufacturers_lost_chart.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any


# def build_lost_manufacturers_svg(
#     revenue_rows: list[dict[str, Any]],
#     years: list[int],
#     *,
#     top_n: int = 15,
#     exclude_unknown: bool = True,  # исключить manufacturer_id=0
# ) -> str | None:
#     """
#     SVG bar chart (для PDF):
#     Top потерянных производителей (pause/stopped) по суммарной выручке "раньше"
#     за период years[0]..years[-1].

#     На строке:
#       - бар = Past (накопленная выручка "раньше")
#       - справа: значение Past
#       - ниже мелко: последняя отгрузка + активные годы X/Y

#     Исключает "Производитель не указан" (manufacturer_id=0), если exclude_unknown=True.
#     """

#     if not revenue_rows or not years:
#         return None

#     last_year = years[-1]
#     prev_year = years[-2] if len(years) >= 2 else None
#     period_len = len(years)

#     items: list[dict[str, Any]] = []

#     for r in revenue_rows:
#         mf_id = int(r.get("manufacturer_id") or 0)
#         if exclude_unknown and mf_id == 0:
#             continue

#         status = r.get("status")
#         if status not in ("pause", "stopped"):
#             continue

#         by_year: dict[int, Decimal] = r.get("by_year", {}) or {}

#         last = Decimal("0")
#         prev = Decimal("0")
#         past = Decimal("0")

#         # активные годы в рассматриваемом периоде (years)
#         active_years_cnt = 0
#         last_active_year = None

#         # считаем last_active_year строго по years (не по by_year keys)
#         for y in years:
#             v = by_year.get(y, Decimal("0"))
#             v = v if isinstance(v, Decimal) else Decimal(str(v or 0))

#             if v > 0:
#                 active_years_cnt += 1
#                 last_active_year = y  # т.к. идём по возрастанию, последним останется самый поздний

#             if y == last_year:
#                 last += v
#             elif prev_year is not None and y == prev_year:
#                 prev += v
#                 past += v  # включаем прошлый год в "раньше" (так честнее для потерь)
#             else:
#                 past += v

#         if past <= 0:
#             continue

#         items.append(
#             {
#                 "name": (r.get("name") or "—").strip() or "—",
#                 "status": status,
#                 "past": past,
#                 "active_years_cnt": active_years_cnt,
#                 "period_len": period_len,
#                 "last_active_year": last_active_year,
#             }
#         )

#     if not items:
#         return None

#     items.sort(key=lambda x: x["past"], reverse=True)
#     items = items[:top_n]

#     # ---- plotting to SVG ----
#     import matplotlib
#     matplotlib.use("Agg")
#     import matplotlib.pyplot as plt
#     from matplotlib.ticker import FuncFormatter

#     def fmt_axis(v, _pos=None):
#         v = float(v or 0)
#         a = abs(v)
#         if a >= 1_000_000:
#             return f"{v/1_000_000:.1f} млн"
#         if a >= 1_000:
#             return f"{v/1_000:.0f} тыс"
#         return f"{v:.0f}"

#     def fmt_value(v: float) -> str:
#         a = abs(v)
#         if a >= 1_000_000:
#             return f"{v/1_000_000:.1f} млн"
#         if a >= 1_000:
#             return f"{v/1_000:.0f} тыс"
#         return f"{v:.0f}"

#     # summary по топу
#     pause_cnt = sum(1 for it in items if it["status"] == "pause")
#     stop_cnt = sum(1 for it in items if it["status"] == "stopped")
#     pause_sum = float(sum(it["past"] for it in items if it["status"] == "pause"))
#     stop_sum = float(sum(it["past"] for it in items if it["status"] == "stopped"))
#     total_sum = float(sum(it["past"] for it in items))

#     # размер
#     h = max(3.4, 0.34 * len(items) + 1.8)
#     fig = plt.figure(figsize=(12.2, h), dpi=150)
#     ax = fig.add_subplot(111)
#     fig.patch.set_facecolor("white")
#     ax.set_facecolor("white")

#     # данные (в обратном порядке для barh)
#     items_r = items[::-1]
#     names = [it["name"] for it in items_r]
#     vals = [float(it["past"]) for it in items_r]
#     statuses = [it["status"] for it in items_r]
#     last_active_years = [it["last_active_year"] for it in items_r]
#     active_years = [it["active_years_cnt"] for it in items_r]

#     # основной цвет баров — один (деловой)
#     bar_color = (0.96, 0.69, 0.29, 0.85)   # спокойный янтарный
#     edge_color = (0, 0, 0, 0.08)

#     # индикаторы статуса (узкая метка слева)
#     # pause — янтарный потемнее, stopped — приглушённый красный
#     status_color_pause = (0.93, 0.55, 0.06, 0.95)
#     status_color_stop = (0.86, 0.20, 0.20, 0.90)

#     y = list(range(len(names)))
#     bars = ax.barh(y, vals, height=0.62, color=bar_color, edgecolor=edge_color, linewidth=0.8)

#     # тонкая статусная полоска слева (как “BI”)
#     for yi, st in enumerate(statuses):
#         c = status_color_pause if st == "pause" else status_color_stop
#         ax.plot([0, 0], [yi - 0.31, yi + 0.31], color=c, linewidth=4, solid_capstyle="round", zorder=5)

#     ax.set_yticks(y)
#     ax.set_yticklabels(names, fontsize=9, fontweight="bold")
#     ax.xaxis.set_major_formatter(FuncFormatter(fmt_axis))

#     title = "Топ потерянных производителей (выручка за период до остановки)"
#     subtitle = f"Период: {years[0]}–{years[-1]} | Показана суммарная выручка за период | Исключён: «Производитель не указан»"
#     ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=18)
#     ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, fontsize=9, color="#6b7280",
#             ha="left", va="bottom")

#     sumline = (
#         f"Итого потерь (Top-{len(items)}): ≈ {fmt_value(total_sum)}   •   "
#         f"Пауза: {pause_cnt} (≈ {fmt_value(pause_sum)})   •   "
#         f"Перестали: {stop_cnt} (≈ {fmt_value(stop_sum)})"
#     )
#     ax.text(0.0, 0.985, sumline, transform=ax.transAxes, fontsize=9, color="#111827",
#             ha="left", va="bottom")

#     # сетка
#     ax.grid(axis="x", alpha=0.15)
#     ax.set_axisbelow(True)

#     maxv = max(vals) or 1.0

#     # подписи справа
#     for yi, v in enumerate(vals):
#         ax.text(
#             v + maxv * 0.012,
#             yi + 0.10,
#             fmt_value(v),
#             va="center",
#             ha="left",
#             fontsize=9,
#             color="#111827",
#             fontweight="bold",
#         )

#         lay = last_active_years[yi]
#         ay = active_years[yi]
#         tail = f"последняя отгрузка: {lay or '—'}  |  активные годы: {ay}/{period_len}"

#         ax.text(
#             v + maxv * 0.012,
#             yi - 0.18,
#             tail,
#             va="center",
#             ha="left",
#             fontsize=8,
#             color="#6b7280",
#         )

#     # оси/рамки
#     for spine in ["top", "right", "left"]:
#         ax.spines[spine].set_visible(False)
#     ax.spines["bottom"].set_alpha(0.2)

#     ax.tick_params(axis="x", labelsize=9)
#     ax.tick_params(axis="y", length=0)

#     fig.tight_layout(pad=1.0)

#     import io
#     buf = io.StringIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight")
#     plt.close(fig)

#     return buf.getvalue()




from __future__ import annotations

from decimal import Decimal
from typing import Any


def build_lost_manufacturers_svg(
    revenue_rows: list[dict[str, Any]],
    years: list[int],
    *,
    top_n: int = 15,
    exclude_unknown: bool = True,   # исключить manufacturer_id=0
    show_tail: bool = False,        # показывать/скрывать "последняя отгрузка | активные годы"
    theme: str = "pastel_rose",     # "pastel_blue" | "pastel_rose" | "amber"
    max_name_len: int = 28,         # обрезка длинных названий слева
) -> str | None:
    """
    SVG bar chart (для PDF):
    Top потерянных производителей (pause/stopped) по суммарной выручке "раньше"
    за период years[0]..years[-1].

    На строке:
      - бар = Past (накопленная выручка "раньше")
      - справа: значение Past
      - (опционально) ниже мелко: последняя отгрузка + активные годы X/Y

    Исключает "Производитель не указан" (manufacturer_id=0), если exclude_unknown=True.
    """

    if not revenue_rows or not years:
        return None

    last_year = years[-1]
    prev_year = years[-2] if len(years) >= 2 else None
    period_len = len(years)

    items: list[dict[str, Any]] = []

    for r in revenue_rows:
        mf_id = int(r.get("manufacturer_id") or 0)
        if exclude_unknown and mf_id == 0:
            continue

        status = (r.get("status") or "").strip()
        if status not in ("pause", "stopped"):
            continue

        by_year: dict[int, Decimal] = r.get("by_year", {}) or {}
        past = Decimal("0")

        active_years_cnt = 0
        last_active_year = None

        # считаем last_active_year строго по years
        for y in years:
            v = by_year.get(y, Decimal("0"))
            v = v if isinstance(v, Decimal) else Decimal(str(v or 0))

            if v > 0:
                active_years_cnt += 1
                last_active_year = y

            # "past" = всё кроме последнего года; прошлый год включаем в past
            if y == last_year:
                pass
            elif prev_year is not None and y == prev_year:
                past += v
            else:
                past += v

        if past <= 0:
            continue

        name = (r.get("name") or "—").strip() or "—"
        items.append(
            {
                "name": name,
                "status": status,
                "past": past,
                "active_years_cnt": active_years_cnt,
                "period_len": period_len,
                "last_active_year": last_active_year,
            }
        )

    if not items:
        return None

    items.sort(key=lambda x: x["past"], reverse=True)
    items = items[:top_n]

    # ---- plotting to SVG ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    def ellipsize(s: str, n: int) -> str:
        s = (s or "").strip()
        if len(s) <= n:
            return s
        return s[: max(0, n - 1)].rstrip() + "…"

    def fmt_axis(v, _pos=None):
        v = float(v or 0)
        a = abs(v)
        if a >= 1_000_000:
            return f"{v/1_000_000:.1f} млн"
        if a >= 1_000:
            return f"{v/1_000:.0f} тыс"
        return f"{v:.0f}"

    def fmt_value(v: float) -> str:
        a = abs(v)
        if a >= 1_000_000:
            return f"{v/1_000_000:.1f} млн"
        if a >= 1_000:
            return f"{v/1_000:.0f} тыс"
        return f"{v:.0f}"

    # summary по топу
    pause_cnt = sum(1 for it in items if it["status"] == "pause")
    stop_cnt = sum(1 for it in items if it["status"] == "stopped")
    pause_sum = float(sum(it["past"] for it in items if it["status"] == "pause"))
    stop_sum = float(sum(it["past"] for it in items if it["status"] == "stopped"))
    total_sum = float(sum(it["past"] for it in items))

    # --- THEMES (гармоничные пастели под белый фон PDF) ---
    if theme == "pastel_rose":
        # нежно-розовый, полупрозрачный, спокойный
        bar_color = (0.93, 0.72, 0.82, 0.78)
        edge_color = (0, 0, 0, 0.05)
        grid_color = "#E5E7EB"
        text_main = "#111827"
        text_muted = "#6B7280"
        status_pause = (0.82, 0.45, 0.62, 0.95)
        status_stop = (0.72, 0.20, 0.38, 0.95)

    elif theme == "amber":
        # твой исходный янтарный (чуть мягче)
        bar_color = (0.96, 0.69, 0.29, 0.78)
        edge_color = (0, 0, 0, 0.05)
        grid_color = "#E5E7EB"
        text_main = "#111827"
        text_muted = "#6B7280"
        status_pause = (0.93, 0.55, 0.06, 0.95)
        status_stop = (0.86, 0.20, 0.20, 0.92)

    else:  # "pastel_blue" default
        # нежно-голубой: самый “дорогой” для отчётов собственникам
        bar_color = (0.70, 0.83, 0.93, 0.82)
        edge_color = (0, 0, 0, 0.05)
        grid_color = "#E5E7EB"
        text_main = "#0F172A"
        text_muted = "#64748B"
        status_pause = (0.36, 0.64, 0.85, 0.95)
        status_stop = (0.75, 0.25, 0.25, 0.95)

    # размер
    h = max(3.6, 0.34 * len(items) + 2.0)
    fig = plt.figure(figsize=(12.6, h), dpi=160)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # данные (в обратном порядке для barh)
    items_r = items[::-1]
    names = [ellipsize(it["name"], max_name_len) for it in items_r]
    vals = [float(it["past"]) for it in items_r]
    statuses = [it["status"] for it in items_r]
    last_active_years = [it["last_active_year"] for it in items_r]
    active_years = [it["active_years_cnt"] for it in items_r]

    y = list(range(len(names)))

    ax.barh(
        y,
        vals,
        height=0.60,
        color=bar_color,
        edgecolor=edge_color,
        linewidth=0.8,
        zorder=3,
    )

    # тонкая статусная полоска слева
    for yi, st in enumerate(statuses):
        c = status_pause if st == "pause" else status_stop
        ax.plot([0, 0], [yi - 0.30, yi + 0.30], color=c, linewidth=3.6, solid_capstyle="round", zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9.5, fontweight="bold", color=text_main)
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_axis))

    # title = "Топ потерянных производителей"
    subtitle = (
        f"Период: {years[0]}–{years[-1]}  •  Показана суммарная выручка за период до остановки    "
        # f"Не учитывается: «Производитель не указан»"
    )

    # ax.set_title(title, fontsize=13, fontweight="bold", loc="left", pad=18, color=text_main)
    ax.text(0.0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=text_muted, ha="left", va="bottom")

    # sumline = (
    #     f"Итого потерь (Top-{len(items)}): ≈ {fmt_value(total_sum)}   •   "
    #     f"Пауза: {pause_cnt} (≈ {fmt_value(pause_sum)})   •   "
    #     f"Перестали: {stop_cnt} (≈ {fmt_value(stop_sum)})"
    # )
    # ax.text(0.0, 0.99, sumline, transform=ax.transAxes, fontsize=9.2, color=text_main, ha="left", va="bottom")

    # сетка (мягкая)
    ax.grid(axis="x", alpha=0.55, linestyle="--", linewidth=0.6, color=grid_color, zorder=0)
    ax.set_axisbelow(True)

    maxv = max(vals) or 1.0
    ax.set_xlim(0, maxv * 1.18)

    # подписи справа
    for yi, v in enumerate(vals):
        ax.text(
            v + maxv * 0.012,
            yi,
            fmt_value(v),
            va="center",
            ha="left",
            fontsize=9.5,
            color=text_main,
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.22,rounding_size=0.12",
                facecolor="white",
                edgecolor="none",
                alpha=0.92,
            ),
            zorder=6,
        )

        if show_tail:
            lay = last_active_years[yi]
            ay = active_years[yi]
            tail = f"последняя отгрузка: {lay or '—'}  •  активные годы: {ay}/{period_len}"
            ax.text(
                v + maxv * 0.012,
                yi - 0.22,
                tail,
                va="center",
                ha="left",
                fontsize=8.2,
                color=text_muted,
                zorder=6,
            )

    # оси/рамки
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_alpha(0.25)

    ax.tick_params(axis="x", labelsize=9, colors=text_muted)
    ax.tick_params(axis="y", length=0)

    fig.tight_layout(pad=1.15)

    import io
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)

    return buf.getvalue()