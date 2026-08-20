# sales/reports/sales_digest/charts.py
"""
Собственные графики Sales Digest.

Раньше секции I и II использовали графики из старого sales_report
(kpi_compare_chart.py и store_chart.py) — их совсем не трогаем в самом
sales_report, но здесь для НОВОГО отчёта рисуем свои: старый график
сравнения (Δ%) собирался вручную как SVG с CSS-стилями в <style>, которые
WeasyPrint не всегда корректно применяет к тексту (font: shorthand) — на
печати это разваливалось в нечитаемые перекрывающиеся фигуры. Старый
график по магазинам был технически исправен, но нарисован в чужой
сине-серой палитре, которая не сочетается с тёплой газетной темой
COSMORELAX.

Оба новых графика используют ту же самую инфраструктуру, что и newspaper
(matplotlib -> SVG, шрифты переводятся в контуры через svg.fonttype=path —
поэтому WeasyPrint всегда рендерит их одинаково, без сюрпризов), и ту же
цветовую палитру.
"""

from __future__ import annotations

import textwrap
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd

from ..newspaper.charts.common import apply_style, fig_to_svg, new_figure
from ..newspaper.config import (
    COLOR_ACCENT,
    COLOR_BRAND_DEEP,
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    COLOR_RULE,
)
from ..newspaper.render.helpers import fmt_money_short, fmt_qty
from ..sales_report.formatters import fmt_delta_short


def _is_num(x) -> bool:
    try:
        return x is not None and float(x) == float(x)
    except Exception:
        return False


def build_compare_delta_chart(compare: dict) -> str:
    """
    Диаграмма отклонений (Δ%) по ключевым метрикам периода — сравнение с
    предыдущим сопоставимым периодом и с аналогичным периодом прошлого
    года. Горизонтальные парные полосы от нулевой линии, цвет полосы —
    хорошо/плохо (для возвратов направление инвертировано).
    """
    items = compare.get("chart") or []
    items = [it for it in items if _is_num(it.get("prev_pct")) or _is_num(it.get("ly_pct"))]
    if not items:
        return ""

    prev_label = (compare.get("prev") or {}).get("label", "предыдущий период")
    ly_label = (compare.get("ly") or {}).get("label", "прошлый год")

    apply_style()
    n = len(items)
    height_in = 0.62 * n + 1.0
    fig, ax = new_figure(width_in=6.0, height_in=height_in)

    y_prev = [i + 0.17 for i in range(n)]
    y_ly = [i - 0.17 for i in range(n)]

    def tone(v: Optional[float], invert: bool) -> str:
        if v is None:
            return COLOR_INK_SOFT
        good = (v < 0) if invert else (v > 0)
        return COLOR_POSITIVE if good else COLOR_NEGATIVE

    prev_vals = [float(it["prev_pct"]) if _is_num(it.get("prev_pct")) else 0.0 for it in items]
    ly_vals = [float(it["ly_pct"]) if _is_num(it.get("ly_pct")) else 0.0 for it in items]

    prev_colors = [tone(it.get("prev_pct"), it.get("invert", False)) for it in items]
    ly_colors = [tone(it.get("ly_pct"), it.get("invert", False)) for it in items]

    bar_h = 0.3
    ax.barh(y_prev, prev_vals, height=bar_h, color=prev_colors, zorder=3, alpha=0.95)
    ax.barh(y_ly, ly_vals, height=bar_h, color=ly_colors, zorder=3, alpha=0.55,
            hatch="////", edgecolor="#ffffff", linewidth=0.4)

    ax.axvline(0, color=COLOR_INK, linewidth=1.0, zorder=2)

    max_abs = max([abs(v) for v in prev_vals + ly_vals] + [5.0]) * 1.35
    ax.set_xlim(-max_abs, max_abs)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks(list(range(n)))
    ax.set_yticklabels([it.get("title", "") for it in items], fontsize=9.4, color=COLOR_INK, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for y, v in zip(y_prev, prev_vals):
        sign = "+" if v > 0 else ("" if v == 0 else "")
        ax.text(
            v + (max_abs * 0.02 if v >= 0 else -max_abs * 0.02), y,
            f"{sign}{v:.1f}%", va="center", ha="left" if v >= 0 else "right",
            fontsize=8.4, color=COLOR_INK, fontweight="bold",
        )
    for y, v in zip(y_ly, ly_vals):
        sign = "+" if v > 0 else ("" if v == 0 else "")
        ax.text(
            v + (max_abs * 0.02 if v >= 0 else -max_abs * 0.02), y,
            f"{sign}{v:.1f}%", va="center", ha="left" if v >= 0 else "right",
            fontsize=8.4, color=COLOR_INK_SOFT,
        )

    # --- легенда серий: ТОЛЬКО про заливку/штриховку (сплошная / штрих),
    # т.к. цвет полосы занят другим смыслом (хорошо/плохо) — если сделать
    # цветные образцы в легенде, это выглядит так, будто "прошлая неделя
    # = такой-то цвет", а на самом деле цвет каждый раз разный (зависит от
    # знака отклонения), и легенда с реальными цветами полос не совпадает.
    # Поэтому образцы легенды нейтрально-серые, различаются только текстурой.
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor=COLOR_INK_SOFT, alpha=0.9, label=prev_label),
        Patch(facecolor=COLOR_INK_SOFT, alpha=0.55, hatch="////", edgecolor="#ffffff", label=ly_label),
    ]
    ax.legend(
        handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, 1.0 + 1.2 / height_in),
        frameon=False, fontsize=8.2, ncol=2, handlelength=1.3, handleheight=1.1,
        labelcolor=COLOR_INK_SOFT,
    )

    # --- сноска: что означает цвет полос (это НЕ серия, а знак отклонения) ---
    ax.text(
        0.5, -0.08,
        "Зелёный — улучшение показателя, терракотовый — ухудшение"
        " (для «Возвраты» направление инвертировано: меньше — лучше).",
        transform=ax.transAxes, ha="center", va="top",
        fontsize=7.4, color=COLOR_INK_SOFT, style="italic",
    )

    return fig_to_svg(fig)


