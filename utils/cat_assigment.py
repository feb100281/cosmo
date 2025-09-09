COLS_DICT = {
    "date": "Дата",
    "client_order_date": "Дата заказа",
    "client_order_number": "Номер заказа",
    "client_order": "Заказ клиента",
    "operation": "Операция",
    "dt": "dt",
    "cr": "cr",
    "amount": "Сумма",
    "quant_dt": "quant_dt",
    "quant_cr": "quant_cr",
    "quant": "Количество",
    "warehouse": "Склад",
    "spec": "Спецификация",
    "fullname": "Номенклатура",
    "imname": "Название в ИМ",
    "article": "Артикл",
    "onec_cat": "onec_cat",
    "onec_subcat": "onec_subcat",
    "init_date": "Дата первого заказа",
    "im_id": "Код товара в ИМ",
    "cat": "Категория",
    "cat_icon": "cat_icon",
    "parent_cat": "Группа",
    "parent_icon": "parent_icon",
    "manu": "Производитель",
    "manu_origin": "Стана происхождения",
    "brend": "Бренд",
    "brend_origin": "Страна бренда",
    "subcat": "Подкатегоря",
    "store": "Торговая точка",
    "chanel": "Канал продаж",
    "store_gr_name": "Магазин",
    "store_region": "Регион",
    "agent": "_Агент",
    "agent_name": "Агент",  # report_name
    "manager": "_Менеджер",
    "manager_name": "Менеджер",  # report_name
    "eom": "Отчетный период",
    "month_fmt": "Месяц",
    "quarter_fmt": "Квартал",
    "week_fmt": "_Неделя",  # сокращенная
    "week_fullname": "Неделя",
    "month_id": "month_id",
}

l = []

for k in COLS_DICT:
    l.append(k)

print(l)