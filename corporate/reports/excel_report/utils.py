from decimal import Decimal
from openpyxl.utils import get_column_letter


def d(x) -> Decimal:
    try:
        return Decimal(str(x or "0"))
    except Exception:
        return Decimal("0")


def autosize_columns(ws, min_width=10, max_width=40):
    for col_cells in ws.columns:
        length = 0
        col_idx = col_cells[0].column
        for cell in col_cells:
            try:
                value = "" if cell.value is None else str(cell.value)
                length = max(length, len(value))
            except Exception:
                pass
        width = min(max(length + 2, min_width), max_width)
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def freeze_top(ws, cell="A2"):
    ws.freeze_panes = cell