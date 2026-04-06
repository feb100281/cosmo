# corporate/reports/manufacturers_top_by_year_svg.py
from __future__ import annotations

from decimal import Decimal
from typing import Any


def build_top_by_year_svg(
    top_by_year: dict[str, Any],
    *,
    title: str = "Топ производителей по годам",
    width: int = 980,
    row_h: int = 26,          # высота строки в топе
    year_block_pad: int = 18, # отступ между годами
    left_label_w: int = 260,  # место под название
    bar_w: int = 420,         # ширина бара
    font: str = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
) -> str:
    """
    Рисует SVG: по каждому году свой блок (small multiples),
    внутри — горизонтальные бары топ-N.
    """
    per_year = top_by_year.get("per_year") or []
    if not per_year:
        return ""

    top_n = int(top_by_year.get("top_n") or 5)

    # общая высота
    blocks_h = []
    for b in per_year:
        n = len(b.get("items") or [])
        # заголовок года + n строк + низ
        blocks_h.append(34 + max(1, n) * row_h + 10)
    height = 20 + sum(blocks_h) + year_block_pad * (len(per_year) - 1) + 20

    # цвета/стиль
    # bg = "#0b1220"
    # card = "rgba(255,255,255,.06)"
    # grid = "rgba(255,255,255,.14)"
    # text = "rgba(255,255,255,.92)"
    # muted = "rgba(255,255,255,.62)"
    # accent = "#7dd3fc"  # аккуратный business-cyan
    
    # цвета/стиль (деловой светлый)
    bg = "#ffffff"
    card = "#f8fafc"                 # очень светлая карточка
    card_border = "rgba(15,23,42,.10)"
    grid = "rgba(15,23,42,.12)"
    text = "rgba(15,23,42,.92)"      # почти чёрный (slate-900)
    muted = "rgba(15,23,42,.60)"
    accent = "#2563eb"               # спокойный business-blue (можно заменить на ваш акцент)
    bar_bg = "#e5e7eb"               # подложка бара

    x0 = 18
    y = 18

    def esc(s: Any) -> str:
        s = str(s or "")
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
        )

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
    )
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="{bg}"/>')

    # title
    parts.append(
        f'<text x="{x0}" y="{y+18}" fill="{text}" font-family="{font}" font-size="16" font-weight="700">'
        f'{esc(title)}</text>'
    )
    y += 34

    # блоки по годам
    for bi, block in enumerate(per_year):
        year = int(block.get("year") or 0)
        items = block.get("items") or []

        # карта-блок
        block_h = 34 + max(1, len(items)) * row_h + 10
        parts.append(f'<rect x="{x0}" y="{y}" width="{width-2*x0}" height="{block_h}" rx="14" fill="{card}"/>')

        # header year + total
        total_disp = esc(block.get("total_disp") or "")
        parts.append(
            f'<text x="{x0+14}" y="{y+22}" fill="{text}" font-family="{font}" font-size="14" font-weight="700">'
            f'{year}</text>'
        )
        parts.append(
            f'<text x="{x0+60}" y="{y+22}" fill="{muted}" font-family="{font}" font-size="12">'
            f'Итого за год: {total_disp}</text>'
        )

        # шкала (grid line) - просто нулевая линия для баров
        bar_x = x0 + 14 + left_label_w
        bar_y0 = y + 34
        parts.append(f'<line x1="{bar_x}" y1="{bar_y0-10}" x2="{bar_x+bar_w}" y2="{bar_y0-10}" stroke="{grid}" stroke-width="1"/>')

        # max value для нормирования
        max_v = Decimal("0")
        for it in items:
            v = it.get("value")
            try:
                vv = Decimal(str(v or "0"))
            except Exception:
                vv = Decimal("0")
            if vv > max_v:
                max_v = vv

        # строки
        for i in range(top_n):
            yy = bar_y0 + i * row_h
            if i < len(items):
                it = items[i]
                name = esc(it.get("name") or "—")
                val_disp = esc(it.get("value_disp") or "")
                share = it.get("share_pct", None)

                # value
                try:
                    vv = Decimal(str(it.get("value") or "0"))
                except Exception:
                    vv = Decimal("0")

                w = 0
                if max_v > 0 and vv > 0:
                    w = int((vv / max_v) * Decimal(bar_w))

                # rank
                parts.append(
                    f'<text x="{x0+14}" y="{yy+18}" fill="{muted}" font-family="{font}" font-size="12">'
                    f'{i+1}.</text>'
                )
                # name
                parts.append(
                    f'<text x="{x0+40}" y="{yy+18}" fill="{text}" font-family="{font}" font-size="12">'
                    f'{name}</text>'
                )

                # bar
                parts.append(f'<rect x="{bar_x}" y="{yy+6}" width="{bar_w}" height="14" rx="2" fill="rgba(255,255,255,.06)"/>')
                if w > 0:
                    parts.append(f'<rect x="{bar_x}" y="{yy+6}" width="{w}" height="14" rx="2" fill="{accent}"/>')

                # value label
                label = val_disp
                if share is not None:
                    label = f"{val_disp}  ({share:.0f}%)"
                parts.append(
                    f'<text x="{bar_x+bar_w+12}" y="{yy+18}" fill="{muted}" font-family="{font}" font-size="12">'
                    f'{esc(label)}</text>'
                )
            else:
                # пустая строка
                parts.append(f'<text x="{x0+40}" y="{yy+18}" fill="{muted}" font-family="{font}" font-size="12">—</text>')

        y += block_h + (year_block_pad if bi < len(per_year)-1 else 0)

    parts.append("</svg>")
    return "".join(parts)