# export_sales_to_redis.py
import os
import sys

# Добавляем путь к корню проекта, где лежит manage.py
sys.path.append("/Users/pavelustenko/fr")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fr.settings")

import django
django.setup()
import django
import pickle
import redis
import pandas as pd
import numpy as np
from django.db import connection


# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fr.settings")  # замените на свой проект
django.setup()

from sales.models import SalesData  # замените на ваше приложение
from django.conf import settings

# Redis клиент из settings.py
r = settings.REDIS_CLIENT

r.flushall()

def load_sales_with_related_to_df():    
    with connection.cursor() as cursor:
        df = pd.read_sql("SELECT * FROM sales_summary", connection)
    return df

def save_df_to_redis(df:pd.DataFrame, key="sales_data"):
    df['date'] = pd.to_datetime(df['date'])
    pickled = pickle.dumps(df)
    r.set(key, pickled)
    last_date = df['date'].max()      
    first_date = df['date'].min() 
   
    r.set('last_date', last_date.strftime('%Y-%m-%d'))
    r.set('first_date', first_date.strftime('%Y-%m-%d'))
    
    print(f"Сохранено {len(df)} строк под ключом '{key}' в Redis.")


if __name__ == "__main__":
    df = load_sales_with_related_to_df()
    save_df_to_redis(df, key="sales_data")
    
