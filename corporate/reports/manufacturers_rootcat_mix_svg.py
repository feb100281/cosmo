# corporate/reports/manufacturers_rootcat_mix_svg.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any

# from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


# def build_rootcat_mix_svg(
#     years: list[str],
#     rootcat_rows: list[dict[str, Any]],
#     *,
#     title: str = "Производители по группам категорий: структура выручки и база",
#     width: int = 1100,
#     height: int = 520,
#     bar_area_h: int = 290,
#     left_pad: int = 56,
#     right_pad: int = 26,
#     top_pad: int = 56,
#     bottom_pad: int = 84,
#     font: str = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
#     max_legend_items: int = 10,
# ) -> str:
#     """
#     NEW (деловой): small multiples по группам (топ-N + Прочие).
#     Для каждой группы: мини-бары по годам + подписи итогов.
#     """
#     if not years or not rootcat_rows:
#         return ""

#     # --------------- helpers ---------------
#     def esc(s: Any) -> str:
#         s = str(s or "")
#         return (
#             s.replace("&", "&amp;")
#              .replace("<", "&lt;")
#              .replace(">", "&gt;")
#              .replace('"', "&quot;")
#         )

#     def to_dec(x: Any) -> Decimal:
#         try:
#             return x if isinstance(x, Decimal) else Decimal(str(x or "0"))
#         except Exception:
#             return Decimal("0")

#     years = [str(y) for y in years]

#     # --------------- normalize rows ---------------
#     rows = []
#     for r in rootcat_rows:
#         name = (r.get("root_name") or "—").strip() or "—"
#         rev_map = r.get("revenue") or {}
#         cnt_map = r.get("counts") or {}

#         rev = {y: to_dec(rev_map.get(y, 0)) for y in years}
#         cnt = {y: int(cnt_map.get(y, 0) or 0) for y in years}

#         total_rev = sum((rev[y] for y in years), Decimal("0"))
#         total_cnt = sum((cnt[y] for y in years))

#         rows.append({
#             "name": name,
#             "rev": rev,
#             "cnt": cnt,
#             "total_rev": total_rev,
#             "total_cnt": total_cnt,
#         })

#     # sort by total revenue desc
#     rows.sort(key=lambda rr: rr["total_rev"], reverse=True)

#     # top groups + other
#     top_n = max(4, min(int(max_legend_items), 8))  # фиксируем “деловой” максимум
#     if len(rows) > top_n:
#         top = rows[:top_n]
#         rest = rows[top_n:]

#         other_rev = {y: Decimal("0") for y in years}
#         other_cnt = {y: 0 for y in years}
#         for rr in rest:
#             for y in years:
#                 other_rev[y] += rr["rev"][y]
#                 other_cnt[y] += rr["cnt"][y]

#         top.append({
#             "name": "Прочие",
#             "rev": other_rev,
#             "cnt": other_cnt,
#             "total_rev": sum(other_rev.values(), Decimal("0")),
#             "total_cnt": sum(other_cnt.values()),
#         })
#         rows = top

#     # --------------- layout ---------------
#     # визуальный стиль (светлый, бизнес)
#     bg = "#ffffff"
#     card = "#f8fafc"
#     card_border = "rgba(15,23,42,.10)"
#     text = "rgba(15,23,42,.92)"
#     muted = "rgba(15,23,42,.62)"
#     grid = "rgba(15,23,42,.10)"
#     bar_bg = "rgba(15,23,42,.08)"
#     accent = "#2563eb"  # единый цвет = деловой стиль

#     # динамически под высоту: 1 строка = 46px
#     row_h = 46
#     header_h = 68
#     footer_h = 26
#     needed_h = 14 + header_h + len(rows) * row_h + footer_h + 14
#     height = max(height, needed_h)

#     # область минибаров внутри строки
#     bars_w = 520
#     bars_h = 18
#     bars_x0 = left_pad + 330
#     right_info_x = bars_x0 + bars_w + 18

#     # годовые бары: равные мини-столбики
#     n_years = len(years)
#     col_w = int(bars_w / max(1, n_years))
#     col_gap = 10
#     mini_w = max(10, col_w - col_gap)

#     # --------------- svg ---------------
#     parts: list[str] = []
#     parts.append(
#         f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
#         f'viewBox="0 0 {width} {height}" role="img">'
#     )
#     parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="{bg}"/>')
#     parts.append(
#         f'<rect x="14" y="14" width="{width-28}" height="{height-28}" rx="16" '
#         f'fill="{card}" stroke="{card_border}" stroke-width="1"/>'
#     )

#     # title
#     parts.append(
#         f'<text x="{left_pad}" y="44" fill="{text}" font-family="{font}" font-size="16" font-weight="700">'
#         f'{esc(title)}</text>'
#     )
#     parts.append(
#         f'<text x="{left_pad}" y="64" fill="{muted}" font-family="{font}" font-size="12">'
#         f'Выручка по годам (мини-бары) и итоги по группе. Показаны крупнейшие группы + «Прочие».</text>'
#     )

#     # year labels above bars column
#     y_hdr = top_pad + 34
#     for i, y in enumerate(years):
#         cx = bars_x0 + i * col_w + mini_w / 2
#         parts.append(
#             f'<text x="{cx:.1f}" y="{y_hdr}" text-anchor="middle" fill="{muted}" '
#             f'font-family="{font}" font-size="11">{esc(y)}</text>'
#         )

#     # rows
#     y0 = top_pad + 48
#     for idx, rr in enumerate(rows):
#         yy = y0 + idx * row_h

#         # separator
#         parts.append(f'<line x1="{left_pad}" y1="{yy+row_h-1}" x2="{width-right_pad}" y2="{yy+row_h-1}" stroke="{grid}" stroke-width="1"/>')

#         # group name
#         parts.append(
#             f'<text x="{left_pad}" y="{yy+20}" fill="{text}" font-family="{font}" font-size="13" font-weight="700">'
#             f'{esc(rr["name"])}</text>'
#         )

#         # small note: total manufacturers over period
#         parts.append(
#             f'<text x="{left_pad}" y="{yy+38}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'Производителей за период: {rr["total_cnt"]}</text>'
#         )

#         # compute max for this group (local scale!)
#         max_v = max((rr["rev"][y] for y in years), default=Decimal("0"))
#         if max_v <= 0:
#             max_v = Decimal("1")

#         # mini bars (per year, local scaling)
#         for i, y in enumerate(years):
#             v = rr["rev"][y]
#             h = int((v / max_v) * Decimal(str(bars_h))) if v > 0 else 1
#             x = bars_x0 + i * col_w
#             y_bar = yy + 30 - h  # baseline

#             # bg
#             parts.append(f'<rect x="{x}" y="{yy+12}" width="{mini_w}" height="{bars_h}" rx="3" fill="{bar_bg}"/>')
#             # fill
#             if v > 0:
#                 parts.append(f'<rect x="{x}" y="{y_bar}" width="{mini_w}" height="{h}" rx="3" fill="{accent}"/>')

#         # right info: total revenue
#         parts.append(
#             f'<text x="{right_info_x}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">'
#             f'{esc(fmt_money_ru(rr["total_rev"]))}</text>'
#         )
#         parts.append(
#             f'<text x="{right_info_x}" y="{yy+38}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'итого выручка</text>'
#         )

#     parts.append("</svg>")
#     return "".join(parts)



# corporate/reports/manufacturers_rootcat_mix_svg.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any

# from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


# def build_rootcat_mix_svg(
#     years: list[str],
#     rootcat_rows: list[dict[str, Any]],
#     *,
#     title: str = "Производители по группам категорий: структура выручки и база",
#     width: int = 1100,
#     height: int = 520,
#     bar_area_h: int = 290,
#     left_pad: int = 56,
#     right_pad: int = 26,
#     top_pad: int = 56,
#     bottom_pad: int = 84,
#     font: str = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
#     max_legend_items: int = 10,
# ) -> str:
#     """
#     Сравнение последнего года (CY) с предыдущим (PY) по группам категорий:
#       - Основной график: вклад групп в изменение выручки (дельта CY-PY), ранжирование
#       - Метрики: CY, PY, Δ, Δ%, доля CY, выручка/производителя, изменение базы производителей
#     Формат: деловой, не дублирует таблицу, даёт управленческий ответ "кто дал падение/рост".
#     Сигнатура сохранена.
#     """
#     if not years or not rootcat_rows:
#         return ""

#     years = [str(y) for y in years]
#     if len(years) < 2:
#         return ""

#     py = years[-2]
#     cy = years[-1]

#     # ---------------- helpers ----------------
#     def esc(s: Any) -> str:
#         s = str(s or "")
#         return (
#             s.replace("&", "&amp;")
#              .replace("<", "&lt;")
#              .replace(">", "&gt;")
#              .replace('"', "&quot;")
#         )

#     def to_dec(x: Any) -> Decimal:
#         try:
#             return x if isinstance(x, Decimal) else Decimal(str(x or "0"))
#         except Exception:
#             return Decimal("0")

#     def safe_pct(delta: Decimal, base: Decimal) -> float | None:
#         if base <= 0:
#             return None
#         return float((delta / base) * Decimal("100"))

#     def money0(v: Decimal) -> str:
#         return fmt_money_ru(v) if v else "0\u00A0₽"

#     # ---------------- normalize + compute ----------------
#     items: list[dict[str, Any]] = []
#     total_py = Decimal("0")
#     total_cy = Decimal("0")
#     total_py_cnt = 0
#     total_cy_cnt = 0

