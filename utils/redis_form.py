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


KEYS_LIST = [b"sales_dynamix_monthly", b"first_date", b"last_date", b"sales_data"]

COLS_DICT = {
    "date": "Дата",
    "client_order_date": "Дата заказа",
    "client_order_number": "Номер заказа",
    "client_order": "Заказ клиента",
    "operation": "Операция",
    "dt": "dt",
    "cr": "cr",
    "amount": "Сумма",
    "quant_dt": "quant_dt",
    "quant_cr": "quant_cr",
    "quant": "Количество",
    "warehouse": "Склад",
    "spec": "Спецификация",
    "fullname": "Номенклатура",
    "imname": "Название в ИМ",
    "article": "Артикл",
    "onec_cat": "onec_cat",
    "onec_subcat": "onec_subcat",
    "init_date": "Дата первого заказа",
    "im_id": "Код товара в ИМ",
    "cat": "Категория",
    "cat_icon": "cat_icon",
    "parent_cat": "Группа",
    "parent_icon": "parent_icon",
    "manu": "Производитель",
    "manu_origin": "Стана происхождения",
    "brend": "Бренд",
    "brend_origin": "Страна бренда",
    "subcat": "Подкатегоря",
    "store": "Торговая точка",
    "chanel": "Канал продаж",
    "store_gr_name": "Магазин",
    "store_region": "Регион",
    "agent": "_Агент",
    "agent_name": "Агент",  # report_name
    "manager": "_Менеджер",
    "manager_name": "Менеджер",  # report_name
    "eom": "Отчетный период",
    "month_fmt": "Месяц",
    "quarter_fmt": "Квартал",
    "week_fmt": "_Неделя",  # сокращенная
    "week_fullname": "Неделя",
    "month_id": "month_id",
    "client_order_num": "Количество заказов",
}

COLS_LIST = [
    "date",
    "client_order_date",
    "client_order_number",
    "client_order",
    "operation",
    "dt",
    "cr",
    "amount",
    "quant_dt",
    "quant_cr",
    "quant",
    "warehouse",
    "spec",
    "fullname",
    "imname",
    "article",
    "onec_cat",
    "onec_subcat",
    "init_date",
    "im_id",
    "cat",
    "cat_icon",
    "parent_cat",
    "parent_icon",
    "manu",
    "manu_origin",
    "brend",
    "brend_origin",
    "subcat",
    "store",
    "chanel",
    "store_gr_name",
    "store_region",
    "agent",
    "agent_name",
    "manager",
    "manager_name",
    "eom",
    "month_fmt",
    "quarter_fmt",
    "week_fmt",
    "week_fullname",
    "month_id",
]


def load_sales_domain():
    def sales_dynamix_monthly(df: pd.DataFrame):
        cols_to_keep = [
            "client_order",
            "amount",
            "quant",
            "chanel",
            "store_gr_name",
            "store",
            "store_region",
            "month_id",
            "eom",
            "quarter_fmt",
        ]
        df = df[[cols_to_keep]]
        df["eom"] = pd.to_datetime(df["eom"])
        df["month_fmt"] = df["eom"].dt.strftime("%b %y").str.capitalize()
        grouped = (
            df.groupby(
                [
                    "eom" "month_id",
                    "month_fmt",
                    "chanel",
                    "store_gr_name",
                    "store",
                    "store_region",
                    "quarter_fmt",
                ]
            )
            .agg(
                amount=("amount", "sum"),
                quant=("quant", "sum"),
                client_order_num=(
                    "client_order",
                    "nunique",
                ),  # количество уникальных заказов
            )
            .reset_index()
            .sort_values(by="eom")
        )

        return grouped

    def range_slider_data(df: pd.DataFrame):
        pass

    df = pd.read_sql("SELECT * FROM sales_domain", connection)
    cols_to_fill = [
        "chanel",
        "store_gr_name",
        "store",
        "store_region",
        "manager_name",
        "agent_name",
    ]
    for col in cols_to_fill:
        df[col] = df[col].fillna("Нет данных")

    # сохраняем sales_dynamix_monthly
    key = "sales_dynamix_monthly"
    pickled = pickle.dumps(sales_dynamix_monthly(df))
    r.set(key, pickled)

    # Делаем данные для слайдера
    key = "range_sliders_data"


def redis_form_uplaoder():
    # _dash_renderer._set_react_version("18.2.0")
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

    def save_df_to_redis(df: pd.DataFrame, key="sales_data"):
        df["date"] = pd.to_datetime(df["date"])
        pickled = pickle.dumps(df)
        r.set(key, pickled)
        last_date = df["date"].max()
        first_date = df["date"].min()

        r.set("last_date", last_date.strftime("%Y-%m-%d"))
        r.set("first_date", first_date.strftime("%Y-%m-%d"))

        print(f"Сохранено {len(df)} строк под ключом '{key}' в Redis.")

    def save_sales_domain(df: pd.DataFrame, key="sales_domain"):
        df["date"] = pd.to_datetime(df["date"])
        df["eom"] = pd.to_datetime(df["eom"])
        pickled = pickle.dumps(df)
        r.set(key, pickled)

    def save_sales_dinamix_monthly(key="sales_dynamix_monthly"):
        df = pd.DataFrame()
        with connection.cursor() as cursor:
            df = pd.read_sql("SELECT * FROM shop_dinamix_monthly", connection)

        df["eom"] = pd.to_datetime(df["eom"])
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

    progress = dmc.Text("Прогресс...", id="progress")

    upload_conteiner = dmc.Container(
        dmc.Stack([title, dcc.Loading([button, progress])]), fluid=True
    )

    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme={"colorScheme": "light"},
        children=[upload_conteiner],
    )

    @app.callback(
        Output("progress", "children"),
        Input("btn", "n_clicks"),
        # State('new_manu','data'),
        # State('new_items','data'),
        # State('new_agents','data'),
        # State('new_stores','data'),
        # State('new_managers','data'),
        # State('new_brends','data'),
        # State('new_collection','data'),
        prevent_initial_call=True,
    )
    def redis_update(nclicks):
        if nclicks > 0:
            r.flushall()
            save_df_to_redis(load_sales_with_related_to_df())
            save_sales_dinamix_monthly()
            # save_sales_domain(load_sales_domain())

        return "Загрузка"

    return app.server
