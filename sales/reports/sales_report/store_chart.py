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