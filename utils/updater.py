# utils/updater.py
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import pymysql
from django.conf import settings
from django.db import connection
from django.db import transaction

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
    "Производитель":'manufacturer',
    "ID товара":'im_id_item',
    "Номенклатура":'fullname',
    "Название товара на сайте":'im_name',
    "Характеристика":'characterictic',
    "Количество":'quant',
    "Выручка":'amount',
    "Коллекция":'collection',
    "Марка (бренд)":'brend',
    "Штрихкод":"barcode"
}


def normalize_text(value):
    if pd.isna(value):
        return None
    return " ".join(str(value).replace("\xa0", " ").strip().split())


def set_data(d:dict):
    # if not d:
    #     return
    print(d)
    sucsess_list = []
    from corporate.models import (
            ItemManufacturer, 
            Stores,
            Items,
            Agents,
            Managers,
            ItemBrend,
            ItemCollections,
            Barcode
        )

    
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
    df['client_order_date'] = df['client_order_date'].fillna('date')
    df['client_order_date'] = pd.to_datetime(df['client_order_date'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    # df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='client_order_date')
    
    
    df = df.pivot_table(
        index = 'fullname',
        values= ['date','article','manufacturer','brend','im_id_item','im_name',"collection","item_cat","cat_type"],
        aggfunc={
            'date':'min',
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
    df.to_sql('_temp_sales',index=False,con=engine,if_exists='replace')
    del df

    q = """
    SELECT  
        t.fullname,
        t.article,
        b.id as brend_id,
        t.date as init_date,
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
    df.to_sql('temp_sales_check',index=False,con=engine,if_exists='replace')
    
    del df
    
    # q_insert = """
    #         INSERT INTO corporate_items (
    #         fullname,
    #         name,
    #         article,
    #         init_date,
    #         brend_id,
    #         manufacturer_id,
    #         im_id,
    #         onec_cat,
    #         onec_subcat
    #     )
    #     SELECT
    #         fullname,
    #         im_name AS name,
    #         article,
    #         init_date AS init_date,
    #         brend_id,
    #         manufacturer_id,
    #         im_id_item AS im_id,
    #         onec_cat,
    #         onec_subcat
    #     FROM temp_sales
    #     AS src
    #     ON DUPLICATE KEY UPDATE
    #         name = VALUES(name),
    #         article = VALUES(article),
    #         brend_id = VALUES(brend_id),
    #         manufacturer_id = VALUES(manufacturer_id),
    #         im_id = VALUES(im_id),
    #         onec_cat = VALUES(onec_cat),
    #         onec_subcat = VALUES(onec_subcat);
    # """
    
    
    
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
            src.fullname,
            src.im_name AS name,
            src.article,
            src.init_date,
            src.brend_id,
            src.manufacturer_id,
            src.im_id_item AS im_id,
            src.onec_cat,
            src.onec_subcat
        FROM temp_sales AS src
        LEFT JOIN corporate_items AS ci
            ON ci.fullname = src.fullname
        WHERE ci.id IS NULL;
    """
    
    
    
    q_update_existing = """
        UPDATE corporate_items AS ci
        JOIN temp_sales AS src
            ON ci.fullname = src.fullname
        SET
            ci.name = CASE
                WHEN (ci.name IS NULL OR ci.name = '') AND src.im_name IS NOT NULL AND src.im_name <> ''
                THEN src.im_name
                ELSE ci.name
            END,
            ci.article = CASE
                WHEN (ci.article IS NULL OR ci.article = '') AND src.article IS NOT NULL AND src.article <> ''
                THEN src.article
                ELSE ci.article
            END,
            ci.brend_id = CASE
                WHEN ci.brend_id IS NULL AND src.brend_id IS NOT NULL
                THEN src.brend_id
                ELSE ci.brend_id
            END,
            ci.manufacturer_id = CASE
                WHEN ci.manufacturer_id IS NULL AND src.manufacturer_id IS NOT NULL
                THEN src.manufacturer_id
                ELSE ci.manufacturer_id
            END,
            ci.im_id = CASE
                WHEN ci.im_id IS NULL AND src.im_id_item IS NOT NULL
                THEN src.im_id_item
                ELSE ci.im_id
            END,
            ci.onec_cat = CASE
                WHEN (ci.onec_cat IS NULL OR ci.onec_cat = '') AND src.onec_cat IS NOT NULL AND src.onec_cat <> ''
                THEN src.onec_cat
                ELSE ci.onec_cat
            END,
            ci.onec_subcat = CASE
                WHEN (ci.onec_subcat IS NULL OR ci.onec_subcat = '') AND src.onec_subcat IS NOT NULL AND src.onec_subcat <> ''
                THEN src.onec_subcat
                ELSE ci.onec_subcat
            END;
    """


    # try:
    
    #     with connection.cursor() as cursor:
    #         cursor.execute(q_insert)
    #     sucsess_list.append('Новые наменклатуры загружены в базу данных')
    
    # except Exception as e:
    #     sucsess_list.append(f'{e} Ошибка')
    
    
    # try:
    #     with transaction.atomic():
    #         with connection.cursor() as cursor:
    #             cursor.execute(q_insert)
    #     sucsess_list.append('Новые номенклатуры загружены в базу данных')

    # except Exception as e:
    #     sucsess_list.append(f'{e} Ошибка')
    
    
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(q_insert)
                cursor.execute(q_update_existing)
        sucsess_list.append('Номенклатуры загружены и обновлены')

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
    def update_barcode():
        q = """
        INSERT IGNORE INTO corporate_barcode (barcode)
        SELECT DISTINCT barcode
        FROM djangodb._new_sales
        WHERE barcode IS NOT NULL;       
        
        """
        with connection.cursor() as cursor:
            cursor.execute(q)
        
        q_mtm = """
        INSERT IGNORE INTO corporate_items_barcode (items_id, barcode_id)
        SELECT 
            i.id AS items_id,
            b.id AS barcode_id
        FROM _new_sales AS t
        JOIN corporate_items AS i ON i.fullname = t.fullname
        JOIN corporate_barcode AS b ON b.barcode = t.barcode;
        
        """
        with connection.cursor() as cursor:
            cursor.execute(q_mtm)
            
        return 'all good'
    
    update_barcode()
    
    
    
    try:
        with transaction.atomic():
    
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
        b.id as barcode_id,
        characterictic as spec
        FROM new_sales
        left join corporate_items as i on i.fullname = new_sales.fullname
        left join corporate_stores as s on s.name = new_sales.store_name
        left join corporate_agents as a on a.name = new_sales.agent
        left join corporate_managers as m on m.name = new_sales.manager
        left join corporate_barcode as b on b.barcode = new_sales.barcode
        
    
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
        barcode_id,
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
        barcode_id,
        spec
        FROM new_sales       
    """
    
    try:
        with transaction.atomic():
    
            with connection.cursor() as cursor:
                cursor.execute(insert_sales)
            sucsess_list.append('Продажи обновлены')
    
    except Exception as e:
        sucsess_list.append(f'{e} Ошибка')
    
    
    def update_mv_orders():
        q = """
        CREATE TABLE IF NOT EXISTS mv_orders
    SELECT
	x.orders_id,
	ord.client_order_type,
	ord.client_order,
    ord.client_order_number,
	ord.client_order_date,    
	min(x.date) as order_min_date,
	max(x.date) as order_max_date,
	DATEDIFF(MAX(x.date), MIN(x.date)) + 1 AS realization_duration,
	DATEDIFF(MAX(x.date),ord.client_order_date) + 1 AS order_duration,
	sum(x.dt) as sales,
	sum(x.cr) as returns,
	sum(x.dt-x.cr) as amount,
	sum(case when parent_id != 86 then x.dt-x.cr else 0 end) as items_amount,
	sum(case when parent_id = 86 then x.dt-x.cr else 0 end) as service_amount,
	sum(case when parent_id != 86 then x.quant_dt-x.quant_cr else 0 end) as items_quant,
	count(distinct(case when parent_id != 86 then x.fullname  else NULL end)) as unique_items,
	GROUP_CONCAT(DISTINCT manager_name ORDER BY manager_name SEPARATOR ', ') as manager_name
	FROM (
	SELECT  
	d.orders_id,
	d.date,
	i.fullname,
	cat.parent_id,
	coalesce(i.article,'нет артикля') as article,
	coalesce(b.barcode,'нет баркода') as barcode,
	d.dt,
	d.cr,
	d.quant_dt,
	d.quant_cr,
	coalesce(mn.name, 'Менеджер не указан') as manager_name,
	coalesce(a.name,'Нет агента') as agent_name,
	coalesce(d.warehouse,'Склад не указан') as warehouse,
	coalesce(sg.name,'') as store_group,
	d.spec
	FROM sales_salesdata d
	LEFT JOIN corporate_items as i on d.item_id = i.id
	LEFT JOIN corporate_cattree as cat on cat.id = i.cat_id
	LEFT JOIN corporate_barcode as b on d.barcode_id = b.id
	LEFT JOIN corporate_managers as mn on d.manager_id = mn.id
	LEFT JOIN corporate_agents as a on a.id = d.agent_id
	LEFT JOIN corporate_stores as store on store.id = d.store_id
	LEFT JOIN corporate_storegroups as sg on sg.id = store.gr_id
	) x
	join sales_salesorders as ord on ord.id = x.orders_id
	group by x.orders_id
	order by ord.client_order_date desc;  
        
        """
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS mv_orders")
            cursor.execute(q)
            cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_manager (manager_name(100));")
            cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_date (client_order_date);")
            cursor.execute("ALTER TABLE mv_orders ADD INDEX idx_mv_orders_order_date (client_order, client_order_date);")
            
        return 'all good'
        
        
        
    def update_salesorders():
        
        q_update_salesorders = """
        INSERT IGNORE INTO sales_salesorders
        (client_order, client_order_date, client_order_number, client_order_type)
        SELECT DISTINCT
        client_order,
        client_order_date,
        client_order_number,

        CASE
            WHEN client_order_number RLIKE '^(Реализация товаров и услуг|Возврат товаров от клиента)'
            THEN 'Продажи без заказа'
            WHEN client_order_number RLIKE '^Отчет комиссионера \\(агента\\) о продажах'
            THEN 'Комиссионные продажи'
            WHEN client_order_number RLIKE '^(Отчет о розничных возвратах|Отчет о розничных продажах)'
            THEN 'Розничные продажи'
            ELSE 'Заказ клиента'
        END AS client_order_type
        FROM sales_salesdata
        WHERE client_order IS NOT NULL
        AND client_order_number IS NOT NULL;  
        """
        
        q_update_relations = """
        UPDATE sales_salesdata AS t
            JOIN sales_salesorders AS s
            ON t.client_order <=> s.client_order
            AND t.client_order_date <=> s.client_order_date
            AND t.client_order_number <=> s.client_order_number
            SET t.orders_id = s.id;
        
        """
        
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE sales_salesorders;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            cursor.execute(q_update_salesorders)
            cursor.execute(q_update_relations)
            
        return 'all good'
        
        
        
        
    def update_sales_with_client_orders():
        q = """
        UPDATE sales_salesdata
            SET
            client_order = CASE
                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Реализация товаров и услуг'
                THEN TRIM(REPLACE(client_order_number, 'Реализация товаров и услуг', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Возврат товаров от клиента'
                THEN TRIM(REPLACE(client_order_number, 'Возврат товаров от клиента', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Отчет комиссионера \\(агента\\) о продажах'
                THEN TRIM(REPLACE(client_order_number, 'Отчет комиссионера (агента) о продажах', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Отчет о розничных возвратах'
                THEN TRIM(REPLACE(client_order_number, 'Отчет о розничных возвратах', ''))

                WHEN (client_order IS NULL OR client_order = '<Продажи без заказа>')
                    AND client_order_number RLIKE '^Отчет о розничных продажах'
                THEN TRIM(REPLACE(client_order_number, 'Отчет о розничных продажах', ''))

                ELSE client_order
            END,

            client_order_date = CASE
                WHEN client_order_date IS NULL THEN
                DATE(
                    STR_TO_DATE(
                    SUBSTRING_INDEX(client_order_number, 'от ', -1),
                    '%d.%m.%Y %H:%i:%s'
                    )
                )
                ELSE client_order_date
            END
            WHERE client_order_number IS NOT NULL
            AND (
                client_order IS NULL OR client_order = '<Продажи без заказа>'
                OR client_order_date IS NULL
            );
        """
        with connection.cursor() as cursor:
            cursor.execute(q)
            return 'all good'
    
    
    def refresh_mv_daily_sales():
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS mv_daily_sales")
            cursor.execute("""
                CREATE TABLE mv_daily_sales AS
                SELECT * FROM daily_sales
            """)
            cursor.execute("""
                ALTER TABLE mv_daily_sales
                ADD UNIQUE KEY ux_mv_daily_sales_date (`date`)
            """)
        
    refresh_mv_daily_sales()
    update_sales_with_client_orders()
    update_salesorders()
    update_mv_orders()
    
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
        from corporate.models import (
            ItemManufacturer, 
            Stores,
            Items,
            Agents,
            Managers,
            ItemBrend,
            ItemCollections,
            Barcode
        )

        df = pd.read_excel(self.file, skiprows=0, skipfooter=1)
        
        
        mask = df.columns.astype(str).str.startswith("Unnamed")
        df = df.loc[:, ~mask]
                
        df['Номер Заказа клиента'] = df['Номер Заказа клиента'].fillna(df['Регистратор'])
        df.drop(columns=['Регистратор'], inplace=True)
        
        
        # df = df.rename(columns=FILE_COLUMNS)
        
        # df["fullname"] = df.fullname.str.strip()
        # df['store_name'] = df['store_name'].str.strip()
        # df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
        # df["client_order_date"] = pd.to_datetime(df["client_order_date"], format="%d.%m.%Y")   
        
        
        
        df = df.rename(columns=FILE_COLUMNS)

        df["fullname"] = df["fullname"].apply(normalize_text)
        df["store_name"] = df["store_name"].apply(normalize_text)

        if "manufacturer" in df.columns:
            df["manufacturer"] = df["manufacturer"].apply(normalize_text)
        if "manager" in df.columns:
            df["manager"] = df["manager"].apply(normalize_text)
        if "agent" in df.columns:
            df["agent"] = df["agent"].apply(normalize_text)
        if "brend" in df.columns:
            df["brend"] = df["brend"].apply(normalize_text)
        if "collection" in df.columns:
            df["collection"] = df["collection"].apply(normalize_text)

        df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y", errors="coerce")
        df["client_order_date"] = pd.to_datetime(df["client_order_date"], format="%d.%m.%Y", errors="coerce")
        
        df.to_sql(name='new_sales',con=engine,if_exists='replace')
        df.to_sql(name='_new_sales',con=engine,if_exists='replace')
        
        
        min_date = pd.to_datetime(df['date'].min())
        max_date = pd.to_datetime(df['date'].max())
        self.log['Период'] = f"C {min_date.strftime('%d %B %Y')} по {max_date.strftime('%d %B %Y')}"
        self.log["Всего записей"] = len(df.index)
        self.log["Всего заказов"] = df["client_order"].nunique()
        
        # manufacturer_list = df['manufacturer'].dropna().unique()
        # existant_manufacturer_list = set(ItemManufacturer.objects.values_list("name", flat=True)        )
        # new_manufacturers = [m for m in manufacturer_list if m not in existant_manufacturer_list]
        # if len(new_manufacturers) > 0:
        #     self.log["Новые производители"] = len(new_manufacturers)        
        # self.new_manufactures = new_manufacturers
        
        # store_list = df['store_name'].dropna().unique()
        # existing_stores = set(Stores.objects.values_list("name", flat=True))
        # new_stores = [s for s in store_list if s not in existing_stores]
        # if len(new_stores) > 0:
        #     self.log["Новые подразделения"] = len(new_stores)    
        # self.new_stores = new_stores
        
        # # items_list = df['fullname'].dropna().unique()
        # # existing_items = set(Items.objects.values_list('fullname',flat=True))
        # # new_items = [i for i in items_list if i not in existing_items]        
        # # if len(new_items) > 0:
        # #     self.log["Новые номенклатуры"] = len(new_items) 
        # # self.new_itemes = new_items
        
        
        
        # items_list = [x for x in df["fullname"].dropna().unique() if x]

        # existing_items = {
        #     normalize_text(x)
        #     for x in Items.objects.values_list("fullname", flat=True)
        #     if x is not None
        # }

        # new_items = [i for i in items_list if normalize_text(i) not in existing_items]

        # if len(new_items) > 0:
        #     self.log["Новые номенклатуры"] = len(new_items)

        # self.new_itemes = new_items
        
        # managers_list = df['manager'].dropna().unique()
        # existing_managers = set(Managers.objects.values_list('name',flat=True))
        # new_managers = [i for i in managers_list if i not in existing_managers]
        # if len(new_managers) > 0:
        #     self.log["Новые менеджеры"] = len(new_managers) 
        # self.new_managers = new_managers
        
        # agents_list = df['agent'].dropna().unique()
        # existing_agents = set(Agents.objects.values_list('name',flat=True))
        # new_agents = [i for i in agents_list if i not in existing_agents]
        # if len(new_agents) > 0:
        #     self.log["Новые агенты"] = len(new_agents) 
        # self.new_agents = new_agents
        

        # brend_list = df['brend'].dropna().unique()
        # existing_brends = set(ItemBrend.objects.values_list('name',flat=True))
        # new_brend = [i for i in brend_list if i not in existing_brends]
        # if len(new_brend) > 0:
        #     self.log["Новые бренды"] = len(new_brend) 
        # self.new_brends = new_brend
        
        # collection_list = df['collection'].dropna().unique()
        # existing_collection = set(ItemCollections.objects.values_list('name',flat=True))
        # new_collection = [i for i in collection_list if i not in existing_collection]
        # if len(new_collection) > 0:
        #     self.log["Новые колеекции"] = len(new_collection) 
        # self.new_collection = new_collection
        
        
        
        
        manufacturer_list = [x for x in df["manufacturer"].dropna().unique() if x]

        existant_manufacturer_list = {
            normalize_text(x)
            for x in ItemManufacturer.objects.values_list("name", flat=True)
            if x is not None
        }

        new_manufacturers = [
            m for m in manufacturer_list
            if normalize_text(m) not in existant_manufacturer_list
        ]

        if len(new_manufacturers) > 0:
            self.log["Новые производители"] = len(new_manufacturers)

        self.new_manufactures = new_manufacturers


        store_list = [x for x in df["store_name"].dropna().unique() if x]

        existing_stores = {
            normalize_text(x)
            for x in Stores.objects.values_list("name", flat=True)
            if x is not None
        }

        new_stores = [
            s for s in store_list
            if normalize_text(s) not in existing_stores
        ]

        if len(new_stores) > 0:
            self.log["Новые подразделения"] = len(new_stores)

        self.new_stores = new_stores


        items_list = [x for x in df["fullname"].dropna().unique() if x]

        existing_items = {
            normalize_text(x)
            for x in Items.objects.values_list("fullname", flat=True)
            if x is not None
        }

        new_items = [i for i in items_list if normalize_text(i) not in existing_items]

        if len(new_items) > 0:
            self.log["Новые номенклатуры"] = len(new_items)

        self.new_itemes = new_items


        managers_list = [x for x in df["manager"].dropna().unique() if x]

        existing_managers = {
            normalize_text(x)
            for x in Managers.objects.values_list("name", flat=True)
            if x is not None
        }

        new_managers = [
            i for i in managers_list
            if normalize_text(i) not in existing_managers
        ]

        if len(new_managers) > 0:
            self.log["Новые менеджеры"] = len(new_managers)

        self.new_managers = new_managers


        agents_list = [x for x in df["agent"].dropna().unique() if x]

        existing_agents = {
            normalize_text(x)
            for x in Agents.objects.values_list("name", flat=True)
            if x is not None
        }

        new_agents = [
            i for i in agents_list
            if normalize_text(i) not in existing_agents
        ]

        if len(new_agents) > 0:
            self.log["Новые агенты"] = len(new_agents)

        self.new_agents = new_agents


        brend_list = [x for x in df["brend"].dropna().unique() if x]

        existing_brends = {
            normalize_text(x)
            for x in ItemBrend.objects.values_list("name", flat=True)
            if x is not None
        }

        new_brend = [
            i for i in brend_list
            if normalize_text(i) not in existing_brends
        ]

        if len(new_brend) > 0:
            self.log["Новые бренды"] = len(new_brend)

        self.new_brends = new_brend


        collection_list = [x for x in df["collection"].dropna().unique() if x]

        existing_collection = {
            normalize_text(x)
            for x in ItemCollections.objects.values_list("name", flat=True)
            if x is not None
        }

        new_collection = [
            i for i in collection_list
            if normalize_text(i) not in existing_collection
        ]

        if len(new_collection) > 0:
            self.log["Новые колеекции"] = len(new_collection)

        self.new_collection = new_collection
        
        
        
        
        
        
        return df

    
            
        


# file = "/Users/pavelustenko/Downloads/Sales (5).xlsx"

# t = Updater(file)
# df = t.get_data()

# print(t.new_stores)


# df.to_sql(name='new_sales',con=engine,if_exists='replace')