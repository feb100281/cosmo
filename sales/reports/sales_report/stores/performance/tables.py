from __future__ import annotations

import math
import html
import pandas as pd


def fmt_money(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.0f} ₽".replace(",", " ")
    except Exception:
        return "—"


def fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(round(float(v))):,}".replace(",", " ")
    except Exception:
        return "—"


def fmt_pct(v, digits: int = 1) -> str:
    if v is None:
        return "—"
    try:
        val = float(v)
        if not math.isfinite(val):
            return "—"
        return f"{val:+.{digits}f}%".replace(".", ",")
    except Exception:
        return "—"


def fmt_delta_money(v) -> str:
    if v is None:
        return "—"
    try:
        val = float(v)
        if not math.isfinite(val):
            return "—"
        return f"{val:+,.0f} ₽".replace(",", " ")
    except Exception:
        return "—"


def fmt_ratio(v, digits: int = 1) -> str:
    if v is None:
        return "—"
    try:
        val = float(v)
        if not math.isfinite(val):
            return "—"
        return f"{val * 100:.{digits}f}%".replace(".", ",")
    except Exception:
        return "—"


def _safe_float(v):
    try:
        if v is None:
            return None
        val = float(v)
        if not math.isfinite(val):
            return None
        return val
    except Exception:
        return None


def _calc_delta(curr, prev):
    curr_val = _safe_float(curr)
    prev_val = _safe_float(prev)

    if curr_val is None and prev_val is None:
        return None

    return (curr_val or 0.0) - (prev_val or 0.0)


def _delta_text_class(v) -> str:
    val = _safe_float(v)
    if val is None:
        return "delta-neutral"
    if val > 0:
        return "delta-pos"
    if val < 0:
        return "delta-neg"
    return "delta-neutral"


def _render_table_header(title: str, subtitle: str = "") -> str:
    return f"""
    <h3 class="section-subtitle">{html.escape(title)}</h3>
    """.strip()


def render_store_kpi_table(df: pd.DataFrame, title: str, curr_year: int, prev_year: int) -> str:
    if df is None or df.empty:
        return ""

    rows = []
    for _, r in df.iterrows():
        store = html.escape(str(r.get("store", "Без магазина")))

        amount_curr = r.get("amount_curr")
        amount_prev = r.get("amount_prev")
        delta_amount = _calc_delta(amount_curr, amount_prev)
        delta_pct = r.get("delta_amount_pct")

        rows.append(f"""
        <tr>
          <td>
            <div class="manager-name">
              <span class="manager-name__last">{store}</span>
            </div>
          </td>
          <td class="text-end">{fmt_money(amount_curr)}</td>
          <td class="text-end">{fmt_money(amount_prev)}</td>
          <td class="text-end">
            <span class="{_delta_text_class(delta_amount)}">{fmt_delta_money(delta_amount)}</span>
          </td>
          <td class="text-end">
            <span class="{_delta_text_class(delta_pct)}">{fmt_pct(delta_pct)}</span>
          </td>
          <td class="text-end">{fmt_ratio(r.get("rtr_ratio_curr"))}</td>
          <td class="text-end">{fmt_ratio(r.get("share_curr"))}</td>
        </tr>
        """)

    total_curr = fmt_money(df["amount_curr"].sum()) if "amount_curr" in df.columns else "—"
    total_prev = fmt_money(df["amount_prev"].sum()) if "amount_prev" in df.columns else "—"

    weighted_return = "—"
    if {"amount_curr", "rtr_ratio_curr"}.issubset(df.columns):
        try:
            amount_sum = float(df["amount_curr"].fillna(0).sum())
            if amount_sum > 0:
                weighted = (df["amount_curr"].fillna(0) * df["rtr_ratio_curr"].fillna(0)).sum() / amount_sum
                weighted_return = fmt_ratio(weighted)
        except Exception:
            weighted_return = "—"

    return f"""
    {_render_table_header(title, f"Выручка, возвраты и вклад магазинов в общую выручку • {curr_year} vs {prev_year}")}

    <table class="compare-table">
      <thead>
        <tr>
          <th>Магазин</th>
          <th class="text-end">Выручка {curr_year}</th>
          <th class="text-end">Выручка {prev_year}</th>
          <th class="text-end">Δ</th>
          <th class="text-end">Δ%</th>
          <th class="text-end">Возвраты {curr_year}</th>
          <th class="text-end">Доля в общей выручке</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
        <tr class="total-row">
          <td><span class="manager-name__last">Итого</span></td>
          <td class="text-end">{total_curr}</td>
          <td class="text-end">{total_prev}</td>
          <td class="text-end">—</td>
          <td class="text-end">—</td>
          <td class="text-end">{weighted_return}</td>
          <td class="text-end">100,0%</td>
        </tr>
      </tbody>
    </table>
    """.strip()


