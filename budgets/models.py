from django.db import models
from corporate.models import StoreGroups, CatTree

class ForecastTypes(models.Model):
    name = models.CharField(verbose_name='Тип бюджета', max_length=250)
    
    class Meta:       
        verbose_name = "Тип бюджета"
        verbose_name_plural = "Типы бюджетов"

    def __str__(self):
        return f"{self.name}"

class ForecastSubjects(models.Model):  # Исправлено название
    name = models.CharField(verbose_name='Раздел бюджета', max_length=205)
    
    class Meta:       
        verbose_name = "Раздел бюджета"
        verbose_name_plural = "Разделы бюджетов"

    def __str__(self):
        return f"{self.name}"

class Forecasts(models.Model):
    subject = models.ForeignKey(ForecastSubjects, on_delete=models.CASCADE, verbose_name='Раздел бюджета', related_name='forecasts')
    tp = models.ForeignKey(ForecastTypes, on_delete=models.CASCADE, verbose_name='Тип бюджета', related_name='forecasts')
    created_by = models.CharField(verbose_name='Кем создан', null=True, blank=True, max_length=250)
    created_at = models.DateTimeField(verbose_name='Создано', auto_now_add=True)
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    parameters = models.JSONField(verbose_name='Параметры модели', null=True, blank=True)
    comments = models.TextField(verbose_name='Комментарии', blank=True, null=True)
    
    class Meta:       
        verbose_name = "Бюджет"
        verbose_name_plural = "Бюджеты"

    def __str__(self):
        return f"{self.subject.name} {self.tp.name} от {self.created_at.strftime('%d.%m.%Y')} на период с {self.start_date.strftime('%d.%m.%Y')} по {self.end_date.strftime('%d.%m.%Y')}"

    
class ForecastData(models.Model):
    forecast = models.ForeignKey(Forecasts,on_delete=models.CASCADE,verbose_name='Бюджет',related_name='forecast_data')
    date = models.DateField(verbose_name='Дата')
    dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='dt')
    cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='cr')
    subaccount = models.CharField(max_length=250,verbose_name='Субсчет',null=True,blank=True)
    store = models.ForeignKey(StoreGroups,verbose_name='Магазин',null=True,blank=True,on_delete=models.CASCADE)
    cat = models.ForeignKey(CatTree,verbose_name='Категория',on_delete=models.CASCADE,null=True,blank=True)
    
    class Meta:       
        verbose_name = "Данные"
        verbose_name_plural = "Данные"
        
    def __str__(self):
        difference = self.dt - self.cr
        return f"{self.date.strftime('%d.%m.%Y')} {difference:,.0f} rub"
    
    