#     for r in rootcat_rows:
#         name = (r.get("root_name") or "—").strip() or "—"
#         rev_map = r.get("revenue") or {}
#         cnt_map = r.get("counts") or {}

#         rev_py = to_dec(rev_map.get(py, 0))
#         rev_cy = to_dec(rev_map.get(cy, 0))
#         cnt_py = int(cnt_map.get(py, 0) or 0)
#         cnt_cy = int(cnt_map.get(cy, 0) or 0)
        
#         py_unique = set()
#         cy_unique = set()

#         for r in rootcat_rows:
#             cnt_map = r.get("counts") or {}

#         total_py += rev_py
#         total_cy += rev_cy
#         total_py_cnt += cnt_py
#         total_cy_cnt += cnt_cy

#         delta = rev_cy - rev_py
#         pct = safe_pct(delta, rev_py)

#         # эффективность: выручка на производителя (за год)
#         eff_py = (rev_py / Decimal(cnt_py)) if cnt_py > 0 else Decimal("0")
#         eff_cy = (rev_cy / Decimal(cnt_cy)) if cnt_cy > 0 else Decimal("0")
#         eff_delta = eff_cy - eff_py
#         eff_pct = safe_pct(eff_delta, eff_py) if eff_py > 0 else None

#         items.append({
#             "name": name,
#             "rev_py": rev_py,
#             "rev_cy": rev_cy,
#             "cnt_py": cnt_py,
#             "cnt_cy": cnt_cy,
#             "delta": delta,
#             "pct": pct,
#             "eff_py": eff_py,
#             "eff_cy": eff_cy,
#             "eff_delta": eff_delta,
#             "eff_pct": eff_pct,
#         })

#     if total_py <= 0 and total_cy <= 0:
#         return ""

#     total_delta = total_cy - total_py
#     total_pct = safe_pct(total_delta, total_py) if total_py > 0 else None

#     # share in CY
#     for it in items:
#         it["share_cy"] = float((it["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

#     # сортируем по вкладу в изменение: по абсолютной дельте
#     items.sort(key=lambda x: abs(x["delta"]), reverse=True)

#     # ограничим число строк (чтобы не раздувать)
#     max_rows = 12
#     if len(items) > max_rows:
#         top = items[:max_rows-1]
#         rest = items[max_rows-1:]

#         agg = {
#             "name": "Прочие",
#             "rev_py": sum((x["rev_py"] for x in rest), Decimal("0")),
#             "rev_cy": sum((x["rev_cy"] for x in rest), Decimal("0")),
#             "cnt_py": sum((x["cnt_py"] for x in rest)),
#             "cnt_cy": sum((x["cnt_cy"] for x in rest)),
#         }
#         agg["delta"] = agg["rev_cy"] - agg["rev_py"]
#         agg["pct"] = safe_pct(agg["delta"], agg["rev_py"]) if agg["rev_py"] > 0 else None
#         agg["eff_py"] = (agg["rev_py"] / Decimal(agg["cnt_py"])) if agg["cnt_py"] > 0 else Decimal("0")
#         agg["eff_cy"] = (agg["rev_cy"] / Decimal(agg["cnt_cy"])) if agg["cnt_cy"] > 0 else Decimal("0")
#         agg["eff_delta"] = agg["eff_cy"] - agg["eff_py"]
#         agg["eff_pct"] = safe_pct(agg["eff_delta"], agg["eff_py"]) if agg["eff_py"] > 0 else None
#         agg["share_cy"] = float((agg["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

#         items = top + [agg]

#     # scale for delta bars
#     max_abs_delta = max((abs(it["delta"]) for it in items), default=Decimal("1"))
#     if max_abs_delta <= 0:
#         max_abs_delta = Decimal("1")

#     # ---------------- style ----------------
#     bg = "#ffffff"
#     card = "#f8fafc"
#     card_border = "rgba(15,23,42,.10)"
#     text = "rgba(15,23,42,.92)"
#     muted = "rgba(15,23,42,.62)"
#     grid = "rgba(15,23,42,.10)"
#     axis = "rgba(15,23,42,.22)"

#     pos = "#2563eb"   # рост (синий — деловой)
#     neg = "#ef4444"   # падение (красный)
#     bar_bg = "rgba(15,23,42,.07)"

#     # ---------------- layout ----------------
#     header_h = 92
#     row_h = 42
#     rows_h = len(items) * row_h
#     footer_h = 18

#     needed_h = 14 + header_h + rows_h + footer_h + 14
#     height = max(height, needed_h)

#     # columns
#     name_x = left_pad
#     chart_x0 = left_pad + 330
#     chart_w = 420
#     chart_mid = chart_x0 + chart_w / 2

#     col_py_x = chart_x0 + chart_w + 24
#     col_cy_x = col_py_x + 140
#     col_eff_x = col_cy_x + 140
#     col_cnt_x = col_eff_x + 170

#     # clamp right
#     if col_cnt_x + 140 > width - right_pad:
#         # если ширины не хватает — ужмём справа колонки
#         col_cnt_x = width - right_pad - 150
#         col_eff_x = col_cnt_x - 170
#         col_cy_x = col_eff_x - 140
#         col_py_x = col_cy_x - 140

#     # ---------------- svg ----------------
#     parts: list[str] = []
#     parts.append(
#     f'<svg xmlns="http://www.w3.org/2000/svg" '
#     f'width="100%" height="auto" '
#     f'viewBox="0 0 {width} {height}" '
#     f'preserveAspectRatio="xMinYMin meet" role="img">'
# )
#     parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="{bg}"/>')
#     parts.append(
#         f'<rect x="14" y="14" width="{width-28}" height="{height-28}" rx="16" '
#         f'fill="{card}" stroke="{card_border}" stroke-width="1"/>'
#     )

#     # title
#     parts.append(
#         f'<text x="{left_pad}" y="44" fill="{text}" font-family="{font}" font-size="16" font-weight="700">'
#         f'{esc("Производители по группам категорий и их выручка")}</text>'
#     )
#     parts.append(
#         f'<text x="{left_pad}" y="64" fill="{muted}" font-family="{font}" font-size="12">'
#         f'Сравнение {esc(py)} → {esc(cy)}: вклад групп в изменение чистой выручки.</text>'
#     )

#     # top KPIs
#     kpi_y = 84
#     parts.append(
#         f'<text x="{left_pad}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">PY ({esc(py)}):</text>'
#         f'<text x="{left_pad+82}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">{esc(money0(total_py))}</text>'
#     )
#     parts.append(
#         f'<text x="{left_pad+230}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">CY ({esc(cy)}):</text>'
#         f'<text x="{left_pad+312}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">{esc(money0(total_cy))}</text>'
#     )

#     sign = "+" if total_delta >= 0 else "−"
#     parts.append(
#         f'<text x="{left_pad+470}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">Δ:</text>'
#         f'<text x="{left_pad+495}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">'
#         f'{sign}{esc(money0(abs(total_delta)))}'
#         f'{"" if total_pct is None else f"  ({sign}{total_pct:.0f}%)"}'
#         f'</text>'
#     )

#     parts.append(
#         f'<text x="{left_pad+760}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">Производители:</text>'
#         f'<text x="{left_pad+852}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">'
#         f'{total_py_cnt} → {total_cy_cnt}</text>'
#     )

#     # column headers
#     hdr_y = 118
#     parts.append(f'<line x1="{left_pad}" y1="{hdr_y}" x2="{width-right_pad}" y2="{hdr_y}" stroke="{grid}" stroke-width="1"/>')

#     parts.append(
#         f'<text x="{name_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Группа</text>'
#     )
#     parts.append(
#         f'<text x="{chart_x0}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Вклад в Δ (CY−PY)</text>'
#     )
#     parts.append(
#         f'<text x="{col_py_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">PY</text>'
#     )
#     parts.append(
#         f'<text x="{col_cy_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">CY</text>'
#     )
#     parts.append(
#         f'<text x="{col_eff_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Выручка/произв.</text>'
#     )
#     parts.append(
#         f'<text x="{col_cnt_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Производители</text>'
#     )

#     # axis line for delta chart
#     y0 = hdr_y + 16
#     chart_top = y0 - 10
#     chart_bottom = y0 + len(items) * row_h - 12

#     # background bar area
#     parts.append(
#         f'<rect x="{chart_x0}" y="{chart_top}" width="{chart_w}" height="{chart_bottom-chart_top}" rx="10" fill="rgba(255,255,255,0)"/>'
#     )
#     parts.append(
#         f'<line x1="{chart_mid}" y1="{chart_top}" x2="{chart_mid}" y2="{chart_bottom}" stroke="{axis}" stroke-width="1.2"/>'
#     )

#     # rows
#     for i, it in enumerate(items):
#         yy = y0 + i * row_h

#         # row separator
#         parts.append(f'<line x1="{left_pad}" y1="{yy+row_h-6}" x2="{width-right_pad}" y2="{yy+row_h-6}" stroke="{grid}" stroke-width="1"/>')

#         name = esc(it["name"])
#         parts.append(
#             f'<text x="{name_x}" y="{yy+16}" fill="{text}" font-family="{font}" font-size="13" font-weight="700">{name}</text>'
#         )

#         # share in CY (tiny hint)
#         parts.append(
#             f'<text x="{name_x}" y="{yy+32}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'доля CY: {it["share_cy"]:.0f}%</text>'
#         )

