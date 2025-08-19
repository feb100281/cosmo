from django.db import models
from corporate.models import Items, Stores, Managers, Agents
from utils.choices import OPERATION_TYPES


# Create your models here.
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

    client_order_number = models.CharField(
        max_length=600, verbose_name="Характеристика", null=True, blank=True
    )

    store = models.ForeignKey(
        Stores, on_delete=models.CASCADE, verbose_name="Точка продаж", null=True, blank=True
    )

    warehouse = models.CharField(
        max_length=250, verbose_name="Склад", null=True, blank=True
    )
    
    spec = models.TextField(
       verbose_name="Харектеристика", null=True, blank=True
    )

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

    class Meta:
        verbose_name = "Данные продаж"
        verbose_name_plural = "Данные продаж"

    def __str__(self):
        return f"{self.date} {self.item}"
