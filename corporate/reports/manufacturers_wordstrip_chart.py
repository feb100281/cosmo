# from __future__ import annotations

# from typing import Any
# from decimal import Decimal

# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt


# def build_manufacturers_wordstrip_svg(
#     revenue_rows: list[dict[str, Any]],
#     years: list[int],
#     *,
#     exclude_unknown: bool = True,
#     height_cm: float = 5.5,     # УЗКАЯ стильная полоса
#     width_cm: float = 27.0,
#     dpi: int = 240,
#     theme: str = "pastel_mix", # новый микс цветов
#     title: bool = False,
# ) -> str | None:
#     """
#     Декоративная word-полоса:
#     — все уникальные производители за период
#     — одинаковый размер слов
#     — разные мягкие цвета
#     — без привязки к выручке
#     """

#     try:
#         from wordcloud import WordCloud
#     except Exception:
#         return None

#     names: list[str] = []

#     for r in revenue_rows:
#         mf_id = int(r.get("manufacturer_id") or 0)
#         name = (r.get("name") or "").strip()

#         if exclude_unknown:
#             if mf_id == 0:
#                 continue
#             if not name or name.startswith("!"):
#                 continue

#         names.append(name)

#     # уникальные
#     names = sorted(set(names), key=lambda x: x.lower())

#     if not names:
#         return None

#     # всем одинаковый вес
#     freqs = {n: 1.0 for n in names}

#     # --- стильные палитры ---
#     if theme == "pastel_mix":
#         palette = [
#             "#4F46E5",  # индиго
#             "#7C3AED",  # фиолетовый
#             "#2563EB",  # синий
#             "#0EA5E9",  # голубой
#             "#6366F1",
#             "#A855F7",
#         ]
#         bg = "white"
#     else:
#         palette = ["#2563EB"]
#         bg = "white"

#     import random

#     def color_func(*args, **kwargs):
#         return random.choice(palette)

#     # размеры
#     width_in = width_cm / 2.54
#     height_in = height_cm / 2.54
#     px_w = int(width_in * dpi)
#     px_h = int(height_in * dpi)

#     wc = WordCloud(
#         width=px_w,
#         height=px_h,
#         background_color=bg,
#         prefer_horizontal=1.0,     # ВСЁ горизонтально
#         random_state=22,
#         collocations=False,
#         min_font_size=18,
#         max_font_size=42,          # одинаковая визуальная плотность
#         margin=4,
#     ).generate_from_frequencies(freqs)

#     wc = wc.recolor(color_func=color_func, random_state=22)

#     fig = plt.figure(figsize=(width_in, height_in), dpi=dpi)
#     ax = fig.add_subplot(111)
#     ax.axis("off")
#     fig.patch.set_facecolor(bg)
#     ax.set_facecolor(bg)

#     if title:
#         ax.text(
#             0,
#             1.04,
#             "Производители",
#             transform=ax.transAxes,
#             fontsize=12,
#             fontweight="bold",
#             ha="left",
#         )

#     ax.imshow(wc, interpolation="bilinear")

#     import io
#     buf = io.StringIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight")
#     plt.close(fig)
#     return buf.getvalue()

from __future__ import annotations

from typing import Any
import random
import hashlib