#         # delta bar
#         delta: Decimal = it["delta"]
#         delta_abs = abs(delta)
#         w = int((delta_abs / max_abs_delta) * Decimal(str(chart_w/2 - 14)))
#         w = max(1, w) if delta_abs > 0 else 1

#         bar_y = yy + 6
#         bar_h = 16
#         rx = 3

#         # background (subtle)
#         parts.append(
#             f'<rect x="{chart_x0+10}" y="{bar_y}" width="{chart_w-20}" height="{bar_h}" rx="{rx}" fill="{bar_bg}"/>'
#         )

#         if delta >= 0:
#             x_bar = int(chart_mid)
#             parts.append(
#                 f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{pos}"/>'
#             )
#         else:
#             x_bar = int(chart_mid - w)
#             parts.append(
#                 f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{neg}"/>'
#             )

#         # delta label
#         sign = "+" if delta >= 0 else "−"
#         pct = it["pct"]
#         pct_txt = "" if pct is None else f" ({sign}{pct:.0f}%)"
#         parts.append(
#             f'<text x="{chart_x0 + chart_w + 6}" y="{yy+18}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'{sign}{esc(money0(delta_abs))}{esc(pct_txt)}</text>'
#         )

#         # PY / CY numbers
#         parts.append(
#             f'<text x="{col_py_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_py"]))}</text>'
#         )
#         parts.append(
#             f'<text x="{col_cy_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_cy"]))}</text>'
#         )

#         # efficiency (rev per manufacturer)
#         eff_py = it["eff_py"]
#         eff_cy = it["eff_cy"]
#         eff_delta = it["eff_delta"]
#         eff_sign = "+" if eff_delta >= 0 else "−"
#         eff_pct = it["eff_pct"]
#         eff_pct_txt = "" if eff_pct is None else f" ({eff_sign}{eff_pct:.0f}%)"

#         parts.append(
#             f'<text x="{col_eff_x}" y="{yy+16}" fill="{text}" font-family="{font}" font-size="12">'
#             f'{esc(money0(eff_py))} → {esc(money0(eff_cy))}</text>'
#         )
#         parts.append(
#             f'<text x="{col_eff_x}" y="{yy+32}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'Δ {eff_sign}{esc(money0(abs(eff_delta)))}{esc(eff_pct_txt)}</text>'
#         )

#         # counts
#         cnt_py = it["cnt_py"]
#         cnt_cy = it["cnt_cy"]
#         cnt_delta = cnt_cy - cnt_py
#         cnt_sign = "+" if cnt_delta >= 0 else "−"
#         parts.append(
#             f'<text x="{col_cnt_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">'
#             f'{cnt_py} → {cnt_cy}</text>'
#         )
#         parts.append(
#             f'<text x="{col_cnt_x}" y="{yy+32}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'Δ {cnt_sign}{abs(cnt_delta)}</text>'
#         )

#     parts.append("</svg>")
#     return "".join(parts)




# corporate/reports/manufacturers_rootcat_mix_svg.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any

# from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


# def build_rootcat_mix_svg(
#     years: list[str],
#     rootcat_rows: list[dict[str, Any]],
#     *,
#     title: str = "Производители по группам категорий: структура выручки и база",
#     width: int = 1100,
#     height: int = 520,
#     bar_area_h: int = 290,
#     left_pad: int = 56,
#     right_pad: int = 26,
#     top_pad: int = 56,
#     bottom_pad: int = 84,
#     font: str = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
#     max_legend_items: int = 10,
# ) -> str:
#     """
#     Сравнение последнего года (CY) с предыдущим (PY) по root-группам:
#       - вклад групп в изменение чистой выручки (Δ CY−PY)
#       - CY/PY, Δ%, доля CY
#       - эффективность: выручка/производителя (внутри группы)
#       - база: производители (внутри группы)
#     ВЕРХНИЙ KPI "Производители" — УНИКАЛЬНЫЕ по всему портфелю (не суммой по группам),
#     берётся из rootcat_rows[*]["_overall_unique_by_year"] (заполняется в manufacturers_by_rootcat.py).
#     """

#     if not years or not rootcat_rows:
#         return ""
#     years = [str(y) for y in years]
#     if len(years) < 2:
#         return ""

#     py = years[-2]
#     cy = years[-1]

#     # ---------------- helpers ----------------
#     def esc(s: Any) -> str:
#         s = str(s or "")
#         return (
#             s.replace("&", "&amp;")
#              .replace("<", "&lt;")
#              .replace(">", "&gt;")
#              .replace('"', "&quot;")
#         )

#     def to_dec(x: Any) -> Decimal:
#         try:
#             return x if isinstance(x, Decimal) else Decimal(str(x or "0"))
#         except Exception:
#             return Decimal("0")

#     def safe_pct(delta: Decimal, base: Decimal) -> float | None:
#         if base <= 0:
#             return None
#         return float((delta / base) * Decimal("100"))

#     def money0(v: Decimal) -> str:
#         return fmt_money_ru(v) if v else "0\u00A0₽"

#     # ---------------- overall unique manufacturers (portfolio) ----------------
#     overall_unique_by_year: dict[str, int] = {}
#     if rootcat_rows and isinstance(rootcat_rows[0], dict):
#         overall_unique_by_year = dict(rootcat_rows[0].get("_overall_unique_by_year") or {})

#     uniq_py = int(overall_unique_by_year.get(py, 0) or 0)
#     uniq_cy = int(overall_unique_by_year.get(cy, 0) or 0)

#     # ---------------- build items from rows ----------------
#     items: list[dict[str, Any]] = []
#     total_py = Decimal("0")
#     total_cy = Decimal("0")

#     for r in rootcat_rows:
#         name = (r.get("root_name") or "—").strip() or "—"
#         rev_map = r.get("revenue") or {}
#         cnt_map = r.get("counts") or {}

#         rev_py = to_dec(rev_map.get(py, 0))
#         rev_cy = to_dec(rev_map.get(cy, 0))
#         cnt_py = int(cnt_map.get(py, 0) or 0)
#         cnt_cy = int(cnt_map.get(cy, 0) or 0)

#         total_py += rev_py
#         total_cy += rev_cy

#         delta = rev_cy - rev_py
#         pct = safe_pct(delta, rev_py) if rev_py > 0 else None

#         eff_py = (rev_py / Decimal(cnt_py)) if cnt_py > 0 else Decimal("0")
#         eff_cy = (rev_cy / Decimal(cnt_cy)) if cnt_cy > 0 else Decimal("0")
#         eff_delta = eff_cy - eff_py
#         eff_pct = safe_pct(eff_delta, eff_py) if eff_py > 0 else None

#         items.append({
#             "name": name,
#             "rev_py": rev_py,
#             "rev_cy": rev_cy,
#             "cnt_py": cnt_py,
#             "cnt_cy": cnt_cy,
#             "delta": delta,
#             "pct": pct,
#             "eff_py": eff_py,
#             "eff_cy": eff_cy,
#             "eff_delta": eff_delta,
#             "eff_pct": eff_pct,
#         })

#     if total_py <= 0 and total_cy <= 0:
#         return ""

#     total_delta = total_cy - total_py
#     total_pct = safe_pct(total_delta, total_py) if total_py > 0 else None

#     for it in items:
#         it["share_cy"] = float((it["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

#     # сортировка: главные драйверы изменений
#     items.sort(key=lambda x: abs(x["delta"]), reverse=True)

#     # ограничение строк + "Прочие" (чтобы в PDF было аккуратно)
#     max_rows = 10
#     if len(items) > max_rows:
#         top = items[:max_rows-1]
#         rest = items[max_rows-1:]
#         agg_py = sum((x["rev_py"] for x in rest), Decimal("0"))
#         agg_cy = sum((x["rev_cy"] for x in rest), Decimal("0"))
#         agg_cnt_py = sum((x["cnt_py"] for x in rest))
#         agg_cnt_cy = sum((x["cnt_cy"] for x in rest))

#         agg = {
#             "name": "Прочие",
#             "rev_py": agg_py,
#             "rev_cy": agg_cy,
#             "cnt_py": agg_cnt_py,
#             "cnt_cy": agg_cnt_cy,
#         }
#         agg["delta"] = agg["rev_cy"] - agg["rev_py"]
#         agg["pct"] = safe_pct(agg["delta"], agg["rev_py"]) if agg["rev_py"] > 0 else None
#         agg["eff_py"] = (agg["rev_py"] / Decimal(agg["cnt_py"])) if agg["cnt_py"] > 0 else Decimal("0")
#         agg["eff_cy"] = (agg["rev_cy"] / Decimal(agg["cnt_cy"])) if agg["cnt_cy"] > 0 else Decimal("0")
#         agg["eff_delta"] = agg["eff_cy"] - agg["eff_py"]
#         agg["eff_pct"] = safe_pct(agg["eff_delta"], agg["eff_py"]) if agg["eff_py"] > 0 else None
#         agg["share_cy"] = float((agg["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

#         items = top + [agg]

#     max_abs_delta = max((abs(it["delta"]) for it in items), default=Decimal("1"))
#     if max_abs_delta <= 0:
#         max_abs_delta = Decimal("1")

#     # ---------------- style ----------------
#     bg = "#ffffff"
#     card = "#f8fafc"
#     card_border = "rgba(15,23,42,.10)"
#     text = "rgba(15,23,42,.92)"
#     muted = "rgba(15,23,42,.62)"
#     grid = "rgba(15,23,42,.10)"
#     axis = "rgba(15,23,42,.22)"

