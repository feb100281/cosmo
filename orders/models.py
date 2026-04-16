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

class OrdersCF(models.Model):
    order_guid =  models.CharField(max_length=100,verbose_name='GUID',null=True,blank=True)
    date = models.DateField(verbose_name='Дата операции',null=True,blank=True)
    oper_type = models.CharField(max_length=300,verbose_name='Тип операции',null=True,blank=True)
    oper_name = models.CharField(max_length=300,verbose_name='Название операции',null=True,blank=True)
    cash_deck = models.CharField(max_length=300,verbose_name='Касса',null=True,blank=True)
    doc_number = models.CharField(max_length=300,verbose_name='Номер документа',null=True,blank=True)
    amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Сумма",default=0)
    store = models.CharField(max_length=300,verbose_name='Подразделение',null=True,blank=True)
    register = models.CharField(max_length=300,verbose_name='Регистратор',null=True,blank=True)
    
    class Meta:
        verbose_name = "Оплата заказов"
        verbose_name_plural = "Оплаты заказов"

    def __str__(self):
        
        return f"{self.oper_type} {self.date} {self.amount:,.0f} руб"

# делаем историю изменений по загрузки нового отчета




# делаем заглушку для mv_model в админке по заказам





