from __future__ import annotations

from io import StringIO
from decimal import Decimal
from typing import Optional

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator, AutoMinorLocator
from matplotlib.patches import Patch
import matplotlib.patheffects as pe


# ---------------- PROFESSIONAL TYPOGRAPHY ----------------

mpl.rcParams.update({
    # Font settings
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": 11,
    
    # Figure aesthetics
    "figure.dpi": 300,
    "figure.autolayout": False,
    
    # Axes settings
    "axes.labelsize": 12,
    "axes.titleweight": "semibold",
    "axes.titlesize": 18,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#333333",
    
    # Tick settings
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "xtick.color": "#666666",
    "ytick.color": "#666666",
    "xtick.direction": "out",
    "ytick.direction": "out",
    
    # Grid settings
    "grid.color": "#E0E0E0",
    "grid.linestyle": "--",
    "grid.linewidth": 0.7,
    "grid.alpha": 0.8,
    
    # Save settings
    "savefig.dpi": 300,
    "savefig.transparent": True,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
})


# ---------------- UTILS ----------------

def _to_float(x):
    """Convert any numeric type to float safely."""
    if x is None:
        return 0.0
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


# ---------------- COLOR PALETTE ----------------

class Colors:
    """Professional color palette for financial charts."""
    
    # Primary colors
    CURRENT_BLUE = "#2E5AAC"  # Professional blue
    PREVIOUS_GRAY = "#8C8C8C"  # Neutral gray
    
    # Status colors
    POSITIVE_GREEN = "#27AE60"  # Success green
    NEGATIVE_RED = "#E74C3C"   # Alert red
    NEUTRAL_GRAY = "#7F8C8D"   # Neutral gray
    
    # Text colors
    DARK_TEXT = "#2C3E50"      # Dark blue-gray
    MEDIUM_TEXT = "#5D6D7E"    # Medium gray
    LIGHT_TEXT = "#95A5A6"     # Light gray
    
    # Background and grid
    GRID_COLOR = "#EAEDF1"
    DIVIDER_COLOR = "#4F73FF"  # Яркий синий для разделителей
    DIVIDER_OPACITY = 0.4      # Прозрачность разделителей
    
    # Bar colors with transparency
    CURRENT_BAR = (*mpl.colors.to_rgb(CURRENT_BLUE), 0.65)  # 65% opacity
    PREVIOUS_BAR = (*mpl.colors.to_rgb(PREVIOUS_GRAY), 0.4)  # 40% opacity
    PREVIOUS_HATCH = (*mpl.colors.to_rgb(PREVIOUS_GRAY), 0.6)  # 60% opacity for hatch
    
    # Tag colors
    CURRENT_TAG = "#1A4780"    # Darker blue
    PREVIOUS_TAG = "#5D6D7E"   # Medium gray
    
    # Store group colors (чередующиеся для разделителей)
    GROUP_COLORS = [
        "#4F73FF",  # Яркий синий

    ]


# ---------------- MAIN FUNCTION ----------------