#     pos = "#2563eb"   # рост
#     neg = "#ef4444"   # падение
#     bar_bg = "rgba(15,23,42,.07)"

#     # ---------------- layout ----------------
#     header_h = 120
#     row_h = 46
#     insight_h = 92  # нижний блок с инсайтами
#     rows_h = len(items) * row_h
#     needed_h = 14 + header_h + rows_h + insight_h + 14
#     height = max(height, needed_h)

#     # columns (переразложено, чтобы справа не было каши)
#     name_x = left_pad
#     chart_x0 = left_pad + 310
#     chart_w = 380
#     chart_mid = chart_x0 + chart_w / 2

#     col_py_x = chart_x0 + chart_w + 18
#     col_cy_x = col_py_x + 140
#     col_eff_x = col_cy_x + 150
#     col_cnt_x = col_eff_x + 210

#     # ---------------- svg ----------------
#     parts: list[str] = []
#     parts.append(
#         f'<svg xmlns="http://www.w3.org/2000/svg" '
#         f'width="100%" height="auto" '
#         f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" role="img">'
#     )

#     parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="{bg}"/>')
#     parts.append(
#         f'<rect x="14" y="14" width="{width-28}" height="{height-28}" rx="16" '
#         f'fill="{card}" stroke="{card_border}" stroke-width="1"/>'
#     )

#     # title
#     parts.append(
#         f'<text x="{left_pad}" y="44" fill="{text}" font-family="{font}" font-size="18" font-weight="700">'
#         f'{esc("Производители по группам категорий и их выручка")}</text>'
#     )
#     parts.append(
#         f'<text x="{left_pad}" y="68" fill="{muted}" font-family="{font}" font-size="12">'
#         f'Сравнение {esc(py)} → {esc(cy)}: вклад групп в изменение чистой выручки (CY может быть YTD).</text>'
#     )

#     # top KPIs
#     kpi_y = 96
#     parts.append(
#         f'<text x="{left_pad}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">PY ({esc(py)}):</text>'
#         f'<text x="{left_pad+82}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">{esc(money0(total_py))}</text>'
#     )
#     parts.append(
#         f'<text x="{left_pad+240}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">CY ({esc(cy)}):</text>'
#         f'<text x="{left_pad+322}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">{esc(money0(total_cy))}</text>'
#     )

#     t_sign = "+" if total_delta >= 0 else "−"
#     t_pct_txt = "" if total_pct is None else f" ({t_sign}{total_pct:.0f}%)"
#     parts.append(
#         f'<text x="{left_pad+495}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">Δ:</text>'
#         f'<text x="{left_pad+518}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">'
#         f'{t_sign}{esc(money0(abs(total_delta)))}{esc(t_pct_txt)}</text>'
#     )

#     # unique manufacturers KPI
#     parts.append(
#         f'<text x="{left_pad+760}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">Производители (уникальные):</text>'
#         f'<text x="{left_pad+920}" y="{kpi_y}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">'
#         f'{uniq_py} → {uniq_cy}</text>'
#     )
#     if not overall_unique_by_year:
#         parts.append(
#             f'<text x="{left_pad+760}" y="{kpi_y+16}" fill="{muted}" font-family="{font}" font-size="10">'
#             f'Примечание: для точного подсчёта уникальных производителей добавьте overall_unique_by_year в источнике данных.</text>'
#         )

#     # column headers
#     hdr_y = 126
#     parts.append(f'<line x1="{left_pad}" y1="{hdr_y}" x2="{width-right_pad}" y2="{hdr_y}" stroke="{grid}" stroke-width="1"/>')
#     parts.append(f'<text x="{name_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Группа</text>')
#     parts.append(f'<text x="{chart_x0}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Вклад в Δ (CY−PY)</text>')
#     parts.append(f'<text x="{col_py_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">PY</text>')
#     parts.append(f'<text x="{col_cy_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">CY</text>')
#     parts.append(f'<text x="{col_eff_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Эффективность</text>')
#     parts.append(f'<text x="{col_cnt_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">База</text>')

#     # axis line for delta chart
#     y0 = hdr_y + 18
#     chart_top = y0 - 10
#     chart_bottom = y0 + len(items) * row_h - 10
#     parts.append(f'<line x1="{chart_mid}" y1="{chart_top}" x2="{chart_mid}" y2="{chart_bottom}" stroke="{axis}" stroke-width="1.2"/>')

#     # rows
#     for i, it in enumerate(items):
#         yy = y0 + i * row_h
#         parts.append(f'<line x1="{left_pad}" y1="{yy+row_h-6}" x2="{width-right_pad}" y2="{yy+row_h-6}" stroke="{grid}" stroke-width="1"/>')

#         name = esc(it["name"])
#         parts.append(f'<text x="{name_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="14" font-weight="700">{name}</text>')
#         parts.append(
#             f'<text x="{name_x}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'доля CY: {it["share_cy"]:.0f}%</text>'
#         )

#         # delta bar
#         delta: Decimal = it["delta"]
#         delta_abs = abs(delta)
#         w = int((delta_abs / max_abs_delta) * Decimal(str(chart_w/2 - 16)))
#         w = max(1, w) if delta_abs > 0 else 1

#         bar_y = yy + 8
#         bar_h = 18
#         rx = 4

#         parts.append(f'<rect x="{chart_x0+10}" y="{bar_y}" width="{chart_w-20}" height="{bar_h}" rx="{rx}" fill="{bar_bg}"/>')
#         if delta >= 0:
#             x_bar = int(chart_mid)
#             parts.append(f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{pos}"/>')
#         else:
#             x_bar = int(chart_mid - w)
#             parts.append(f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{neg}"/>')

#         sign = "+" if delta >= 0 else "−"
#         pct = it["pct"]
#         pct_txt = "" if pct is None else f" ({sign}{pct:.0f}%)"
#         parts.append(
#             f'<text x="{chart_x0 + chart_w + 6}" y="{yy+22}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'{sign}{esc(money0(delta_abs))}{esc(pct_txt)}</text>'
#         )

#         # PY / CY
#         parts.append(f'<text x="{col_py_x}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_py"]))}</text>')
#         parts.append(f'<text x="{col_cy_x}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_cy"]))}</text>')

#         # efficiency compact
#         eff_py = it["eff_py"]
#         eff_cy = it["eff_cy"]
#         eff_delta = it["eff_delta"]
#         eff_sign = "+" if eff_delta >= 0 else "−"
#         eff_pct = it["eff_pct"]
#         eff_pct_txt = "" if eff_pct is None else f" ({eff_sign}{eff_pct:.0f}%)"

#         parts.append(
#             f'<text x="{col_eff_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">'
#             f'{esc(money0(eff_py))} → {esc(money0(eff_cy))}</text>'
#         )
#         parts.append(
#             f'<text x="{col_eff_x}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'Δ {eff_sign}{esc(money0(abs(eff_delta)))}{esc(eff_pct_txt)}</text>'
#         )

#         # base compact
#         cnt_py = int(it["cnt_py"])
#         cnt_cy = int(it["cnt_cy"])
#         cnt_delta = cnt_cy - cnt_py
#         cnt_sign = "+" if cnt_delta >= 0 else "−"

#         parts.append(
#             f'<text x="{col_cnt_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">'
#             f'{cnt_py} → {cnt_cy}</text>'
#         )
#         parts.append(
#             f'<text x="{col_cnt_x}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">'
#             f'Δ {cnt_sign}{abs(cnt_delta)}</text>'
#         )

#     # ---------------- Insights block (below) ----------------
#     block_y = y0 + len(items) * row_h + 18
#     parts.append(f'<line x1="{left_pad}" y1="{block_y-8}" x2="{width-right_pad}" y2="{block_y-8}" stroke="{grid}" stroke-width="1"/>')

#     parts.append(
#         f'<text x="{left_pad}" y="{block_y+14}" fill="{text}" font-family="{font}" font-size="13" font-weight="700">'
#         f'Ключевые факторы изменения выручки</text>'
#     )

#     # top negative drivers
#     neg_items = [x for x in items if x["delta"] < 0]
#     neg_items.sort(key=lambda x: x["delta"])  # most negative first

#     top3 = neg_items[:3]
#     if not top3:
#         parts.append(
#             f'<text x="{left_pad}" y="{block_y+36}" fill="{muted}" font-family="{font}" font-size="12">'
#             f'Падения по группам не выявлено.</text>'
#         )
#     else:
#         yy = block_y + 36
#         for k, x in enumerate(top3, start=1):
#             d = abs(x["delta"])
#             share_of_drop = float((d / abs(total_delta)) * Decimal("100")) if total_delta != 0 else 0.0
#             parts.append(
#                 f'<text x="{left_pad}" y="{yy}" fill="{muted}" font-family="{font}" font-size="12">'
#                 f'{k}. {esc(x["name"])}: −{esc(money0(d))} '
#                 f'(≈ {share_of_drop:.0f}% от общего изменения)</text>'
#             )
#             yy += 18

#     parts.append("</svg>")
#     return "".join(parts)







# # corporate/reports/manufacturers_rootcat_mix_svg.py
# from __future__ import annotations

# from decimal import Decimal
# from typing import Any

# from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


# def build_rootcat_mix_svg(
#     years: list[str],
#     rootcat_rows: list[dict[str, Any]],
#     *,

