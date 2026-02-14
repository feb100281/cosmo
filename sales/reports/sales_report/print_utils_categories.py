# sales/reports/sales_report/print_utils_categories.py

def build_categories_table(rows, title: str, mode: str = "cat"):
    if not rows:
        return {"html": ""}

    def _cls_from_text(s: str) -> str:
        # ожидаем "+..." или "−..." или "-..."
        if not s or s == "—":
            return ""
        s = str(s).replace("\u00A0", "").strip()  # NBSP убрать совсем
        if not s:
            return ""
        if s[0] == "+":
            return "positive"
        if s[0] in ("-", "−"):
            return "negative"
        return ""

    html = []
    html.append(f"""
      <div class="kpi-compare-section" style="margin-top: 14px;">
        <h3 class="compare-title">{title}</h3>

        <table class="compare-table">
          <thead>
            <tr>
    """)

    if mode == "sub":
        html.append("""
              <th>Категория</th>
              <th>Подкатегория</th>
              <th>Выручка</th>
              <th>Кол-во</th>
              <th>Δ</th>
              <th>Δ%</th>
        """)
    else:
        html.append("""
              <th>Категория</th>
              <th>Выручка</th>
              <th>Кол-во</th>
              <th>Δ</th>
              <th>Δ%</th>
        """)

    html.append("""
            </tr>
          </thead>
          <tbody>
    """)

    for r in rows:
        amount = r.get("amount", "—")
        quant = r.get("quant", "—")

        d_abs = r.get("delta", {}).get("abs", "—")
        d_pct = r.get("delta", {}).get("pct", "—")

        cls = _cls_from_text(d_pct) or _cls_from_text(d_abs)

        if mode == "sub":
            html.append(f"""
              <tr>
                <td>{r.get("cat_name","")}</td>
                <td>{r.get("sc_name","")}</td>
                <td>{amount}</td>
                <td>{quant}</td>
                <td>{d_abs}</td>
                <td class="{cls}">{d_pct}</td>
              </tr>
            """)
        else:
            html.append(f"""
              <tr>
                <td>{r.get("cat_name","")}</td>
                <td>{amount}</td>
                <td>{quant}</td>
                <td>{d_abs}</td>
                <td class="{cls}">{d_pct}</td>
              </tr>
            """)

    html.append("""
          </tbody>
        </table>
      </div>
    """)

    return {"html": "".join(html)}