def build_store_amount_bar_svg(
    store_rows_raw: list[dict],
    *,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    top_n: int = 12,
    currency: str = "руб.",
    show_delta_percent: bool = True,
    show_color_dividers: bool = True,
    bar_width_scale: float = 1.0,
) -> str:
    """
    Build a professional horizontal bar chart comparing current vs previous amounts.
    
    Args:
        store_rows_raw: List of dictionaries with store data
        title: Main chart title
        subtitle: Optional subtitle
        top_n: Number of top stores to display
        currency: Currency symbol/name
        show_delta_percent: Whether to show percentage change
        show_color_dividers: Whether to show color dividers between store groups
        bar_width_scale: Multiplier for bar width (1.0 = default, 1.5 = 50% wider)
    
    Returns:
        SVG string
    """
    # Filter and sort data
    rows = [r for r in store_rows_raw if r.get("store")]
    rows.sort(key=lambda r: _to_float(r["amount"]), reverse=True)
    rows = rows[:top_n][::-1]  # Reverse for horizontal bar display
    
    # Extract data
    labels = [r["store"] for r in rows]
    curr = [_to_float(r["amount"]) for r in rows]
    prev = [_to_float(r["prev_amount"]) for r in rows]
    
    max_value = max(curr + prev + [1])
    
    # Уменьшаем высоту фигуры
    base_height = 3.2
    height_per_store = 1.35
    fig_height = max(base_height, len(labels) * height_per_store + 0.8)
    
    fig, ax = plt.subplots(figsize=(11.8, fig_height))
    
    # Set background color
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    
    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Configure ticks
    ax.tick_params(length=0, pad=8, labelsize=10)
    ax.tick_params(axis='x', which='both', bottom=False, top=False)
    ax.tick_params(axis='y', which='both', left=False, right=False)
    
    # ---- Layout and spacing ----
    group_spacing = 1.5
    
    y_positions = np.arange(len(labels)) * group_spacing
    
    y_prev = y_positions + 0.60
    y_curr = y_positions + 0.28
    y_delta = y_positions - 0.30
    
    # Позиция разделителя ПОСЛЕ магазина
    y_divider = y_positions - 0.60
    
    # Широкие столбики
    bar_height = 0.35 * bar_width_scale
    
    # ---- Create bars ----
    prev_bars = ax.barh(
        y_prev, prev, bar_height,
        color=Colors.PREVIOUS_BAR,
        edgecolor=Colors.PREVIOUS_HATCH,
        hatch="///",
        linewidth=0.7,
        zorder=2,
    )
    
    curr_bars = ax.barh(
        y_curr, curr, bar_height,
        color=Colors.CURRENT_BAR,
        edgecolor=Colors.CURRENT_BLUE,
        linewidth=0.7,
        zorder=3,
    )
    
    # Set y-ticks to store labels
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=12, color=Colors.DARK_TEXT, fontweight='semibold')
    
    # Remove x-axis labels
    ax.set_xticklabels([])
    
    # ---- Grid ----
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=Colors.GRID_COLOR, linestyle='-', linewidth=0.8, alpha=0.7)
    ax.xaxis.set_major_locator(MaxNLocator(8, integer=True))
    
    # Remove y-axis grid
    ax.yaxis.grid(False)
    
    # ---- Titles ----
    if not title:
        title = "Чистая выручка по магазинам (было / стало)"
    
    fig.suptitle(
        title,
        y=0.98,
        fontsize=20,
        fontweight='semibold',
        color=Colors.DARK_TEXT,
        va='top'
    )
    
    if subtitle:
        ax.text(
            0.5, 1.04, subtitle,
            transform=ax.transAxes,
            fontsize=12,
            color=Colors.MEDIUM_TEXT,
            ha='center',
            va='bottom'
        )
    
    # ---- X-axis formatting ----
    if max_value >= 1_000_000_000:
        scale, suffix = 1_000_000_000, "млрд"
    elif max_value >= 1_000_000:
        scale, suffix = 1_000_000, "млн"
    elif max_value >= 1000:
        scale, suffix = 1000, "тыс"
    else:
        scale, suffix = 1, ""
    
    ax.set_xlim(0, max_value * 1.15)
    
    # Add custom x-axis labels
    x_ticks = ax.get_xticks()
    for tick in x_ticks[1:-1]:
        if tick > 0:
            ax.text(
                tick, -0.02,
                f'{tick/scale:.0f}',
                fontsize=10,
                color=Colors.MEDIUM_TEXT,
                ha='center',
                va='top',
                transform=ax.get_xaxis_transform(),
                fontweight='medium'
            )
    
    # Add scale label
    if suffix:
        ax.text(
            1.0, -0.04,
            f'{suffix} {currency}',
            transform=ax.transAxes,
            fontsize=9,
            color=Colors.LIGHT_TEXT,
            ha='right',
            va='top',
            style='italic'
        )
    
    # ---- Text effects ----
    text_effects = [
        pe.Stroke(linewidth=3, foreground='white', alpha=0.8),
        pe.Normal()
    ]
    
    # ---- Add labels and values ----
    for i in range(len(labels)):
        # ===== PERIOD LABELS =====
        label_x = max_value * 0.008
        
        # "Было" label
        ax.text(
            label_x, y_prev[i], "Было",
            va='center', ha='left',
            fontsize=10,
            color=Colors.PREVIOUS_TAG,
            fontstyle='italic',
            path_effects=text_effects,
            zorder=4,
        )
        
        # "Стало" label
        ax.text(
            label_x, y_curr[i], "Стало",
            va='center', ha='left',
            fontsize=10,
            color=Colors.CURRENT_TAG,
            fontweight='medium',
            path_effects=text_effects,
            zorder=4,
        )
        
        # ===== VALUES ON BARS =====
        # Previous period value
        if prev[i] > 0:
            prev_text = f'{prev[i]/scale:.1f}'
            ax.text(
                prev[i], y_prev[i],
                prev_text,
                va='center',
                ha='right',
                fontsize=11,
                color=Colors.PREVIOUS_TAG,
                fontweight='medium',
                path_effects=text_effects,
                zorder=4,
                bbox=dict(
                    boxstyle='round,pad=0.15',
                    facecolor='white',
                    edgecolor='none',
                    alpha=0.7
                )
            )
        
        # Current period value
        curr_text = f'{curr[i]/scale:.1f}'
        ax.text(
            curr[i], y_curr[i],
            curr_text,
            va='center',
            ha='right',
            fontsize=12,
            color=Colors.CURRENT_TAG,
            fontweight='bold',
            path_effects=text_effects,
            zorder=4,
            bbox=dict(
                boxstyle='round,pad=0.15',
                facecolor='white',
                edgecolor='none',
                alpha=0.7
            )
        )
        
        # ===== DELTA/CHANGE INFO =====
        delta = curr[i] - prev[i]
        
        if prev[i] > 0:
            pct_change = (delta / prev[i]) * 100
        else:
            pct_change = 0
        
        # Choose color and symbol based on delta
        if delta > 0:
            symbol = "▲"
            color = Colors.POSITIVE_GREEN
            delta_text = f"+{delta/scale:.1f}"
            pct_text = f"+{pct_change:.0f}%"
        elif delta < 0:
            symbol = "▼"
            color = Colors.NEGATIVE_RED
            delta_text = f"{delta/scale:.1f}"
            pct_text = f"{pct_change:.0f}%"
        else:
            symbol = "●"
            color = Colors.NEUTRAL_GRAY
            delta_text = f"{delta/scale:.1f}"
            pct_text = f"{pct_change:.0f}%"
        
        # Format change text
        if show_delta_percent and prev[i] > 0:
            change_text = f"Изменение: {symbol} {delta_text} {suffix} ({pct_text})"
        else:
            change_text = f"Изменение: {symbol} {delta_text} {suffix}"
        
        # Position change text
        ax.text(
            max_value * 0.008,
            y_delta[i],
            change_text,
            ha='left',
            va='center',
            fontsize=11,
            color=color,
            fontweight='medium',
            path_effects=text_effects,
            zorder=4,
        )
        
        # ===== COLOR DIVIDERS ПОСЛЕ КАЖДОГО МАГАЗИНА (кроме последнего) =====
        if show_color_dividers and i < len(labels) - 1:
            divider_color = Colors.GROUP_COLORS[i % len(Colors.GROUP_COLORS)]
            
            # Толстая цветная полоса-разделитель
            ax.axhline(
                y=y_divider[i],
                xmin=0,
                xmax=1,
                color=divider_color,
                linewidth=2.5,
                alpha=0.7,
                zorder=1,
            )
            
            # Дополнительная тонкая белая линия
            ax.axhline(
                y=y_divider[i],
                xmin=0,
                xmax=1,
                color='white',
                linewidth=0.8,
                linestyle=(0, (1, 1)),
                alpha=0.9,
                zorder=2,
            )
    
    # ---- Final layout adjustments ----
    plt.tight_layout(rect=[0, 0.01, 1, 0.95])
    
    # Save to SVG
    buf = StringIO()
    fig.savefig(
        buf,
        format='svg',
        transparent=True,
        bbox_inches='tight',
        pad_inches=0.03,
        facecolor=fig.get_facecolor(),
        edgecolor='none'
    )
    
    plt.close(fig)
    
    return buf.getvalue()





