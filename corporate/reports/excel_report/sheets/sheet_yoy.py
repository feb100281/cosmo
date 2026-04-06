# corporate/reports/excel_report/sheets/sheet_yoy.py

from collections import defaultdict

from ..styles.theme import FILLS, FONTS, ALIGNMENTS, FORMATS, BORDERS
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


def build_yoy_sheet(wb, years, manufacturer_rows, category_rows):
    ws = wb.create_sheet("YOY analysis")
    ws.sheet_properties.outlinePr.summaryBelow = False

    # -------------------------------------------------
    # Дата среза отчета
    # -------------------------------------------------
    if manufacturer_rows:
        cutoff_year = int(manufacturer_rows[0].get("cutoff_year") or 0)
        cutoff_month = int(manufacturer_rows[0].get("cutoff_month") or 0)
        cutoff_day = int(manufacturer_rows[0].get("cutoff_day") or 0)
    else:
        cutoff_year = 0
        cutoff_month = 0
        cutoff_day = 0

    last_year = years[-1] if years else None
    is_last_year_incomplete = bool(
        last_year
        and cutoff_year == last_year
        and (cutoff_month < 12 or cutoff_day < 31)
    )

    if is_last_year_incomplete:
        note = (
            f"Для закрытых лет показан YOY. Для {last_year} год еще не закрыт, "
            f"поэтому последний блок рассчитан как YTD на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}: "
            f"сравнение {last_year} с {last_year - 1} за сопоставимый период."
        )
    else:
        note = "Для каждого производителя показана выручка по годам, YOY-изменение и итог за период."

    # -------------------------------------------------
    # Layout колонок
    # -------------------------------------------------
    layout = [("name", "Производитель")]

    for i, y in enumerate(years):
        year_header = f"{y}\nYTD" if (is_last_year_incomplete and y == last_year) else str(y)
        layout.append((f"year_{y}", year_header))

        if i > 0:
            prev_y = years[i - 1]
            if is_last_year_incomplete and y == last_year:
                yoy_header = f"YTD\n{prev_y}→{y}"
            else:
                yoy_header = f"YOY\n{prev_y}→{y}"
            layout.append((f"delta_{prev_y}_{y}", yoy_header))

        # разделитель после каждого блока, включая последний
        layout.append((f"gap_after_{y}", ""))

    layout.append(("total", "Итого"))

    headers = [label for _, label in layout]

    gap_cols = set()
    col_map = {}
    for idx, (key, _) in enumerate(layout, start=1):
        col_map[key] = idx
        if key.startswith("gap_after_"):
            gap_cols.add(idx)

    last_used_col = len(layout)

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="YOY analysis",
        subtitle="Год-к-году анализ выручки производителей",
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
    # Данные по производителям
    # -------------------------------------------------
    data = defaultdict(dict)
    for r in manufacturer_rows:
        manufacturer = r.get("manufacturer") or "—"
        year = int(r.get("year"))
        full_amount = float(r.get("full_amount") or 0)
        ytd_amount = float(r.get("ytd_amount") or 0)

        data[manufacturer][year] = {
            "full_amount": full_amount,
            "ytd_amount": ytd_amount,
        }

    # -------------------------------------------------
    # Данные по категориям внутри производителя
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

    names = sorted(
        data.keys(),
        key=lambda n: sum(float(data[n].get(y, {}).get("full_amount", 0) or 0) for y in years),
        reverse=True,
    )

    totals_full_by_year = {y: 0 for y in years}
    totals_ytd_by_year = {y: 0 for y in years}
    grand_total = 0

    # -------------------------------------------------
    # Вспомогательная функция для строк категорий
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
    # Строки данных
    # -------------------------------------------------
    cur_row = data_start_row
    for name in names:
        row_values = []
        number_formats = {}
        display_values_by_year = {}

        for y in years:
            full_amount = float(data[name].get(y, {}).get("full_amount", 0) or 0)
            ytd_amount = float(data[name].get(y, {}).get("ytd_amount", 0) or 0)

            display_val = ytd_amount if (is_last_year_incomplete and y == last_year) else full_amount
            display_values_by_year[y] = display_val

            totals_full_by_year[y] += full_amount
            totals_ytd_by_year[y] += ytd_amount

        row_total = sum(display_values_by_year[y] for y in years)
        grand_total += row_total

        for key, _label in layout:
            if key == "name":
                row_values.append(name)

            elif key.startswith("year_"):
                y = int(key.replace("year_", ""))
                row_values.append(display_values_by_year[y])
                number_formats[len(row_values)] = FORMATS["money"]

            elif key.startswith("delta_"):
                _, prev_y, curr_y = key.split("_")
                prev_y = int(prev_y)
                curr_y = int(curr_y)

                if is_last_year_incomplete and curr_y == last_year:
                    prev_val = float(data[name].get(prev_y, {}).get("ytd_amount", 0) or 0)
                    curr_val = float(data[name].get(curr_y, {}).get("ytd_amount", 0) or 0)
                else:
                    prev_val = float(data[name].get(prev_y, {}).get("full_amount", 0) or 0)
                    curr_val = float(data[name].get(curr_y, {}).get("full_amount", 0) or 0)

                yoy = 0 if prev_val == 0 else (curr_val - prev_val) / prev_val
                row_values.append(yoy)
                number_formats[len(row_values)] = FORMATS["pct"]

            elif key.startswith("gap_after_"):
                row_values.append(None)

            elif key == "total":
                row_values.append(row_total)
                number_formats[len(row_values)] = FORMATS["money"]

        style_data_row(
            ws,
            row=cur_row,
            values=row_values,
            number_formats=number_formats,
        )

        # форматируем YOY колонки производителя
        for key, col_idx in col_map.items():
            if key.startswith("delta_"):
                cell = ws.cell(row=cur_row, column=col_idx)
                cell.alignment = ALIGNMENTS["center"]
                if isinstance(cell.value, (int, float)) and cell.value < 0:
                    cell.fill = FILLS["section"]
                    cell.font = FONTS["bold"]

        manufacturer_row_idx = cur_row
        cur_row += 1

        # -------------------------------------------------
        # Вложенные строки категорий под производителем
        # -------------------------------------------------
        mf_categories = category_data.get(name, {})

        category_names = sorted(
            mf_categories.keys(),
            key=lambda c: sum(
                float(mf_categories[c].get(y, {}).get("full_amount", 0) or 0)
                for y in years
            ),
            reverse=True,
        )

        for category_name in category_names:
            cat_row_values = []
            cat_number_formats = {}
            cat_display_values_by_year = {}

            for y in years:
                full_amount = float(mf_categories[category_name].get(y, {}).get("full_amount", 0) or 0)
                ytd_amount = float(mf_categories[category_name].get(y, {}).get("ytd_amount", 0) or 0)

                display_val = ytd_amount if (is_last_year_incomplete and y == last_year) else full_amount
                cat_display_values_by_year[y] = display_val

            cat_row_total = sum(cat_display_values_by_year[y] for y in years)

            for key, _label in layout:
                if key == "name":
                    cat_row_values.append(f"    ↳ {category_name}")

                elif key.startswith("year_"):
                    y = int(key.replace("year_", ""))
                    cat_row_values.append(cat_display_values_by_year[y])
                    cat_number_formats[len(cat_row_values)] = FORMATS["money"]

                elif key.startswith("delta_"):
                    _, prev_y, curr_y = key.split("_")
                    prev_y = int(prev_y)
                    curr_y = int(curr_y)

                    if is_last_year_incomplete and curr_y == last_year:
                        prev_val = float(mf_categories[category_name].get(prev_y, {}).get("ytd_amount", 0) or 0)
                        curr_val = float(mf_categories[category_name].get(curr_y, {}).get("ytd_amount", 0) or 0)
                    else:
                        prev_val = float(mf_categories[category_name].get(prev_y, {}).get("full_amount", 0) or 0)
                        curr_val = float(mf_categories[category_name].get(curr_y, {}).get("full_amount", 0) or 0)

                    yoy = 0 if prev_val == 0 else (curr_val - prev_val) / prev_val
                    cat_row_values.append(yoy)
                    cat_number_formats[len(cat_row_values)] = FORMATS["pct"]

                elif key.startswith("gap_after_"):
                    cat_row_values.append(None)

                elif key == "total":
                    cat_row_values.append(cat_row_total)
                    cat_number_formats[len(cat_row_values)] = FORMATS["money"]

            style_category_row(
                ws,
                row=cur_row,
                values=cat_row_values,
                number_formats=cat_number_formats,
            )

            # gap-колонки у строк категорий тоже очищаем
            for gap_col in gap_cols:
                clear_column(ws, col_idx=gap_col, row_start=cur_row, row_end=cur_row)

            # форматируем YOY колонки категорий
            for key, col_idx in col_map.items():
                if key.startswith("delta_"):
                    cell = ws.cell(row=cur_row, column=col_idx)
                    cell.alignment = ALIGNMENTS["center"]
                    if isinstance(cell.value, (int, float)) and cell.value < 0:
                        cell.font = FONTS["bold"]

            # группировка / скрытие
            ws.row_dimensions[cur_row].outlineLevel = 1
            ws.row_dimensions[cur_row].hidden = True

            cur_row += 1

        if category_names:
            ws.row_dimensions[manufacturer_row_idx].collapsed = True

    # -------------------------------------------------
    # ИТОГО
    # -------------------------------------------------
    total_values = []
    total_number_formats = {}

    for key, _label in layout:
        if key == "name":
            total_values.append("ИТОГО")

        elif key.startswith("year_"):
            y = int(key.replace("year_", ""))
            year_total = totals_ytd_by_year[y] if (is_last_year_incomplete and y == last_year) else totals_full_by_year[y]
            total_values.append(year_total)
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key.startswith("delta_"):
            _, prev_y, curr_y = key.split("_")
            prev_y = int(prev_y)
            curr_y = int(curr_y)

            if is_last_year_incomplete and curr_y == last_year:
                prev_total = totals_ytd_by_year[prev_y]
                curr_total = totals_ytd_by_year[curr_y]
            else:
                prev_total = totals_full_by_year[prev_y]
                curr_total = totals_full_by_year[curr_y]

            yoy_total = 0 if prev_total == 0 else (curr_total - prev_total) / prev_total
            total_values.append(yoy_total)
            total_number_formats[len(total_values)] = FORMATS["pct"]

        elif key.startswith("gap_after_"):
            total_values.append(None)

        elif key == "total":
            total_values.append(grand_total)
            total_number_formats[len(total_values)] = FORMATS["money"]

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
            widths[col_letter] = 14
        elif key.startswith("delta_"):
            widths[col_letter] = 13
        elif key.startswith("gap_after_"):
            widths[col_letter] = 3.5
        elif key == "total":
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