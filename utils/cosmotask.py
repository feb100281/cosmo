#This is the script for initial data import 

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import pymysql

config = {
    'user': 'root',       # Имя пользователя MySQL
    'password': '',      # Пароль пользователя MySQL
    'host': '127.0.0.1',  # Хост (локальный)
    'database': 'cosmo',     # Имя базы данных
}

conn = pymysql.connect(**config)
cur = conn.cursor()

# Создание строки подключения для SQLAlchemy
connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}/{config['database']}"

# Создание движка SQLAlchemy
engine = create_engine(connection_string)

#conn = sqlite3.connect('cosmo.db')

files = [
         '/Users/pavelustenko/Downloads/2021.xlsx',
         '/Users/pavelustenko/Downloads/2022.xlsx',
         '/Users/pavelustenko/Downloads/2025.xlsx',
         '/Users/pavelustenko/Downloads/2024 (1).xlsx',
         '/Users/pavelustenko/Downloads/2023 (1).xlsx'         
         ]

stores = ['Фэшн Хаус','РигаМолл','Партнерские продажи','Капитолий Вернадского','Европарк','Гарден Сити','ТВИНСТОР','Интернет-продажи',
          'Передача заказов','Корпоративные продажи','Ривер Хаус', 'Администрация', 
          'ФРЯЗИНО', 'ОФИС', 'Василеостровский','Нахимовский','B2B: Дилерские продажи','B2B: Прочее','РигаМолл 3 этаж']

pattern = '|'.join(stores)  

def make_db():
    combine = pd.DataFrame()
    for file in files:
        df = pd.read_excel(file, skiprows=9, skipfooter=1)
        df = df[df['all'].notna()]
        
        df['parsed_date'] = pd.to_datetime(df['all'], format='%d.%m.%Y', errors='coerce')
        df['date'] = df['parsed_date'].ffill()
        df = df[df['parsed_date'].isna()]
        
        df['store'] = np.where(df['all'].str.contains(pattern, na=False), df['all'], np.nan)
        df['store'] = df['store'].bfill()

        # item — только если это не название магазина
        df['item'] = np.where(df['all'].str.contains(pattern, na=False), np.nan, df['all'])
        df['item'] = df['item'].ffill()

        # 🔥 Оставим только строки, где 'all' ≠ названию магазина
        df = df[~df['all'].isin(stores)]

        # Извлечение артикула
        last_words = df['item'].str.split().str[-1]
        mask = last_words.str.match(r'.*[A-Z\d]$', case=True)
        df['article'] = np.where(mask, last_words, '')
        df['name'] = df.apply(lambda row: row['item'].replace(row['article'], '').strip(), axis=1)

        try:
            df = df[['date','item','name','article','store','quant','amount','amount_undisc',
                     'discount_auto','discount_design','quant_base','wieght_base','volume_base',
                     'discount_amount','discount_percent_auto','discount_percent_design','diccount_percent']]
        except KeyError as e:
            print(f"Ошибка в файле {file}: отсутствует колонка {e}")
            continue

        combine = pd.concat([combine, df], ignore_index=True)

    return combine

def make_dayly():
    combine = pd.DataFrame()
    for file in files:
        df = pd.read_excel(file, skiprows=9, skipfooter=1)
        df = df[df['all'].notna()]
        df['parsed_date'] = pd.to_datetime(df['all'], format='%d.%m.%Y', errors='coerce')
        df = df[df['parsed_date'].notna()] 
        
        df = df[['parsed_date','quant','amount']]     
        
        combine = pd.concat([combine, df], ignore_index=True)
    return combine


df = make_dayly()
df.to_sql('daily_db',if_exists='replace',index=False,con=engine)

df = make_db()
#df.to_excel('norm.xlsx')
df.to_sql('sales_db',if_exists='replace',index=False,con=engine)