#     title: str | None = None,
#     width: int = 1100,
#     height: int = 520,
#     left_pad: int = 56,
#     right_pad: int = 26,
#     top_pad: int = 22,
#     bottom_pad: int = 26,
#     font: str = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
#     max_rows: int = 10,
# ) -> str:
#     if not years or not rootcat_rows:
#         return ""
#     years = [str(y) for y in years]
#     if len(years) < 2:
#         return ""

#     py = years[-2]
#     cy = years[-1]

#     # ---------------- helpers ----------------
#     def esc(s: Any) -> str:
#         s = str(s or "")
#         return (
#             s.replace("&", "&amp;")
#             .replace("<", "&lt;")
#             .replace(">", "&gt;")
#             .replace('"', "&quot;")
#         )
#     if title is None:
#         title = f"Производители по группам категорий и их выручка: {py} → {cy}"
#     else:
#         # чтобы годы ВСЕГДА были в заголовке
#         if f"{py}" not in title and f"{cy}" not in title:
#             title = f"{title}: {py} → {cy}"

#     def to_dec(x: Any) -> Decimal:
#         try:
#             return x if isinstance(x, Decimal) else Decimal(str(x or "0"))
#         except Exception:
#             return Decimal("0")

#     def safe_pct(delta: Decimal, base: Decimal) -> float | None:
#         if base <= 0:
#             return None
#         return float((delta / base) * Decimal("100"))

#     def money0(v: Decimal) -> str:
#         return fmt_money_ru(v) if v else "0\u00A0₽"

#     def fmt_pct(p: float | None) -> str:
#         if p is None:
#             return ""
#         sgn = "+" if p >= 0 else "−"
#         return f" ({sgn}{abs(p):.0f}%)"

#     # грубая оценка ширины символов (для обрезки)
#     def ellipsis(text: str, max_px: int, font_size: int = 14) -> str:
#         if not text:
#             return "—"
#         approx_char_px = max(6, int(font_size * 0.56))
#         max_chars = max(4, max_px // approx_char_px)
#         if len(text) <= max_chars:
#             return text
#         if max_chars <= 6:
#             return text[:max_chars]
#         return text[: max_chars - 1] + "…"

#     # ---------------- overall unique manufacturers (portfolio) ----------------
#     overall_unique_by_year: dict[str, int] = {}
#     if rootcat_rows and isinstance(rootcat_rows[0], dict):
#         overall_unique_by_year = dict(rootcat_rows[0].get("_overall_unique_by_year") or {})

#     uniq_py = int(overall_unique_by_year.get(py, 0) or 0)
#     uniq_cy = int(overall_unique_by_year.get(cy, 0) or 0)

#     # ---------------- build items from rows ----------------
#     items: list[dict[str, Any]] = []
#     total_py = Decimal("0")
#     total_cy = Decimal("0")

#     for r in rootcat_rows:
#         name = (r.get("root_name") or "—").strip() or "—"
#         rev_map = r.get("revenue") or {}
#         cnt_map = r.get("counts") or {}

#         rev_py = to_dec(rev_map.get(py, 0))
#         rev_cy = to_dec(rev_map.get(cy, 0))
#         cnt_py = int(cnt_map.get(py, 0) or 0)
#         cnt_cy = int(cnt_map.get(cy, 0) or 0)

#         total_py += rev_py
#         total_cy += rev_cy

#         delta = rev_cy - rev_py
#         pct = safe_pct(delta, rev_py) if rev_py > 0 else None

#         eff_py = (rev_py / Decimal(cnt_py)) if cnt_py > 0 else Decimal("0")
#         eff_cy = (rev_cy / Decimal(cnt_cy)) if cnt_cy > 0 else Decimal("0")
#         eff_delta = eff_cy - eff_py
#         eff_pct = safe_pct(eff_delta, eff_py) if eff_py > 0 else None

#         items.append(
#             {
#                 "name": name,
#                 "rev_py": rev_py,
#                 "rev_cy": rev_cy,
#                 "cnt_py": cnt_py,
#                 "cnt_cy": cnt_cy,
#                 "delta": delta,
#                 "pct": pct,
#                 "eff_py": eff_py,
#                 "eff_cy": eff_cy,
#                 "eff_delta": eff_delta,
#                 "eff_pct": eff_pct,
#             }
#         )

#     if total_py <= 0 and total_cy <= 0:
#         return ""

#     total_delta = total_cy - total_py
#     total_pct = safe_pct(total_delta, total_py) if total_py > 0 else None

#     for it in items:
#         it["share_cy"] = float((it["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

#     # сортировка: главные драйверы изменений
#     items.sort(key=lambda x: abs(x["delta"]), reverse=True)

#     # ограничение строк + "Прочие"
#     if len(items) > max_rows:
#         top = items[: max_rows - 1]
#         rest = items[max_rows - 1 :]

#         agg_py = sum((x["rev_py"] for x in rest), Decimal("0"))
#         agg_cy = sum((x["rev_cy"] for x in rest), Decimal("0"))
#         agg_cnt_py = sum((x["cnt_py"] for x in rest))
#         agg_cnt_cy = sum((x["cnt_cy"] for x in rest))

#         agg = {
#             "name": "Прочие",
#             "rev_py": agg_py,
#             "rev_cy": agg_cy,
#             "cnt_py": agg_cnt_py,
#             "cnt_cy": agg_cnt_cy,
#         }
#         agg["delta"] = agg["rev_cy"] - agg["rev_py"]
#         agg["pct"] = safe_pct(agg["delta"], agg["rev_py"]) if agg["rev_py"] > 0 else None
#         agg["eff_py"] = (agg["rev_py"] / Decimal(agg["cnt_py"])) if agg["cnt_py"] > 0 else Decimal("0")
#         agg["eff_cy"] = (agg["rev_cy"] / Decimal(agg["cnt_cy"])) if agg["cnt_cy"] > 0 else Decimal("0")
#         agg["eff_delta"] = agg["eff_cy"] - agg["eff_py"]
#         agg["eff_pct"] = safe_pct(agg["eff_delta"], agg["eff_py"]) if agg["eff_py"] > 0 else None
#         agg["share_cy"] = float((agg["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

#         items = top + [agg]

#     max_abs_delta = max((abs(it["delta"]) for it in items), default=Decimal("1"))
#     if max_abs_delta <= 0:
#         max_abs_delta = Decimal("1")

#     # ---------------- Insights data ----------------
#     neg_items = sorted([x for x in items if x["delta"] < 0], key=lambda x: x["delta"])
#     pos_items = sorted([x for x in items if x["delta"] > 0], key=lambda x: x["delta"], reverse=True)

#     top_drop = neg_items[:3]
#     top_grow = pos_items[:3]

#     total_drop_abs = sum((abs(x["delta"]) for x in neg_items), Decimal("0"))
#     total_grow_abs = sum((abs(x["delta"]) for x in pos_items), Decimal("0"))

#     conc1 = 0.0
#     conc3 = 0.0
#     if total_drop_abs > 0 and top_drop:
#         conc1 = float((abs(top_drop[0]["delta"]) / total_drop_abs) * Decimal("100"))
#         conc3 = float((sum(abs(x["delta"]) for x in top_drop) / total_drop_abs) * Decimal("100"))

#     # ---------------- style ----------------
#     bg = "#ffffff"
#     card = "#ffffff"
#     card_border = "rgba(15,23,42,.10)"
#     text = "rgba(15,23,42,.92)"
#     muted = "rgba(15,23,42,.62)"
#     grid = "rgba(15,23,42,.10)"
#     axis = "rgba(15,23,42,.22)"

#     pos = "#2563eb"
#     neg = "#ef4444"
#     bar_bg = "rgba(15,23,42,.07)"

#     # ---------------- layout ----------------
#     header_h = 118
#     row_h = 46

#     # Динамическая высота выводов:
#     #  - заголовок + 2 строки summary + заголовки колонок + max(3 строки) + футер
#     lines_drop = max(1, len(top_drop))
#     lines_grow = max(1, len(top_grow))
#     max_list_lines = max(lines_drop, lines_grow)

#     insights_h = (
#         14  # title
#         + 18  # total line
#         + 18  # concentration line
#         + 24  # spacing + section headers
#         + 18  # section headers row
#         + (max_list_lines * 18)  # list lines
#         + 18  # spacing
#         + 12  # footnote
#         + 10  # bottom breathing
#     )

#     rows_h = len(items) * row_h

#     needed_h = top_pad + header_h + rows_h + 22 + insights_h + bottom_pad + 16
#     height = max(height, needed_h)

#     # ---------------- adaptive columns (HARD GUARANTEE fits in viewBox) ----------------
#     content_w = width - left_pad - right_pad
#     content_w = int(content_w)

#     # сначала задаём желаемые доли
#     name_w = max(220, int(content_w * 0.27))
#     chart_w = max(300, int(content_w * 0.34))
#     py_w = max(96, int(content_w * 0.11))
#     cy_w = max(96, int(content_w * 0.11))
#     eff_w = max(170, int(content_w * 0.17))

#     # ВАЖНО: последнюю колонку делаем остатком, чтобы НИКОГДА не вылезти вправо
#     base_w = content_w - (name_w + chart_w + py_w + cy_w + eff_w)
#     if base_w < 90:
#         # если остаток слишком мал — ужимаем chart и eff, чтобы вернуть место base
#         need = 90 - base_w
#         cut_chart = min(need, max(0, chart_w - 260))
#         chart_w -= cut_chart
#         need -= cut_chart

