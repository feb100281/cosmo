from .data import get_sales_plan_data


def build_sales_plan_report_context(report_date, request=None):
    sales_plan = get_sales_plan_data(report_date)

    return {
        "company": 'ООО "КОСМО"',
        "title": "Выполнение cash-плана по магазинам",
        "subtitle": "План / факт поступлений денежных средств по торговым точкам",
        "period_label": f"Данные на {report_date.strftime('%d.%m.%Y')}",
        "sales_plan": sales_plan,
    }