def render_lfl_table(df: pd.DataFrame, title: str) -> str:
    if df is None or df.empty:
        return ""

    rows = []
    for _, r in df.iterrows():
        store = html.escape(str(r.get("store", "Без магазина")))

        amount_curr = r.get("amount_curr")
        amount_prev = r.get("amount_prev")
        delta_amount = _calc_delta(amount_curr, amount_prev)
        delta_pct = r.get("delta_amount_pct")

        rows.append(f"""
        <tr>
          <td>
            <div class="manager-name">
              <span class="manager-name__last">{store}</span>
            </div>
          </td>
          <td class="text-end">{fmt_money(amount_curr)}</td>
          <td class="text-end">{fmt_money(amount_prev)}</td>
          <td class="text-end">
            <span class="{_delta_text_class(delta_amount)}">{fmt_delta_money(delta_amount)}</span>
          </td>
          <td class="text-end">
            <span class="{_delta_text_class(delta_pct)}">{fmt_pct(delta_pct)}</span>
          </td>
        </tr>
        """)

    total_curr = fmt_money(df["amount_curr"].sum()) if "amount_curr" in df.columns else "—"
    total_prev = fmt_money(df["amount_prev"].sum()) if "amount_prev" in df.columns else "—"

    return f"""
    {_render_table_header(title, "Сопоставимые магазины like-for-like")}

    <table class="compare-table">
      <thead>
        <tr>
          <th>Магазин</th>
          <th class="text-end">Выручка текущий год</th>
          <th class="text-end">Выручка прошлый год</th>
          <th class="text-end">Δ</th>
          <th class="text-end">Δ%</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
        <tr class="total-row">
          <td><span class="manager-name__last">Итого</span></td>
          <td class="text-end">{total_curr}</td>
          <td class="text-end">{total_prev}</td>
          <td class="text-end">—</td>
          <td class="text-end">—</td>
        </tr>
      </tbody>
    </table>
    """.strip()





def render_store_monthly_table(df: pd.DataFrame, title: str) -> str:
    if df is None or df.empty:
        return ""

    rows = []

    grouped = df.groupby("store", sort=False)

    for store, group in grouped:
        group = group.copy()
        store_html = html.escape(str(store))
        rowspan = len(group)

        for i, (_, r) in enumerate(group.iterrows()):
            month_name = html.escape(str(r.get("month_name", "")))

            curr_amount = r.get("curr_amount")
            prev_amount = r.get("prev_amount")
            delta_amount = _calc_delta(curr_amount, prev_amount)
            delta_pct = r.get("delta_amount_pct")

            if i == 0:
                store_cell = f"""
                <td class="store-cell-group" rowspan="{rowspan}">
                  <div class="manager-name">
                    <span class="manager-name__last">{store_html}</span>
                  </div>
                </td>
                """
            else:
                store_cell = ""

            row_class = "monthly-row monthly-row--group-start" if i == 0 else "monthly-row"

            rows.append(f"""
            <tr class="{row_class}">
              {store_cell}
              <td>{month_name}</td>
              <td class="text-end">{fmt_money(curr_amount)}</td>
              <td class="text-end">{fmt_money(prev_amount)}</td>
              <td class="text-end">
                <span class="{_delta_text_class(delta_amount)}">{fmt_delta_money(delta_amount)}</span>
              </td>
              <td class="text-end">
                <span class="{_delta_text_class(delta_pct)}">{fmt_pct(delta_pct)}</span>
              </td>
            </tr>
            """)

        rows.append("""
        <tr class="group-separator-row">
          <td colspan="6"></td>
        </tr>
        """)

    if rows:
        rows.pop()

    total_curr_raw = df["curr_amount"].sum() if "curr_amount" in df.columns else None
    total_prev_raw = df["prev_amount"].sum() if "prev_amount" in df.columns else None
    total_delta_raw = _calc_delta(total_curr_raw, total_prev_raw)

    total_curr = fmt_money(total_curr_raw) if total_curr_raw is not None else "—"
    total_prev = fmt_money(total_prev_raw) if total_prev_raw is not None else "—"
    total_delta = fmt_delta_money(total_delta_raw) if total_delta_raw is not None else "—"

    return f"""
    {_render_table_header(title, "Помесячная динамика выручки по магазинам")}

    <table class="compare-table compare-table--monthly">
      <thead>
        <tr>
          <th>Магазин</th>
          <th>Месяц</th>
          <th class="text-end">Текущий год</th>
          <th class="text-end">Прошлый год</th>
          <th class="text-end">Δ</th>
          <th class="text-end">Δ%</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
        <tr class="total-row">
          <td><span class="manager-name__last">Итого</span></td>
          <td>—</td>
          <td class="text-end">{total_curr}</td>
          <td class="text-end">{total_prev}</td>
          <td class="text-end">
            <span class="{_delta_text_class(total_delta_raw)}">{total_delta}</span>
          </td>
          <td class="text-end">—</td>
        </tr>
      </tbody>
    </table>
    """.strip()
    

