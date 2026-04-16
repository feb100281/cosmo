# orders/reports/sheets/dashboard_sheet.py
from datetime import date
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from .base_sheet import BaseSheet
from ..styles.theme import FILLS, FONTS, BORDERS, ALIGNMENTS, COLORS
from ..styles.helpers import draw_toc_button


class DashboardSheet(BaseSheet):
    """Лист с общей аналитикой - дашборд"""

    def __init__(self, workbook, sheet_number):
        super().__init__(workbook, sheet_number)  

    def _format_manager_name(self, name):
        """Форматирует имя менеджера: ИВАНОВ И.В."""
        if not name or name == "Не назначен":
            return name
        parts = str(name).split()
        if len(parts) >= 2:
            first = parts[0].upper()
            second = f"{parts[1][0].upper()}." if parts[1] else ""
            third = f"{parts[2][0].upper()}." if len(parts) >= 3 and parts[2] else ""
            return f"{first} {second}{third}"
        return str(name).upper()

    def _draw_kpi_grid(self, start_row, items):
        """
        Рисует KPI карточки в формате 3 колонки × 2 ряда.
        Каждая карточка = [заголовок] + [значение]
        """
        cards_per_row = 3
        cols_per_card = 2

        for idx, (title, value) in enumerate(items):
            row_offset = idx // cards_per_row
            col_offset = (idx % cards_per_row) * cols_per_card

            # Каждая карточка занимает 2 строки
            title_row = start_row + row_offset * 3
            value_row = title_row + 1

            start_col = 2 + col_offset
            end_col = start_col + cols_per_card - 1

            # --- ЗАГОЛОВОК ---
            # Сначала установим границы для всех ячеек, которые будут объединены
            for col in range(start_col, end_col + 1):
                cell = self.ws.cell(row=title_row, column=col)
                cell.border = BORDERS["thin"]
            
            self.ws.merge_cells(
                start_row=title_row, start_column=start_col,
                end_row=title_row, end_column=end_col
            )

            title_cell = self.ws.cell(row=title_row, column=start_col, value=title)
            title_cell.font = Font(name="Roboto", size=9, bold=True)
            title_cell.alignment = ALIGNMENTS["center"]
            title_cell.fill = PatternFill(
                start_color=COLORS["light_green"],
                end_color=COLORS["light_green"],
                fill_type="solid"
            )
            # Границы уже установлены, но если нужно перезаписать:
            title_cell.border = BORDERS["thin"]

            # --- ЗНАЧЕНИЕ ---
            # Сначала установим границы для всех ячеек, которые будут объединены
            for col in range(start_col, end_col + 1):
                cell = self.ws.cell(row=value_row, column=col)
                cell.border = BORDERS["thin"]
            
            self.ws.merge_cells(
                start_row=value_row, start_column=start_col,
                end_row=value_row, end_column=end_col
            )

            value_cell = self.ws.cell(row=value_row, column=start_col, value=value)
            value_cell.font = Font(name="Roboto", size=14, bold=True, color=COLORS["dark_green"])
            value_cell.alignment = ALIGNMENTS["center"]
            value_cell.border = BORDERS["thin"]
    def build(self, dashboard_data):
        kpi = dashboard_data.get("kpi", {})
        ytd = dashboard_data.get("ytd", {})
        mtd = dashboard_data.get("mtd", {})
        major_debtors = dashboard_data.get("major_debtors", [])
        managers_top = dashboard_data.get("managers_top", [])
        clients_top = dashboard_data.get("clients_top", [])
        major_threshold = dashboard_data.get("major_debt_threshold", 300000)

        today = date.today()
        report_date = today.strftime("%d.%m.%Y")

        row = 1

        # Ссылка в оглавление (на лист TOC)
        draw_toc_button(self.ws, cell="B1", text="← ВЕРНУТЬСЯ В ОГЛАВЛЕНИЕ", target_sheet="TOC")

        # Шапка
        self.ws.cell(row=row + 1, column=2, value="ОБЩАЯ АНАЛИТИКА")
        self.ws.cell(row=row + 1, column=2).font = Font(name="Roboto", size=16, bold=True, color=COLORS["dark_green"])

        self.ws.cell(row=row + 2, column=2, value="Ключевые показатели по активным заказам")
        self.ws.cell(row=row + 2, column=2).font = Font(name="Roboto", size=10, color=COLORS["text_gray"])

        period_text = (
            f"Отчёт сформирован: {report_date} | "
            f"Активные статусы: На согласовании, К выполнению / В резерве | "
            f"Дебиторская задолженность на листе показана по всем активным заказам на дату отчёта"
        )
        self.ws.cell(row=row + 3, column=2, value=period_text)
        self.ws.cell(row=row + 3, column=2).font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])

        row = 6

        # -------------------------------------------------
        # БЛОК 1: KPI в формате 3×2
        # -------------------------------------------------
        kpi_items = [
            ("АКТИВНЫХ ЗАКАЗОВ", f"{kpi.get('active_orders', 0):,}"),
            ("СУММА АКТИВНЫХ", f"{kpi.get('active_amount', 0):,.0f} ₽"),
            ("ОПЛАЧЕНО", f"{kpi.get('active_paid', 0):,.0f} ₽"),
            ("ДОЛГ", f"{kpi.get('active_debt', 0):,.0f} ₽"),
            ("СРЕДНИЙ ЧЕК", f"{kpi.get('active_avg_check', 0):,.0f} ₽"),
            ("ОТМЕНЕНО ЗА 7 ДНЕЙ", f"{kpi.get('cancelled_last_7_days', 0):,}"),
        ]
        self._draw_kpi_grid(row, kpi_items)
        row += 7  

        # -------------------------------------------------
        # БЛОК 2: YTD / MTD
        # -------------------------------------------------
        self.ws.cell(row=row, column=2, value="СВОДКА ПО ПЕРИОДАМ")
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
        row += 1

        headers = ["ПЕРИОД", "ЗАКАЗОВ", "СУММА", "ОПЛАЧЕНО", "ДОЛГ"]
        for col_idx, header in enumerate(headers, 2):
            cell = self.ws.cell(row=row, column=col_idx, value=header)
            cell.font = FONTS["header_white"]
            cell.alignment = ALIGNMENTS["center"]
            cell.fill = FILLS["header"]
            cell.border = BORDERS["thin"]
        row += 1

        periods = [
            ("С НАЧАЛА ГОДА (YTD)", 
             ytd.get("orders", 0), 
             ytd.get("amount", 0), 
             ytd.get("paid", 0), 
             ytd.get("debt", 0)),
            ("ТЕКУЩИЙ МЕСЯЦ (MTD)", 
             mtd.get("orders", 0), 
             mtd.get("amount", 0), 
             mtd.get("paid", 0), 
             mtd.get("debt", 0)),
        ]

        for idx, (period_name, orders, amount, paid, debt) in enumerate(periods):
            fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]

            c1 = self.ws.cell(row=row, column=2, value=period_name)
            c1.font = FONTS["normal"]
            c1.alignment = ALIGNMENTS["left"]
            c1.border = BORDERS["thin"]
            c1.fill = fill

            c2 = self.ws.cell(row=row, column=3, value=orders)
            c2.font = FONTS["normal"]
            c2.alignment = ALIGNMENTS["right"]
            c2.border = BORDERS["thin"]
            c2.fill = fill
            c2.number_format = '#,##0'

            c3 = self.ws.cell(row=row, column=4, value=amount)
            c3.font = FONTS["normal"]
            c3.alignment = ALIGNMENTS["right"]
            c3.border = BORDERS["thin"]
            c3.fill = fill
            c3.number_format = '#,##0.00'

            c4 = self.ws.cell(row=row, column=5, value=paid)
            c4.font = FONTS["normal"]
            c4.alignment = ALIGNMENTS["right"]
            c4.border = BORDERS["thin"]
            c4.fill = fill
            c4.number_format = '#,##0.00'

            c5 = self.ws.cell(row=row, column=6, value=debt)
            c5.font = Font(name="Roboto", size=9, bold=True, color="CD5C5C")
            c5.alignment = ALIGNMENTS["right"]
            c5.border = BORDERS["thin"]
            c5.fill = fill
            c5.number_format = '#,##0.00'

            row += 1

        row += 2

        # -------------------------------------------------
        # БЛОК 3: КРУПНАЯ ДЕБИТОРКА
        # -------------------------------------------------
        self.ws.cell(row=row, column=2, value=f"КРУПНАЯ ДЕБИТОРСКАЯ ЗАДОЛЖЕННОСТЬ (ОТ {major_threshold:,.0f} ₽)")
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
        row += 1

        note = "Показаны только крупные долги по всем активным заказам. Полный список см. на листе «ДЕБИТОРКА»."
        self.ws.cell(row=row, column=2, value=note)
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
        row += 1

        if major_debtors:
            headers = ["КЛИЕНТ", "ЗАКАЗ", "ДАТА", "СУММА", "ОПЛАЧЕНО", "ДОЛГ"]
            for col_idx, header in enumerate(headers, 2):
                cell = self.ws.cell(row=row, column=col_idx, value=header)
                cell.font = FONTS["header_white"]
                cell.alignment = ALIGNMENTS["center"]
                cell.fill = FILLS["header"]
                cell.border = BORDERS["thin"]
            row += 1

            total_major_debt = 0
            for idx, debtor in enumerate(major_debtors):
                fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]

                client = debtor.get("client", "НЕ УКАЗАН")
                order_number = debtor.get("order_number", "")
                order_date = debtor.get("order_date", "")
                amount = debtor.get("total_amount", 0)
                paid = debtor.get("paid_amount", 0)
                debt = debtor.get("debt_amount", 0)
                total_major_debt += debt

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

            total_cell = self.ws.cell(row=row, column=7, value=total_major_debt)
            total_cell.font = Font(name="Roboto", size=10, bold=True, color="CD5C5C")
            total_cell.alignment = ALIGNMENTS["right"]
            total_cell.border = BORDERS["thin"]
            total_cell.fill = FILLS["total"]
            total_cell.number_format = '#,##0.00'
            row += 2
        else:
            self.ws.cell(row=row, column=2, value="Крупная задолженность отсутствует.")
            self.ws.cell(row=row, column=2).font = FONTS["normal"]
            row += 2

        # -------------------------------------------------
        # БЛОК 4: ТОП МЕНЕДЖЕРОВ
        # -------------------------------------------------
        if managers_top:
            self.ws.cell(row=row, column=2, value="ТОП-10 МЕНЕДЖЕРОВ ПО СУММЕ АКТИВНЫХ ЗАКАЗОВ")
            self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
            row += 1

            headers = ["МЕНЕДЖЕР", "ЗАКАЗОВ", "СУММА", "ОПЛАЧЕНО", "ДОЛГ", "СРЕДНИЙ ЧЕК"]
            for col_idx, header in enumerate(headers, 2):
                cell = self.ws.cell(row=row, column=col_idx, value=header)
                cell.font = FONTS["header_white"]
                cell.alignment = ALIGNMENTS["center"]
                cell.fill = FILLS["header"]
                cell.border = BORDERS["thin"]
            row += 1

            for idx, manager in enumerate(managers_top):
                fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]

                values = [
                    self._format_manager_name(manager.get("manager", "Не назначен")),
                    manager.get("orders_count", 0),
                    manager.get("total_amount", 0),
                    manager.get("paid_amount", 0),
                    manager.get("debt_amount", 0),
                    manager.get("avg_check", 0),
                ]

                for offset, value in enumerate(values, start=2):
                    cell = self.ws.cell(row=row, column=offset, value=value)
                    cell.border = BORDERS["thin"]
                    cell.fill = fill
                    cell.font = FONTS["normal"]
                    cell.alignment = ALIGNMENTS["left"] if offset == 2 else ALIGNMENTS["right"]

                    if offset >= 3:
                        if offset == 3:
                            cell.number_format = '#,##0'
                        else:
                            cell.number_format = '#,##0.00'

                row += 1

            row += 2

        # -------------------------------------------------
        # БЛОК 5: ТОП КЛИЕНТОВ
        # -------------------------------------------------
        if clients_top:
            self.ws.cell(row=row, column=2, value="ТОП-10 КЛИЕНТОВ ПО СУММЕ АКТИВНЫХ ЗАКАЗОВ")
            self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
            row += 1

            headers = ["КЛИЕНТ", "ЗАКАЗОВ", "СУММА", "ОПЛАЧЕНО", "ДОЛГ", "СРЕДНИЙ ЧЕК"]
            for col_idx, header in enumerate(headers, 2):
                cell = self.ws.cell(row=row, column=col_idx, value=header)
                cell.font = FONTS["header_white"]
                cell.alignment = ALIGNMENTS["center"]
                cell.fill = FILLS["header"]
                cell.border = BORDERS["thin"]
            row += 1

            for idx, client in enumerate(clients_top):
                fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]

                values = [
                    str(client.get("client", "НЕ УКАЗАН"))[:40],
                    client.get("orders_count", 0),
                    client.get("total_amount", 0),
                    client.get("paid_amount", 0),
                    client.get("debt_amount", 0),
                    client.get("avg_check", 0),
                ]

                for offset, value in enumerate(values, start=2):
                    cell = self.ws.cell(row=row, column=offset, value=value)
                    cell.border = BORDERS["thin"]
                    cell.fill = fill
                    cell.font = FONTS["normal"]
                    cell.alignment = ALIGNMENTS["left"] if offset == 2 else ALIGNMENTS["right"]

                    if offset >= 3:
                        if offset == 3:
                            cell.number_format = '#,##0'
                        else:
                            cell.number_format = '#,##0.00'

                row += 1

        # Ширины колонок
        self.ws.column_dimensions["A"].width = 3
        self.ws.column_dimensions["B"].width = 20
        self.ws.column_dimensions["C"].width = 18
        self.ws.column_dimensions["D"].width = 14
        self.ws.column_dimensions["E"].width = 18
        self.ws.column_dimensions["F"].width = 18
        self.ws.column_dimensions["G"].width = 18

        self.ws.freeze_panes = "A8"
        self.ws.sheet_view.showGridLines = False