#         if need > 0:
#             cut_eff = min(need, max(0, eff_w - 150))
#             eff_w -= cut_eff
#             need -= cut_eff

#         base_w = content_w - (name_w + chart_w + py_w + cy_w + eff_w)
#         base_w = max(90, base_w)

#     # X позиции — строго целые
#     name_x = int(left_pad)
#     chart_x = int(name_x + name_w)
#     py_x = int(chart_x + chart_w)
#     cy_x = int(py_x + py_w)
#     eff_x = int(cy_x + cy_w)
#     base_x = int(eff_x + eff_w)

#     # финальная проверка правой границы
#     right_edge = base_x + base_w
#     target_edge = width - right_pad
#     if right_edge != target_edge:
#         # подгоняем base_w на расхождение (1-2 px из-за int)
#         base_w += (target_edge - right_edge)

#     cell_pad = 10

#     chart_mid = chart_x + chart_w / 2
#     bar_max_half = (chart_w / 2) - 16

#     # ---------------- svg ----------------
#     parts: list[str] = []
#     parts.append(
#         f'<svg xmlns="http://www.w3.org/2000/svg" '
#         f'width="100%" height="auto" '
#         f'style="display:block; max-width:100%; height:auto;" '
#         f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" role="img">'
#     )

#     parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="{bg}"/>')
#     parts.append(
#         f'<rect x="14" y="14" width="{width-28}" height="{height-28}" rx="16" fill="{card}"/>'
#     )

#     # clipPaths
#     parts.append("<defs>")
#     parts.append(f'<clipPath id="clipName"><rect x="{name_x}" y="0" width="{name_w-6}" height="{height}"/></clipPath>')
#     parts.append(f'<clipPath id="clipPY"><rect x="{py_x}" y="0" width="{py_w-6}" height="{height}"/></clipPath>')
#     parts.append(f'<clipPath id="clipCY"><rect x="{cy_x}" y="0" width="{cy_w-6}" height="{height}"/></clipPath>')
#     parts.append(f'<clipPath id="clipEff"><rect x="{eff_x}" y="0" width="{eff_w-6}" height="{height}"/></clipPath>')
#     parts.append(f'<clipPath id="clipBase"><rect x="{base_x}" y="0" width="{base_w-6}" height="{height}"/></clipPath>')
#     parts.append("</defs>")

#     # title + subtitle
#     parts.append(
#         f'<text x="{left_pad}" y="{top_pad+22}" fill="{text}" font-family="{font}" font-size="18" font-weight="700">'
#         f"{esc(title)}</text>"
#     )
#     # parts.append(
#     #     f'<text x="{left_pad}" y="{top_pad+46}" fill="{muted}" font-family="{font}" font-size="12">'
#     #     f'Сравнение {esc(py)} → {esc(cy)}: вклад групп в изменение чистой выручки (CY может быть YTD).</text>'
#     # )

#     # KPIs (в 4 блока)
#     kpi_y = top_pad + 74

#     def kpi_block(x: int, label: str, value: str) -> None:
#         parts.append(f'<text x="{x}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">{esc(label)}</text>')
#         parts.append(f'<text x="{x}" y="{kpi_y+18}" fill="{text}" font-family="{font}" font-size="13" font-weight="700">{esc(value)}</text>')

#     t_sign = "+" if total_delta >= 0 else "−"
#     delta_txt = f"{t_sign}{money0(abs(total_delta))}{fmt_pct(total_pct)}"

#     kpi_block(left_pad, f"PY ({py})", money0(total_py))
#     kpi_block(left_pad + 210, f"CY ({cy})", money0(total_cy))
#     kpi_block(left_pad + 430, "Δ (CY−PY)", delta_txt)
#     # kpi_block(left_pad + 720, "Производители (уникальные)", f"{uniq_py} → {uniq_cy}")

#     # if not overall_unique_by_year:
#     #     parts.append(
#     #         f'<text x="{left_pad+720}" y="{kpi_y+36}" fill="{muted}" font-family="{font}" font-size="10">'
#     #         f'Примечание: добавьте overall_unique_by_year в источнике для точного KPI.</text>'
#     #     )

#     # headers line
#     hdr_y = top_pad + header_h
#     parts.append(f'<line x1="{left_pad}" y1="{hdr_y}" x2="{width-right_pad}" y2="{hdr_y}" stroke="{grid}" stroke-width="1"/>')

#     parts.append(f'<text x="{name_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Группа</text>')
#     parts.append(f'<text x="{chart_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Вклад в Δ</text>')
#     parts.append(f'<text x="{py_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">PY</text>')
#     parts.append(f'<text x="{cy_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">CY</text>')
#     parts.append(f'<text x="{eff_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Выручка на производителя</text>')
#     parts.append(f'<text x="{base_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Производителей</text>')

#     # separators
#     sep_top = hdr_y - 22
#     sep_bottom = hdr_y + len(items) * row_h + 10
#     for sx in [chart_x, py_x, cy_x, eff_x, base_x]:
#         parts.append(f'<line x1="{sx}" y1="{sep_top}" x2="{sx}" y2="{sep_bottom}" stroke="{grid}" stroke-width="1"/>')

#     # axis line
#     y0 = hdr_y + 18
#     chart_top = y0 - 10
#     chart_bottom = y0 + len(items) * row_h - 10
#     parts.append(f'<line x1="{chart_mid:.1f}" y1="{chart_top}" x2="{chart_mid:.1f}" y2="{chart_bottom}" stroke="{axis}" stroke-width="1.2"/>')

#     # rows
#     for i, it in enumerate(items):
#         yy = y0 + i * row_h
#         parts.append(f'<line x1="{left_pad}" y1="{yy+row_h-6}" x2="{width-right_pad}" y2="{yy+row_h-6}" stroke="{grid}" stroke-width="1"/>')

#         raw_name = (it["name"] or "—").strip() or "—"
#         nm = ellipsis(raw_name, max(80, name_w - 14), 14)

#         parts.append(
#             f'<g clip-path="url(#clipName)">'
#             f'<text x="{name_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="14" font-weight="700">{esc(nm)}</text>'
#             f'<text x="{name_x}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">доля CY: {it["share_cy"]:.0f}%</text>'
#             f"</g>"
#         )

#         # delta bar
#         delta: Decimal = it["delta"]
#         delta_abs = abs(delta)

#         bar_y = yy + 8
#         bar_h = 18
#         rx = 4

#         parts.append(f'<rect x="{chart_x + 10}" y="{bar_y}" width="{chart_w - 20}" height="{bar_h}" rx="{rx}" fill="{bar_bg}"/>')

#         w = int((delta_abs / max_abs_delta) * Decimal(str(max(1, bar_max_half))))
#         w = max(1, w) if delta_abs > 0 else 1

#         if delta >= 0:
#             x_bar = int(chart_mid)
#             parts.append(f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{pos}"/>')
#         else:
#             x_bar = int(chart_mid - w)
#             parts.append(f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{neg}"/>')

#         sign = "+" if delta >= 0 else "−"
#         dlabel = f"{sign}{money0(delta_abs)}{fmt_pct(it['pct'])}"
#         parts.append(
#             f'<text x="{chart_x + chart_w - 10}" y="{yy+22}" fill="{muted}" font-family="{font}" font-size="11" text-anchor="end">'
#             f"{esc(dlabel)}</text>"
#         )

#         parts.append(f'<g clip-path="url(#clipPY)"><text x="{py_x + cell_pad}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_py"]))}</text></g>')
#         parts.append(f'<g clip-path="url(#clipCY)"><text x="{cy_x + cell_pad}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_cy"]))}</text></g>')

#         eff_py = it["eff_py"]
#         eff_cy = it["eff_cy"]
#         eff_delta = it["eff_delta"]
#         eff_sign = "+" if eff_delta >= 0 else "−"
#         eff_line1 = f"{money0(eff_py)} → {money0(eff_cy)}"
#         eff_line2 = f"Δ {eff_sign}{money0(abs(eff_delta))}{fmt_pct(it['eff_pct'])}"

#         parts.append(
#             f'<g clip-path="url(#clipEff)">'
#             f'<text x="{eff_x + cell_pad}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">{esc(eff_line1)}</text>'
#             f'<text x="{eff_x + cell_pad}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">{esc(eff_line2)}</text>'
#             f"</g>"
#         )

#         cnt_py = int(it["cnt_py"])
#         cnt_cy = int(it["cnt_cy"])
#         cnt_delta = cnt_cy - cnt_py
#         cnt_sign = "+" if cnt_delta >= 0 else "−"

#         parts.append(
#             f'<g clip-path="url(#clipBase)">'
#             f'<text x="{base_x + cell_pad}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">{cnt_py} → {cnt_cy}</text>'
#             f'<text x="{base_x + cell_pad}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">Δ {cnt_sign}{abs(cnt_delta)}</text>'
#             f"</g>"
#         )

#     # ---------------- Insights block (DYNAMIC HEIGHT) ----------------
#     block_y = y0 + len(items) * row_h + 22
#     parts.append(f'<line x1="{left_pad}" y1="{block_y-10}" x2="{width-right_pad}" y2="{block_y-10}" stroke="{grid}" stroke-width="1"/>')

#     parts.append(f'<text x="{left_pad}" y="{block_y+14}" fill="{text}" font-family="{font}" font-size="13" font-weight="700">Выводы по структуре и драйверам</text>')

