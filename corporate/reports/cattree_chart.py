# corporate/reports/cattree_chart.py
import base64
import io
from collections import defaultdict


def build_cattree_chart_base64(
    rows,
    top_n_roots=8,
    max_l1_per_root=10,
    max_l2_per_l1=12,
    sort="alpha",   # "alpha" | "structure"
):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.patches import FancyBboxPatch

    if not rows:
        return None

    # ---------------- helpers ----------------
    def lighten(rgba, amount=0.55):
        r, g, b, a = rgba
        r = r + (1 - r) * amount
        g = g + (1 - g) * amount
        b = b + (1 - b) * amount
        return (r, g, b, a)

    def add_box(ax, x, y, w, h, face, edge=(1, 1, 1, 0.95), lw=0.9, radius=0.010):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle=f"round,pad=0.002,rounding_size={radius}",
                facecolor=face,
                edgecolor=edge,
                linewidth=lw,
                mutation_aspect=1,
            )
        )

    def add_text_fit(ax, x, y, w, h, text, *,
                     rotation=0,
                     size=10,
                     min_size=5,
                     weight="bold",
                     color="#0f172a",
                     pad_ratio=0.92,
                     ellipsis=True):
        """
        Универсальный текст:
        - пробует уменьшать шрифт, пока не влезет
        - если всё равно не влезло и ellipsis=True -> режет и ставит '…'
        Ограничение:
          rotation=0  -> проверяем bbox.width <= rect_w_px
          rotation=90 -> проверяем bbox.height <= rect_h_px
        """
        t_full = (text or "—").strip()
        fig = ax.figure

        txt = ax.text(
            x + w / 2,
            y + h / 2,
            t_full,
            fontsize=size,
            fontweight=weight,
            color=color,
            rotation=rotation,
            va="center",
            ha="center",
        )

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        p0 = ax.transData.transform((x, y))
        p1 = ax.transData.transform((x + w, y + h))
        rect_w_px = abs(p1[0] - p0[0]) * pad_ratio
        rect_h_px = abs(p1[1] - p0[1]) * pad_ratio

        def fits():
            bbox = txt.get_window_extent(renderer=renderer)
            if rotation == 90:
                return bbox.height <= rect_h_px
            return bbox.width <= rect_w_px

        # 1) уменьшаем шрифт
        fs = size
        while not fits() and fs > min_size:
            fs -= 1
            txt.set_fontsize(fs)
            fig.canvas.draw()

        if fits() or not ellipsis:
            return

        # 2) режем + …
        base = t_full
        lo, hi = 0, len(base)
        best = "…"
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = (base[:mid].rstrip() + "…") if mid > 0 else "…"
            txt.set_text(candidate)
            fig.canvas.draw()
            if fits():
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1

        txt.set_text(best)

    def split_2lines(text: str) -> str:
        s = (text or "").strip()
        if not s:
            return "—"
        mid = len(s) // 2
        candidates = [i for i, ch in enumerate(s) if ch in (" ", "-", "–", "—", "/")]
        if candidates:
            cut = min(candidates, key=lambda i: abs(i - mid))
            left = s[:cut].strip(" -–—/")
            right = s[cut + 1:].strip(" -–—/")
            if left and right:
                return left + "\n" + right
        return s[:mid].strip() + "\n" + s[mid:].strip()

    def add_label_root(ax, x, y, w, h, text, *,
                       size=10,
                       min_size=6,
                       rotate_threshold=0.060,
                       color="#0f172a"):
        # Root: если узко -> вертикально; иначе горизонтально
        rot = 90 if w < rotate_threshold else 0
        add_text_fit(
            ax, x, y, w, h, text,
            rotation=rot,
            size=size,
            min_size=min_size,
            weight="bold",
            color=color,
            pad_ratio=0.92,
            ellipsis=True,
        )

    def add_label_l1(ax, x, y, w, h, text, *,
                     size=8,
                     min_size=5,
                     color="#0f172a"):
        """
        Level1: ВСЕГДА пишем.
        Сначала пытаемся как есть (вертикально).
        Если не влезло — перенос на 2 строки + авто-уменьшение.
        Если всё равно не влезло — режем с '…'.
        """
        t = (text or "—").strip()
        fig = ax.figure

        # 1) пробуем обычный текст
        add_text_fit(
            ax, x, y, w, h, t,
            rotation=90,
            size=size,
            min_size=min_size,
            weight="bold",
            color=color,
            pad_ratio=0.90,
            ellipsis=False,   # пока без обрезки
        )

        # проверим, влез ли (если нет — заменим на перенос)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # найдём последний добавленный Text объект в axes
        # (в matplotlib это нормально для такой задачи)
        txt = ax.texts[-1]
        p0 = ax.transData.transform((x, y))
        p1 = ax.transData.transform((x, y + h))
        rect_h_px = abs(p1[1] - p0[1]) * 0.90
        bbox = txt.get_window_extent(renderer=renderer)

        if bbox.height <= rect_h_px:
            return

        # 2) перенос на 2 строки (всё равно rotation=90, но строки помогут)
        txt.set_text(split_2lines(t))
        fig.canvas.draw()
        bbox = txt.get_window_extent(renderer=renderer)

        fs = txt.get_fontsize()
        while bbox.height > rect_h_px and fs > min_size:
            fs -= 1
            txt.set_fontsize(fs)
            fig.canvas.draw()
            bbox = txt.get_window_extent(renderer=renderer)

        if bbox.height <= rect_h_px:
            return

        # 3) если всё равно не влезло — обрезаем
        # (тут проще создать новый текст, а старый “погасить”)
        txt.set_visible(False)
        add_text_fit(
            ax, x, y, w, h, t,
            rotation=90,
            size=size,
            min_size=min_size,
            weight="bold",
            color=color,
            pad_ratio=0.90,
            ellipsis=True,
        )

    def add_label_l2(ax, x, y, w, h, text, *,
                     size=6,
                     min_size=4,
                     color="#0f172a"):
        # Level2: всегда вертикально + авто-уменьшение + …
        add_text_fit(
            ax, x, y, w, h, str(text),
            rotation=90,
            size=size,
            min_size=min_size,
            weight="normal",
            color=color,
            pad_ratio=0.92,
            ellipsis=True,
        )

    # ---------------- 1) собрать структуру (level0 -> level1) ----------------
    by_id = {r["id"]: r for r in rows if r.get("id") is not None}

    children = defaultdict(list)
    for r in rows:
        pid = r.get("parent_id")
        rid = r.get("id")
        if pid is not None and rid is not None:
            children[pid].append(rid)

    root_ids = [
        r["id"]
        for r in rows
        if int(r.get("level", 0) or 0) == 0 and r.get("id") in by_id
    ]

    def name_key(rid):
        return (by_id[rid].get("name") or "").strip().lower()

    def struct_key_root(rid):
        l1_ids = [c for c in children.get(rid, []) if int(by_id[c].get("level", 0) or 0) == 1]
        l2_cnt = 0
        for c1 in l1_ids:
            l2_cnt += len(by_id[c1].get("l2_names", []) or [])
        return -(len(l1_ids) + l2_cnt)

    if sort == "structure":
        root_ids.sort(key=lambda rid: (struct_key_root(rid), name_key(rid)))
    else:
        root_ids.sort(key=name_key)

    root_ids = root_ids[:top_n_roots]
    if not root_ids:
        return None

    # ---------------- 2) level1 + level2 ----------------
    root_to_l1 = {}
    l1_to_l2 = {}

    for rid in root_ids:
        l1_ids = [c for c in children.get(rid, []) if int(by_id[c].get("level", 0) or 0) == 1]
        l1_ids.sort(key=name_key)

        shown_l1 = l1_ids[:max_l1_per_root]
        rest_l1 = len(l1_ids) - len(shown_l1)
        root_to_l1[rid] = (shown_l1, rest_l1)

        for c1 in shown_l1:
            l2_names = list(by_id[c1].get("l2_names", []) or [])
            l2_names = sorted(set([str(x).strip() for x in l2_names if str(x).strip()]))

            shown_l2 = l2_names[:max_l2_per_l1]
            rest_l2 = len(l2_names) - len(shown_l2)
            l1_to_l2[c1] = (shown_l2, rest_l2)

    # ---------------- 3) веса (структурные) ----------------
    def l1_weight(l1_id):
        shown_l2, rest_l2 = l1_to_l2.get(l1_id, ([], 0))
        return max(1, len(shown_l2) + (1 if rest_l2 > 0 else 0))

    def root_weight(rid):
        shown_l1, rest_l1 = root_to_l1.get(rid, ([], 0))
        w = sum(l1_weight(c1) for c1 in shown_l1) + (1 if rest_l1 > 0 else 0)
        return max(1, w)

    root_weights = [(rid, root_weight(rid)) for rid in root_ids]
    total_w = sum(w for _, w in root_weights) or 1

    # ---------------- 4) рисование ----------------
    fig = plt.figure(figsize=(12.2, 5.0), dpi=170)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 3.05)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        0.0,
        2.92,
        "Структура каталога",
        fontsize=12,
        fontweight="bold",
        color="#0f172a",
        va="bottom",
        ha="left",
    )

    palette = cm.get_cmap("tab20", len(root_weights))

    H = 0.82
    y_l0 = 2.05
    y_l1 = 1.05
    y_l2 = 0.10

    # gap между root для читаемости
    gap = 0.006
    total_gap = gap * (len(root_weights) - 1) if len(root_weights) > 1 else 0.0
    usable = 1.0 - total_gap
    if usable <= 0:
        usable = 1.0

    x = 0.0
    for i, (rid, rw_struct) in enumerate(root_weights):
        rw = (rw_struct / total_w) * usable
        root_name = (by_id[rid].get("name") or "—").strip()
        root_color = palette(i)

        # Level0
        add_box(ax, x, y_l0, rw, H, face=lighten(root_color, 0.15), lw=0.9, radius=0.012)
        add_label_root(ax, x, y_l0, rw, H, root_name, size=10, min_size=6, rotate_threshold=0.060)

        # Level1
        shown_l1, rest_l1 = root_to_l1.get(rid, ([], 0))
        l1_units = [("ID", c1, l1_weight(c1)) for c1 in shown_l1]
        if rest_l1 > 0:
            l1_units.append(("MORE", None, 1))

        l1_total = sum(u[2] for u in l1_units) or 1
        cx = x

        for kind, c1, w1 in l1_units:
            cw1 = (w1 / l1_total) * rw
            if cw1 <= 0:
                continue

            if kind == "MORE":
                add_box(ax, cx, y_l1, cw1, H, face=(0.94, 0.95, 0.97, 1), lw=0.8, radius=0.010)
                add_text_fit(ax, cx, y_l1, cw1, H, "+ ещё", rotation=90, size=8, min_size=6,
                             weight="bold", color="#334155", pad_ratio=0.90, ellipsis=True)
                cx += cw1
                continue

            l1_name = (by_id[c1].get("name") or "—").strip()
            add_box(ax, cx, y_l1, cw1, H, face=lighten(root_color, 0.55), lw=0.8, radius=0.010)
            add_label_l1(ax, cx, y_l1, cw1, H, l1_name, size=8, min_size=5)

            # Level2
            shown_l2, rest_l2 = l1_to_l2.get(c1, ([], 0))
            l2_units = [("ID", nm) for nm in shown_l2]
            if rest_l2 > 0:
                l2_units.append(("MORE", None))

            l2_total = len(l2_units) or 1
            cxx = cx

            for k2, nm in l2_units:
                cw2 = (1 / l2_total) * cw1
                if cw2 <= 0:
                    continue

                if k2 == "MORE":
                    add_box(ax, cxx, y_l2, cw2, H, face=(0.96, 0.96, 0.97, 1), lw=0.75, radius=0.009)
                    add_text_fit(ax, cxx, y_l2, cw2, H, "+ ещё", rotation=90, size=7, min_size=5,
                                 weight="bold", color="#64748b", pad_ratio=0.92, ellipsis=True)
                    cxx += cw2
                    continue

                add_box(ax, cxx, y_l2, cw2, H, face=lighten(root_color, 0.70), lw=0.75, radius=0.009)
                add_label_l2(ax, cxx, y_l2, cw2, H, nm, size=6, min_size=4)

                cxx += cw2

            cx += cw1

        x += rw
        if i < len(root_weights) - 1:
            x += gap

    fig.tight_layout(pad=0.35)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)

    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"