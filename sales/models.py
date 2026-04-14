# sales/models.py
from django.db import models
from corporate.models import Items, Stores, Managers, Agents, Barcode
from utils.choices import OPERATION_TYPES
from orders.models import Order

class SalesOrders(models.Model):
    client_order = models.CharField(max_length=250, verbose_name="Заказ клиента")

    client_order_date = models.DateField(
        verbose_name="Дата заказа", null=True, blank=True
    )

    client_order_number = models.CharField(
        max_length=250,
        verbose_name="Номер заказа клиента",
        null=True,
        blank=True,
        db_index=True,
    )

    client_order_type = models.CharField(
        max_length=250, verbose_name="Тип заказа", null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "client_order",
                    "client_order_date",
                    "client_order_number",
                ],
                name="uniq_sales_order_combo",
            )
        ]


class SalesData(models.Model):
    date = models.DateField(verbose_name="Дата")
    client_order_date = models.DateField(
        verbose_name="Дата заказа", null=True, blank=True
    )
    client_order = models.CharField(
        max_length=100, verbose_name="Описание", null=True, blank=True
    )
    client_order_number = models.CharField(
        max_length=100, verbose_name="Номер заказа", null=True, blank=True
    )
    orders = models.ForeignKey(
        SalesOrders,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="id заказа",
    )
    operation = models.CharField(
        choices=OPERATION_TYPES,
        max_length=100,
        verbose_name="Тип операций",
        null=True,
        blank=True,
    )
    item = models.ForeignKey(
        Items, on_delete=models.CASCADE, verbose_name="Наименование"
    )

    client_order_feature = models.CharField(
        max_length=600, verbose_name="Характеристика", null=True, blank=True
    )

    store = models.ForeignKey(
        Stores,
        on_delete=models.CASCADE,
        verbose_name="Точка продаж",
        null=True,
        blank=True,
    )

    warehouse = models.CharField(
        max_length=250, verbose_name="Склад", null=True, blank=True
    )

    spec = models.TextField(verbose_name="Харектеристика", null=True, blank=True)

    manager = models.ForeignKey(
        Managers,
        on_delete=models.CASCADE,
        verbose_name="Менеджер",
        null=True,
        blank=True,
    )

    agent = models.ForeignKey(
        Agents, on_delete=models.CASCADE, verbose_name="Агент", null=True, blank=True
    )

    dt = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Дт", default=0.0
    )
    cr = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Кр", default=0.0
    )
    quant_dt = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Количество_Дт", default=0.0
    )
    quant_cr = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Количество_Кр", default=0.0
    )
    amount_undisc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма без скидки",
        null=True,
        blank=True,
    )
    discount_auto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Скидка автомат",
        null=True,
        blank=True,
    )
    discount_design = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Скидка дизайнер",
        null=True,
        blank=True,
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Размер скидки",
        null=True,
        blank=True,
    )
    discount_percent_auto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Процент скидки автомат",
        null=True,
        blank=True,
    )
    discount_percent_design = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Процент скидки дизайнер",
        null=True,
        blank=True,
    )
    diccount_percent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Процент скидки",
        null=True,
        blank=True,
    )
    barcode = models.ForeignKey(
        Barcode, on_delete=models.CASCADE, verbose_name="Баркод", null=True, blank=True
    )
    order_id = models.ForeignKey(
        Order, on_delete=models.CASCADE, verbose_name="всегда null", null=True, blank=True
    )
    order_guid = models.CharField(
        max_length=250, verbose_name="Заказ GUID", null=True, blank=True
    )

    class Meta:
        verbose_name = "Данные продаж"
        verbose_name_plural = "Данные продаж"

    def __str__(self):
        return f"{self.date} {self.item}"


# MV MODELs
class MV_Daily_Sales(models.Model):
    date = models.DateField(primary_key=True, verbose_name="Дата")
    amount = models.DecimalField(
        verbose_name="Выручка", max_digits=12, decimal_places=2, null=True, blank=True
    )
    quant = models.DecimalField(
        verbose_name="Кол-во товаров",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    orders = models.BigIntegerField(
        verbose_name="Кол-во заказов", null=True, blank=True
    )
    ave_check = models.DecimalField(
        verbose_name="Ср чек", max_digits=12, decimal_places=2, null=True, blank=True
    )
    dt = models.DecimalField(
        verbose_name="Продажи", max_digits=12, decimal_places=2, null=True, blank=True
    )
    cr = models.DecimalField(
        verbose_name="Возвраты", max_digits=12, decimal_places=2, null=True, blank=True
    )
    rtr_ratio = models.DecimalField(
        verbose_name="К возв. (%)",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quant_dt = models.DecimalField(
        verbose_name="Кол-во продано",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quant_cr = models.DecimalField(
        verbose_name="Кол-во возвращено",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "mv_daily_sales"
        verbose_name = "Дневные продажи"
        verbose_name_plural = "Дневные продажи"

    def __str__(self):
        return self.date.strftime("%d %b-%Y")


class MVSalesOrder(models.Model):
    orders_id = models.BigIntegerField(primary_key=True)
    client_order_type = models.CharField(
        max_length=250, blank=True, null=True, verbose_name="Тип заказов"
    )
    client_order = models.CharField(
        max_length=500, blank=True, null=True, verbose_name="Заказ"
    )
    client_order_number = models.CharField(
        max_length=500, blank=True, null=True, verbose_name="Номер заказа"
    )
    client_order_date = models.DateField("Дата формирования", null=True, blank=True)
    order_min_date = models.DateField("Первая отгрузка", null=True, blank=True)
    order_max_date = models.DateField("Последняя отгрузка", null=True, blank=True)
    order_duration = models.BigIntegerField(
        verbose_name="Срок", blank=True, null=True
    )
    realization_duration = models.BigIntegerField(
        verbose_name="Срок реализации", blank=True, null=True
    )
    sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма продаж",
        null=True,
        blank=True,
    )
    returns = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма возвратов",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Стоимость заказа",
        null=True,
        blank=True,
    )
    items_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Стоимость товара",
        null=True,
        blank=True,
    )
    service_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Стоимость услуг",
        null=True,
        blank=True,
    )
    items_quant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Количество мест в заказе",
        null=True,
        blank=True,
    )
    unique_items = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Кол-во номенклатур",
        null=True,
        blank=True,
    )
    manager_name = models.CharField(
        max_length=500, blank=True, null=True, verbose_name="Менеджеры"
    )

    class Meta:
        managed = False
        db_table = "mv_orders"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы (в реализации)"

    def __str__(self):
        return f"{self.client_order}"
