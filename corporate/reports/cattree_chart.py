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
    """
    Icicle 3 уровня (структура, без метрик):
      Level 0 = CatTree level 0
      Level 1 = CatTree level 1
      Level 2 = SubCategory names (rows[*].l2_names) привязанные к узлу level 1

    ВАЖНО:
      - Никаких цифр/процентов
      - Ширины считаем по структуре (ветвистости), а не по товарам
      - Подписи:
          Level0 = по центру
          Level1 = вертикальные (если не влезают — перенос на 2 строки)
          Level2 = вертикальные (если не влезают — многоточие)
      - Без верхней полосы "Каталог"
      - Без пустого места снизу (поджимаем ось Y)
    """

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.patches import Rectangle

    if not rows:
        return None

    # ---------- helpers ----------
    def lighten(rgba, amount=0.55):
        r, g, b, a = rgba
        r = r + (1 - r) * amount
        g = g + (1 - g) * amount
        b = b + (1 - b) * amount
        return (r, g, b, a)

    def add_box(ax, x, y, w, h, face, edge=(1, 1, 1, 1), lw=1.0):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw))

    def add_label_h(ax, x, y, w, h, text, *, size=9, weight="bold", color="#0f172a",
                    pad=0.008, min_w=0.05):
        """Горизонтальная подпись (не используем для Level0, но оставляем как helper)."""
        if w < min_w:
            return
        t = (text or "—").strip()
        ax.text(
            x + pad,
            y + h - 0.16,
            t,
            fontsize=size,
            fontweight=weight,
            color=color,
            va="top",
            ha="left",
        )

    def add_label_center(ax, x, y, w, h, text, *, size=10, weight="bold", color="#0f172a", min_w=0.04):
        """Центрированная подпись (Level0)."""
        if w < min_w:
            return
        t = (text or "—").strip()
        ax.text(
            x + w / 2,
            y + h / 2,
            t,
            fontsize=size,
            fontweight=weight,
            color=color,
            va="center",
            ha="center",
        )

    def add_label_v(ax, x, y, w, h, text, *, size=8, weight="bold", color="#0f172a",
                    min_w=0.015):
        """Простая вертикальная подпись (для коротких служебных текстов типа '+ ещё')."""
        if w < min_w:
            return
        t = (text or "—").strip()
        ax.text(
            x + w / 2,
            y + h / 2,
            t,
            fontsize=size,
            fontweight=weight,
            color=color,
            rotation=90,
            va="center",
            ha="center",
        )

    def add_label_v_ellipsis(ax, x, y, w, h, text, *, size=6, weight="normal", color="#0f172a",
                            min_w=0.010, pad_ratio=0.92):
        """
        Вертикальная подпись с многоточием (Level2):
        если текст по высоте не помещается в прямоугольник — обрезаем и добавляем '…'.
        """
        if w < min_w:
            return

        t_full = (text or "—").strip()
        fig = ax.figure

        txt = ax.text(
            x + w / 2,
            y + h / 2,
            t_full,
            fontsize=size,
            fontweight=weight,
            color=color,
            rotation=90,
            va="center",
            ha="center",
        )

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # высота прямоугольника в пикселях
        p0 = ax.transData.transform((x, y))
        p1 = ax.transData.transform((x, y + h))
        rect_h_px = abs(p1[1] - p0[1]) * pad_ratio

        bbox = txt.get_window_extent(renderer=renderer)
        if bbox.height <= rect_h_px:
            return  # влезло

        # не влезло -> уменьшаем строку, добавляя многоточие
        base = t_full
        lo, hi = 0, len(base)
        best = "…"

        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = (base[:mid].rstrip() + "…") if mid > 0 else "…"
            txt.set_text(candidate)
            fig.canvas.draw()
            bbox = txt.get_window_extent(renderer=renderer)

            if bbox.height <= rect_h_px:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1

        txt.set_text(best)

    def split_2lines(text: str) -> str:
        """Разбить строку на 2 строки максимально красиво (Level1)."""
        s = (text or "").strip()
        if not s:
            return "—"

        mid = len(s) // 2
        candidates = []
        for i, ch in enumerate(s):
            if ch in (" ", "-", "–", "—", "/"):
                candidates.append(i)

        if candidates:
            cut = min(candidates, key=lambda i: abs(i - mid))
            left = s[:cut].strip(" -–—/")
            right = s[cut + 1:].strip(" -–—/")
            if left and right:
                return left + "\n" + right

        return s[:mid].strip() + "\n" + s[mid:].strip()

    def add_label_v_l1(ax, x, y, w, h, text, *, size=8, weight="bold", color="#0f172a",
                       min_w=0.012, pad_ratio=0.92):
        """
        Вертикальная подпись для Level1:
        если не влазит в высоту прямоугольника — переносим на 2 строки,
        если всё равно не влезло — уменьшаем шрифт.
        """
        if w < min_w:
            return

        t = (text or "—").strip()
        fig = ax.figure

        txt = ax.text(
            x + w / 2,
            y + h / 2,
            t,
            fontsize=size,
            fontweight=weight,
            color=color,
            rotation=90,
            va="center",
            ha="center",
        )

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        p0 = ax.transData.transform((x, y))
        p1 = ax.transData.transform((x, y + h))
        rect_h_px = abs(p1[1] - p0[1]) * pad_ratio

        bbox = txt.get_window_extent(renderer=renderer)

        # если не влезло — перенос на 2 строки
        if bbox.height > rect_h_px:
            txt.set_text(split_2lines(t))
            fig.canvas.draw()
            bbox = txt.get_window_extent(renderer=renderer)

            # если всё равно не влезло — уменьшаем шрифт
            fs = size
            while bbox.height > rect_h_px and fs > 6:
                fs -= 1
                txt.set_fontsize(fs)
                fig.canvas.draw()
                bbox = txt.get_window_extent(renderer=renderer)

    # ---------- 1) соберём CatTree структуру (level0 -> level1) ----------
    # rows MUST contain: id, parent_id, level, name, l2_names(for level1)
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

    # ---------- 2) подготовим узлы level1 и их level2=SubCategory ----------
    root_to_l1 = {}
    l1_to_l2 = {}

    for rid in root_ids:
        l1_ids = [c for c in children.get(rid, []) if int(by_id[c].get("level", 0) or 0) == 1]
        l1_ids.sort(key=name_key)

        shown_l1 = l1_ids[:max_l1_per_root]
        rest_l1 = len(l1_ids) - len(shown_l1)
        root_to_l1[rid] = (shown_l1, rest_l1)

        for c1 in shown_l1:
            # Level2 = SubCategory names from print_tree_view (l2_names)
            l2_names = list(by_id[c1].get("l2_names", []) or [])
            l2_names = sorted(set([str(x).strip() for x in l2_names if str(x).strip()]))

            shown_l2 = l2_names[:max_l2_per_l1]
            rest_l2 = len(l2_names) - len(shown_l2)
            l1_to_l2[c1] = (shown_l2, rest_l2)

    # ---------- 3) структурные веса (НЕ items!) ----------
    def l1_weight(l1_id):
        shown_l2, rest_l2 = l1_to_l2.get(l1_id, ([], 0))
        return max(1, len(shown_l2) + (1 if rest_l2 > 0 else 0))

    def root_weight(rid):
        shown_l1, rest_l1 = root_to_l1.get(rid, ([], 0))
        w = sum(l1_weight(c1) for c1 in shown_l1) + (1 if rest_l1 > 0 else 0)
        return max(1, w)

    root_weights = [(rid, root_weight(rid)) for rid in root_ids]
    total_w = sum(w for _, w in root_weights) or 1

    # ---------- 4) рисуем 3 полосы (без "Каталог") ----------
    fig = plt.figure(figsize=(12.2, 5.0), dpi=170)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)

    # ВАЖНО: поджимаем по высоте, чтобы не было пустого места снизу
    ax.set_ylim(0, 3.05)
    ax.axis("off")

    ax.text(
        0.0,
        2.92,
        "Структура каталога",
        fontsize=12,
        fontweight="bold",
        va="bottom",
    )

    palette = cm.get_cmap("tab20", len(root_weights))

    H = 0.82
    y_l0 = 2.05
    y_l1 = 1.05
    y_l2 = 0.10

    # Level0 -> Level1 -> Level2
    x = 0.0
    for i, (rid, rw_struct) in enumerate(root_weights):
        rw = rw_struct / total_w
        root_name = (by_id[rid].get("name") or "—").strip()
        root_color = palette(i)

        # Level 0 block
        add_box(ax, x, y_l0, rw, H, face=lighten(root_color, 0.15), edge=(1, 1, 1, 1), lw=1.2)
        add_label_center(ax, x, y_l0, rw, H, root_name, size=10, min_w=0.04)

        # Level 1 inside root
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
                add_box(ax, cx, y_l1, cw1, H, face=(0.92, 0.93, 0.95, 1), edge=(1, 1, 1, 1), lw=1.0)
                add_label_v(ax, cx, y_l1, cw1, H, "+ ещё", size=8, weight="bold", color="#334155", min_w=0.012)
                cx += cw1
                continue

            l1_name = (by_id[c1].get("name") or "—").strip()
            add_box(ax, cx, y_l1, cw1, H, face=lighten(root_color, 0.55), edge=(1, 1, 1, 1), lw=1.0)
            add_label_v_l1(ax, cx, y_l1, cw1, H, l1_name, size=8, min_w=0.012)

            # Level 2 = SubCategory names for this level1
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
                    add_box(ax, cxx, y_l2, cw2, H, face=(0.95, 0.95, 0.96, 1), edge=(1, 1, 1, 1), lw=1.0)
                    add_label_v(ax, cxx, y_l2, cw2, H, "+ ещё", size=7, weight="bold", color="#64748b", min_w=0.010)
                    cxx += cw2
                    continue

                add_box(ax, cxx, y_l2, cw2, H, face=lighten(root_color, 0.70), edge=(1, 1, 1, 1), lw=1.0)
                add_label_v_ellipsis(ax, cxx, y_l2, cw2, H, str(nm),
                                    size=6, weight="normal", color="#0f172a", min_w=0.010)

                cxx += cw2

            cx += cw1

        x += rw

    fig.tight_layout(pad=0.4)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)

    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
