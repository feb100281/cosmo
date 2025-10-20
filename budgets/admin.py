from django.contrib import admin
from .models import ForecastTypes, ForecastSubjects, ForecastData, Forecasts
# Register your models here.

admin.site.register(ForecastTypes)
admin.site.register(ForecastSubjects)
admin.site.register(Forecasts)