# sales/reports/newspaper/charts/cash_ytd.py
"""
Графики страницы "Год к дате" (YTD): тот же визуальный язык, что и
charts/cash.py для месяца — просто на годовом горизонте.

  - build_cash_ytd_pace_chart:   такой же bullet-chart "план/факт", что и
    build_cash_pace_chart, но факт/план — накопительные с начала года, и
    вместо прогноза до конца месяца — прогноз до конца года по текущему
    среднедневному темпу.
  - build_cash_ytd_monthly_chart: помесячные бары факта (в этом году,
    сплошным) на фоне факта того же месяца прошлого года (контур) — чтобы
    сезонность и динамика год-к-году были видны на одной картинке, а не
    только в цифрах таблицы.
"""

from __future__ import annotations

from ..config import (
    COLOR_ACCENT,
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_NEGATIVE,
    COLOR_NEGATIVE_BG,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
    COLOR_POSITIVE_BG,
    COLOR_RULE,
)
from ..render.helpers import fmt_money_mln_or_rub, fmt_money_short, to_decimal
from .common import apply_style, fig_to_svg, new_figure


def build_cash_ytd_pace_chart(ytd_data: dict) -> str:
    totals = ytd_data["totals"]

    plan_to_date = float(to_decimal(totals["plan_to_date"]))
    plan_year_full = float(to_decimal(totals["plan_year_full"]))
    fact = float(to_decimal(totals["fact"]))
    forecast = float(to_decimal(totals["projected_year_fact"]))
    # План на год может быть заведён не на все 12 месяцев (см.
    # sales_plan_report.get_cash_ytd_data) — пока это так, рисовать риску
    # "план на год" нельзя: она будет расти сама по себе по мере ввода
    # новых месяцев и не имеет отношения к текущему темпу.
    plan_year_complete = bool(totals.get("plan_year_complete", False))

    max_value = max(plan_to_date, fact, forecast, (plan_year_full if plan_year_complete else 0), 1.0) * 1.1

    fig, ax = new_figure(width_in=7.4, height_in=1.5)

    bar_height = 0.5

    # Тонкая базовая линия — визуально "заземляет" бары, а не просто
    # плавающие прямоугольники в пустоте.
    ax.axhline(-0.32, color=COLOR_RULE, linewidth=0.8, zorder=1)

    # Прогноз на конец года — светлый фон-бар, как и на месячном графике.
    ax.barh(0, forecast, height=bar_height, color="#e5ded0", zorder=2)

    is_on_track = totals["is_on_track"]
    fact_color = COLOR_POSITIVE if is_on_track else COLOR_ACCENT
    ax.barh(0, fact, height=bar_height, color=fact_color, zorder=3)

    # Метка "план на сегодня" (накопительно) — основная риска, как в месяце.
    if plan_to_date > 0:
        plan_color = COLOR_NEGATIVE if fact < plan_to_date else COLOR_INK
        ax.plot([plan_to_date, plan_to_date], [-0.32, 0.42], color=plan_color, linewidth=1.8, zorder=4)
        ax.text(
            plan_to_date, 0.56, f"План на сегодня {fmt_money_short(plan_to_date)}",
            ha="center", va="bottom", fontsize=8.4, color=plan_color, fontweight="bold",
        )

    # Годовой план — вторая, более тонкая риска правее (ориентир на весь год).
    # Показываем только если план заведён на весь год целиком.
    if plan_year_complete and (plan_year_full > plan_to_date > 0 or (plan_year_full > 0 and plan_to_date == 0)):
        ax.plot(
            [plan_year_full, plan_year_full], [-0.32, 0.42],
            color=COLOR_INK_SOFT, linewidth=1.2, linestyle=(0, (2, 2)), zorder=4,
        )
        ax.text(
            plan_year_full, -0.42, f"План на год {fmt_money_short(plan_year_full)}",
            ha="center", va="top", fontsize=7.6, color=COLOR_INK_SOFT,
        )

    summary = (
        f"Факт с начала года {fmt_money_short(fact)}   ·   "
        f"Прогноз на конец года {fmt_money_short(forecast)}"
    )
    if plan_year_complete and plan_year_full > 0:
        summary += f"   ·   План на год {fmt_money_short(plan_year_full)}"
    ax.text(
        0, -0.62, summary,
        ha="left", va="top", fontsize=8.6, color=COLOR_INK_SOFT,
    )

    ax.set_xlim(0, max_value)
    ax.set_ylim(-1.05, 0.95)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    return fig_to_svg(fig)