def _top_and_tail(store_rows_raw: list[dict], top_n: int) -> tuple[list[str], list[float], int]:
    rows = [r for r in (store_rows_raw or []) if (r.get("amount") or 0) > 0]
    rows.sort(key=lambda r: float(r.get("amount") or 0), reverse=True)

    head = rows[:top_n]
    tail = rows[top_n:]

    labels = [r["store"] for r in head]
    values = [float(r.get("amount") or 0) for r in head]

    tail_n = 0
    if tail:
        tail_sum = sum(float(r.get("amount") or 0) for r in tail)
        labels.append(f"Остальные ({len(tail)})")
        values.append(tail_sum)
        tail_n = len(tail)

    return labels, values, tail_n


def build_stores_amount_chart(store_rows_raw: list[dict], top_n: int = 10) -> str:
    """
    Чистая выручка по магазинам — горизонтальный бар-чарт, топ-N магазинов
    по убыванию, остальные агрегируются в одну полосу "Остальные", чтобы
    график не расползался на десятки узких строк. Рассчитан на левую
    колонку разворота (рядом — круговая диаграмма долей, см.
    build_stores_share_pie), поэтому уже, чем полностраничные графики.
    """
    labels, values, tail_n = _top_and_tail(store_rows_raw, top_n)
    if not labels:
        return ""

    apply_style()
    n = len(labels)
    height_in = min(0.4 * n + 0.6, 5.2)
    fig, ax = new_figure(width_in=3.5, height_in=height_in)

    y_pos = list(range(n))
    head_n = n - (1 if tail_n else 0)
    colors = [COLOR_BRAND_DEEP] * head_n + (["#8c9188"] if tail_n else [])
    if head_n:
        colors[0] = COLOR_ACCENT  # лидер продаж — акцентный цвет

    ax.barh(y_pos, values, color=colors, height=0.62, zorder=3)

    max_x = max(values) * 1.28
    ax.set_xlim(0, max_x)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.2, color=COLOR_INK)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for y, v in zip(y_pos, values):
        ax.text(
            v + max_x * 0.02, y, fmt_money_short(v),
            va="center", ha="left", fontsize=7.6, color=COLOR_INK_SOFT, fontweight="bold",
        )

    return fig_to_svg(fig)


def build_stores_share_pie(store_rows_raw: list[dict], max_slices: int = 6) -> str:
    """
    Доли магазинов в чистой выручке — донат-диаграмма (правая колонка
    разворота, рядом со столбиками build_stores_amount_chart). Мелкие
    магазины сверх max_slices агрегируются в "Остальные", чтобы диаграмма
    не превращалась в десяток нечитаемых узких долек.
    """
    import matplotlib.pyplot as plt

    apply_style()

    rows = [r for r in (store_rows_raw or []) if (r.get("amount") or 0) > 0]
    rows.sort(key=lambda r: float(r.get("amount") or 0), reverse=True)
    if not rows:
        return ""

    total = sum(float(r.get("amount") or 0) for r in rows)
    if total <= 0:
        return ""

    head = rows[:max_slices]
    tail = rows[max_slices:]

    labels = [r["store"] for r in head]
    values = [float(r.get("amount") or 0) for r in head]

    if tail:
        tail_sum = sum(float(r.get("amount") or 0) for r in tail)
        labels.append(f"Остальные ({len(tail)})")
        values.append(tail_sum)

    from ..newspaper.config import CHART_PALETTE
    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(3.5, 3.2), dpi=150)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "#faf8f4", "linewidth": 1.2},
    )
    ax.set_aspect("equal")

    ax.text(0, 0.08, "Итого", ha="center", va="center", fontsize=8.2, color=COLOR_INK_SOFT)
    ax.text(0, -0.08, fmt_money_short(total), ha="center", va="center",
            fontsize=11.5, color=COLOR_INK, fontweight="bold")

    legend_labels = [
        f"{label} — {value / total * 100:.0f}%"
        for label, value in zip(labels, values)
    ]
    ax.legend(
        wedges, legend_labels,
        loc="center left", bbox_to_anchor=(1.02, 0.5),
        frameon=False, fontsize=7.6, labelspacing=0.9,
        handlelength=1.1, handleheight=1.1,
    )

    return fig_to_svg(fig)


