# orders/reports/order_report.py
from django.http import HttpResponse
from openpyxl import Workbook
from datetime import datetime
import io


from .queries.dashboard_queries import DashboardQueries

from .sheets.toc_sheet import TOCSheet
from .sheets.dashboard_sheet import DashboardSheet
from .sheets.debtors_sheet import ActiveDebtorsSheet, ClosedDebtorsSheet



def generate_orders_report(request):
    # Получаем данные
    dashboard_data = DashboardQueries.get_dashboard_data(request=request)
    active_debtors = DashboardQueries.get_active_debtors(request=request)
    closed_debtors = DashboardQueries.get_closed_debtors(request=request)
    status_summary = DashboardQueries.get_status_summary(request=request) 

    wb = Workbook()

    # Удаляем дефолтный лист
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    # Список для оглавления
    sheets_info = []
    sheet_counter = 1
    
    # Лист TOC (оглавление)
    toc_sheet = TOCSheet(wb)
    
    # Лист 1: Общая аналитика (Dashboard)
    dashboard_sheet = DashboardSheet(wb, str(sheet_counter))
    dashboard_sheet.build(
        dashboard_data=dashboard_data, 
        active_debtors=active_debtors,
        status_summary=status_summary  # НОВЫЙ ПАРАМЕТР
    )
    sheets_info.append({
        "number": sheet_counter,
        "name": "ОБЩАЯ_АНАЛИТИКА",
        "description": "Ключевые показатели, статусы заказов, топы и предупреждения"
    })
    sheet_counter += 1
    
    # Лист 2: Активная дебиторка
    active_debtors_sheet = ActiveDebtorsSheet(wb, str(sheet_counter))
    active_debtors_sheet.build(active_debtors)
    sheets_info.append({
        "number": sheet_counter,
        "name": "АКТИВНАЯ_ДЕБИТОРКА",
        "description": f"Активные заказы с долгом ({len(active_debtors)} шт.)"
    })
    sheet_counter += 1
    
    # Лист 3: Закрытая дебиторка (отгружено, но не оплачено)
    if closed_debtors:
        closed_debtors_sheet = ClosedDebtorsSheet(wb, str(sheet_counter))
        closed_debtors_sheet.build(closed_debtors)
        sheets_info.append({
            "number": sheet_counter,
            "name": "ЗАКРЫТАЯ_ДЕБИТОРКА",
            "description": f"Отгружено, но не оплачено ({len(closed_debtors)} шт.)"
        })
        sheet_counter += 1
    
    # Переставляем TOC на первое место
    toc_index = wb.sheetnames.index("TOC")
    wb.move_sheet(wb["TOC"], offset=-toc_index)
    
    # Строим оглавление
    toc_sheet.build(sheets_info, request=request, filters=None)

    # Сохраняем отчет
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f'orders_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    with io.BytesIO() as output:
        wb.save(output)
        response.write(output.getvalue())

    return response