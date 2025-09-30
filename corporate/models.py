from django.db import models
from mptt.models import MPTTModel, TreeForeignKey # type: ignore
from utils.choices import CHANNEL_CHOICES,REGION_CHOICES,FURNITURE_ZONES
from django_countries.fields import CountryField
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe


# Create your models here.
class Companies(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование')
    
    class Meta:       
        verbose_name = "Компания"
        verbose_name_plural = "Компании"

    def __str__(self):
        return f"{self.name}"
    

class Projects(models.Model):
    name = models.CharField(max_length=250, verbose_name='Наименование')
    company = models.ForeignKey(Companies, on_delete=models.CASCADE,verbose_name='Компания')
    
    class Meta:       
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"

    def __str__(self):
        return f"Проект {self.name}"

class ItemMaterial(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование материала')
    
    class Meta:       
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"

    def __str__(self):
        return f"{self.name}"

class ItemManufacturer(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование производителя',unique=True)    
    country = CountryField(verbose_name='Страна',default='RU')
        
    class Meta:       
        verbose_name = "Производитель"
        verbose_name_plural = "Производители"

    def __str__(self):
        return f"{self.name}"
    

class ItemBrend(models.Model):
    name = models.CharField(max_length=250,verbose_name='Название')
    logo = models.ImageField(upload_to='bredlogos/', blank=True, null=True,verbose_name='Логотип')
    country = CountryField(verbose_name='Страна',default='RU')
    
    class Meta:       
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self):
        return f"{self.name}"
    


class ItemProperty(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование характеристики',unique=True)
    
    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики"

    def __str__(self):
        return f"{self.name}"
    
class ItemColors(models.Model):
    name =  models.CharField(max_length=250,verbose_name='Наименование цвета',unique=True)
    
    class Meta:
        verbose_name = "Цвет"
        verbose_name_plural = "Цвета"

    def __str__(self):
        return f"{self.name}"

class ItemSizes(models.Model):
    name =  models.CharField(max_length=250,verbose_name='Наименование размера',unique=True)
    
    class Meta:
        verbose_name = "Размер"
        verbose_name_plural = "Размеры"

    def __str__(self):
        return f"{self.name}"

class ItemZones(models.Model):
    name =  models.CharField(max_length=250,verbose_name='Наименование',unique=True)
    
    class Meta:
        verbose_name = "Доп сегментации"
        verbose_name_plural = "Доп сегментации"

    def __str__(self):
        return f"{self.name}"


class ItemCollections(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование коллекции',unique=True)
    
    class Meta:
        verbose_name = "Коллекция"
        verbose_name_plural = "Коллекции"

    def __str__(self):
        return f"{self.name}"
    
class CatTree(MPTTModel):
    name = models.CharField(max_length=255, verbose_name="Наименование категории")
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="Родительская категория")
    icon = models.TextField(verbose_name='Иконка',null=True,blank=True,help_text='Скопируйте и вставьте svg код')
    comments = models.TextField(verbose_name='Комментарий',null=True,blank=True)
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
    
    
    def __str__(self):
        return f"{self.name}"

class SubCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name='Подкатегория')
    category = models.ForeignKey(CatTree, on_delete=models.CASCADE, verbose_name='Категория', related_name='subcategories')
    icon = models.TextField(verbose_name='Иконка',null=True,blank=True,help_text='Скопируйте и вставьте svg код')
    comments = models.TextField(verbose_name='Комментарий',null=True,blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"


class Items(models.Model):
    guid = models.CharField(max_length=200,verbose_name='1c id',null=True,blank=True)
    fullname = models.CharField(max_length=250,verbose_name='Наименование 1С',unique=True) 
    name = models.CharField(max_length=200,verbose_name='Название товара на сайте')
    article = models.CharField(max_length=250,verbose_name='Артикль',blank=True,null=True)
    description = models.TextField(verbose_name='Описание',help_text='Краткое описание товара', blank=True,null=True)
    weight = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Вес', null=True,blank=True)
    volume = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Объем',null=True, blank=True)
    collection = models.ManyToManyField(ItemCollections,verbose_name='Коллекции',blank=True)
    item_property = models.ManyToManyField(ItemProperty,verbose_name='Характеристики',blank=True)
    colors = models.ManyToManyField(ItemColors,verbose_name='Доступные цвета',blank=True)
    sizes = models.ManyToManyField(ItemSizes,verbose_name='Доступные размеры',blank=True)    
    pict = models.ImageField(upload_to='itempic/', blank=True, null=True,verbose_name='Изображение')
    cat = models.ForeignKey(CatTree,on_delete=models.SET_NULL,verbose_name='Категория',null=True)
    material = models.ManyToManyField(ItemMaterial,verbose_name='Материалы',blank=True)
    manufacturer = models.ForeignKey(ItemManufacturer,verbose_name='Производитель',on_delete=models.SET_NULL,null=True,blank=True)
    brend = models.ForeignKey(ItemBrend, verbose_name='Бренд',on_delete=models.SET_NULL,null=True,blank=True)
    init_date = models.DateField(verbose_name='Дата инициализации',help_text='Дата появления номенклатуры в ассортименте',default=timezone.now)
    zones = models.ManyToManyField(ItemZones, verbose_name='Доп сегментации',blank=True)
    subcat = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, verbose_name='Подкатегория', null=True, blank=True)
    im_id = models.CharField(max_length=200,verbose_name='im id',null=True,blank=True)
    onec_cat = models.CharField(max_length=200,verbose_name='Группа номенклатуры 1С',null=True,blank=True)
    onec_subcat = models.CharField(max_length=200,verbose_name='Вид номенклатуры 1С',null=True,blank=True)

    
    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатуры"

    
    
    
    def __str__(self):
        return f"{self.fullname}"


class StoreGroups(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование группы')
    region = models.CharField(max_length=250,choices=REGION_CHOICES, default='г. Москва')
    pict = models.ImageField(upload_to='storelogos/', blank=True, null=True,verbose_name='Логотип')
    
    class Meta:
        verbose_name = "Группа магазина"
        verbose_name_plural = "Группы магазинов"

    def __str__(self):
        return f"{self.name}"


class Stores(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование',unique=True,help_text='Как в 1С выгрузке')
    chanel = models.CharField(max_length=100,choices=CHANNEL_CHOICES,default='RETAIL',verbose_name='Канал')
    adress = models.TextField(verbose_name='Адрес',null=True,blank=True)
    gr = models.ForeignKey(StoreGroups,on_delete=models.SET_NULL,null=True,blank=True,verbose_name='Группа магазинов')
   
    
    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"

    def __str__(self):
        return f"{self.name}"
    

class Managers(models.Model):
    name = models.CharField(max_length=250,verbose_name='Имя в 1С',unique=True,help_text='Как в 1С выгрузке')
    report_name = models.CharField(max_length=250,verbose_name='Имя в отчете',unique=True,help_text='Как в отчете показывать',null=True,blank=True)
    tel = models.CharField(max_length=20,verbose_name='Телефон',blank=True,null=True)
    email = models.EmailField('Почта',null=True,blank=True)
    
    class Meta:
        verbose_name = "Менеджер"
        verbose_name_plural = "Менеджеры"

    def __str__(self):
        return f"{self.name}"
    
    def save(self, *args, **kwargs):
        if not self.report_name:  # если пустое
            self.report_name = self.name
        super().save(*args, **kwargs)

class Agents(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование',unique=True,help_text='Как в 1С выгрузке')
    report_name = models.CharField(max_length=250,verbose_name='Имя в отчете',unique=True,help_text='Как в отчете показывать',null=True,blank=True)
    tel = models.CharField(max_length=20,verbose_name='Телефон',blank=True,null=True)
    email = models.EmailField('Почта',null=True,blank=True)
    
    class Meta:
        verbose_name = "Агент"
        verbose_name_plural = "Агенты"

    def __str__(self):
        return f"{self.name}"
    
    def save(self, *args, **kwargs):
        if not self.report_name:  # если пустое
            self.report_name = self.name
        super().save(*args, **kwargs)