def build_cash_ytd_monthly_chart(ytd_data: dict) -> str:
    """
    Помесячный факт на фоне плана месяца: план — светлый фоновый бар, факт —
    узкий цветной бар поверх него, поэтому и объём, и разрыв план/факт
    видны на одной картинке, а не только в цифрах таблицы. Цвет факта:
      - акцентный — текущий (ещё не закончившийся) месяц: сравнивать его
        с полным планом месяца рано, поэтому не окрашиваем в зелёный/красный;
      - зелёный — завершённый месяц, план выполнен;
      - красный — завершённый месяц, план не дотянут;
      - серый — план на этот месяц не заведён (сравнивать не с чем).
    Без сравнения с прошлым годом: качество прошлогодних данных под
    вопросом, поэтому в отчёт не выводим.
    """
    import matplotlib.pyplot as plt

    apply_style()

    months = ytd_data["monthly"]
    if not months:
        return ""

    labels = [m["month_name"] for m in months]
    fact_values = [float(to_decimal(m["fact"])) for m in months]
    plan_values = [float(to_decimal(m["plan"])) for m in months]

    # ACCENT (текущий месяц) и NEGATIVE (план не дотянут) — оба тёплые
    # терракотовые тона, на глаз их можно спутать. Поэтому текущий месяц
    # дополнительно выделяем штриховкой, чтобы "месяц ещё не закончен" не
    # читался как "план провален" даже при беглом взгляде.
    colors = []
    hatches = []
    for m, fact_v, plan_v in zip(months, fact_values, plan_values):
        if m["is_current"]:
            colors.append(COLOR_ACCENT)
            hatches.append("///")
        elif plan_v > 0:
            colors.append(COLOR_POSITIVE if fact_v >= plan_v else COLOR_NEGATIVE)
            hatches.append(None)
        else:
            colors.append(COLOR_NEUTRAL)
            hatches.append(None)

    # Ширина фигуры растёт вместе с числом месяцев (а не фиксирована),
    # но пропорции (высота/ширина) всегда те же — картинка потом всегда
    # растягивается версткой на всю ширину колонки (width:100%;
    # height:auto в CSS), поэтому конечная высота на странице не меняется
    # ни при 4 месяцах, ни при 12: меняется только "внутреннее" число
    # колонок, а место на одну колонку (и, значит, размер шрифта и
    # бейджей относительно неё) остаётся постоянным. Это и не даёт
    # подписям слипаться по мере того, как в течение года добавляются
    # новые месяцы.
    PER_MONTH_WIDTH_IN = 7.4 / 9  # ширина на 1 месяц, подобранная и проверенная на 9 месяцах
    ASPECT_RATIO = 1.85 / 7.4     # высота/ширина эталонного макета — сохраняем всегда (уменьшено по просьбе — график был слишком высоким)
    effective_n = max(len(months), 9)  # не уже эталонной 9-месячной ширины: на малом числе месяцев edge-подписи начинают доминировать в bbox_inches="tight" и искажают масштаб
    fig_w = PER_MONTH_WIDTH_IN * effective_n
    fig_h = fig_w * ASPECT_RATIO

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_RULE)

    x = list(range(len(months)))
    max_v = max(fact_values + plan_values + [1.0])

    # План — широкий светлый фоновый бар; факт — узкий цветной бар поверх
    # него по центру, как маленький bullet-chart на каждый месяц.
    ax.bar(x, plan_values, width=0.6, color="#e5ded0", zorder=2)
    fact_bars = ax.bar(x, fact_values, width=0.34, color=colors, zorder=3)
    for bar, hatch in zip(fact_bars, hatches):
        if hatch:
            bar.set_hatch(hatch)
            bar.set_edgecolor("#f7f8f3")
            bar.set_linewidth(0.4)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.4)
    ax.set_yticks([])

    # Подпись факта — над самим фактом (а не над более высоким из
    # факта/плана): так подписи у месяцев с более скромным фактом сами
    # собой оказываются пониже, а не толпятся все на одной высоте — план
    # у соседних месяцев обычно куда ближе друг к другу по величине, чем
    # факт, и выравнивание по плану сбивало подписи в кучу.
    #
    # Цвет подписи факта совпадает с цветом самого факт-бара (зелёный /
    # красный / акцентный) — число не просто нейтрально-чёрное, а сразу
    # несёт тот же сигнал, что и бар под ним.
    for i, (fact_v, color) in enumerate(zip(fact_values, colors)):
        ax.text(
            i, fact_v + max_v * 0.035, fmt_money_short(fact_v),
            ha="center", va="bottom", fontsize=6.8, color=color, fontweight="bold",
        )

    ax.set_ylim(0, max_v * 1.2)

    # Отклонение от плана по месяцам (₽ и %) — компактным цветным бейджем
    # ровно под подписью месяца на оси, в две строки (сумма / %), чтобы на
    # девяти месяцах в ряд каждая строка была короткой и не наезжала на
    # соседей. Выровнено через ось X, поэтому всегда точно под "своим"
    # столбцом, а не отдельной строкой, которая может перенестись и
    # разъехаться с месяцами.
    axis_transform = ax.get_xaxis_transform()
    for i, (m, fact_v, plan_v) in enumerate(zip(months, fact_values, plan_values)):
        is_judged = (not m["is_current"]) and plan_v > 0
        if not is_judged:
            continue
        diff = fact_v - plan_v
        diff_pct = (fact_v / plan_v - 1) * 100
        sign = "+" if diff >= 0 else "−"
        bg = COLOR_POSITIVE_BG if diff >= 0 else COLOR_NEGATIVE_BG
        fg = COLOR_POSITIVE if diff >= 0 else COLOR_NEGATIVE
        text = f"{sign}{fmt_money_mln_or_rub(abs(diff))}\n{sign}{abs(diff_pct):.0f}%"
        ax.text(
            i, -0.22, text, transform=axis_transform,
            ha="center", va="top", fontsize=5.2, color=fg, fontweight="bold",
            linespacing=1.35,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=bg, edgecolor="none"),
        )

    return fig_to_svg(fig)
