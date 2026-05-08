# corporate/reports/assouline/forms.py
from django import forms

class AssoulineCatalogForm(forms.Form):
    catalog_file = forms.FileField(
        label="Файл каталога ASSOULINE (.xlsx)",
        help_text="Загрузите файл ASSOULINE Spring 2026 Form",
        widget=forms.FileInput(attrs={'accept': '.xlsx', 'class': 'vTextField'})
    )
    
    REGION_CHOICES = [
        ('EMEA', 'EMEA (EUROPE, MIDDLE EAST, AFRICA)'),
        ('Americas & Caribbean', 'Americas & Caribbean'),
    ]
    region = forms.ChoiceField(
        choices=REGION_CHOICES,
        initial='EMEA',
        label="Регион поставки",
        help_text="Выберите ваш регион для расчета доступности",
        widget=forms.Select(attrs={'class': 'vTextField'})
    )
    
    start_year = forms.IntegerField(
        initial=2022,
        label="Начальный год анализа",
        help_text="С какого года анализировать продажи",
        widget=forms.NumberInput(attrs={'class': 'vTextField'})
    )