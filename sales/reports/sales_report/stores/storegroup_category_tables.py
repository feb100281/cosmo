# sales/reports/sales_report/stores/storegroup_category_tables.py
from __future__ import annotations

import math
import pandas as pd

from ..formatters import fmt_money, fmt_delta_short, fmt_delta_pct


def _safe_pct(v):
    return v if v is not None and isinstance(v, (int, float)) and math.isfinite(v) else None


def _fmt_qty_delta(v: float) -> str:
    """
    Форматирование Δшт:
    +12 шт / −12 шт / +1,2 тыс шт
    """
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    if not math.isfinite(v):
        return "—"

    if v == 0:
        return "0 шт"

    sign = "+" if v > 0 else "−"
    a = abs(v)

    if a >= 1000:
        return f"{sign}{a/1000:.1f} тыс шт".replace(".", ",")
    return f"{sign}{int(round(a))} шт"


def _fmt_qty(v: float) -> str:
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    if not math.isfinite(v):
        return "—"

    if v == 0:
        return "0 шт"

    a = abs(v)
    if a >= 1000:
        return f"{a/1000:.1f} тыс шт".replace(".", ",")
    return f"{int(round(a))} шт"

def render_top_drops_table(df: pd.DataFrame, title: str) -> str:
    """
    Таблица ТОП падений (group × category).
    + добавлена колонка Δшт.
    """
    if df is None or df.empty:
        return ""

    rows = []
    for _, r in df.iterrows():
        d = float(r.get("delta", 0.0))
        pct = _safe_pct(r.get("delta_pct"))

        dq = float(r.get("delta_qty", 0.0))

        pill = "pill pill-pos" if d >= 0 else "pill pill-neg"

        sg = str(r.get("storegroup_name", "") or "Без группы")
        cat = str(r.get("cat_name", "") or "Без категории")
        
        prev_qty = float(r.get("prev_qty", 0.0))
        curr_qty = float(r.get("curr_qty", 0.0))

        rows.append(
            f"""
            <tr>
              <td class="text-muted text-truncate" title="{sg}">{sg}</td>
              <td class="text-truncate" title="{cat}">{cat}</td>
            <td class="text-end num">
            <div class="val-main">{fmt_money(r.get("prev"))}</div>
            <div class="val-sub">{_fmt_qty(prev_qty)}</div>
            </td>
            <td class="text-end num">
            <div class="val-main">{fmt_money(r.get("curr"))}</div>
            <div class="val-sub">{_fmt_qty(curr_qty)}</div>
            </td>
              <td class="text-end"><span class="{pill}">{fmt_delta_short(d)}</span></td>
              <td class="text-end num">{_fmt_qty_delta(dq)}</td>
              <td class="text-end text-muted num">{fmt_delta_pct(pct)}</td>
            </tr>
            """
        )

    return f"""

    <div class="card mb-3 diag-card diag-card-top">
      <div class="card-header diag-card-header">
        <strong>{title}</strong>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0 diag-table diag-top">
          <colgroup>
            <col style="width: 22%">
            <col style="width: 26%">
            <col style="width: 13%">
            <col style="width: 13%">
            <col style="width: 12%">
            <col style="width: 8%">
            <col style="width: 6%">
          </colgroup>
          <thead class="table-dark">
            <tr>
              <th>Магазин</th>
              <th>Категория</th>
              <th class="text-end">Было</th>
              <th class="text-end">Стало</th>
              <th class="text-end">Δ₽</th>
              <th class="text-end">Δшт</th>
              <th class="text-end">Δ%</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    </div>
    """.strip()


def render_delta_matrix_table(mat: pd.DataFrame, title: str, max_cols: int = 12) -> str:
    """
    Матрица Δ₽ (магазин × категории).
    """
    if mat is None or mat.empty:
        return ""

    cols = list(mat.columns)[:max_cols]
    mat = mat[cols].copy()

    vmax = float(mat.abs().max().max()) if not mat.empty else 0.0
    vmax = vmax or 1.0

    def cell_style(v: float) -> str:
        a = min(1.0, abs(v) / vmax)

        # более контрастно: 0.08..0.62
        alpha = 0.08 + a * 0.54

        if v < 0:
            # строгий красный, не "пастель"
            return f"background: rgba(220, 38, 38, {alpha:.2f});"
        if v > 0:
            # строгий зелёный
            return f"background: rgba(22, 163, 74, {alpha:.2f});"
        return "background: transparent;"

    thead = (
        "<th class='diag-sticky-col'>Магазин \\ Категория</th>"
        + "".join([f"<th class='text-end diag-colhead'>{c}</th>" for c in cols])
    )

    body_rows = []
    for idx, row in mat.iterrows():
        sg = str(idx)
        tds = [f"<td class='text-muted diag-sticky-col text-truncate' title='{sg}'>{sg}</td>"]

        for c in cols:
            v = float(row[c])

            cls_extra = []
            if abs(v) < 1e-9:
                cls_extra.append("is-zero")
            elif abs(v) / vmax < 0.18:
                cls_extra.append("is-low")

            cls = "text-end diag-cell num " + " ".join(cls_extra)

            txt_color = "#ffffff" if abs(v) / vmax >= 0.35 else "inherit"

            # текст для нуля — пусто
            cell_text = "" if abs(v) < 1e-9 else fmt_delta_short(v)

            tds.append(
                f"<td class='{cls}' style='{cell_style(v)} color: {txt_color};'>"
                f"{cell_text}"
                f"</td>"
            )

        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    return f"""

    <div class="card mb-3 diag-card diag-card-top">
      <div class="card-header diag-card-header">
        <strong>{title}</strong>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive diag-matrix-wrap">
          <table class="table table-sm mb-0 diag-table diag-matrix">
            <thead class="table-dark">
              <tr>{thead}</tr>
            </thead>
            <tbody>
              {''.join(body_rows)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """.strip()
    

