from django.db import models

# Create your models here.
class SalesDash(models.Model): # type: ignore
    class Meta:
        managed = False  # Django не будет создавать/мигрировать таблицу
        verbose_name = "Отчёт по продажам"
        verbose_name_plural = "Отчёт по продажам"
        default_permissions = ()  # Убирает стандартные разрешения

    def __str__(self):
        return "Отчет по продажам"


class CatDash(models.Model): # type: ignore
    class Meta:
        managed = False  # Django не будет создавать/мигрировать таблицу
        verbose_name = "Сегментный анализ"
        verbose_name_plural = "Сегментный анализ"
        default_permissions = ()  # Убирает стандартные разрешения

    def __str__(self):
        return "Сегментный анализ"
    
class SalesReport(models.Model): # type: ignore
    class Meta:
        managed = False  # Django не будет создавать/мигрировать таблицу
        verbose_name = "Панель продаж"
        verbose_name_plural = "Панель продаж"
        default_permissions = ('view',)

    def __str__(self):
        return "Панель продаж"