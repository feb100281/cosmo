# orders/reports/sheets/debtors_sheet.py
from datetime import date
from openpyxl.styles import Font
from .base_sheet import BaseSheet
from ..styles.theme import FILLS, FONTS, BORDERS, ALIGNMENTS, COLORS


class DashboardDebtorsSheet(BaseSheet):
    """Полный список дебиторской задолженности"""

    def __init__(self, workbook, sheet_number):  # добавил sheet_number
        super().__init__(workbook, sheet_number)  # передаем номер (цифру)

    def build(self, debtors):
        today = date.today().strftime("%d.%m.%Y")
        row = 1

        # Ссылка в оглавление (на лист TOC)
        toc_link = self.ws.cell(row=row, column=2, value="← ВЕРНУТЬСЯ В ОГЛАВЛЕНИЕ")
        toc_link.font = Font(name="Roboto", size=9, bold=True, color=COLORS["blue"], underline="single")
        toc_link.alignment = ALIGNMENTS["left"]
        toc_link.hyperlink = "#'TOC'!A1"

        self.ws.cell(row=row + 1, column=2, value="ПОЛНАЯ ДЕБИТОРСКАЯ ЗАДОЛЖЕННОСТЬ")
        self.ws.cell(row=row + 1, column=2).font = Font(name="Roboto", size=16, bold=True, color=COLORS["dark_green"])

        self.ws.cell(row=row + 2, column=2, value=f"По всем активным заказам на дату отчёта: {today}")
        self.ws.cell(row=row + 2, column=2).font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])

        row = 6

        headers = ["КЛИЕНТ", "ЗАКАЗ", "ДАТА", "СУММА", "ОПЛАЧЕНО", "ДОЛГ"]
        for col_idx, header in enumerate(headers, 2):
            cell = self.ws.cell(row=row, column=col_idx, value=header)
            cell.font = FONTS["header_white"]
            cell.alignment = ALIGNMENTS["center"]
            cell.fill = FILLS["header"]
            cell.border = BORDERS["thin"]
        row += 1

        total_debt = 0

        for idx, debtor in enumerate(debtors):
            fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]

            client = debtor.get("client", "НЕ УКАЗАН")
            order_number = debtor.get("order_number", "")
            order_date = debtor.get("order_date", "")
            amount = debtor.get("total_amount", 0)
            paid = debtor.get("paid_amount", 0)
            debt = debtor.get("debt_amount", 0)
            total_debt += debt

            c1 = self.ws.cell(row=row, column=2, value=str(client)[:40])
            c1.font = FONTS["normal"]
            c1.alignment = ALIGNMENTS["left"]
            c1.border = BORDERS["thin"]
            c1.fill = fill

            c2 = self.ws.cell(row=row, column=3, value=order_number)
            c2.font = Font(name="Roboto", size=9, color=COLORS["blue"], underline="single")
            c2.alignment = ALIGNMENTS["left"]
            c2.border = BORDERS["thin"]
            c2.fill = fill
            # c2.hyperlink = "#'1_ЗАКАЗЫ'!A1"  # закомментировано, т.к. листа может не быть

            date_str = order_date.strftime("%d.%m.%Y") if hasattr(order_date, "strftime") else str(order_date)
            c3 = self.ws.cell(row=row, column=4, value=date_str)
            c3.font = FONTS["normal"]
            c3.alignment = ALIGNMENTS["center"]
            c3.border = BORDERS["thin"]
            c3.fill = fill

            c4 = self.ws.cell(row=row, column=5, value=amount)
            c4.font = FONTS["normal"]
            c4.alignment = ALIGNMENTS["right"]
            c4.border = BORDERS["thin"]
            c4.fill = fill
            c4.number_format = '#,##0.00'

            c5 = self.ws.cell(row=row, column=6, value=paid)
            c5.font = FONTS["normal"]
            c5.alignment = ALIGNMENTS["right"]
            c5.border = BORDERS["thin"]
            c5.fill = fill
            c5.number_format = '#,##0.00'

            c6 = self.ws.cell(row=row, column=7, value=debt)
            c6.font = Font(name="Roboto", size=9, bold=True, color="CD5C5C")
            c6.alignment = ALIGNMENTS["right"]
            c6.border = BORDERS["thin"]
            c6.fill = fill
            c6.number_format = '#,##0.00'

            row += 1

        total_label = self.ws.cell(row=row, column=6, value="ИТОГО:")
        total_label.font = Font(name="Roboto", size=10, bold=True)
        total_label.alignment = ALIGNMENTS["right"]
        total_label.border = BORDERS["thin"]
        total_label.fill = FILLS["total"]

        total_cell = self.ws.cell(row=row, column=7, value=total_debt)
        total_cell.font = Font(name="Roboto", size=10, bold=True, color="CD5C5C")
        total_cell.alignment = ALIGNMENTS["right"]
        total_cell.border = BORDERS["thin"]
        total_cell.fill = FILLS["total"]
        total_cell.number_format = '#,##0.00'

        self.ws.column_dimensions["A"].width = 3
        self.ws.column_dimensions["B"].width = 32
        self.ws.column_dimensions["C"].width = 20
        self.ws.column_dimensions["D"].width = 14
        self.ws.column_dimensions["E"].width = 18
        self.ws.column_dimensions["F"].width = 18
        self.ws.column_dimensions["G"].width = 18

        self.ws.freeze_panes = "A7"
        self.ws.sheet_view.showGridLines = False

