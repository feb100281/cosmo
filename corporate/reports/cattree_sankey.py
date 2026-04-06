from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from math import ceil

@dataclass
class Node:
    key: str
    label: str
    col: int  # 0/1/2
    value: int

def build_sankey_svg(links, *, width=980, height=180) -> str:
    """
    links: list of tuples (src_key, dst_key, value, src_label, dst_label, src_col, dst_col)
    Возвращает SVG строку. Без JS.
    """
    # --- собираем ноды ---
    nodes = {}
    out_sum = defaultdict(int)
    in_sum = defaultdict(int)

    for s, t, v, sl, tl, sc, tc in links:
        out_sum[s] += v
        in_sum[t] += v
        if s not in nodes:
            nodes[s] = Node(key=s, label=sl, col=sc, value=0)
        if t not in nodes:
            nodes[t] = Node(key=t, label=tl, col=tc, value=0)

    for k, n in nodes.items():
        n.value = max(out_sum.get(k, 0), in_sum.get(k, 0), 1)

    # --- раскладка по колонкам ---
    cols = {0: [], 1: [], 2: []}
    for n in nodes.values():
        cols[n.col].append(n)

    for c in cols:
        cols[c].sort(key=lambda x: (-x.value, x.label.casefold()))

    pad_y = 10
    pad_x = 20
    col_x = {
        0: pad_x,
        1: width * 0.46,
        2: width - pad_x - 220,
    }

    # масштабы высоты: чтобы влезало
    def scale_for(col_nodes):
        total = sum(n.value for n in col_nodes)
        if total <= 0:
            return 1.0
        usable = max(40, height - 2 * pad_y - 10 * max(0, len(col_nodes)-1))
        return usable / total

    scales = {c: scale_for(cols[c]) for c in cols}

    # --- позиции узлов ---
    pos = {}  # key -> (x, y, w, h)
    node_w = 14

    for c in [0,1,2]:
        y = pad_y
        for n in cols[c]:
            h = max(10, n.value * scales[c])
            pos[n.key] = (col_x[c], y, node_w, h)
            y += h + 10

    # --- подготовка "стеков" для линков, чтобы распределять по высоте ---
    src_offset = defaultdict(float)
    dst_offset = defaultdict(float)

    # сортируем линки стабильнее
    links_sorted = sorted(links, key=lambda x: (x[5], x[3].casefold(), x[4].casefold(), -x[2]))

    # --- helper для cubic bezier path ---
    def path_cubic(x1, y1, x2, y2):
        dx = (x2 - x1) * 0.55
        return f"M {x1:.1f},{y1:.1f} C {x1+dx:.1f},{y1:.1f} {x2-dx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"

    # --- рисуем ---
    svg = []
    svg.append(f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">')

    # defs (легкая тень)
    svg.append("""
    <defs>
      <filter id="s-shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#111827" flood-opacity="0.12"/>
      </filter>
    </defs>
    """)

    # links
    for s, t, v, sl, tl, sc, tc in links_sorted:
        sx, sy, sw, sh = pos[s]
        tx, ty, tw, th = pos[t]

        sy0 = sy + src_offset[s] + max(5, (v * scales[sc]) / 2)
        ty0 = ty + dst_offset[t] + max(5, (v * scales[tc]) / 2)

        src_offset[s] += max(10, v * scales[sc])
        dst_offset[t] += max(10, v * scales[tc])

        x1 = sx + sw
        x2 = tx
        stroke_w = max(2.0, min(18.0, v * 1.2))  # визуальная толщина, можно подстроить

        svg.append(
            f'<path d="{path_cubic(x1, sy0, x2, ty0)}" '
            f'stroke="#4f46e5" stroke-opacity="0.18" stroke-width="{stroke_w:.1f}" fill="none" />'
        )

    # nodes
    for n in nodes.values():
        x, y, w, h = pos[n.key]
        svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h:.1f}" rx="6" fill="#4f46e5" opacity="0.55" filter="url(#s-shadow)"/>')

        # подписи только для колонок 0 и 1 (чтобы не было каши)
        if n.col in (0, 1):
            tx = x + w + 8
            ty = y + 12
            label = (n.label or "")[:34]
            svg.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="11" fill="#111827">{escape_xml(label)}</text>')

    svg.append("</svg>")
    return "".join(svg)

def escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))