def render_delta_qty_matrix_table(mat: pd.DataFrame, title: str, max_cols: int = 12) -> str:
    """
    Матрица Δшт (группы × категории).
    """
    if mat is None or mat.empty:
        return ""

    cols = list(mat.columns)[:max_cols]
    mat = mat[cols].copy()

    vmax = float(mat.abs().max().max()) if not mat.empty else 0.0
    vmax = vmax or 1.0

    def cell_style(v: float) -> str:
        a = min(1.0, abs(v) / vmax)
        alpha = 0.08 + a * 0.54  # можешь потом подкрутить

        if v < 0:
            return f"background: rgba(220, 38, 38, {alpha:.2f});"
        if v > 0:
            return f"background: rgba(22, 163, 74, {alpha:.2f});"
        return "background: transparent;"

    thead = (
        "<th class='diag-sticky-col'>Группа \\ Категория</th>"
        + "".join([f"<th class='text-end diag-colhead'>{c}</th>" for c in cols])
    )

    body_rows = []
    for idx, row in mat.iterrows():
        sg = str(idx)
        tds = [f"<td class='text-muted diag-sticky-col text-truncate' title='{sg}'>{sg}</td>"]

        for c in cols:
            v = float(row[c])

            cls_extra = []
            if abs(v) < 1e-9:
                cls_extra.append("is-zero")

            cls = "text-end diag-cell num " + " ".join(cls_extra)

            # ВАЖНО: всегда тёмный текст (у тебя CSS это и так добивает)
            cell_text = "" if abs(v) < 1e-9 else _fmt_qty_delta(v)

            tds.append(
                f"<td class='{cls}' style='{cell_style(v)}'>"
                f"{cell_text}"
                f"</td>"
            )

        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    return f"""
 
    <div class="card mb-3 diag-card diag-card-top">
      <div class="card-header diag-card-header">
        <strong>{title}</strong>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive diag-matrix-wrap">
          <table class="table table-sm mb-0 diag-table diag-matrix">
            <thead class="table-dark">
              <tr>{thead}</tr>
            </thead>
            <tbody>
              {''.join(body_rows)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """.strip()   
    
    
def render_delta_matrices_by_root_html(
    matrices: list[tuple[str, pd.DataFrame]],
    title_prefix: str,
    max_cols: int = 10,
) -> str:
    """
    Рендер нескольких матриц подряд (каждая по root).
    title_prefix: например "YTD: Матрица Δ₽"
    """
    if not matrices:
        return ""

    blocks = []
    for root, mat in matrices:
        if mat is None or mat.empty:
            continue

        blocks.append(
                render_delta_matrix_table(
                    mat,
                    title=f"{title_prefix}: <span class='matrix-root'>{root}</span>",
                    max_cols=max_cols
                )
            )

    return "\n".join([b for b in blocks if b])

def render_delta_qty_matrices_by_root_html(
    matrices: list[tuple[str, pd.DataFrame]],
    title_prefix: str,
    max_cols: int = 10,
) -> str:
    """
    Рендер нескольких матриц Δшт подряд (каждая по root).
    """
    if not matrices:
        return ""

    blocks = []
    for root, mat in matrices:
        if mat is None or mat.empty:
            continue

        blocks.append(
            render_delta_qty_matrix_table(
                mat,
                title=f"{title_prefix}: <span class='matrix-root'>{root}</span>",
                max_cols=max_cols
            )
        )

    return "\n".join([b for b in blocks if b])



def render_delta_matrices_by_root_pair_html(
    matrices_money: list[tuple[str, pd.DataFrame]],
    matrices_qty: list[tuple[str, pd.DataFrame]],
    title_prefix_money: str,
    title_prefix_qty: str,
    max_cols: int = 10,
) -> str:
    """
    Рендерит матрицы ПАРАМИ по root:
      Мебель: Δ₽
      Мебель: Δшт
      Свет: Δ₽
      Свет: Δшт
      ...
    """
    if not matrices_money:
        return ""

    qty_map = {str(root): mat for root, mat in (matrices_qty or [])}

    blocks = []
    for root, mat_money in matrices_money:
        if mat_money is None or mat_money.empty:
            continue

        root_s = str(root)

        # 1) Деньги
        blocks.append(
            render_delta_matrix_table(
                mat_money,
                title=f"{title_prefix_money}: <span class='matrix-root'>{root_s}</span>",
                max_cols=max_cols
            )
        )

        # 2) Штуки (если есть)
        mat_qty = qty_map.get(root_s)
        if mat_qty is not None and not mat_qty.empty:
            blocks.append(
                render_delta_qty_matrix_table(
                    mat_qty,
                    title=f"{title_prefix_qty}: <span class='matrix-root'>{root_s}</span>",
                    max_cols=max_cols
                )
            )

        # небольшой разрыв между корнями
        blocks.append("<div class='page-break'></div>")

    # убираем последний page-break
    out = "\n".join(blocks).rstrip()
    out = out.rsplit("<div class='page-break'></div>", 1)[0]
    return out