#     total_line = f"Итого: CY {money0(total_cy)} vs PY {money0(total_py)} → Δ {t_sign}{money0(abs(total_delta))}{fmt_pct(total_pct)}."
#     parts.append(f'<text x="{left_pad}" y="{block_y+36}" fill="{muted}" font-family="{font}" font-size="12">{esc(total_line)}</text>')

#     if total_drop_abs > 0:
#         conc_line = f"Концентрация падения: топ-1 группа даёт ≈ {conc1:.0f}% падения, топ-3 — ≈ {conc3:.0f}%."
#     else:
#         conc_line = "Падение по группам не выявлено (все группы в росте или около нуля)."
#     parts.append(f'<text x="{left_pad}" y="{block_y+54}" fill="{muted}" font-family="{font}" font-size="12">{esc(conc_line)}</text>')

#     colA_x = left_pad
#     colB_x = left_pad + int((width - left_pad - right_pad) * 0.52)

#     parts.append(f'<text x="{colA_x}" y="{block_y+80}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">Топ падений</text>')
#     parts.append(f'<text x="{colB_x}" y="{block_y+80}" fill="{text}" font-family="{font}" font-size="12" font-weight="700">Топ роста</text>')

#     def driver_line(idx: int, name: str, val: Decimal, base_total: Decimal) -> str:
#         share = 0.0
#         if base_total > 0:
#             share = float((abs(val) / base_total) * Decimal("100"))
#         sgn = "−" if val < 0 else "+"
#         return f"{idx}. {name}: {sgn}{money0(abs(val))} (≈ {share:.0f}%)"

#     list_y0 = block_y + 98

#     # left list
#     if not top_drop:
#         parts.append(f'<text x="{colA_x}" y="{list_y0}" fill="{muted}" font-family="{font}" font-size="12">—</text>')
#     else:
#         y = list_y0
#         for k, x in enumerate(top_drop, start=1):
#             nm = ellipsis(str(x["name"]), int((colB_x - colA_x) * 0.95), 12)
#             parts.append(f'<text x="{colA_x}" y="{y}" fill="{muted}" font-family="{font}" font-size="12">{esc(driver_line(k, nm, x["delta"], total_drop_abs))}</text>')
#             y += 18

#     # right list
#     if not top_grow:
#         parts.append(f'<text x="{colB_x}" y="{list_y0}" fill="{muted}" font-family="{font}" font-size="12">—</text>')
#     else:
#         y = list_y0
#         base_total = total_grow_abs if total_grow_abs > 0 else Decimal("1")
#         for k, x in enumerate(top_grow, start=1):
#             nm = ellipsis(str(x["name"]), int((width - right_pad - colB_x) * 0.95), 12)
#             parts.append(f'<text x="{colB_x}" y="{y}" fill="{muted}" font-family="{font}" font-size="12">{esc(driver_line(k, nm, x["delta"], base_total))}</text>')
#             y += 18

#     # footnote (ставим НИЖЕ списков гарантированно)
#     # foot_y = list_y0 + (max_list_lines * 18) + 22
#     # base_note = f"База производителей (портфель): {uniq_py} → {uniq_cy}. Эффективность — выручка на 1 производителя внутри группы."
#     # parts.append(f'<text x="{left_pad}" y="{foot_y}" fill="{muted}" font-family="{font}" font-size="10">{esc(base_note)}</text>')

#     parts.append("</svg>")
#     return "".join(parts)








# corporate/reports/manufacturers_rootcat_mix_svg.py
# corporate/reports/manufacturers_rootcat_mix_svg.py
from __future__ import annotations

from decimal import Decimal
from typing import Any

from corporate.reports.manufacturers_revenue_summary import fmt_money_ru


