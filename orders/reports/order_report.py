# orders/reports/order_report.py
from django.http import HttpResponse
from openpyxl import Workbook
from datetime import datetime
import io

from .queries.duckdb_queries import DuckDBReportQueries
from .queries.toc_queries import TOCQueries
from .queries.dashboard_queries import DashboardQueries

from .sheets.toc_sheet import TOCSheet
from .sheets.dashboard_sheet import DashboardSheet
from .sheets.debtors_sheet import DashboardDebtorsSheet
from .sheets.inconsistencies_sheet import InconsistenciesSheet


def generate_orders_report(request):
    # Получаем данные
    inconsistencies = TOCQueries.get_inconsistencies(request=request)
    dashboard_data = DashboardQueries.get_dashboard_data(request=request)

    total_inconsistencies = (
        len(inconsistencies.get("agreement_cancelled", [])) +
        len(inconsistencies.get("execution_cancelled", []))
    )

    wb = Workbook()

    # Удаляем дефолтный лист
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    # Список для оглавления
    sheets_info = []
    sheet_counter = 1
    
    # Лист TOC (оглавление) создаем отдельно
    toc_sheet = TOCSheet(wb)
    
    # Лист 1: Несоответствия (если есть)
    if total_inconsistencies > 0:
        inconsistencies_sheet = InconsistenciesSheet(wb, sheet_counter)
        inconsistencies_sheet.build(inconsistencies)
        sheets_info.append({
            "number": sheet_counter,
            "name": "НЕСООТВЕТСТВИЯ",
            "description": f"Отмененные заказы с активными статусами ({total_inconsistencies} шт.)"
        })
        sheet_counter += 1
    
    # Лист 2 (или 1): Общая аналитика
    dashboard_sheet = DashboardSheet(wb, sheet_counter)
    dashboard_sheet.build(dashboard_data)
    sheets_info.append({
        "number": sheet_counter,
        "name": "ОБЩАЯ_АНАЛИТИКА",
        "description": "Ключевые показатели и аналитика по активным заказам"
    })
    sheet_counter += 1
    
    # Лист 3 (или 2): Дебиторка
    debtors_sheet = DashboardDebtorsSheet(wb, sheet_counter)
    debtors_sheet.build(dashboard_data.get("all_debtors", []))
    sheets_info.append({
        "number": sheet_counter,
        "name": "ДЕБИТОРКА",
        "description": "Полный список дебиторской задолженности по активным заказам"
    })
    
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