# from __future__ import annotations

# from io import StringIO
# from decimal import Decimal
# from typing import List, Dict, Any, Optional, Tuple

# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.ticker import FuncFormatter


# # ---------------- helpers ----------------

# def _to_float(x) -> float:
#     if x is None:
#         return 0.0
#     if isinstance(x, Decimal):
#         return float(x)
#     try:
#         return float(x)
#     except Exception:
#         return 0.0


# def _fig_to_svg(fig) -> str:
#     buf = StringIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.02)
#     plt.close(fig)
#     return buf.getvalue()


# def _human_money(x: float) -> str:
#     x = float(x)
#     a = abs(x)
#     if a >= 1_000_000_000:
#         return f"{x/1_000_000_000:.2f} млрд"
#     if a >= 1_000_000:
#         return f"{x/1_000_000:.2f} млн"
#     if a >= 1_000:
#         return f"{x/1_000:.1f} тыс"
#     return f"{x:.0f}"


# def _pct_change(curr: float, prev: float) -> float:
#     if prev > 0:
#         return (curr - prev) / prev * 100.0
#     if curr > 0:
#         return 100.0
#     return 0.0


# def _pareto_threshold_index(cum: np.ndarray, threshold: float = 0.8) -> Optional[int]:
#     """Возвращает индекс первой точки, где cum >= threshold."""
#     if cum.size == 0:
#         return None
#     idx = int(np.argmax(cum >= threshold))
#     return idx if cum[idx] >= threshold else None


