import redis
import pickle
import base64
import io
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, _dash_renderer, clientside_callback
import dash_ag_grid as dag
import dash_mantine_components as dmc
import plotly.express as px
from dash_iconify import DashIconify
from asgiref.sync import sync_to_async
import locale


locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
from utils.updater import Updater, set_data

from django.conf import settings

from django.db import connection


r = settings.REDIS_CLIENT

   

def get_data():

    SALES_DOMAIN = pd.read_sql("SELECT * FROM sales_domain order by eom", connection)
    SALES_DOMAIN['client_order_date'] = SALES_DOMAIN['client_order_date'].fillna(SALES_DOMAIN['date'])

    SALES_DOMAIN['date'] = pd.to_datetime(SALES_DOMAIN['date'],errors='coerce').dt.normalize()
    SALES_DOMAIN['client_order_date'] = pd.to_datetime(SALES_DOMAIN['client_order_date'],errors='coerce').dt.normalize()
    SALES_DOMAIN['year'] = SALES_DOMAIN['date'].dt.year
    
    cols_for_non_data = [
    'client_order_number','client_order','warehouse','spec','imname','article',"onec_cat", "onec_subcat",
    'manu','manu_origin','brend','brend_origin','agent','agent_name','manager','manager_name','store_region'    
    ]

    # колонки для аналитики
    a_cols = [
        'store_gr_name',    
        'manager_name',
        'agent_name',
        'fullname',
        'brend',
        'manu',
        
    ]

    d_cols = [
        'dt',
        'cr',
        'quant_dt',
        'quant_cr',
        'amount',
        'quant',
    ]

    # for col in cols_for_non_data:
    #     SALES_DOMAIN[col] = SALES_DOMAIN[col].fillna('Нет данных')



    SALES_DOMAIN['parent_cat'] = SALES_DOMAIN['parent_cat'].fillna('Группа не указана')
    SALES_DOMAIN['cat'] = SALES_DOMAIN['cat'].fillna('Категория не указана')
    SALES_DOMAIN['subcat'] = SALES_DOMAIN['subcat'].fillna('Подкатегория не указана')

    SALES_DOMAIN['fullname'] = SALES_DOMAIN['fullname'].fillna('Номенклатура не указана')  

    # SALES_DOMAIN['subcat_agg'] = SALES_DOMAIN['parent_cat'] + '-' + SALES_DOMAIN['cat'] + SALES_DOMAIN['subcat'] #Для аггрегации по подгатегориям

    SALES_DOMAIN['store'] = SALES_DOMAIN['store'].fillna('Магазин не указан')
    SALES_DOMAIN['store_gr_name'] = SALES_DOMAIN['store_gr_name'].fillna('Магазин не указан')
    SALES_DOMAIN['chanel'] = SALES_DOMAIN['chanel'].fillna('Канал не указан')
    # упорядочиваем на всяк
    SALES_DOMAIN = SALES_DOMAIN.sort_values(by='date')

    # Делаем значения YTD для отмеченных колонок

    for analitics in a_cols:
        for item in d_cols:
            col_name = f"{analitics}_{item}_ytd"
            SALES_DOMAIN[col_name] = (
                SALES_DOMAIN
                .sort_values("eom")  # чтобы cum правильно шел
                .groupby(["year", analitics])[item]
                .cumsum()
            )


    total_memory = str(SALES_DOMAIN.memory_usage(deep=True).sum() / 1024**2) + "MB использует REDIS для всей херни"
    # SALES_DOMAIN.to_csv('data.csv',sep='|',index=False)

    return SALES_DOMAIN, total_memory

def set_data(df):
    SALES_DOMAIN = df
    
    for eom in SALES_DOMAIN["eom"].unique():
        chunk_df = SALES_DOMAIN[SALES_DOMAIN["eom"] == eom]
        for col in chunk_df.columns:
            key = f"mydf:{col}:{eom}"
            # сохраняем как Series
            r.set(key, pickle.dumps(chunk_df[col]))
            print(key + ' saved')
            
            # обновляем мета с доступными чанками
            meta_key = f"mydf:{col}:__chunks__"
            chunks_list = pickle.loads(r.get(meta_key)) if r.exists(meta_key) else []
            if eom not in chunks_list:
                chunks_list.append(eom)
                r.set(meta_key, pickle.dumps(chunks_list))
  

def redis_form_uplaoder():
    # _dash_renderer._set_react_version("18.2.0")
    app = dash.Dash(
        __name__,
        requests_pathname_prefix="/redis-form/",
        external_stylesheets=dmc.styles.ALL,
        suppress_callback_exceptions=True,
    )

    title = dmc.Title("Обновление данных для отчета", order=1, c="blue")

    button = dmc.Button(
        children="Загрузить",
        variant="filled",
        color="#5c7cfa",
        size="sm",
        radius="sm",
        loading=False,
        disabled=False,
        id="btn",
        # other props...
    )
    mem_text = dmc.Text(id='mem_text')

    progress = dmc.Text("Прогресс...", id="progress")

    upload_conteiner = dmc.Container(
        dmc.Stack([title, dcc.Loading([button, progress]),mem_text]), fluid=True
    )

    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme={"colorScheme": "light"},
        children=[upload_conteiner],
    )

    @app.callback(
        Output("progress", "children"),
        Output("mem_text",'children'),
        Input("btn", "n_clicks"),
        
        prevent_initial_call=True,
    )
    def redis_update(nclicks):
        if nclicks > 0:
            r.flushall()
            data, text = get_data()
            set_data(data)
            

        return "Загрузка", text

    return app.server
