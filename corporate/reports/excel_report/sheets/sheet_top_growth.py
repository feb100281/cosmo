# corporate/reports/excel_report/sheets/sheet_top_growth.py

from collections import defaultdict

from ..styles.theme import FILLS, FONTS, FORMATS, ALIGNMENTS, BORDERS
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


def build_top_growth_sheet(wb, top_growth_data, top_growth_categories_data=None):
    ws = wb.create_sheet("Top growth manufacturers")
    ws.sheet_properties.outlinePr.summaryBelow = False

    years_for_display = top_growth_data.get("years_for_display", [])
    rows = top_growth_data.get("rows", [])

    top_growth_categories_data = top_growth_categories_data or {}
    category_rows = top_growth_categories_data.get("rows", [])

    is_ytd_comparison = top_growth_data.get("is_ytd_comparison", False)
    cutoff_year = top_growth_data.get("cutoff_year")
    cutoff_month = top_growth_data.get("cutoff_month")
    cutoff_day = top_growth_data.get("cutoff_day")
    compare_prev_year = top_growth_data.get("compare_prev_year")
    compare_last_year = top_growth_data.get("compare_last_year")

    # -------------------------------------------------
    # Категории: manufacturer -> category -> year -> amounts
    # -------------------------------------------------
    category_data = defaultdict(lambda: defaultdict(dict))
    for r in category_rows:
        manufacturer = r.get("manufacturer") or "—"
        category = r.get("category") or "—"
        year = int(r.get("year"))
        full_amount = float(r.get("full_amount") or 0)
        ytd_amount = float(r.get("ytd_amount") or 0)

        category_data[manufacturer][category][year] = {
            "full_amount": full_amount,
            "ytd_amount": ytd_amount,
        }

    # -------------------------------------------------
    # Header
    # -------------------------------------------------
    draw_toc_button(ws, cell="A1", target_sheet="TOC")

    if is_ytd_comparison and cutoff_year and cutoff_month and cutoff_day:
        note = (
            f"Показаны производители с наибольшим ростом выручки. "
            f"Последний период рассчитан как YTD на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}, "
            f"сравнение выполнено с {compare_prev_year} за сопоставимый период."
        )
    else:
        note = "Показаны производители с наибольшим ростом выручки относительно предыдущего года."

    # -------------------------------------------------
    # Layout колонок
    # -------------------------------------------------
    layout = [("name", "Производитель")]

    for i, y in enumerate(years_for_display):
        if i == len(years_for_display) - 1 and is_ytd_comparison:
            year_header = f"{y}\nYTD"
        else:
            year_header = str(y)

        layout.append((f"year_{y}", year_header))

        if i < len(years_for_display) - 1:
            layout.append((f"gap_after_year_{y}", ""))

    if years_for_display:
        layout.append(("gap_before_change", ""))

    change_label = "Рост YTD" if is_ytd_comparison else "Рост"
    change_pct_label = "Рост YTD, %" if is_ytd_comparison else "Рост, %"

    layout.extend(
        [
            ("diff_amount", change_label),
            ("diff_pct", change_pct_label),
            ("growth_share", "Вклад в рост"),
        ]
    )

    headers = [label for _, label in layout]

    gap_cols = set()
    col_map = {}
    for idx, (key, _) in enumerate(layout, start=1):
        col_map[key] = idx
        if key.startswith("gap_"):
            gap_cols.add(idx)

    last_used_col = len(layout)

    draw_sheet_header(
        ws,
        title="Рост производителей",
        subtitle="Производители с наибольшим ростом выручки",
        note=note,
        line_to_col=last_used_col,
    )

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
    # Нет данных
    # -------------------------------------------------
    if len(years_for_display) < 2 or not rows:
        style_total_row(
            ws,
            row=data_start_row,
            values=["Недостаточно данных для сравнения"] + [""] * (len(headers) - 1),
        )

        for gap_col in gap_cols:
            clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=data_start_row)

        widths = {"A": 42}
        for key, col_idx in col_map.items():
            col_letter = ws.cell(1, col_idx).column_letter
            if key.startswith("year_"):
                widths[col_letter] = 16
            elif key.startswith("gap_"):
                widths[col_letter] = 3.5
            elif key == "diff_amount":
                widths[col_letter] = 16
            elif key == "diff_pct":
                widths[col_letter] = 14
            elif key == "growth_share":
                widths[col_letter] = 16

        set_column_widths(ws, widths)

        set_row_heights(
            ws,
            {
                2: 24,
                3: 18,
                4: 34,
                8: 30,
            },
        )

        hide_grid_and_freeze(ws, "B9")
        return

    # -------------------------------------------------
    # Helper для строк категорий
    # -------------------------------------------------
    def style_category_row(ws, row, values, start_col=1, number_formats=None):
        for i, value in enumerate(values, start=start_col):
            cell = ws.cell(row=row, column=i, value=value)

            cell.font = FONTS["normal"]
            cell.fill = FILLS["alt"]
            cell.border = BORDERS["thin"]

            if i == start_col:
                cell.alignment = ALIGNMENTS["left"]
            else:
                cell.alignment = ALIGNMENTS["right"]

            if number_formats and i in number_formats:
                cell.number_format = number_formats[i]

    # -------------------------------------------------
    # Data rows
    # -------------------------------------------------
    cur_row = data_start_row

    total_years = {y: 0 for y in years_for_display}
    total_diff = 0
    total_compare_prev = 0
    total_growth_share = 0

    for row in rows:
        row_values = []
        number_formats = {}

        for key, _label in layout:
            if key == "name":
                row_values.append(row["manufacturer"])

            elif key.startswith("year_"):
                y = int(key.replace("year_", ""))
                idx_in_source = years_for_display.index(y)
                val = row["year_values"][idx_in_source]
                row_values.append(val)
                number_formats[len(row_values)] = FORMATS["money"]
                total_years[y] += float(val or 0)

            elif key.startswith("gap_"):
                row_values.append(None)

            elif key == "diff_amount":
                row_values.append(row["diff_amount"])
                number_formats[len(row_values)] = FORMATS["money"]

            elif key == "diff_pct":
                row_values.append(row["diff_pct"])
                number_formats[len(row_values)] = FORMATS["pct"]

            elif key == "growth_share":
                row_values.append(row["growth_share"])
                number_formats[len(row_values)] = FORMATS["pct"]

        style_data_row(
            ws,
            row=cur_row,
            values=row_values,
            number_formats=number_formats,
        )

        for key in ("diff_amount", "diff_pct"):
            col_idx = col_map[key]
            ws.cell(row=cur_row, column=col_idx).font = FONTS["bold"]
            ws.cell(row=cur_row, column=col_idx).fill = FILLS["total"]
            ws.cell(row=cur_row, column=col_idx).alignment = ALIGNMENTS["center"]

        ws.cell(row=cur_row, column=col_map["growth_share"]).alignment = ALIGNMENTS["center"]

        total_diff += float(row["diff_amount"] or 0)
        total_compare_prev += float(row["prev_compare_amount"] or 0)
        total_growth_share += float(row["growth_share"] or 0)

        manufacturer_row_idx = cur_row
        cur_row += 1

        # -------------------------------------------------
        # Вложенные строки категорий
        # -------------------------------------------------
        manufacturer_name = row["manufacturer"]
        mf_categories = category_data.get(manufacturer_name, {})

        def get_compare_value(cat_name, year):
            if is_ytd_comparison:
                return float(mf_categories[cat_name].get(year, {}).get("ytd_amount", 0) or 0)
            return float(mf_categories[cat_name].get(year, {}).get("full_amount", 0) or 0)

        def get_display_value(cat_name, year):
            if is_ytd_comparison and year == compare_last_year:
                return float(mf_categories[cat_name].get(year, {}).get("ytd_amount", 0) or 0)
            return float(mf_categories[cat_name].get(year, {}).get("full_amount", 0) or 0)

        category_names = sorted(
            mf_categories.keys(),
            key=lambda c: get_compare_value(c, compare_last_year) - get_compare_value(c, compare_prev_year),
            reverse=True,
        )

        visible_category_names = []

        for category_name in category_names:
            prev_cat_val = get_compare_value(category_name, compare_prev_year)
            last_cat_val = get_compare_value(category_name, compare_last_year)
            cat_diff = last_cat_val - prev_cat_val

            # показываем только категории с ростом
            if cat_diff <= 0:
                continue

            visible_category_names.append(category_name)

            cat_diff_pct = 0 if prev_cat_val == 0 else cat_diff / prev_cat_val
            cat_growth_share = 0 if row["diff_amount"] == 0 else cat_diff / row["diff_amount"]

            cat_row_values = []
            cat_number_formats = {}

            for key, _label in layout:
                if key == "name":
                    cat_row_values.append(f"    ↳ {category_name}")

                elif key.startswith("year_"):
                    y = int(key.replace("year_", ""))
                    val = get_display_value(category_name, y)
                    cat_row_values.append(val)
                    cat_number_formats[len(cat_row_values)] = FORMATS["money"]

                elif key.startswith("gap_"):
                    cat_row_values.append(None)

                elif key == "diff_amount":
                    cat_row_values.append(cat_diff)
                    cat_number_formats[len(cat_row_values)] = FORMATS["money"]

                elif key == "diff_pct":
                    cat_row_values.append(cat_diff_pct)
                    cat_number_formats[len(cat_row_values)] = FORMATS["pct"]

                elif key == "growth_share":
                    cat_row_values.append(cat_growth_share)
                    cat_number_formats[len(cat_row_values)] = FORMATS["pct"]

            style_category_row(
                ws,
                row=cur_row,
                values=cat_row_values,
                number_formats=cat_number_formats,
            )

            for gap_col in gap_cols:
                clear_column(ws, col_idx=gap_col, row_start=cur_row, row_end=cur_row)

            ws.cell(row=cur_row, column=col_map["diff_amount"]).font = FONTS["bold"]
            ws.cell(row=cur_row, column=col_map["diff_pct"]).font = FONTS["bold"]
            ws.cell(row=cur_row, column=col_map["diff_amount"]).alignment = ALIGNMENTS["center"]
            ws.cell(row=cur_row, column=col_map["diff_pct"]).alignment = ALIGNMENTS["center"]
            ws.cell(row=cur_row, column=col_map["growth_share"]).alignment = ALIGNMENTS["center"]

            ws.row_dimensions[cur_row].outlineLevel = 1
            ws.row_dimensions[cur_row].hidden = True

            cur_row += 1

        if visible_category_names:
            ws.row_dimensions[manufacturer_row_idx].collapsed = True

    # -------------------------------------------------
    # TOTAL
    # -------------------------------------------------
    total_diff_pct = 0 if total_compare_prev == 0 else total_diff / total_compare_prev

    total_values = []
    total_number_formats = {}

    for key, _label in layout:
        if key == "name":
            total_values.append("ИТОГО")

        elif key.startswith("year_"):
            y = int(key.replace("year_", ""))
            total_values.append(total_years[y])
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key.startswith("gap_"):
            total_values.append(None)

        elif key == "diff_amount":
            total_values.append(total_diff)
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key == "diff_pct":
            total_values.append(total_diff_pct)
            total_number_formats[len(total_values)] = FORMATS["pct"]

        elif key == "growth_share":
            total_values.append(total_growth_share)
            total_number_formats[len(total_values)] = FORMATS["pct"]

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=total_number_formats,
    )

    total_row = cur_row

    # -------------------------------------------------
    # Очищаем gap-колонки
    # -------------------------------------------------
    for gap_col in gap_cols:
        clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

    # -------------------------------------------------
    # Widths
    # -------------------------------------------------
    widths = {"A": 42}

    for key, col_idx in col_map.items():
        col_letter = ws.cell(1, col_idx).column_letter

        if key.startswith("year_"):
            widths[col_letter] = 16
        elif key.startswith("gap_"):
            widths[col_letter] = 3.5
        elif key == "diff_amount":
            widths[col_letter] = 16
        elif key == "diff_pct":
            widths[col_letter] = 14
        elif key == "growth_share":
            widths[col_letter] = 16

    set_column_widths(ws, widths)

    # -------------------------------------------------
    # Heights
    # -------------------------------------------------
    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 34,
            8: 30,
        },
    )

    hide_grid_and_freeze(ws, "B9")