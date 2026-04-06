# # corporate/reports/excel_report/sheets/sheet_share.py


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


def build_share_sheet(wb, years, share_rows):
    ws = wb.create_sheet("Manufacturer share")
    ws.sheet_properties.outlinePr.summaryBelow = False

    # -------------------------------------------------
    # Header
    # -------------------------------------------------
    draw_toc_button(ws, cell="A1", target_sheet="TOC")

    note = (
        "Для каждого года показаны абсолютная выручка, доля производителя "
        "и изменение доли к предыдущему году. "
        "Строки отсортированы по доле в последнем году."
    )

    # -------------------------------------------------
    # Layout колонок
    # -------------------------------------------------
    layout = [("name", "Производитель")]

    for i, y in enumerate(years):
        layout.extend(
            [
                (f"revenue_{y}", f"{y}\nВыручка"),
                (f"share_{y}", f"{y}\nДоля"),
            ]
        )

        if i > 0:
            prev_y = years[i - 1]
            layout.append((f"delta_share_{prev_y}_{y}", f"Δ доли\n{prev_y}→{y}"))

        layout.append((f"gap_after_{y}", ""))

    headers = [label for _, label in layout]

    gap_cols = set()
    col_map = {}
    for idx, (key, _) in enumerate(layout, start=1):
        col_map[key] = idx
        if key.startswith("gap_after_"):
            gap_cols.add(idx)

    last_used_col = len(layout)

    draw_sheet_header(
        ws,
        title="Доли производителей",
        subtitle="Выручка, доля и изменение доли по годам",
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
    # Данные
    # -------------------------------------------------
    data = defaultdict(dict)
    for r in share_rows:
        manufacturer = r.get("manufacturer") or "—"
        year = int(r.get("year"))
        data[manufacturer][year] = {
            "net_amount": float(r.get("net_amount") or 0),
            "share": float(r.get("share") or 0),
        }

    last_year = years[-1] if years else None

    names = sorted(
        data.keys(),
        key=lambda n: (
            float((data[n].get(last_year) or {}).get("share", 0) or 0),
            float((data[n].get(last_year) or {}).get("net_amount", 0) or 0),
            n,
        ),
        reverse=True,
    )

    cur_row = data_start_row
    totals_by_year = {y: {"revenue": 0, "share": 0} for y in years}

    # -------------------------------------------------
    # Data rows
    # -------------------------------------------------
    for name in names:
        row_values = []
        number_formats = {}

        for key, _label in layout:
            if key == "name":
                row_values.append(name)

            elif key.startswith("revenue_"):
                y = int(key.replace("revenue_", ""))
                revenue = float((data[name].get(y) or {}).get("net_amount", 0) or 0)
                row_values.append(revenue)
                number_formats[len(row_values)] = FORMATS["money"]
                totals_by_year[y]["revenue"] += revenue

            elif key.startswith("share_"):
                y = int(key.replace("share_", ""))
                share = float((data[name].get(y) or {}).get("share", 0) or 0)
                row_values.append(share)
                number_formats[len(row_values)] = FORMATS["pct"]
                totals_by_year[y]["share"] += share

            elif key.startswith("delta_share_"):
                _, _, prev_y, curr_y = key.split("_")
                prev_y = int(prev_y)
                curr_y = int(curr_y)

                prev_share = float((data[name].get(prev_y) or {}).get("share", 0) or 0)
                curr_share = float((data[name].get(curr_y) or {}).get("share", 0) or 0)

                delta_share = curr_share - prev_share
                row_values.append(None if prev_share == 0 and curr_share == 0 else delta_share)
                number_formats[len(row_values)] = FORMATS["pct"]

            elif key.startswith("gap_after_"):
                row_values.append(None)

        style_data_row(
            ws,
            row=cur_row,
            values=row_values,
            number_formats=number_formats,
        )

        # центрируем доли и дельты
        for key, col_idx in col_map.items():
            if key.startswith("share_") or key.startswith("delta_share_"):
                ws.cell(row=cur_row, column=col_idx).alignment = ALIGNMENTS["center"]

        # подсветка дельты доли
        for key, col_idx in col_map.items():
            if key.startswith("delta_share_"):
                cell = ws.cell(row=cur_row, column=col_idx)
                if isinstance(cell.value, (int, float)):
                    if cell.value < 0:
                        cell.fill = FILLS["section"]
                        cell.font = FONTS["bold"]
                    elif cell.value > 0:
                        cell.font = FONTS["bold"]

        cur_row += 1

    # -------------------------------------------------
    # TOTAL
    # -------------------------------------------------
    total_values = []
    total_number_formats = {}

    for key, _label in layout:
        if key == "name":
            total_values.append("ИТОГО")

        elif key.startswith("revenue_"):
            y = int(key.replace("revenue_", ""))
            total_values.append(totals_by_year[y]["revenue"])
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key.startswith("share_"):
            y = int(key.replace("share_", ""))
            total_values.append(totals_by_year[y]["share"])
            total_number_formats[len(total_values)] = FORMATS["pct"]

        elif key.startswith("delta_share_"):
            _, _, prev_y, curr_y = key.split("_")
            prev_y = int(prev_y)
            curr_y = int(curr_y)

            total_delta_share = totals_by_year[curr_y]["share"] - totals_by_year[prev_y]["share"]
            total_values.append(total_delta_share)
            total_number_formats[len(total_values)] = FORMATS["pct"]

        elif key.startswith("gap_after_"):
            total_values.append(None)

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=total_number_formats,
    )

    total_row = cur_row

    # центрируем total для долей и дельт
    for key, col_idx in col_map.items():
        if key.startswith("share_") or key.startswith("delta_share_"):
            ws.cell(row=total_row, column=col_idx).alignment = ALIGNMENTS["center"]

    # -------------------------------------------------
    # Очищаем gap-колонки
    # -------------------------------------------------
    for gap_col in gap_cols:
        clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

    # -------------------------------------------------
    # Widths
    # -------------------------------------------------
    widths = {"A": 34}

    for key, col_idx in col_map.items():
        col_letter = ws.cell(1, col_idx).column_letter

        if key.startswith("revenue_"):
            widths[col_letter] = 14
        elif key.startswith("share_"):
            widths[col_letter] = 12
        elif key.startswith("delta_share_"):
            widths[col_letter] = 13
        elif key.startswith("gap_after_"):
            widths[col_letter] = 3.5

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
            8: 32,
        },
    )

    hide_grid_and_freeze(ws, "B9")