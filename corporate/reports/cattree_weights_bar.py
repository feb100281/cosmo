# corporate/reports/cattree_weights_bar.py
import base64
import io
from collections import defaultdict


def build_cattree_weights_bar_base64(
    rows,
    top_n_roots=12,
    max_l1_per_root=10,
    max_l2_per_l1=12,
    sort="structure",          # "structure" | "alpha"
    show_percent=True,
):
    """
    Горизонтальный bar chart по "весу" категорий (Level0).
    Вес считается структурно, как в treemap:
      - для root: сумма весов его L1 + (1 если есть скрытые L1)
      - для L1: кол-во L2, показанных + (1 если есть скрытые L2)
      - всё минимум 1

    rows must contain:
      - id, parent_id, level, name
      - for level1 rows: l2_names: list[str]  (подкатегории 2 уровня)
    """

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not rows:
        return None

    # ---------------- 1) собрать дерево ----------------
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
    if not root_ids:
        return None

    def name_key(rid):
        return (by_id[rid].get("name") or "").strip().lower()

    def struct_key_root(rid):
        # (для сортировки) оцениваем структурную “массу”
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

    # ---------------- 2) подготовить L1/L2 ограничения (как в treemap) ----------------
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

    # ---------------- 3) веса ----------------
    def l1_weight(l1_id):
        shown_l2, rest_l2 = l1_to_l2.get(l1_id, ([], 0))
        return max(1, len(shown_l2) + (1 if rest_l2 > 0 else 0))

    def root_weight(rid):
        shown_l1, rest_l1 = root_to_l1.get(rid, ([], 0))
        w = sum(l1_weight(c1) for c1 in shown_l1) + (1 if rest_l1 > 0 else 0)
        return max(1, w)

    data = []
    for rid in root_ids:
        nm = (by_id[rid].get("name") or "—").strip()
        w = root_weight(rid)
        data.append((nm, w))

    # сортируем по весу (для bar chart так нагляднее)
    data.sort(key=lambda x: (-x[1], x[0].lower()))

    names = [x[0] for x in data]
    weights = [x[1] for x in data]
    total = sum(weights) or 1
    perc = [w / total * 100 for w in weights]

    # ---------------- 4) рисуем ----------------
    # высота фигуры под число строк (чтобы было аккуратно)
    n = len(names)
    fig_h = max(2.6, 0.35 * n + 1.2)
    fig = plt.figure(figsize=(10.5, fig_h), dpi=170)
    ax = fig.add_subplot(111)

    y = list(range(n))
    ax.barh(y, weights)  # без явного цвета — дефолт matplotlib
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()

    ax.set_title("Вес категорий (структура каталога)", fontsize=12, fontweight="bold", loc="left", pad=10)

    ax.grid(axis="x", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Вес (структурные единицы)", fontsize=9)

    # подписи справа (вес и %)
    for i, (w, p) in enumerate(zip(weights, perc)):
        if show_percent:
            label = f"{w}  ({p:.1f}%)"
        else:
            label = f"{w}"
        ax.text(w + max(weights) * 0.01, i, label, va="center", fontsize=8)

    # чуть подчистим рамки
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)

    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"