def build_rootcat_mix_svg(
    years: list[str],
    rootcat_rows: list[dict[str, Any]],
    *,
    title: str | None = None,
    width: int = 1100,
    height: int = 520,
    left_pad: int = 56,
    right_pad: int = 26,
    top_pad: int = 22,
    bottom_pad: int = 26,
    font: str = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
    max_rows: int = 10,
) -> str:
    if not years or not rootcat_rows:
        return ""

    # years: unique + sorted (устойчиво, даже если пришёл set/неотсортированный список)
    years = sorted({str(y) for y in years})
    if len(years) < 2:
        return ""

    py, cy = years[-2], years[-1]

    # ---------------- helpers ----------------
    def esc(s: Any) -> str:
        s = str(s or "")
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    if title is None:
        title = f"Производители по группам категорий и их выручка: {py} → {cy}"
    else:
        # чтобы годы ВСЕГДА были в заголовке
        if f"{py}" not in title and f"{cy}" not in title:
            title = f"{title}: {py} → {cy}"

    def to_dec(x: Any) -> Decimal:
        try:
            return x if isinstance(x, Decimal) else Decimal(str(x or "0"))
        except Exception:
            return Decimal("0")

    def safe_pct(delta: Decimal, base: Decimal) -> float | None:
        if base <= 0:
            return None
        return float((delta / base) * Decimal("100"))

    def money0(v: Decimal) -> str:
        return fmt_money_ru(v) if v else "0\u00A0₽"

    def fmt_pct(p: float | None) -> str:
        if p is None:
            return ""
        sgn = "+" if p >= 0 else "−"
        return f" ({sgn}{abs(p):.0f}%)"

    # грубая оценка ширины символов (для обрезки)
    def ellipsis(text: str, max_px: int, font_size: int = 14) -> str:
        if not text:
            return "—"
        approx_char_px = max(6, int(font_size * 0.56))
        max_chars = max(4, max_px // approx_char_px)
        if len(text) <= max_chars:
            return text
        if max_chars <= 6:
            return text[:max_chars]
        return text[: max_chars - 1] + "…"

    # ---------------- build items from rows ----------------
    items: list[dict[str, Any]] = []
    total_py = Decimal("0")
    total_cy = Decimal("0")

    for r in rootcat_rows:
        name = (r.get("root_name") or "—").strip() or "—"
        rev_map = r.get("revenue") or {}
        cnt_map = r.get("counts") or {}

        rev_py = to_dec(rev_map.get(py, 0))
        rev_cy = to_dec(rev_map.get(cy, 0))
        cnt_py = int(cnt_map.get(py, 0) or 0)
        cnt_cy = int(cnt_map.get(cy, 0) or 0)

        total_py += rev_py
        total_cy += rev_cy

        delta = rev_cy - rev_py
        pct = safe_pct(delta, rev_py) if rev_py > 0 else None

        eff_py = (rev_py / Decimal(cnt_py)) if cnt_py > 0 else Decimal("0")
        eff_cy = (rev_cy / Decimal(cnt_cy)) if cnt_cy > 0 else Decimal("0")
        eff_delta = eff_cy - eff_py
        eff_pct = safe_pct(eff_delta, eff_py) if eff_py > 0 else None

        items.append(
            {
                "name": name,
                "rev_py": rev_py,
                "rev_cy": rev_cy,
                "cnt_py": cnt_py,
                "cnt_cy": cnt_cy,
                "delta": delta,
                "pct": pct,
                "eff_py": eff_py,
                "eff_cy": eff_cy,
                "eff_delta": eff_delta,
                "eff_pct": eff_pct,
            }
        )

    if total_py <= 0 and total_cy <= 0:
        return ""

    total_delta = total_cy - total_py
    total_pct = safe_pct(total_delta, total_py) if total_py > 0 else None

    for it in items:
        it["share_cy"] = float((it["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

    # сортировка: главные драйверы изменений
    items.sort(key=lambda x: abs(x["delta"]), reverse=True)

    # ограничение строк + "Прочие"
    if len(items) > max_rows:
        top = items[: max_rows - 1]
        rest = items[max_rows - 1 :]

        agg_py = sum((x["rev_py"] for x in rest), Decimal("0"))
        agg_cy = sum((x["rev_cy"] for x in rest), Decimal("0"))
        agg_cnt_py = sum((x["cnt_py"] for x in rest))
        agg_cnt_cy = sum((x["cnt_cy"] for x in rest))

        agg = {
            "name": "Прочие",
            "rev_py": agg_py,
            "rev_cy": agg_cy,
            "cnt_py": agg_cnt_py,
            "cnt_cy": agg_cnt_cy,
        }
        agg["delta"] = agg["rev_cy"] - agg["rev_py"]
        agg["pct"] = safe_pct(agg["delta"], agg["rev_py"]) if agg["rev_py"] > 0 else None
        agg["eff_py"] = (agg["rev_py"] / Decimal(agg["cnt_py"])) if agg["cnt_py"] > 0 else Decimal("0")
        agg["eff_cy"] = (agg["rev_cy"] / Decimal(agg["cnt_cy"])) if agg["cnt_cy"] > 0 else Decimal("0")
        agg["eff_delta"] = agg["eff_cy"] - agg["eff_py"]
        agg["eff_pct"] = safe_pct(agg["eff_delta"], agg["eff_py"]) if agg["eff_py"] > 0 else None
        agg["share_cy"] = float((agg["rev_cy"] / total_cy) * Decimal("100")) if total_cy > 0 else 0.0

        items = top + [agg]

    max_abs_delta = max((abs(it["delta"]) for it in items), default=Decimal("1"))
    if max_abs_delta <= 0:
        max_abs_delta = Decimal("1")

    # ---------------- style ----------------
    bg = "#ffffff"
    card = "#ffffff"
    text = "rgba(15,23,42,.92)"
    muted = "rgba(15,23,42,.62)"
    grid = "rgba(15,23,42,.10)"
    axis = "rgba(15,23,42,.22)"

    pos = "#2563eb"
    neg = "#ef4444"
    bar_bg = "rgba(15,23,42,.07)"

    # ---------------- layout ----------------
    header_h = 118
    row_h = 46

    rows_h = len(items) * row_h

    # Выводы убраны => высоту под них НЕ закладываем
    needed_h = top_pad + header_h + rows_h + bottom_pad + 16
    height = max(height, needed_h)

    # ---------------- adaptive columns (HARD GUARANTEE fits in viewBox) ----------------
    content_w = int(width - left_pad - right_pad)

    name_w = max(220, int(content_w * 0.27))
    chart_w = max(300, int(content_w * 0.34))
    py_w = max(96, int(content_w * 0.11))
    cy_w = max(96, int(content_w * 0.11))
    eff_w = max(170, int(content_w * 0.17))

    # последняя колонка — остаток
    base_w = content_w - (name_w + chart_w + py_w + cy_w + eff_w)
    if base_w < 90:
        need = 90 - base_w
        cut_chart = min(need, max(0, chart_w - 260))
        chart_w -= cut_chart
        need -= cut_chart

        if need > 0:
            cut_eff = min(need, max(0, eff_w - 150))
            eff_w -= cut_eff
            need -= cut_eff

        base_w = content_w - (name_w + chart_w + py_w + cy_w + eff_w)
        base_w = max(90, base_w)

    name_x = int(left_pad)
    chart_x = int(name_x + name_w)
    py_x = int(chart_x + chart_w)
    cy_x = int(py_x + py_w)
    eff_x = int(cy_x + cy_w)
    base_x = int(eff_x + eff_w)

    right_edge = base_x + base_w
    target_edge = width - right_pad
    if right_edge != target_edge:
        base_w += (target_edge - right_edge)

    cell_pad = 10
    chart_mid = chart_x + chart_w / 2
    bar_max_half = (chart_w / 2) - 16

    # ---------------- svg ----------------
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" height="auto" '
        f'style="display:block; max-width:100%; height:auto;" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" role="img">'
    )

    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="{bg}"/>')
    parts.append(f'<rect x="14" y="14" width="{width-28}" height="{height-28}" rx="16" fill="{card}"/>')

    # clipPaths
    parts.append("<defs>")
    parts.append(f'<clipPath id="clipName"><rect x="{name_x}" y="0" width="{name_w-6}" height="{height}"/></clipPath>')
    parts.append(f'<clipPath id="clipPY"><rect x="{py_x}" y="0" width="{py_w-6}" height="{height}"/></clipPath>')
    parts.append(f'<clipPath id="clipCY"><rect x="{cy_x}" y="0" width="{cy_w-6}" height="{height}"/></clipPath>')
    parts.append(f'<clipPath id="clipEff"><rect x="{eff_x}" y="0" width="{eff_w-6}" height="{height}"/></clipPath>')
    parts.append(f'<clipPath id="clipBase"><rect x="{base_x}" y="0" width="{base_w-6}" height="{height}"/></clipPath>')
    parts.append("</defs>")

    # title
    parts.append(
        f'<text x="{left_pad}" y="{top_pad+22}" fill="{text}" font-family="{font}" font-size="18" font-weight="700">'
        f"{esc(title)}</text>"
    )

    # KPIs (сабтайтл убран — поднимаем KPI ближе к заголовку)
    kpi_y = top_pad + 66

    def kpi_block(x: int, label: str, value: str) -> None:
        parts.append(
            f'<text x="{x}" y="{kpi_y}" fill="{muted}" font-family="{font}" font-size="11">{esc(label)}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{kpi_y+18}" fill="{text}" font-family="{font}" font-size="13" font-weight="700">{esc(value)}</text>'
        )

    t_sign = "+" if total_delta >= 0 else "−"
    delta_txt = f"{t_sign}{money0(abs(total_delta))}{fmt_pct(total_pct)}"

    kpi_block(left_pad, f"PY ({py})", money0(total_py))
    kpi_block(left_pad + 210, f"CY ({cy})", money0(total_cy))
    kpi_block(left_pad + 430, "Δ (CY−PY)", delta_txt)

    # headers line
    hdr_y = top_pad + header_h
    parts.append(
        f'<line x1="{left_pad}" y1="{hdr_y}" x2="{width-right_pad}" y2="{hdr_y}" stroke="{grid}" stroke-width="1"/>'
    )

    parts.append(f'<text x="{name_x}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Группа</text>')
    parts.append(f'<text x="{chart_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Вклад в Δ</text>')
    parts.append(f'<text x="{py_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">PY ({esc(py)})</text>')
    parts.append(f'<text x="{cy_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">CY ({esc(cy)})</text>')
    parts.append(f'<text x="{eff_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Выручка на производителя</text>')
    parts.append(f'<text x="{base_x + cell_pad}" y="{hdr_y-8}" fill="{muted}" font-family="{font}" font-size="11">Производителей</text>')

    # separators
    sep_top = hdr_y - 22
    sep_bottom = hdr_y + len(items) * row_h + 10
    for sx in [chart_x, py_x, cy_x, eff_x, base_x]:
        parts.append(f'<line x1="{sx}" y1="{sep_top}" x2="{sx}" y2="{sep_bottom}" stroke="{grid}" stroke-width="1"/>')

    # axis line
    y0 = hdr_y + 18
    chart_top = y0 - 10
    chart_bottom = y0 + len(items) * row_h - 10
    parts.append(
        f'<line x1="{chart_mid:.1f}" y1="{chart_top}" x2="{chart_mid:.1f}" y2="{chart_bottom}" stroke="{axis}" stroke-width="1.2"/>'
    )

    # rows
    for i, it in enumerate(items):
        yy = y0 + i * row_h
        parts.append(
            f'<line x1="{left_pad}" y1="{yy+row_h-6}" x2="{width-right_pad}" y2="{yy+row_h-6}" stroke="{grid}" stroke-width="1"/>'
        )

        raw_name = (it["name"] or "—").strip() or "—"
        nm = ellipsis(raw_name, max(80, name_w - 14), 14)

        parts.append(
            f'<g clip-path="url(#clipName)">'
            f'<text x="{name_x}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="14" font-weight="700">{esc(nm)}</text>'
            f'<text x="{name_x}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">доля CY: {it["share_cy"]:.0f}%</text>'
            f"</g>"
        )

        # delta bar
        delta: Decimal = it["delta"]
        delta_abs = abs(delta)

        bar_y = yy + 8
        bar_h = 18
        rx = 4

        parts.append(
            f'<rect x="{chart_x + 10}" y="{bar_y}" width="{chart_w - 20}" height="{bar_h}" rx="{rx}" fill="{bar_bg}"/>'
        )

        w = int((delta_abs / max_abs_delta) * Decimal(str(max(1, bar_max_half))))
        w = max(1, w) if delta_abs > 0 else 1

        if delta >= 0:
            x_bar = int(chart_mid)
            parts.append(f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{pos}"/>')
        else:
            x_bar = int(chart_mid - w)
            parts.append(f'<rect x="{x_bar}" y="{bar_y}" width="{w}" height="{bar_h}" rx="{rx}" fill="{neg}"/>')

        sign = "+" if delta >= 0 else "−"
        dlabel = f"{sign}{money0(delta_abs)}{fmt_pct(it['pct'])}"
        parts.append(
            f'<text x="{chart_x + chart_w - 10}" y="{yy+22}" fill="{muted}" font-family="{font}" font-size="11" text-anchor="end">'
            f"{esc(dlabel)}</text>"
        )

        parts.append(
            f'<g clip-path="url(#clipPY)"><text x="{py_x + cell_pad}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_py"]))}</text></g>'
        )
        parts.append(
            f'<g clip-path="url(#clipCY)"><text x="{cy_x + cell_pad}" y="{yy+22}" fill="{text}" font-family="{font}" font-size="12">{esc(money0(it["rev_cy"]))}</text></g>'
        )

        eff_py = it["eff_py"]
        eff_cy = it["eff_cy"]
        eff_delta = it["eff_delta"]
        eff_sign = "+" if eff_delta >= 0 else "−"
        eff_line1 = f"{money0(eff_py)} → {money0(eff_cy)}"
        eff_line2 = f"Δ {eff_sign}{money0(abs(eff_delta))}{fmt_pct(it['eff_pct'])}"

        parts.append(
            f'<g clip-path="url(#clipEff)">'
            f'<text x="{eff_x + cell_pad}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">{esc(eff_line1)}</text>'
            f'<text x="{eff_x + cell_pad}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">{esc(eff_line2)}</text>'
            f"</g>"
        )

        cnt_py = int(it["cnt_py"])
        cnt_cy = int(it["cnt_cy"])
        cnt_delta = cnt_cy - cnt_py
        cnt_sign = "+" if cnt_delta >= 0 else "−"

        parts.append(
            f'<g clip-path="url(#clipBase)">'
            f'<text x="{base_x + cell_pad}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">{cnt_py} → {cnt_cy}</text>'
            f'<text x="{base_x + cell_pad}" y="{yy+36}" fill="{muted}" font-family="{font}" font-size="11">Δ {cnt_sign}{abs(cnt_delta)}</text>'
            f"</g>"
        )

    parts.append("</svg>")
    return "".join(parts)