# # ---------------- main chart ----------------

# def build_store_amount_bar_svg(
#     rows_raw: List[Dict[str, Any]],
#     *,
#     title: str = "Чистая выручка по магазинам",
#     subtitle: Optional[str] = None,
#     top_n: int = 12,
#     currency: str = "₽",
#     show_pareto: bool = True,
#     pareto_threshold: float = 0.80,          # линия 80% (по умолчанию)
#     show_delta_labels: bool = True,          # справа: значение и % изменения
#     show_delta_bars: bool = True,            # добавляет маленький “Δ” маркер рядом (не перегружает)
# ) -> str:
#     """
#     Красивый бизнес-график уровня “в отчёт собственнику”:
#       - сортировка по текущей выручке
#       - основной бар: текущий период
#       - “было”: тонкий фон/контур (не конкурирует)
#       - справа: значение и % (1 знак) цветом
#       - Pareto-линия накопленной доли + отметка порога (например 80%)
#       - аккуратная сетка, без рамок, читабельно в PDF
#     Ожидаемые ключи в rows_raw: store, amount, prev_amount
#     """
#     rows = [r for r in (rows_raw or []) if r.get("store")]
#     if not rows:
#         return ""

#     rows.sort(key=lambda r: _to_float(r.get("amount")), reverse=True)
#     rows = rows[:top_n]

#     labels = [str(r["store"]) for r in rows]
#     curr = np.array([_to_float(r.get("amount")) for r in rows], dtype=float)
#     prev = np.array([_to_float(r.get("prev_amount")) for r in rows], dtype=float)

#     # safety
#     curr = np.nan_to_num(curr, nan=0.0, posinf=0.0, neginf=0.0)
#     prev = np.nan_to_num(prev, nan=0.0, posinf=0.0, neginf=0.0)

#     # Pareto по текущему (как правило, так и нужно)
#     total_curr = float(curr.sum()) if curr.size else 0.0
#     share = (curr / total_curr) if total_curr > 0 else np.zeros_like(curr)
#     cum_share = np.cumsum(share)

#     # для горизонтального barh разворачиваем порядок (топ сверху)
#     labels_r = labels[::-1]
#     curr_r = curr[::-1]
#     prev_r = prev[::-1]
#     cum_r = cum_share[::-1]  # для отображения слева направо по y тоже разворачиваем
#     share_r = share[::-1]

#     max_val = float(max(curr.max(initial=0.0), prev.max(initial=0.0), 1.0))
#     n = len(labels_r)
#     y = np.arange(n)

#     # --------- style ----------
#     COLOR_MAIN = "#2563EB"   # основной (синий)
#     COLOR_PREV = "#D1D5DB"   # фон “было”
#     COLOR_GRID = "#E5E7EB"
#     COLOR_TEXT = "#0F172A"
#     COLOR_MUTED = "#64748B"
#     COLOR_POS = "#16A34A"
#     COLOR_NEG = "#DC2626"
#     COLOR_PARETO = "#0F172A"      # линия Pareto (чёрная)
#     COLOR_THRESH = "#94A3B8"      # линия 80%

#     fig_h = max(3.4, 0.44 * n + 1.5)
#     fig_w = 12.2 if show_pareto else 11.6

#     fig, ax = plt.subplots(figsize=(fig_w, fig_h))
#     fig.patch.set_facecolor("white")
#     ax.set_facecolor("white")

#     # --- bars ---
#     # “Было” как лёгкий фон
#     ax.barh(y, prev_r, height=0.58, color=COLOR_PREV, zorder=1)

#     # “Стало” как главный бар
#     ax.barh(y, curr_r, height=0.36, color=COLOR_MAIN, zorder=2)