def build_manufacturers_wordstrip_svg(
    revenue_rows: list[dict[str, Any]],
    years: list[int],
    *,
    exclude_unknown: bool = True,
    height_cm: float = 2.8,
    width_cm: float = 27.0,
    dpi: int = 240,
    theme: str = "elegant_mono",
    title: bool = False,
) -> str | None:
    """
    Декоративная word-полоса (стикеры/плашки) — стильная версия:
    — минималистичный дизайн, приглушённые цвета
    — небольшие повороты только для акцента
    — системные шрифты
    """

    # 1) собираем имена
    names: list[str] = []
    for r in revenue_rows:
        mf_id = int(r.get("manufacturer_id") or 0)
        name = (r.get("name") or "").strip()

        if exclude_unknown:
            if mf_id == 0:
                continue
            if not name or name.startswith("!"):
                continue

        if name:
            names.append(name)

    names = sorted(set(names), key=lambda x: x.lower())
    if not names:
        return None

    # 2) размеры в px
    width_in = width_cm / 2.54
    height_in = height_cm / 2.54
    W = int(width_in * dpi)
    H = int(height_in * dpi)

    # 3) темы — теперь более сдержанные и стильные
    if theme == "elegant_mono":
        bg = "#F8FAFC"  # очень светлый серо-голубой
        palette = [
            "#2C3E50", "#34495E", "#4A5568", "#5D6D7E",
            "#6B7B8E", "#7F8C8D", "#95A5A6", "#BDC3C7"
        ]
        # Текст всегда тёмный на светлом фоне
        def pick_text_color(hex_color: str) -> str:
            return "#1E293B"
    
    elif theme == "warm_minimal":
        bg = "#FEF9E7"  # тёплый кремовый
        palette = [
            "#A65A4A", "#B76E5E", "#C88272", "#D99686",
            "#8B6B61", "#9C7A6E", "#AD8A7B", "#BE9988"
        ]
        def pick_text_color(hex_color: str) -> str:
            return "#3D2B1F"
    
    elif theme == "cool_elegant":
        bg = "#EFF6FF"  # светло-голубой
        palette = [
            "#1E3A5F", "#254E7A", "#2E6295", "#3A76B0",
            "#4682B4", "#5F9EA0", "#6A9FB5", "#7FB0C5"
        ]
        def pick_text_color(hex_color: str) -> str:
            return "#0F2B3D"
    
    elif theme == "modern_glass":
        bg = "#F0F4F8"  # полупрозрачный фон имитируем светлым
        palette = [
            "#334E68", "#4A6A8A", "#6185A5", "#79A0C0",
            "#90B8D1", "#A7CFE2", "#BED6EC", "#C9E0F0"
        ]
        def pick_text_color(hex_color: str) -> str:
            return "#1A2B3C"
    
    else:  # fallback для обратной совместимости
        bg = "#FFFFFF"
        palette = ["#2563EB", "#7C3AED", "#0EA5E9", "#14B8A6"]
        def pick_text_color(hex_color: str) -> str:
            return "#FFFFFF"

    # 4) детерминированность
    seed_base = int(hashlib.md5(("|".join(names) + str(years)).encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed_base)

    # 5) оценка размеров плашки
    def estimate_label_size(text: str, font_px: int, pad_x: int, pad_y: int) -> tuple[int, int]:
        k = 0.56
        w = int(len(text) * font_px * k) + 2 * pad_x
        h = int(font_px * 1.15) + 2 * pad_y
        return w, h

    # параметры плашек — более утончённые
    pad_x = 12      # чуть больше воздуха
    pad_y = 8
    gap = 12        # расстояние между плашками
    radius = 20     # более скруглённые углы

    max_font = 16   # чуть крупнее
    min_font = 11

    # меньше углов, только лёгкие повороты
    angles = [-6, -3, 0, 3, 6]  # убрали сильные наклоны

    # 6) область размещения
    margin = max(20, int(min(W, H) * 0.05))

    card = False
    card_pad = 10
    card_bg = "#FFFFFF"
    card_radius = max(18, int(min(W, H) * 0.08))

    title_h = int(H * 0.22) if title else 0

    x0 = margin + (card_pad if card else 0)
    y0 = margin + (card_pad if card else 0) + title_h
    x1 = W - margin - (card_pad if card else 0)
    y1 = H - margin - (card_pad if card else 0)

    if x1 <= x0 or y1 <= y0:
        return None

    # Ограничим максимальную ширину плашки
    max_label_w = int((x1 - x0) * 0.35)

    # 7) готовим элементы + авто-подбор размера шрифта
    def font_for_index(i: int) -> int:
        n = len(names)
        if i < max(2, int(0.15 * n)):
            return max_font
        if i < max(6, int(0.5 * n)):
            return int((max_font + min_font) / 2)
        return min_font

    items = []
    for i, name in enumerate(names):
        base_font = font_for_index(i)
        font_px = base_font

        # уменьшаем шрифт, пока не влезет в max_label_w
        while font_px > min_font:
            w, h = estimate_label_size(name, font_px, pad_x, pad_y)
            if w <= max_label_w:
                break
            font_px -= 2

        w, h = estimate_label_size(name, font_px, pad_x, pad_y)

        # если всё равно слишком широко — обрежем текст с многоточием
        if w > max_label_w:
            k = 0.56
            approx_chars = max(6, int((max_label_w - 2 * pad_x) / (font_px * k)) - 1)
            short = name[:approx_chars].rstrip() + "…"
            name_use = short
            w, h = estimate_label_size(name_use, font_px, pad_x, pad_y)
        else:
            name_use = name

        # цвет из палитры
        color_idx = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16) % len(palette)
        color = palette[color_idx]
        
        items.append({
            "text": name_use,
            "font": font_px,
            "w": w,
            "h": h,
            "angle": rng.choice(angles),
            "bg": color,
            "fg": pick_text_color(color),
        })

    # перемешаем, чтобы не было строгой сортировки по размеру
    rng.shuffle(items)

    # 8) раскладываем по строкам
    placed = []
    cursor_x = x0
    cursor_y = y0
    row_h = 0

    for it in items:
        w = it["w"]
        h = it["h"]

        if cursor_x + w > x1:
            cursor_x = x0 + rng.randint(-gap // 2, gap // 2)
            cursor_y += row_h + gap
            row_h = 0

        if cursor_y + h > y1:
            continue

        # очень лёгкий джиттер
        jitter_x = rng.randint(-gap // 4, gap // 4)
        jitter_y = rng.randint(-gap // 6, gap // 6)

        it["x"] = max(x0, min(x1 - w, cursor_x + jitter_x))
        it["y"] = max(y0, min(y1 - h, cursor_y + jitter_y))

        placed.append(it)
        cursor_x = it["x"] + w + gap
        row_h = max(row_h, h)

    if not placed:
        return None

    # 9) SVG
    font_stack = (
        "system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "
        "Noto Sans, Helvetica, Arial, 'DejaVu Sans', sans-serif"
    )

    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;")
        )

    # более мягкая тень
    shadow = """
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000000" flood-opacity="0.08"/>
    </filter>
    """

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" width="100%">',
        "<defs>",
        shadow,
        "</defs>",
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>'
    ]

    if card:
        card_x = margin
        card_y = margin
        card_w = W - 2 * margin
        card_h = H - 2 * margin
        svg_parts.append(
            f'<rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" '
            f'rx="{card_radius}" ry="{card_radius}" fill="{card_bg}" '
            f'stroke="#0B1020" stroke-opacity="0.05" stroke-width="1.5"/>'
        )

    if title:
        tx = x0
        ty = margin + (card_pad if card else 0) + int(title_h * 0.62)
        svg_parts.append(
            f'<text x="{tx}" y="{ty}" font-family="{font_stack}" '
            f'font-size="{max(16, int(H*0.1))}" font-weight="600" fill="#334155" opacity="0.9">'
            f'Производители</text>'
        )
        line_y = margin + (card_pad if card else 0) + title_h - int(H * 0.03)
        svg_parts.append(
            f'<rect x="{x0}" y="{line_y}" width="{x1-x0}" height="1.5" fill="#94A3B8" opacity="0.3"/>'
        )

    for it in placed:
        x, y, w, h = it["x"], it["y"], it["w"], it["h"]
        angle = it["angle"]
        bgc, fgc = it["bg"], it["fg"]
        text = esc(it["text"])
        font_px = it["font"]

        cx = x + w / 2
        cy = y + h / 2

        svg_parts.append(f'<g transform="rotate({angle} {cx} {cy})">')

        # плашка с очень тонкой обводкой
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{radius}" ry="{radius}" fill="{bgc}" filter="url(#softShadow)" '
            f'stroke="#FFFFFF" stroke-opacity="0.3" stroke-width="1"/>'
        )

        # текст
        svg_parts.append(
            f'<text x="{x + w/2:.1f}" y="{y + h/2:.1f}" '
            f'font-family="{font_stack}" font-size="{font_px}" font-weight="500" '
            f'fill="{fgc}" text-anchor="middle" dominant-baseline="central" '
            f'letter-spacing="0.2">{text}</text>'
        )

        svg_parts.append("</g>")

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)