def render_store_pareto_svg(df: pd.DataFrame, title: str) -> str:
    if df is None or df.empty:
        return ""

    data = df.head(12).copy()
    if data.empty:
        return ""

    width = 980
    height = 380
    ml = 60
    mr = 30
    mt = 35
    mb = 90

    chart_w = width - ml - mr
    chart_h = height - mt - mb

    max_amount = max(float(data["amount_curr"].max()), 1.0)
    bar_gap = 12
    n = len(data)
    bar_w = max(20, (chart_w - (n - 1) * bar_gap) / n)

    def y_amount(v):
        return mt + chart_h - (float(v) / max_amount) * chart_h

    def y_pct(v):
        return mt + chart_h - (float(v) * chart_h)

    svg_parts = []

    for i, (_, r) in enumerate(data.iterrows()):
        x = ml + i * (bar_w + bar_gap)
        amount = float(r["amount_curr"])
        y = y_amount(amount)
        h = mt + chart_h - y

        store = html.escape(str(r["store"]))
        label = store[:14] + "…" if len(store) > 14 else store

        svg_parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="10" fill="rgba(233,30,99,0.85)"></rect>'
        )
        svg_parts.append(
            f'<text x="{x + bar_w/2:.1f}" y="{mt + chart_h + 18}" text-anchor="middle" fill="#cfd3dc" font-size="11">{label}</text>'
        )

    points = []
    for i, (_, r) in enumerate(data.iterrows()):
        x = ml + i * (bar_w + bar_gap) + bar_w / 2
        y = y_pct(float(r["cum_share_curr"] or 0))
        points.append(f"{x:.1f},{y:.1f}")

    svg_parts.append(
        f'<polyline fill="none" stroke="#7ee787" stroke-width="3" points="{" ".join(points)}"></polyline>'
    )

    for i, (_, r) in enumerate(data.iterrows()):
        x = ml + i * (bar_w + bar_gap) + bar_w / 2
        y = y_pct(float(r["cum_share_curr"] or 0))
        svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#7ee787"></circle>')

    for frac, label in [(0, "0%"), (0.5, "50%"), (0.8, "80%"), (1.0, "100%")]:
        y = y_pct(frac)
        svg_parts.append(
            f'<line x1="{ml}" y1="{y:.1f}" x2="{width - mr}" y2="{y:.1f}" stroke="rgba(255,255,255,0.08)"></line>'
        )
        svg_parts.append(
            f'<text x="{width - mr + 5}" y="{y + 4:.1f}" fill="#9aa4b2" font-size="11">{label}</text>'
        )

    return f"""
    {_render_table_header(title, "Топ магазинов по выручке и накопленная доля")}

    <div class="managers-chart-card">
      <svg viewBox="0 0 {width} {height}" width="100%" height="auto" role="img" aria-label="{html.escape(title)}">
        {''.join(svg_parts)}
      </svg>
    </div>
    """.strip()