def build_trend_chart(trend: list[dict], metric_key: str = "amount_raw") -> str:
    """
    Динамика по N аналогичным периодам (обычно — тот же день недели, шаг
    7 дней) — линия с мягкой заливкой, пунктирная линия среднего и
    подсвеченная последняя точка ("сегодня"/текущий период). Раньше этот
    график рисовался вручную в чужой сине-розовой палитре (Material-стиль)
    и не имел ничего общего с остальным отчётом — здесь та же логика
    (значение, среднее, точка "сейчас"), но в теме COSMORELAX.
    """
    rows = [t for t in (trend or []) if _is_num(t.get(metric_key))]
    if not rows:
        return ""

    values = [float(t[metric_key]) for t in rows]
    labels = [str(t.get("label", "")) for t in rows]
    n = len(values)
    curr_idx = next((i for i, t in enumerate(rows) if t.get("is_current")), n - 1)
    avg = sum(values) / n

    apply_style()
    fig, ax = new_figure(width_in=7.4, height_in=1.25)

    xs = list(range(n))
    ax.plot(xs, values, color=COLOR_BRAND_DEEP, linewidth=2.0, zorder=4,
            marker="o", markersize=4.2, markerfacecolor=COLOR_BRAND_DEEP,
            markeredgecolor="#faf8f4", markeredgewidth=0.8)
    ax.fill_between(xs, values, min(values) * 0.0, color=COLOR_BRAND_DEEP, alpha=0.08, zorder=2)

    ax.axhline(avg, color=COLOR_INK_SOFT, linewidth=1.0, linestyle=(0, (3, 3)), zorder=3)
    # подпись "среднее" — сразу за левым краем осей (blended transform: X —
    # доля осей, Y — данные), фиксированный крошечный отступ вместо смещения
    # в единицах данных — иначе итоговый tight-bbox "плавает" непредсказуемо
    # при рендере в PDF и график может внезапно раздуться по высоте.
    ax.text(-0.01, avg, "среднее", va="center", ha="right", fontsize=7.6, color=COLOR_INK_SOFT,
            transform=ax.get_yaxis_transform())

    # текущая точка — акцентный маркер + подпись значения (однострочная,
    # смещение в ТОЧКАХ, а не в единицах данных — иначе на печати из-за
    # tight-bbox итоговая высота графика "плавает" и может неожиданно
    # раздуться в несколько раз при масштабировании under CSS width:100%).
    ax.scatter([xs[curr_idx]], [values[curr_idx]], color=COLOR_ACCENT, s=70, zorder=5,
               edgecolors="#faf8f4", linewidths=1.0)
    va = "bottom" if values[curr_idx] < max(values) else "top"
    offset_pts = 10 if va == "bottom" else -10
    ax.annotate(
        f"{labels[curr_idx]}: {fmt_money_short(values[curr_idx])}",
        xy=(xs[curr_idx], values[curr_idx]),
        xytext=(0, offset_pts), textcoords="offset points",
        ha="center", va=va, fontsize=7.8, color=COLOR_INK, fontweight="bold",
    )

    # Разреженные подписи по X (все 13 периодов и так перечислены в таблице
    # выше — на графике достаточно первой/средних/последней, иначе подписи
    # либо накладываются, либо (при повороте) сильно раздувают высоту).
    tick_idx = sorted(set([0, n // 4, n // 2, (3 * n) // 4, n - 1]))
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([labels[i] for i in tick_idx], fontsize=6.2, color=COLOR_INK_SOFT)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.margins(y=0.28)

    return fig_to_svg(fig)


def _build_cum_chart(
    series_cur: list[dict],
    series_ly: list[dict],
    width_in: float,
    height_in: float,
    n_ticks: int = 4,
) -> str:
    """
    Общий "движок" для накопительных графиков (MTD/YTD): текущий год —
    сплошная линия с мягкой заливкой и лёгкой сеткой по Y; прошлый год —
    пунктир. Единая COSMORELAX-палитра вместо старых "чужих" синего/
    розового цветов.
    """
    if not series_cur:
        return ""

    n = len(series_cur)
    cur_vals = [float(p["cum_raw"]) for p in series_cur]
    ly_vals = [float(p["cum_raw"]) for p in series_ly[:n]] if series_ly else []

    apply_style()
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    # лёгкая горизонтальная сетка — помогает читать масштаб без "шума"
    top_val = max(cur_vals + ly_vals + [1.0])
    for frac in (0.25, 0.5, 0.75, 1.0):
        ax.axhline(top_val * frac, color=COLOR_RULE, linewidth=0.6, zorder=1)

    xs = list(range(n))
    ax.fill_between(xs, cur_vals, 0, color=COLOR_BRAND_DEEP, alpha=0.10, zorder=2)
    ax.plot(xs, cur_vals, color=COLOR_BRAND_DEEP, linewidth=2.2, zorder=4, label="Текущий год")

    if ly_vals:
        xs_ly = list(range(len(ly_vals)))
        ax.plot(xs_ly, ly_vals, color=COLOR_INK_SOFT, linewidth=1.6, zorder=3,
                linestyle=(0, (4, 3)), label="Прошлый год")

    # конечная точка текущего года
    ax.scatter([xs[-1]], [cur_vals[-1]], color=COLOR_ACCENT, s=55, zorder=5,
               edgecolors="#faf8f4", linewidths=0.9)
    ax.annotate(
        fmt_money_short(cur_vals[-1]),
        xy=(xs[-1], cur_vals[-1]), xytext=(-4, 9), textcoords="offset points",
        ha="right", va="bottom", fontsize=8.4, color=COLOR_INK, fontweight="bold",
    )

    if ly_vals:
        ax.scatter([len(ly_vals) - 1], [ly_vals[-1]], color=COLOR_INK_SOFT, s=32, zorder=4,
                   edgecolors="#faf8f4", linewidths=0.8)

    step = max(1, (n - 1) // n_ticks) if n > 1 else 1
    tick_idx = sorted(set(list(range(0, n, step)) + [n - 1]))
    # если последний "регулярный" тик слишком близко к финальной точке —
    # убираем его, иначе подписи "17.08"/"18.08" налезают друг на друга
    if len(tick_idx) >= 2 and (tick_idx[-1] - tick_idx[-2]) < max(1, step // 2):
        tick_idx.pop(-2)
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([series_cur[i]["label"] for i in tick_idx], fontsize=6.2, color=COLOR_INK_SOFT)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.margins(y=0.2)
    ax.set_xlim(-0.5, n - 0.5)

    # Легенда — ВНУТРИ осей (без bbox_to_anchor за пределами axes): якорь
    # выше 1.0 в сочетании с bbox_inches="tight" при сохранении в SVG иногда
    # раздувает итоговый bbox фигуры в несколько раз (WeasyPrint потом
    # получает "гигантский" svg и разваливает вёрстку страницы).
    ax.legend(
        loc="upper left",
        frameon=False,
        fontsize=6.4,
        labelcolor=COLOR_INK_SOFT,
        handlelength=1.15,
        handleheight=0.8,
        labelspacing=0.45,
        borderaxespad=0.2,
    )

    return fig_to_svg(fig)


def build_mtd_cum_chart(mtd_cum_ctx: dict, width_in: float = 4.3, height_in: float = 1.6) -> str:
    """
    Накопленная выручка нарастающим итогом (MTD, текущий год vs прошлый) —
    замена старого графика с "чужими" синим/розовым цветами (#4da3ff /
    #e91e63), которые визуально выбивались из тёплой темы COSMORELAX.
    """
    return _build_cum_chart(
        mtd_cum_ctx.get("series_cur") or [],
        mtd_cum_ctx.get("series_ly") or [],
        width_in=width_in, height_in=height_in, n_ticks=4,
    )


def build_ytd_cum_chart(ytd_cum_ctx: dict, width_in: float = 4.3, height_in: float = 1.6) -> str:
    """
    То же самое, что build_mtd_cum_chart, но для YTD (больше точек на оси —
    почти год дневных данных, поэтому подписи по X реже).
    """
    return _build_cum_chart(
        ytd_cum_ctx.get("series_cur") or [],
        ytd_cum_ctx.get("series_ly") or [],
        width_in=width_in, height_in=height_in, n_ticks=6,
    )


def _short_label(label: str, max_len: int = 16) -> str:
    label = str(label)
    return label if len(label) <= max_len else label[: max_len - 1] + "…"


def build_categories_waterfall_chart(
    df_raw: pd.DataFrame,
    top_n: int = 8,
    width_in: float = 8.7,
    height_in: float = 1.6,
) -> str:
    """
    "Вклад категорий в изменение выручки" (MTD/YTD, текущий год к прошлому)
    в теме COSMORELAX — тот же каскадный принцип, что и в старом отчёте
    (categories_waterfall_mtd/ytd.py), но перерисован средствами matplotlib
    в общей палитре/шрифтах отчёта (там был отдельный slate/red-green SVG,
    не сочетавшийся с остальными графиками), и компактнее, чтобы уверенно
    помещаться на одну страницу вместе с таблицей и текстом.
    """
    if df_raw is None or df_raw.empty:
        return ""

    df = df_raw.copy()
    for c in ("year", "cat_name", "amount"):
        if c not in df.columns:
            return ""
    if "quant" not in df.columns:
        df["quant"] = 0.0

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["quant"] = pd.to_numeric(df["quant"], errors="coerce").fillna(0.0)
    df["cat_name"] = df["cat_name"].fillna("Без категории").astype(str)

    years = sorted(df["year"].dropna().unique())
    if len(years) < 2:
        return ""
    y_prev, y_curr = years[-2], years[-1]

    ga = (
        df.groupby(["year", "cat_name"], as_index=False)["amount"].sum()
        .pivot(index="cat_name", columns="year", values="amount")
        .fillna(0.0)
    )
    for y in (y_prev, y_curr):
        if y not in ga.columns:
            ga[y] = 0.0
    ga["delta"] = ga[y_curr] - ga[y_prev]

    gq = (
        df.groupby(["year", "cat_name"], as_index=False)["quant"].sum()
        .pivot(index="cat_name", columns="year", values="quant")
        .fillna(0.0)
    )
    for y in (y_prev, y_curr):
        if y not in gq.columns:
            gq[y] = 0.0
    ga["delta_qty"] = gq[y_curr] - gq[y_prev]

    g2 = ga.sort_values("delta", key=lambda s: s.abs(), ascending=False)
    main = g2.head(top_n)
    rest = g2.iloc[top_n:]

    items: list[dict] = []
    for name, row in main.iterrows():
        items.append({"label": str(name), "delta": float(row["delta"]), "qty": float(row.get("delta_qty", 0.0))})
    if not rest.empty:
        items.append({
            "label": f"Прочие ({len(rest)})",
            "delta": float(rest["delta"].sum()),
            "qty": float(rest["delta_qty"].sum()) if "delta_qty" in rest.columns else 0.0,
            "is_other": True,
        })

    n = len(items)
    if n == 0:
        return ""

    levels = [0.0]
    for it in items:
        levels.append(levels[-1] + it["delta"])

    apply_style()
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    all_levels = levels + [0.0]
    span = max(all_levels) - min(all_levels) or 1.0
    pad = span * 0.16

    xs = list(range(n))
    for i, it in enumerate(items):
        start, end = levels[i], levels[i + 1]
        bottom = min(start, end)
        h = max(abs(end - start), span * 0.004)
        color = COLOR_POSITIVE if it["delta"] >= 0 else COLOR_NEGATIVE
        ax.bar(i, h, bottom=bottom, width=0.6, color=color, zorder=3)

        if i < n - 1:
            ax.plot([i + 0.3, i + 1 - 0.3], [end, end], color=COLOR_RULE,
                     linewidth=0.9, linestyle=(0, (2, 2)), zorder=2)

        money_txt = fmt_delta_short(it["delta"])
        qty_txt = (
                    ""
                    if it.get("is_other") or not it["qty"]
                    else f"({'+' if it['qty'] > 0 else '−'}{fmt_qty(abs(it['qty']))} шт)"
                )
        label_txt = f"{money_txt}\n{qty_txt}" if qty_txt else money_txt

        va = "bottom" if it["delta"] >= 0 else "top"
        y_txt = end + (pad * 0.22 if va == "bottom" else -pad * 0.22)
        ax.text(
            i,
            y_txt,
            label_txt,
            ha="center",
            va=va,
            fontsize=6.6,
            color=COLOR_INK,
            fontweight="normal",
            linespacing=1.15,
        )

    ax.axhline(0, color=COLOR_INK, linewidth=1.0, zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(
            [_short_label(it["label"], 14) for it in items],
            fontsize=6.4,
            color=COLOR_INK_SOFT,
        )
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylim(min(all_levels) - pad, max(all_levels) + pad)
    ax.set_xlim(-0.6, n - 0.4)

    return fig_to_svg(fig)


def build_manager_bar_chart(
    df: pd.DataFrame,
    top_n: int = 8,
    name_col: str = "manager_name",
    amount_col: str = "amount",
    width_in: float = 4.4,
    height_in: Optional[float] = None,
) -> str:
    """
    ТОП менеджеров по чистой выручке — компактный горизонтальный бар-чарт в
    теме COSMORELAX (замена старого matplotlib-графика в серо-синей палитре
    со встроенным заголовком, который дублировал подпись под графиком).
    """
    if df is None or df.empty:
        return ""

    d = df.copy()
    d[amount_col] = pd.to_numeric(d[amount_col], errors="coerce").fillna(0.0)
    d = d[d[amount_col] > 0].sort_values(amount_col, ascending=False)
    if d.empty:
        return ""

    total = float(d[amount_col].sum())
    head = d.head(top_n)
    tail = d.iloc[top_n:]

    labels = [_short_label(r[name_col], 20) for _, r in head.iterrows()]
    values = [float(r[amount_col]) for _, r in head.iterrows()]

    tail_n = 0
    if not tail.empty:
        labels.append(f"Остальные ({len(tail)})")
        values.append(float(tail[amount_col].sum()))
        tail_n = len(tail)

    apply_style()
    n = len(labels)
    if height_in is None:
        height_in = min(0.3 * n + 0.4, 3.0)
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    y_pos = list(range(n))
    head_n = n - (1 if tail_n else 0)
    colors = [COLOR_BRAND_DEEP] * head_n + (["#8c9188"] if tail_n else [])
    if head_n:
        colors[0] = COLOR_ACCENT

    ax.barh(y_pos, values, color=colors, height=0.6, zorder=3)

    max_x = (max(values) if values else 1.0) * 1.4
    ax.set_xlim(0, max_x)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7.8, color=COLOR_INK)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for y, v in zip(y_pos, values):
        share = v / total * 100 if total else 0.0
        ax.text(v + max_x * 0.02, y, f"{fmt_money_short(v)} ({share:.0f}%)",
                 va="center", ha="left", fontsize=7.4, color=COLOR_INK_SOFT, fontweight="bold")

    return fig_to_svg(fig)


def build_period_pareto_chart(
    df: pd.DataFrame,
    name_col: str,
    top_n: int = 8,
    width_in: float = 4.4,
    height_in: Optional[float] = None,
) -> str:
    """
    ТОП категорий/производителей за период — выручка + количество (шт) в
    подписи справа от бара. Используется в новом блоке "Категории за
    период" / "Производители за период" (данные уже считались для KPI, но
    раньше нигде не выводились).
    """
    if df is None or df.empty:
        return ""

    d = df.copy()
    d["amount"] = pd.to_numeric(d.get("amount"), errors="coerce").fillna(0.0)
    d["quant"] = pd.to_numeric(d.get("quant"), errors="coerce").fillna(0.0) if "quant" in d.columns else 0.0
    d = d[d["amount"] > 0].sort_values("amount", ascending=False)
    if d.empty:
        return ""

    total = float(d["amount"].sum())
    head = d.head(top_n)
    tail = d.iloc[top_n:]

    labels = [_short_label(r[name_col], 22) for _, r in head.iterrows()]
    values = [float(r["amount"]) for _, r in head.iterrows()]
    quants = [float(r["quant"]) for _, r in head.iterrows()]

    tail_n = 0
    if not tail.empty:
        labels.append(f"Остальные ({len(tail)})")
        values.append(float(tail["amount"].sum()))
        quants.append(float(tail["quant"].sum()) if "quant" in tail.columns else 0.0)
        tail_n = len(tail)

    apply_style()
    n = len(labels)
    if height_in is None:
        height_in = min(0.3 * n + 0.4, 2.6)
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    y_pos = list(range(n))
    head_n = n - (1 if tail_n else 0)
    colors = [COLOR_BRAND_DEEP] * head_n + (["#8c9188"] if tail_n else [])
    if head_n:
        colors[0] = COLOR_ACCENT

    ax.barh(y_pos, values, color=colors, height=0.6, zorder=3)

    max_x = (max(values) if values else 1.0) * 1.5
    ax.set_xlim(0, max_x)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7.8, color=COLOR_INK)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for y, v, q in zip(y_pos, values, quants):
        share = v / total * 100 if total else 0.0
        qty_part = f" · {fmt_qty(q)} шт" if q else ""
        ax.text(v + max_x * 0.02, y, f"{fmt_money_short(v)} ({share:.0f}%){qty_part}",
                 va="center", ha="left", fontsize=6.2, color=COLOR_INK_SOFT, fontweight="bold")

    return fig_to_svg(fig)


_RU_MONTHS_SHORT = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]


def build_prophet_fy_chart(
    df_fact_daily: pd.DataFrame,
    df_forecast_daily: pd.DataFrame,
    report_date,
    width_in: float = 8.7,
    height_in: float = 2.7,
) -> str:
    """
    Факт по месяцам + прогноз Prophet до конца года — перерисовано в теме
    COSMORELAX вместо старого сине-белого графика prophet_fy_chart.py
    (свой встроенный заголовок, синий #002FA7 не из палитры отчёта).
    Ожидает df_fact_daily: date/amount; df_forecast_daily: ds/yhat.
    """
    if df_fact_daily is None or df_fact_daily.empty or df_forecast_daily is None or df_forecast_daily.empty:
        return ""

    report_ts = pd.to_datetime(report_date).normalize()
    year = int(report_ts.year)
    curr_month = int(report_ts.month)

    df_f = df_fact_daily.copy()
    df_f["date"] = pd.to_datetime(df_f["date"], errors="coerce").dt.normalize()
    df_f["amount"] = pd.to_numeric(df_f["amount"], errors="coerce").fillna(0.0)
    df_f = df_f.dropna(subset=["date"])
    df_f = df_f[df_f["date"].dt.year == year]

    df_p = df_forecast_daily.copy()
    df_p["ds"] = pd.to_datetime(df_p["ds"], errors="coerce").dt.normalize()
    df_p["yhat"] = pd.to_numeric(df_p["yhat"], errors="coerce").fillna(0.0)
    df_p = df_p.dropna(subset=["ds"])
    df_p = df_p[df_p["ds"].dt.year == year]

    if df_f.empty or df_p.empty:
        return ""

    fact_monthly = df_f.set_index("date")["amount"].resample("MS").sum().reset_index()
    fact_monthly["month"] = fact_monthly["date"].dt.month
    plan_monthly = df_p.set_index("ds")["yhat"].resample("MS").sum().reset_index()
    plan_monthly["month"] = plan_monthly["ds"].dt.month

    months = np.arange(1, 13)
    fact_map = dict(zip(fact_monthly["month"], fact_monthly["amount"]))
    plan_map = dict(zip(plan_monthly["month"], plan_monthly["yhat"]))
    fact_full = np.array([float(fact_map.get(m, 0.0)) for m in months])
    plan_full = np.array([float(plan_map.get(m, 0.0)) for m in months])

    ms = report_ts.replace(day=1)
    eom = (report_ts + pd.offsets.MonthEnd(0)).normalize()
    mtd_fact = float(df_f[(df_f["date"] >= ms) & (df_f["date"] <= report_ts)]["amount"].sum())
    rest_start = (report_ts + pd.Timedelta(days=1)).normalize()
    remaining = float(df_p[(df_p["ds"] >= rest_start) & (df_p["ds"] <= eom)]["yhat"].sum())

    fact_draw = fact_full.copy()
    plan_draw = np.zeros_like(plan_full)
    for m in months:
        if m > curr_month:
            fact_draw[m - 1] = 0.0
            plan_draw[m - 1] = plan_full[m - 1]
    fact_draw[curr_month - 1] = mtd_fact
    plan_draw[curr_month - 1] = remaining
    for m in months:
        if m < curr_month:
            plan_draw[m - 1] = 0.0
    total_draw = fact_draw + plan_draw

    apply_style()
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    width = 0.6
    ax.bar(months, fact_draw, width=width, color=COLOR_BRAND_DEEP, zorder=3, label="Факт")
    ax.bar(months,plan_draw,width=width,bottom=fact_draw,color=COLOR_BRAND_DEEP,alpha=0.42,hatch="////",edgecolor="#faf8f4",linewidth=0.6,zorder=3,label="Прогноз (остаток)",)

    ax.set_xticks(months)
    ax.set_xticklabels(_RU_MONTHS_SHORT, fontsize=7.8, color=COLOR_INK_SOFT)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ymax = float(np.nanmax(total_draw)) if len(total_draw) else 1.0
    ax.set_ylim(0, ymax * 1.4)
    ax.set_xlim(0.3, 12.7)

    for m in months:
        v = float(total_draw[m - 1])
        if v <= 0:
            continue
        ax.text(m, v + ymax * 0.025, fmt_money_short(v), ha="center", va="bottom",
                 fontsize=6.2, color=COLOR_INK, fontweight="bold")

    if remaining > 0:
        ax.text(curr_month, mtd_fact + remaining / 2, f"+{fmt_money_short(remaining)}",
                 ha="center", va="center", fontsize=7.4, color="#faf8f4", fontweight="bold")

    ax.axvline(curr_month, color=COLOR_RULE, linewidth=0.9, linestyle=(0, (3, 3)), zorder=1)

    ax.legend(
        loc="upper left", frameon=False, fontsize=7.6, labelcolor=COLOR_INK_SOFT,
        handlelength=1.3, handleheight=1.0, borderaxespad=0.2,
    )

    return fig_to_svg(fig)


def build_categories_compare_chart(
    df_raw: pd.DataFrame,
    top_n: int = 10,
    width_in: float = 4.3,
    height_in: Optional[float] = None,
) -> str:
    """
    ТОП категорий: текущий год vs прошлый — парные горизонтальные бары в
    теме COSMORELAX. Заменяет старый categories_chart.py (обычный
    matplotlib без общего стиля отчёта: другие шрифты/цвета, не сочетался
    с остальными графиками sales_digest).
    """
    if df_raw is None or df_raw.empty:
        return ""
    d = df_raw.copy()
    for c in ("year", "cat_name", "amount"):
        if c not in d.columns:
            return ""
    d["amount"] = pd.to_numeric(d["amount"], errors="coerce").fillna(0.0)
    d["cat_name"] = d["cat_name"].fillna("Без категории").astype(str)

    years = sorted(d["year"].dropna().unique())
    if len(years) < 2:
        return ""
    y_prev, y_curr = years[-2], years[-1]

    g = (
        d.groupby(["cat_name", "year"], as_index=False)["amount"].sum()
        .pivot(index="cat_name", columns="year", values="amount")
        .fillna(0.0)
    )
    for y in (y_prev, y_curr):
        if y not in g.columns:
            g[y] = 0.0
    g = g.sort_values(y_curr, ascending=False).head(top_n)
    g = g.sort_values(y_curr)  # ascending — самая крупная сверху после invert

    labels = [_short_label(i, 18) for i in g.index]
    curr_vals = g[y_curr].tolist()
    prev_vals = g[y_prev].tolist()
    n = len(labels)
    if n == 0:
        return ""

    apply_style()
    if height_in is None:
        height_in = min(0.34 * n + 0.5, 3.4)
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    y_pos = list(range(n))
    bar_h = 0.34
    # верхняя (самая крупная) категория — акцентный терракотовый, как в
    # остальных бар-чартах отчёта (лидер визуально выделен); остальные —
    # фирменный тёмно-зелёный. g отсортирован по возрастанию, поэтому
    # "лидер" — последний элемент (сверху после invert оси).
    curr_colors = [COLOR_BRAND_DEEP] * n
    if n:
        curr_colors[-1] = COLOR_ACCENT
    ax.barh([y + bar_h / 2 for y in y_pos], curr_vals, height=bar_h,
             color=curr_colors, zorder=3, label=str(int(y_curr)))
    ax.barh([y - bar_h / 2 for y in y_pos], prev_vals, height=bar_h,
             color=COLOR_INK_SOFT, alpha=0.55, zorder=3, label=str(int(y_prev)))

    max_x = (max(curr_vals + prev_vals) if (curr_vals or prev_vals) else 1.0) * 1.32
    ax.set_xlim(0, max_x)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7.6, color=COLOR_INK)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for y, v in zip(y_pos, curr_vals):
        ax.text(v + max_x * 0.015, y + bar_h / 2, fmt_money_short(v),
                 va="center", ha="left", fontsize=6.6, color=COLOR_INK, fontweight="bold")

    ax.legend(
        loc="lower right", frameon=False, fontsize=7.4, labelcolor=COLOR_INK_SOFT,
        handlelength=1.2, handleheight=1.0,
    )

    return fig_to_svg(fig)


def _wrap_store_title(name: str, width: int = 24, max_lines: int = 2) -> str:
    """
    Название магазина в заголовке подграфика — переносим на 2 строки вместо
    обрезания многоточием (по фидбэку: раньше при сетке из многих узких
    колонок длинные названия вроде "Корпоративные прода…" резались после
    первых 15-16 символов; сетка 2×3 даёт достаточно ширины на подграфик,
    чтобы уместить название целиком в 1-2 строки, урезаем только если оно
    экстремально длинное).
    """
    name = str(name or "—").strip()
    wrapped = textwrap.wrap(name, width=width) or [name]
    if len(wrapped) > max_lines:
        head = wrapped[:max_lines]
        last = head[-1].rstrip()
        if len(last) > width - 1:
            last = last[: width - 1].rstrip()
        head[-1] = last + "…"
        wrapped = head
    return "\n".join(wrapped)


def build_store_monthly_bars_chart(
    monthly_df: pd.DataFrame,
    y_curr,
    y_prev,
    top_n: int = 6,
    width_in: float = 10.2,
    height_in: float = 6.0,
) -> str:
    """
    Помесячная динамика по магазинам — раздел, который убирали по фидбэку
    (была сетка спарклайнов на много узких колонок с пунктиром/сплошной
    линией — плохо читалась, названия магазинов резались), теперь вернули,
    но перерисовали заново: сгруппированные столбики (2 колонки × 3 строки,
    топ-N магазинов YTD по выручке), помесячно, с той же цветовой логикой,
    что и парные YTD/MTD бар-чарты раздела "KPI по магазинам"
    (build_categories_compare_chart) — текущий год (COLOR_BRAND_DEEP) и
    прошлый год (COLOR_INK_SOFT, полупрозрачный) — для консистентности
    легенды "2026"/"2025" по всему отчёту. У каждого столбика — подпись
    суммы (fmt_money_short, тот же компактный формат, что и везде в отчёте),
    по оси X — короткие русские названия месяцев (monthly_df уже приходит с
    готовым month_name из stores/performance/metrics._build_monthly_compare).

    Ожидает "длинный" DataFrame с колонками store/month_no/month_name/
    curr_amount/prev_amount (см. data["monthly"] из
    stores.performance.metrics.build_store_performance_block).
    """
    if monthly_df is None or monthly_df.empty:
        return ""

    df = monthly_df.copy()
    for c in ("store", "month_no", "curr_amount", "prev_amount"):
        if c not in df.columns:
            return ""
    df["curr_amount"] = pd.to_numeric(df["curr_amount"], errors="coerce").fillna(0.0)
    df["prev_amount"] = pd.to_numeric(df["prev_amount"], errors="coerce").fillna(0.0)
    if "month_name" not in df.columns:
        df["month_name"] = df["month_no"].astype(str)

    totals = df.groupby("store")["curr_amount"].sum().sort_values(ascending=False)
    stores = [s for s in totals.index if totals[s] > 0][:top_n]
    if not stores:
        return ""

    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    apply_style()
    nrows, ncols = 3, 2
    fig, axes = plt.subplots(nrows, ncols, figsize=(width_in, height_in), dpi=150)
    fig.patch.set_alpha(0)
    axes_flat = list(axes.flatten())

    bar_w = 0.36
    for i, ax in enumerate(axes_flat):
        ax.patch.set_alpha(0)
        for spine in ax.spines.values():
            spine.set_visible(False)

        if i >= len(stores):
            ax.axis("off")
            continue

        store = stores[i]
        sd = df[df["store"] == store].sort_values("month_no")
        months = sd["month_no"].tolist()
        month_labels = sd["month_name"].tolist()
        curr_vals = sd["curr_amount"].tolist()
        prev_vals = sd["prev_amount"].tolist()
        n = len(months)
        if n == 0:
            ax.axis("off")
            continue
        xs = list(range(n))

        ax.bar([x - bar_w / 2 for x in xs], curr_vals, width=bar_w,
               color=COLOR_BRAND_DEEP, zorder=3, label=str(y_curr))
        ax.bar([x + bar_w / 2 for x in xs], prev_vals, width=bar_w,
               color=COLOR_INK_SOFT, alpha=0.55, zorder=3, label=str(y_prev))

        max_v = max(curr_vals + prev_vals) if (curr_vals or prev_vals) else 0.0
        ax.set_ylim(0, max_v * 1.4 if max_v > 0 else 1.0)
        ax.set_xlim(-0.6, n - 0.4)
        ax.set_xticks(xs)
        ax.set_xticklabels(month_labels, fontsize=6.8, color=COLOR_INK_SOFT)
        ax.set_yticks([])
        ax.tick_params(axis="x", length=0)

        for x, v in zip(xs, curr_vals):
            if v <= 0:
                continue
            ax.text(x - bar_w / 2, v + max_v * 0.03, fmt_money_short(v),
                     ha="center", va="bottom", fontsize=5.6, color=COLOR_INK,
                     fontweight="bold", rotation=90)
        for x, v in zip(xs, prev_vals):
            if v <= 0:
                continue
            ax.text(x + bar_w / 2, v + max_v * 0.03, fmt_money_short(v),
                     ha="center", va="bottom", fontsize=5.6, color=COLOR_INK_SOFT,
                     rotation=90)

        ax.set_title(_wrap_store_title(store), fontsize=8.4, color=COLOR_INK,
                     fontweight="bold", loc="left", pad=8, linespacing=1.25)

    legend_handles = [
        Patch(facecolor=COLOR_BRAND_DEEP, label=str(y_curr)),
        Patch(facecolor=COLOR_INK_SOFT, alpha=0.55, label=str(y_prev)),
    ]
    fig.legend(
        handles=legend_handles, loc="upper center", ncol=2, frameon=False,
        fontsize=8.6, labelcolor=COLOR_INK_SOFT, bbox_to_anchor=(0.5, 1.015),
        handlelength=1.3, handleheight=1.0,
    )

    fig.tight_layout(rect=(0, 0, 1, 0.95), h_pad=3.4, w_pad=3.0)

    return fig_to_svg(fig)
