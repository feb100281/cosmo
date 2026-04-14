from django.db import models
from corporate.models import Items

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
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"{self.fullname}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,verbose_name='Заказ')
    fullname = models.CharField(max_length=500,verbose_name='Наименование в заказе')
    item = models.ForeignKey(Items,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Номенклатура')
    order_barcode = models.CharField(max_length=500,verbose_name='Наименование в заказе',null=True,blank=True)
    order_article = models.CharField(max_length=500,verbose_name='Наименование в заказе',null=True,blank=True)
    qty = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Количество",default=0)
    price = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Цена",default=0)
    amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Сумма",default=0)
    
    class Meta:
        verbose_name = "Состав заказа"
        verbose_name_plural = "Состав заказов"

    def __str__(self):
        return f"{self.fullname} {self.qty:,.0f} шт на {self.amount:,.0f} руб"

