# orders/models.py

from django.db import models
from corporate.models import Items
from corporate.models import Barcode



# Create your models here.

class Order(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    fullname = models.CharField(max_length=250,verbose_name='Наименование',null=True,blank=True)
    number = models.CharField(max_length=250,verbose_name='Номер',null=True,blank=True)
    date_from = models.DateField(verbose_name='Дата создания',null=True,blank=True)
    update_at = models.DateField(verbose_name='Дата изменения',null=True,blank=True)
    is_cancelled = models.BooleanField(verbose_name='Отмененный заказ',default=False)
    cancellation_reason =  models.CharField(max_length=500,verbose_name='Причина отмены',null=True,blank=True)
    status = models.CharField(max_length=500,verbose_name='Статус',null=True,blank=True)
    manager = models.CharField(max_length=500,verbose_name='Менеджер',null=True,blank=True)
    client = models.CharField(max_length=500,verbose_name='Клиент',null=True,blank=True)
    oper_type = models.CharField(max_length=500,verbose_name='Тип заказа',null=True,blank=True)
    store = models.CharField(max_length=500,verbose_name='Магазин',null=True,blank=True)
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"{self.fullname}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,verbose_name='Заказ')
    item = models.ForeignKey(Items,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Номенклатура')
    barcode = models.ForeignKey(Barcode,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Номенклатура')
    qty = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Количество",default=0)
    price = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Цена",default=0)
    amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Сумма",default=0)
    
    class Meta:
        verbose_name = "Состав заказа"
        verbose_name_plural = "Состав заказов"

    def __str__(self):
        item_name = self.item.fullname if self.item else "Без номенклатуры"
        return f"{item_name} {self.qty:,.0f} шт на {self.amount:,.0f} руб"



class MV_Orders(models.Model):
    order_id = models.CharField(max_length=100,primary_key=True)
    order_name = models.CharField(max_length=250,null=True,blank=True,verbose_name='Наименование')
    number = models.CharField(max_length=100,null=True,blank=True,verbose_name='Номер')
    date_from = models.DateField(verbose_name='Дата создания',null=True,blank=True)
    update_at = models.DateField(verbose_name='Дата обновления',null=True,blank=True)
    status = models.CharField(max_length=100,null=True,blank=True,verbose_name='Стаутус заказа')
    change_status = models.CharField(max_length=100,null=True,blank=True,verbose_name='Стаутус изменения')
    client = models.CharField(max_length=500,null=True,blank=True,verbose_name='Клиент')
    manager = models.CharField(max_length=500,null=True,blank=True,verbose_name='Менеджер')
    store = models.CharField(max_length=500,null=True,blank=True,verbose_name='Магазин')
    qty_ordered = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Количество заказано',null=True,blank=True)
    qty_cancelled = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Количество отмененно',null=True,blank=True)
    order_qty = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Количество финальное',null=True,blank=True)
    order_amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Сумма заказа',null=True,blank=True)
    amount_delivery = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='В т.ч стоимость услуг',null=True,blank=True)
    amount_cancelled = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Сумма отмен',null=True,blank=True)
    amount_active = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Финальная сумма',null=True,blank=True)
    cash_recieved = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Посутпления денег',null=True,blank=True)
    cash_returned = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Возвраты денег',null=True,blank=True)
    cash_pmts = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Всего оплачено',null=True,blank=True)
    shiped = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Отгружено',null=True,blank=True)
    returned = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Возвращено',null=True,blank=True)
    shiped_qty = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Фианально отгружено',null=True,blank=True)
    shiped_amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Реализация',null=True,blank=True)
    returned_amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Возвраты',null=True,blank=True)
    total_shiped_amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Итого реализация',null=True,blank=True)
    shiped_delivery_amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='В т.ч реализация услуг',null=True,blank=True)
    payment_dates = models.TextField(verbose_name='Даты и суммы оплат',null=True,blank=True)
    
    class Meta:
        managed = False
        db_table = "mv_orders_summary_table"
        verbose_name = "Заказ информация"
        verbose_name_plural = "Заказы информация"
        
    def __str__(self):
        return self.order_name

class OrdersCF(models.Model):
    order = models.ForeignKey(
        "MV_Orders",
        to_field="order_id",
        db_column="order_guid",
        on_delete=models.DO_NOTHING,
        related_name="payments",
        null=True,
        blank=True,
        db_constraint=False,
        verbose_name="Заказ",
    )
    date = models.DateField(verbose_name='Дата операции', null=True, blank=True)
    oper_type = models.CharField(max_length=300, verbose_name='Тип операции', null=True, blank=True)
    oper_name = models.CharField(max_length=300, verbose_name='Название операции', null=True, blank=True)
    cash_deck = models.CharField(max_length=300, verbose_name='Касса', null=True, blank=True)
    doc_number = models.CharField(max_length=300, verbose_name='Номер документа', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма", default=0)
    store = models.CharField(max_length=300, verbose_name='Подразделение', null=True, blank=True)
    register = models.CharField(max_length=300, verbose_name='Регистратор', null=True, blank=True)

    class Meta:
        managed = False
        db_table = "orders_orderscf"
        verbose_name = "Оплата заказов"
        verbose_name_plural = "Оплаты заказов" 

    def __str__(self):
        return f"{self.oper_type} {self.date} {self.amount:,.0f} руб"




# делаем заглушку для mv_model в админке по заказам не берем молеи выше в них нет смысла

class MV_OrdersItems(models.Model):
    id = models.BigIntegerField(primary_key=True)
    order = models.ForeignKey(
        "MV_Orders",
        to_field="order_id",
        db_column="order_id",
        on_delete=models.DO_NOTHING,
        related_name="items",
        null=True,
        blank=True,
        db_constraint=False,
        verbose_name="Заказ",
    )
    fullname = models.CharField(max_length=300, verbose_name='Номенклатура', null=True, blank=True)
    name = models.CharField(max_length=300, verbose_name='Название в ИМ', null=True, blank=True)
    article = models.CharField(max_length=300, verbose_name='Артикль', null=True, blank=True)
    barcode = models.CharField(max_length=300, verbose_name='Штрихкод', null=True, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Кол-во", default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма", default=0)
    cancellation_reason = models.CharField(max_length=300, verbose_name='Причина отмены', null=True, blank=True)
    parent_cat = models.CharField(max_length=300, verbose_name='Группа', null=True, blank=True)
    cat =  models.CharField(max_length=300, verbose_name='Категория', null=True, blank=True)
    subcat  = models.CharField(max_length=300, verbose_name='Подкатегоря', null=True, blank=True)
    warehouse =  models.CharField(max_length=300, verbose_name='Склад', null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = "mv_orders_items"
        verbose_name = "Состав заказа"
        verbose_name_plural = "Состав заказов"

    def __str__(self):
        return f"{self.article} {self.fullname}"
    





