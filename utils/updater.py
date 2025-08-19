import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import pymysql
from django.conf import settings
from django.db import connection

db_settings = settings.DATABASES["default"]

# Вытаскиваем настройки
user = db_settings["USER"]
password = db_settings["PASSWORD"]
host = db_settings["HOST"] or "127.0.0.1"
database = db_settings["NAME"]

# Подключение для SQLAlchemy
connection_string = f"mysql+pymysql://{user}:{password}@{host}/{database}"

# conn = pymysql.connect(**config)
# cur = conn.cursor()

# # Создание строки подключения для SQLAlchemy
# connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}/{config['database']}"

# Создание движка SQLAlchemy
engine = create_engine(connection_string)

from corporate.models import (
            ItemManufacturer, 
            Stores,
            Items,
            Agents,
            Managers,
            ItemBrend,
            ItemCollections
        )

# Деляем класс updater

FILE_COLUMNS = {
    "Дата документа":'date',    
    "Заказ клиента":'client_order',
    "Номер Заказа клиента":'client_order_number',
    "Дата Заказа клиента":'client_order_date',
    "Менеджер":'manager',
    "Подразделение":'store_name',
    "Агент":'agent',
    "Склад":'warehouse',
    "Группа номенклатуры":'item_cat',
    "Вид номенклатуры":'cat_type',
    "Артикул":'article',
    "Производитель ":'manufacturer',
    "ID товара":'im_id_item',
    "Номенклатура":'fullname',
    "Название товара на сайте":'im_name',
    "Характеристика":'characterictic',
    "Количество":'quant',
    "Выручка":'amount',
    "Номенклатура.Коллекция (Прочие товары с характеристиками)":'collection',
    "Номенклатура.Производитель":'brend'
}


