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



def redis_form_uplaoder():
    #_dash_renderer._set_react_version("18.2.0")
    app = dash.Dash(
        __name__,
        requests_pathname_prefix="/redis-form/",
        external_stylesheets=dmc.styles.ALL,
        suppress_callback_exceptions=True,
    )
    
    def load_sales_with_related_to_df():    
        with connection.cursor() as cursor:
            df = pd.read_sql("SELECT * FROM sales_summary", connection)
        return df
    
    def load_sales_domain():    
        with connection.cursor() as cursor:
            df = pd.read_sql("SELECT * FROM sales_domain", connection)
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
    

    def save_sales_domain(df:pd.DataFrame,key='sales_domain'):
        df['date'] = pd.to_datetime(df['date'])
        df['eom'] = pd.to_datetime(df['eom'])
        pickled = pickle.dumps(df)
        r.set(key, pickled)
    
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
    
    progress = dmc.Text('Прогресс...',id='progress')

    upload_conteiner = dmc.Container(
        dmc.Stack([title, dcc.Loading([button,progress])]), fluid=True
    )

    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme={"colorScheme": "light"},
        children=[upload_conteiner]
    )
    
    @app.callback(        
        Output("progress", "children"),
        Input('btn','n_clicks'),
        # State('new_manu','data'),
        # State('new_items','data'),
        # State('new_agents','data'),
        # State('new_stores','data'),
        # State('new_managers','data'),
        # State('new_brends','data'),
        # State('new_collection','data'),
        prevent_initial_call=True          
    )
    def redis_update(nclicks):
        if nclicks > 0:
            save_df_to_redis(load_sales_with_related_to_df())
            save_sales_domain(load_sales_domain())
        
        return 'Загрузка'
            
    return app.server
    