#     # --- axes / grid ---
#     ax.xaxis.grid(True, color=COLOR_GRID, linewidth=1.0)
#     ax.set_axisbelow(True)
#     for s in ax.spines.values():
#         s.set_visible(False)
#     ax.tick_params(axis="both", length=0)
#     ax.set_yticks(y)
#     ax.set_yticklabels(labels_r, fontsize=11, color=COLOR_TEXT)
#     ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: _human_money(v)))
#     ax.set_xlabel(f"Чистая выручка за период, {currency}", fontsize=10.5, color=COLOR_MUTED, labelpad=10)

#     # место справа под подписи + pareto-ось
#     right_pad = max_val * (0.30 if show_pareto else 0.22)
#     ax.set_xlim(0, max_val + right_pad)

#     # title / subtitle
#     ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color=COLOR_TEXT, pad=10)
#     if subtitle:
#         ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=11, color=COLOR_MUTED, ha="left")

#     # --- delta labels (value + %), + optional delta marker ---
#     for i in range(n):
#         c = float(curr_r[i])
#         p = float(prev_r[i])
#         pct = _pct_change(c, p)

#         if pct > 0:
#             col = COLOR_POS
#             sign = "+"
#         elif pct < 0:
#             col = COLOR_NEG
#             sign = ""  # минус уже в числе
#         else:
#             col = COLOR_MUTED
#             sign = ""

#         x_text = c + max_val * 0.018

#         if show_delta_labels:
#             ax.text(
#                 x_text,
#                 i,
#                 f"{_human_money(c)}   {sign}{pct:.1f}%",
#                 va="center",
#                 ha="left",
#                 fontsize=11,
#                 fontweight="bold",
#                 color=col if abs(pct) >= 0.05 else COLOR_MUTED,
#                 zorder=5,
#             )

#         if show_delta_bars:
#             # маленький “Δ” маркер рядом с текстом (очень деликатно)
#             # рисуем короткую вертикальную черту — зелёную/красную
#             if abs(pct) >= 0.05 and (c > 0 or p > 0):
#                 ax.plot(
#                     [x_text - max_val * 0.010, x_text - max_val * 0.010],
#                     [i - 0.13, i + 0.13],
#                     color=col,
#                     linewidth=2.4,
#                     solid_capstyle="round",
#                     zorder=5,
#                 )

#     # --- Pareto line (cumulative share) ---
#     if show_pareto:
#         ax2 = ax.twiny()
#         ax2.set_facecolor("none")
#         for s in ax2.spines.values():
#             s.set_visible(False)

#         # шкала 0..100%
#         ax2.set_xlim(0, 1.0)
#         ax2.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
#         ax2.set_xticklabels([f"{int(t*100)}%" for t in ax2.get_xticks()], fontsize=10, color=COLOR_MUTED)
#         ax2.tick_params(axis="x", length=0, pad=6)

#         # линия накопленной доли — по y магазинам
#         ax2.plot(cum_r, y, color=COLOR_PARETO, linewidth=2.0, zorder=6)
#         ax2.scatter(cum_r, y, s=16, color=COLOR_PARETO, zorder=7)

#         # линия порога (80%)
#         ax2.axvline(pareto_threshold, color=COLOR_THRESH, linewidth=1.4, linestyle="--", zorder=4)

#         # подпись “80%” сверху
#         ax2.text(
#             pareto_threshold,
#             1.02,
#             f"{int(pareto_threshold*100)}% порог",
#             transform=ax2.get_xaxis_transform(),
#             ha="center",
#             va="bottom",
#             fontsize=10,
#             color=COLOR_MUTED,
#         )

#         # подсветка магазина, на котором достигнут порог
#         idx = _pareto_threshold_index(cum_share, pareto_threshold)
#         if idx is not None:
#             # idx относится к оригинальному порядку (топ->низ), у нас разворот:
#             idx_r = (n - 1) - idx
#             ax.axhline(idx_r, color=COLOR_GRID, linewidth=2.2, zorder=0, alpha=0.9)
#             ax.text(
#                 max_val + right_pad * 0.02,
#                 idx_r,
#                 f"достигли {int(pareto_threshold*100)}% на «{labels[idx]}»",
#                 ha="left",
#                 va="center",
#                 fontsize=10,
#                 color=COLOR_MUTED,
#             )

#     fig.tight_layout()
#     return _fig_to_svg(fig)