def set_data(d:dict):
    # if not d:
    #     return
    
    sucsess_list = []
    
    for k, v in d.items():
        if k == 'ItemManufacturer':
            objs = [ItemManufacturer(name=n) for n in v]
            sucsess_list.append('Данные по новым производителям успешно загружены')
            ItemManufacturer.objects.bulk_create(
                objs,
                ignore_conflicts=True  # <--- главное
            ) 
        elif k == 'Agents':
            objs = [Agents(name=n, report_name=n) for n in v]
            sucsess_list.append('Данные по новым агентам успешно загружены')
            Agents.objects.bulk_create(
                objs,
                ignore_conflicts=True  # <--- главное
            ) 
        elif k == 'Managers':
            objs = [Managers(name=n, report_name=n) for n in v]
            sucsess_list.append('Данные по новым менеджерам успешно загружены')
            Managers.objects.bulk_create(
                objs,
                ignore_conflicts=True  # <--- главное
            ) 
        elif k == 'Stores':
            objs = [Stores(name=n, chanel='RETAIL') for n in v]
            sucsess_list.append('Данные по новым магазинам успешно загружены')
            Stores.objects.bulk_create(
                objs,
                ignore_conflicts=True  # <--- главное
            )
        elif k == 'ItemBrend':
            objs = [ItemBrend(name=n, country='RU') for n in v]
            sucsess_list.append('Данные по новым брендам успешно загружены')
            ItemBrend.objects.bulk_create(
                objs,
                ignore_conflicts=True  # <--- главное
            ) 
        elif k == 'ItemCollections':
            objs = [ItemCollections(name=n) for n in v]
            sucsess_list.append('Данные по новым колеекциям успешно загружены')
            ItemCollections.objects.bulk_create(
                objs,
                ignore_conflicts=True  # <--- главное
            ) 
        
    
    df = pd.read_sql("SELECT * FROM new_sales", con=engine)
    df['client_order_date'] = pd.to_datetime(df['client_order_date'])
    df = df.sort_values(by='client_order_date')
    
    df = df.pivot_table(
        index = 'fullname',
        values= ['client_order_date','article','manufacturer','brend','im_id_item','im_name',"collection","item_cat","cat_type"],
        aggfunc={
            'client_order_date':'min',
            'article':'last',
            'manufacturer':'last',
            'brend':'last',
            'im_id_item':'last',
            'im_name':'last',
            "collection":'last',
            "item_cat":'last',
            "cat_type":'last'            
        }
        
    ).reset_index()
    
    
    expected_cols = [
        'article', 'manufacturer', 'brend', 'im_id_item',
        'im_name', 'collection', 'item_cat', 'cat_type'
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    
    df.to_sql('temp_sales',index=False,con=engine,if_exists='replace')
    del df

    q = """
    SELECT  
        t.fullname,
        t.article,
        b.id as brend_id,
        t.client_order_date as init_date,
        c.id as itemcollections_id,
        t.im_id_item,
        COALESCE(t.im_name, t.fullname) AS im_name,
        m.id as manufacturer_id,
        t.item_cat as onec_cat,
        t.cat_type as onec_subcat
        FROM temp_sales as t
        left join corporate_itembrend as b on b.name = t.brend
        left join corporate_itemcollections as c on c.name = t.collection
        left join corporate_itemmanufacturer as m on m.name = t.manufacturer        
    """
    df = pd.read_sql(q,con=engine)
    df.to_sql('temp_sales',index=False,con=engine,if_exists='replace')
    del df
    
    q_insert = """
            INSERT INTO corporate_items (
            fullname,
            name,
            article,
            init_date,
            brend_id,
            manufacturer_id,
            im_id,
            onec_cat,
            onec_subcat
        )
        SELECT
            fullname,
            im_name AS name,
            article,
            init_date AS init_date,
            brend_id,
            manufacturer_id,
            im_id_item AS im_id,
            onec_cat,
            onec_subcat
        FROM temp_sales
        AS src
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            article = VALUES(article),
            brend_id = VALUES(brend_id),
            manufacturer_id = VALUES(manufacturer_id),
            im_id = VALUES(im_id),
            onec_cat = VALUES(onec_cat),
            onec_subcat = VALUES(onec_subcat);
    """
    
    try:
    
        with connection.cursor() as cursor:
            cursor.execute(q_insert)
        sucsess_list.append('Новые наменклатуры загружены в базу данных')
    
    except Exception as e:
        sucsess_list.append(f'{e} Ошибка')
    
    q_collection = """
    select distinct  i.id as item_id, itemcollections_id as itemcollections_id  from temp_sales as t
    left join corporate_items as i on i.fullname = t.fullname
    where itemcollections_id is not null    
    """
    df = pd.read_sql(q_collection,con=engine)
    df.to_sql('temp_sales',index=False,con=engine,if_exists='replace')
    del df
    
    q_m2m_insert = """
    INSERT IGNORE INTO corporate_items_collection (items_id, itemcollections_id)
    SELECT item_id, itemcollections_id
    FROM temp_sales;
    """
    
    try:
    
        with connection.cursor() as cursor:
            cursor.execute(q_m2m_insert)
        sucsess_list.append('Kолекции обновлены')
    
    except Exception as e:
        sucsess_list.append(f'{e} Ошибка')
    
    q_new_sales = """
    SELECT 
        date,
        case when amount > 0 then 'Sales' else 'Return' end as operation,
        case when amount > 0 then amount end as dt,
        case when amount < 0 then abs(amount) end as cr,
        case when amount > 0 then quant end as quant_dt,
        case when amount < 0 then abs(quant) end as quant_cr,
        i.id as item_id,
        s.id as store_id,
        a.id as agent_id,
        client_order as client_order,
        client_order_date as client_order_date,
        client_order_number as client_order_number,
        m.id as manager_id,
        warehouse,
        characterictic as spec
        FROM new_sales
        left join corporate_items as i on i.fullname = new_sales.fullname
        left join corporate_stores as s on s.name = new_sales.store_name
        left join corporate_agents as a on a.name = new_sales.agent
        left join corporate_managers as m on m.name = new_sales.manager
    
    """
    df = pd.read_sql(q_new_sales,con=engine)
    df['dt'] = df['dt'].fillna(0.0)
    df['cr'] = df['cr'].fillna(0.0)
    df['quant_dt'] = df['quant_dt'].fillna(0.0)
    df['quant_cr'] = df['quant_cr'].fillna(0.0)
    
    max_date = pd.to_datetime(df['date'].max()).strftime('%Y-%m-%d')
    min_date = pd.to_datetime(df['date'].min()).strftime('%Y-%m-%d')
    
    df.to_sql('new_sales',index=False,con=engine,if_exists='replace')
    del df
    
    delete_sql = """
    DELETE FROM sales_salesdata
    WHERE date BETWEEN %s AND %s
    """
    with connection.cursor() as cursor:
        cursor.execute(delete_sql, [min_date, max_date])
        
    
    insert_sales = """
    insert into sales_salesdata(
        date,
        operation,
        dt,
        cr,
        quant_dt,
        quant_cr,
        item_id,
        store_id,
        agent_id,
        client_order,
        client_order_date,
        client_order_number,
        manager_id,
        warehouse,
        spec
        )
        SELECT
        date,
        operation,
        dt,
        cr,
        quant_dt,
        quant_cr,
        item_id,
        store_id,
        agent_id,
        client_order,
        client_order_date,
        client_order_number,
        manager_id,
        warehouse,
        spec
        FROM new_sales       
    """
    
    try:
    
        with connection.cursor() as cursor:
            cursor.execute(insert_sales)
        sucsess_list.append('Продажи обновлены')
    
    except Exception as e:
        sucsess_list.append(f'{e} Ошибка')
    
    
    return sucsess_list



class Updater:
    def __init__(self, file_obj):
        """
        file_obj: BytesIO (загруженный файл)
        """
        self.file = file_obj
        self.log = {}
        self.new_manufactures = []
        self.new_stores = []
        self.new_itemes = []
        self.new_managers = []
        self.new_agents = []
        self.new_brends = []
        self.new_collection = []
        
        
        

    def get_data(self):
        df = pd.read_excel(self.file, skiprows=3, skipfooter=1)
        
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
        df = df.rename(columns=FILE_COLUMNS)
        df["fullname"] = df.fullname.str.strip()
        df['store_name'] = df['store_name'].str.strip()
        df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
        df["client_order_date"] = pd.to_datetime(df["client_order_date"], format="%d.%m.%Y")           
        df.to_sql(name='new_sales',con=engine,if_exists='replace')
        #df.to_sql(name='new_sales_to_drop',con=engine,if_exists='replace')
        
        
        min_date = pd.to_datetime(df['date'].min())
        max_date = pd.to_datetime(df['date'].max())
        self.log['Период'] = f'C {min_date.strftime('%d %B %Y')} по {max_date.strftime('%d %B %Y')} '
        self.log["Всего записей"] = len(df.index)
        self.log["Всего заказов"] = df["client_order"].nunique()
        
        manufacturer_list = df['manufacturer'].dropna().unique()
        existant_manufacturer_list = set(ItemManufacturer.objects.values_list("name", flat=True)        )
        new_manufacturers = [m for m in manufacturer_list if m not in existant_manufacturer_list]
        if len(new_manufacturers) > 0:
            self.log["Новые производители"] = len(new_manufacturers)        
        self.new_manufactures = new_manufacturers
        
        store_list = df['store_name'].dropna().unique()
        existing_stores = set(Stores.objects.values_list("name", flat=True))
        new_stores = [s for s in store_list if s not in existing_stores]
        if len(new_stores) > 0:
            self.log["Новые подразделения"] = len(new_stores)    
        self.new_stores = new_stores
        
        items_list = df['fullname'].dropna().unique()
        existing_items = set(Items.objects.values_list('fullname',flat=True))
        new_items = [i for i in items_list if i not in existing_items]        
        if len(new_items) > 0:
            self.log["Новые номенклатуры"] = len(new_items) 
        self.new_itemes = new_items
        
        managers_list = df['manager'].dropna().unique()
        existing_managers = set(Managers.objects.values_list('name',flat=True))
        new_managers = [i for i in managers_list if i not in existing_managers]
        if len(new_managers) > 0:
            self.log["Новые менеджеры"] = len(new_managers) 
        self.new_managers = new_managers
        
        agents_list = df['agent'].dropna().unique()
        existing_agents = set(Agents.objects.values_list('name',flat=True))
        new_agents = [i for i in agents_list if i not in existing_agents]
        if len(new_agents) > 0:
            self.log["Новые агенты"] = len(new_agents) 
        self.new_agents = new_agents
        

        brend_list = df['brend'].dropna().unique()
        existing_brends = set(ItemBrend.objects.values_list('name',flat=True))
        new_brend = [i for i in brend_list if i not in existing_brends]
        if len(new_brend) > 0:
            self.log["Новые бренды"] = len(new_brend) 
        self.new_brends = new_brend
        
        collection_list = df['collection'].dropna().unique()
        existing_collection = set(ItemCollections.objects.values_list('name',flat=True))
        new_collection = [i for i in collection_list if i not in existing_collection]
        if len(new_collection) > 0:
            self.log["Новые колеекции"] = len(new_collection) 
        self.new_collection = new_collection
        
        
        
        
        return df

    
            
        


# file = "/Users/pavelustenko/Downloads/Sales (5).xlsx"

# t = Updater(file)
# df = t.get_data()

# print(t.new_stores)


# df.to_sql(name='new_sales',con=engine,if_exists='replace')