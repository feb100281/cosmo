from collections import defaultdict

from ..styles.theme import FORMATS, ALIGNMENTS, FILLS, FONTS
from ..styles.style_helpers import (
    draw_toc_button,
    draw_sheet_header,
    draw_table_header_with_gaps,
    hide_grid_and_freeze,
    set_column_widths,
    set_row_heights,
    style_data_row,
    style_total_row,
    clear_column,
)


def build_assortment_width_sheet(wb, years, rows):
    ws = wb.create_sheet("Ширина ассортимента")
    ws.sheet_properties.outlinePr.summaryBelow = False

    draw_toc_button(ws, cell="A1", target_sheet="TOC")

    # -------------------------------------------------
    # cutoff / логика YTD
    # -------------------------------------------------
    if rows:
        cutoff_year = int(rows[0].get("cutoff_year") or 0)
        cutoff_month = int(rows[0].get("cutoff_month") or 0)
        cutoff_day = int(rows[0].get("cutoff_day") or 0)
    else:
        cutoff_year = 0
        cutoff_month = 0
        cutoff_day = 0

    last_year = years[-1] if years else None
    compare_prev_year = years[-2] if len(years) >= 2 else None
    compare_last_year = years[-1] if years else None

    is_last_year_incomplete = bool(
        last_year
        and cutoff_year == last_year
        and (cutoff_month < 12 or cutoff_day < 31)
    )

    if is_last_year_incomplete and compare_prev_year is not None:
        note = (
            f"Лист показывает активную ширину ассортимента по производителям: "
            f"учитываются только SKU с ненулевым количеством продаж. "
            f"Так как {last_year} год еще не закрыт, сравнение выполнено как "
            f"{compare_prev_year} YTD vs {compare_last_year} YTD на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}. "
            f"Дополнительно показаны выручка, штуки и эффективность на 1 SKU."
        )
    else:
        note = (
            "Лист показывает активную ширину ассортимента по производителям: "
            "учитываются только SKU с ненулевым количеством продаж. "
            "Дополнительно показаны выручка, штуки и эффективность на 1 SKU."
        )

    draw_sheet_header(
        ws,
        title="Ширина ассортимента",
        subtitle="Активные SKU и эффективность по производителям",
        note=note,
        line_to_col=11,
    )

    # -------------------------------------------------
    # layout
    # -------------------------------------------------
    prev_label = (
        f"{compare_prev_year}\nSKU YTD"
        if (is_last_year_incomplete and compare_prev_year is not None)
        else f"{compare_prev_year}\nSKU"
    ) if compare_prev_year is not None else "Пред.\nSKU"

    last_label = (
        f"{compare_last_year}\nSKU YTD"
        if (is_last_year_incomplete and compare_last_year is not None)
        else f"{compare_last_year}\nSKU"
    ) if compare_last_year is not None else "Тек.\nSKU"

    revenue_label = (
        f"{compare_last_year}\nВыручка YTD"
        if is_last_year_incomplete and compare_last_year is not None
        else f"{compare_last_year}\nВыручка"
    ) if compare_last_year is not None else "Выручка"

    qty_label = (
        f"{compare_last_year}\nШт YTD"
        if is_last_year_incomplete and compare_last_year is not None
        else f"{compare_last_year}\nШт"
    ) if compare_last_year is not None else "Шт"

    layout = [
        ("name", "Производитель"),
        ("sku_prev", prev_label),
        ("sku_last", last_label),
        ("sku_delta", "Δ SKU"),
        ("sku_delta_pct", "Δ SKU %"),
        ("gap1", ""),
        ("revenue", revenue_label),
        ("qty", qty_label),
        ("revenue_per_sku", "Выручка\nна 1 SKU"),
        ("qty_per_sku", "Шт\nна 1 SKU"),
    ]

    headers = [label for _, label in layout]
    gap_cols = set()
    col_map = {}

    for idx, (key, _) in enumerate(layout, start=1):
        col_map[key] = idx
        if key.startswith("gap"):
            gap_cols.add(idx)

    header_row = 8
    data_start_row = 9

    draw_table_header_with_gaps(
        ws,
        row=header_row,
        headers=headers,
        wrap=True,
        gap_cols=gap_cols,
    )

    # -------------------------------------------------
    # подготовка данных
    # -------------------------------------------------
    data = defaultdict(dict)

    for r in rows:
        manufacturer = r.get("manufacturer") or "—"
        year = int(r.get("year"))

        data[manufacturer][year] = {
            "full_sku_count": float(r.get("full_sku_count") or 0),
            "ytd_sku_count": float(r.get("ytd_sku_count") or 0),
            "full_qty": float(r.get("full_qty") or 0),
            "ytd_qty": float(r.get("ytd_qty") or 0),
            "full_amount": float(r.get("full_amount") or 0),
            "ytd_amount": float(r.get("ytd_amount") or 0),
        }

    def get_period_metrics(manufacturer_name, year):
        payload = data[manufacturer_name].get(year, {})
        if is_last_year_incomplete and year in {compare_prev_year, compare_last_year}:
            return {
                "sku_count": float(payload.get("ytd_sku_count", 0) or 0),
                "qty": float(payload.get("ytd_qty", 0) or 0),
                "amount": float(payload.get("ytd_amount", 0) or 0),
            }
        return {
            "sku_count": float(payload.get("full_sku_count", 0) or 0),
            "qty": float(payload.get("full_qty", 0) or 0),
            "amount": float(payload.get("full_amount", 0) or 0),
        }

    sorted_names = sorted(
        data.keys(),
        key=lambda name: (
            get_period_metrics(name, compare_last_year)["amount"] if compare_last_year is not None else 0,
            get_period_metrics(name, compare_last_year)["sku_count"] if compare_last_year is not None else 0,
            name,
        ),
        reverse=True,
    )

    cur_row = data_start_row

    total_sku_prev = 0
    total_sku_last = 0
    total_revenue = 0
    total_qty = 0

    # -------------------------------------------------
    # строки
    # -------------------------------------------------
    for name in sorted_names:
        prev_metrics = get_period_metrics(name, compare_prev_year) if compare_prev_year is not None else {"sku_count": 0, "qty": 0, "amount": 0}
        last_metrics = get_period_metrics(name, compare_last_year) if compare_last_year is not None else {"sku_count": 0, "qty": 0, "amount": 0}

        sku_prev = prev_metrics["sku_count"]
        sku_last = last_metrics["sku_count"]
        sku_delta = sku_last - sku_prev
        sku_delta_pct = 0 if sku_prev == 0 else sku_delta / sku_prev

        revenue = last_metrics["amount"]
        qty = last_metrics["qty"]
        revenue_per_sku = 0 if sku_last == 0 else revenue / sku_last
        qty_per_sku = 0 if sku_last == 0 else qty / sku_last

        total_sku_prev += sku_prev
        total_sku_last += sku_last
        total_revenue += revenue
        total_qty += qty

        row_values = []
        number_formats = {}

        for key, _label in layout:
            if key == "name":
                row_values.append(name)

            elif key == "sku_prev":
                row_values.append(None if sku_prev == 0 else sku_prev)
                number_formats[len(row_values)] = '#,##0'

            elif key == "sku_last":
                row_values.append(None if sku_last == 0 else sku_last)
                number_formats[len(row_values)] = '#,##0'

            elif key == "sku_delta":
                row_values.append(None if sku_prev == 0 and sku_last == 0 else sku_delta)
                number_formats[len(row_values)] = '#,##0;[Red]-#,##0'

            elif key == "sku_delta_pct":
                row_values.append(None if sku_prev == 0 and sku_last == 0 else sku_delta_pct)
                number_formats[len(row_values)] = FORMATS["pct"]

            elif key == "gap1":
                row_values.append(None)

            elif key == "revenue":
                row_values.append(None if revenue == 0 else revenue)
                number_formats[len(row_values)] = FORMATS["money"]

            elif key == "qty":
                row_values.append(None if qty == 0 else qty)
                number_formats[len(row_values)] = '#,##0'

            elif key == "revenue_per_sku":
                row_values.append(None if revenue_per_sku == 0 else revenue_per_sku)
                number_formats[len(row_values)] = FORMATS["money"]

            elif key == "qty_per_sku":
                row_values.append(None if qty_per_sku == 0 else qty_per_sku)
                number_formats[len(row_values)] = '#,##0.0'

        style_data_row(
            ws,
            row=cur_row,
            values=row_values,
            number_formats=number_formats,
        )

        for key in ("sku_prev", "sku_last", "sku_delta", "sku_delta_pct", "qty", "qty_per_sku"):
            if key in col_map:
                ws.cell(row=cur_row, column=col_map[key]).alignment = ALIGNMENTS["center"]

        if "sku_delta" in col_map:
            cell = ws.cell(row=cur_row, column=col_map["sku_delta"])
            if isinstance(cell.value, (int, float)) and cell.value < 0:
                cell.fill = FILLS["section"]
                cell.font = FONTS["bold"]

        if "sku_delta_pct" in col_map:
            cell = ws.cell(row=cur_row, column=col_map["sku_delta_pct"])
            if isinstance(cell.value, (int, float)) and cell.value < 0:
                cell.fill = FILLS["section"]
                cell.font = FONTS["bold"]

        cur_row += 1

    # -------------------------------------------------
    # итого
    # -------------------------------------------------
    total_delta = total_sku_last - total_sku_prev
    total_delta_pct = 0 if total_sku_prev == 0 else total_delta / total_sku_prev
    total_revenue_per_sku = 0 if total_sku_last == 0 else total_revenue / total_sku_last
    total_qty_per_sku = 0 if total_sku_last == 0 else total_qty / total_sku_last

    total_values = []
    total_number_formats = {}

    for key, _label in layout:
        if key == "name":
            total_values.append("ИТОГО")

        elif key == "sku_prev":
            total_values.append(total_sku_prev)
            total_number_formats[len(total_values)] = '#,##0'

        elif key == "sku_last":
            total_values.append(total_sku_last)
            total_number_formats[len(total_values)] = '#,##0'

        elif key == "sku_delta":
            total_values.append(total_delta)
            total_number_formats[len(total_values)] = '#,##0;[Red]-#,##0'

        elif key == "sku_delta_pct":
            total_values.append(total_delta_pct)
            total_number_formats[len(total_values)] = FORMATS["pct"]

        elif key == "gap1":
            total_values.append(None)

        elif key == "revenue":
            total_values.append(total_revenue)
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key == "qty":
            total_values.append(total_qty)
            total_number_formats[len(total_values)] = '#,##0'

        elif key == "revenue_per_sku":
            total_values.append(total_revenue_per_sku)
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key == "qty_per_sku":
            total_values.append(total_qty_per_sku)
            total_number_formats[len(total_values)] = '#,##0.0'

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=total_number_formats,
    )

    total_row = cur_row

    if "sku_delta" in col_map:
        cell = ws.cell(row=total_row, column=col_map["sku_delta"])
        cell.alignment = ALIGNMENTS["center"]
        if isinstance(cell.value, (int, float)) and cell.value < 0:
            cell.fill = FILLS["section"]
            cell.font = FONTS["bold"]

    if "sku_delta_pct" in col_map:
        cell = ws.cell(row=total_row, column=col_map["sku_delta_pct"])
        cell.alignment = ALIGNMENTS["center"]
        if isinstance(cell.value, (int, float)) and cell.value < 0:
            cell.fill = FILLS["section"]
            cell.font = FONTS["bold"]

    for key in ("sku_prev", "sku_last", "qty", "qty_per_sku"):
        if key in col_map:
            ws.cell(row=total_row, column=col_map[key]).alignment = ALIGNMENTS["center"]

    # -------------------------------------------------
    # gap cols
    # -------------------------------------------------
    for gap_col in gap_cols:
        clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

    # -------------------------------------------------
    # widths
    # -------------------------------------------------
    widths = {
        "A": 34,
    }

    for key, col_idx in col_map.items():
        col_letter = ws.cell(1, col_idx).column_letter

        if key in {"sku_prev", "sku_last"}:
            widths[col_letter] = 11
        elif key == "sku_delta":
            widths[col_letter] = 10
        elif key == "sku_delta_pct":
            widths[col_letter] = 10
        elif key.startswith("gap"):
            widths[col_letter] = 2.0
        elif key == "revenue":
            widths[col_letter] = 16
        elif key == "qty":
            widths[col_letter] = 11
        elif key == "revenue_per_sku":
            widths[col_letter] = 15
        elif key == "qty_per_sku":
            widths[col_letter] = 11

    set_column_widths(ws, widths)

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 36,
            8: 30,
        },
    )

    hide_grid_and_freeze(ws, "B9")