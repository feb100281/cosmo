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
import locale

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
from utils.updater import Updater, set_data



def upload_form():
    _dash_renderer._set_react_version("18.2.0")
    app = dash.Dash(
        __name__,
        requests_pathname_prefix="/upload-form/",
        external_stylesheets=dmc.styles.ALL,
        suppress_callback_exceptions=True,
    )

    # ==== компоненты формы

    

    upload_area = dcc.Upload(
        id="upload-data",
        children=html.Div(["Перетащите или ", html.A("выберите файл данных")]),
        style={
            "width": "100%",
            "height": "60px",
            "lineHeight": "60px",
            "borderWidth": "1px",
            "borderStyle": "dashed",
            "borderRadius": "5px",
            "textAlign": "center",
            "margin": "10px",
        },
        multiple=False,  # если один файл
    )

    title = dmc.Title("Загрузка данных", order=1, c="blue")

    disclamer = dmc.Text(
        "Файл данных о продажах из 1С должен быть в формате excel и строиться из отчета ..... Важно - нужно загружать данные на польный день.",
        size="xs",
    )

    button = dmc.Button(
        children="Загрузить",
        variant="filled",
        color="#5c7cfa",
        size="sm",
        radius="sm",
        loading=False,
        disabled=True,
        id="btn",
        # other props...
    )

    # ==== Контейнера

    upload_conteiner = dmc.Container(
        dmc.Stack([title, disclamer, dmc.Group([upload_area, button])]), fluid=True
    )

    # Layouts

    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme={"colorScheme": "light"},
        children=[upload_conteiner, dmc.Container(id="output-data-upload", fluid=True),
                  dcc.Store(id='dummy'),
                  dcc.Store(id='new_manu'),
                  dcc.Store(id='new_managers'),
                  dcc.Store(id='new_agents'),
                  dcc.Store(id='new_items'),
                  dcc.Store(id='new_stores'),    
                  dcc.Store(id='new_brends'),
                  dcc.Store(id='new_collection')              
                  ],
    )

    @app.callback(
        Output("output-data-upload", "children"),
        Output("btn", "disabled"),
        
        Output("new_manu", "data"),
        Output("new_managers", "data"),
        Output("new_agents", "data"),
        Output("new_items", "data"),
        Output("new_stores", "data"),     
        Output("new_brends", "data"), 
        Output("new_collection", "data"),   
        
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        prevent_initial_call=True
    )
    def update_output(contents, filename):
        if contents is None:
            return dmc.Alert("Файл не загружен", color="red", title="Ошибка")

        try:
            # достаем base64
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            file_obj = io.BytesIO(decoded)

            # обработка через Updater
            updater = Updater(file_obj)

           
            df = updater.get_data()
            df_new_manu = df[df["manufacturer"].isin(updater.new_manufactures)]
            if not df_new_manu.empty:
                df_new_manu = (
                    df_new_manu.pivot_table(
                        index="manufacturer",
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )

            df_new_stores = df[df["store_name"].isin(updater.new_stores)]
            if not df_new_stores.empty:
                df_new_stores = (
                    df_new_stores.pivot_table(
                        index="store_name",
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )

            df_new_items = df[df["fullname"].isin(updater.new_itemes)]
            if not df_new_items.empty:
                df_new_items = (
                    df_new_items.pivot_table(
                        index=["fullname"],
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )

            df_new_managers = df[df["manager"].isin(updater.new_managers)]
            if not df_new_managers.empty:
                df_new_managers = (
                    df_new_managers.pivot_table(
                        index=["manager"],
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )

            df_new_agents = df[df["agent"].isin(updater.new_agents)]
            if not df_new_agents.empty:
                df_new_agents = (
                    df_new_agents.pivot_table(
                        index=["agent"],
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )
            
            df_new_brends = df[df["brend"].isin(updater.new_brends)]
            if not df_new_brends.empty:
                df_new_brends = (
                    df_new_brends.pivot_table(
                        index=["brend"],
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )
            
            df_new_collections = df[df["collection"].isin(updater.new_collection)]
            if not df_new_collections.empty:
                df_new_collections = (
                    df_new_collections.pivot_table(
                        index=["collection"],
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                )

            summary_list = dmc.List(
                icon=dmc.ThemeIcon(
                    DashIconify(icon="radix-icons:check-circled", width=16),
                    radius="xl",
                    color="teal",
                    size=24,
                ),
                size="sm",
                spacing="sm",
                children=[dmc.ListItem(f"{k}: {v}") for k, v in updater.log.items()],
            )

            details = dmc.Tabs(
                color="teal",
                value="manu",
                children=[
                    dmc.TabsList(
                        children=[
                            dmc.TabsTab("Новые производители", value="manu"),
                            dmc.TabsTab(
                                "Новые подраздения", value="stores", color="blue"
                            ),
                            dmc.TabsTab(
                                "Новые номенклатуры", value="items", color="blue"
                            ),
                            dmc.TabsTab(
                                "Новые менеджеры", value="managers", color="blue"
                            ),
                            dmc.TabsTab("Новые агенты", value="agents", color="blue"
                            ),
                            dmc.TabsTab("Новые бренды", value="brends", color="blue"
                            ),
                            dmc.TabsTab("Новые колеекции", value="collections", color="blue"
                            )
                            
                        ]
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_manu.to_string()), h=200
                        ),
                        value="manu",
                        pt="xs",
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_stores.to_string()), h=200
                        ),
                        value="stores",
                        pt="xs",
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_items.to_string()), h=200
                        ),
                        value="items",
                        pt="xs",
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_managers.to_string()), h=200
                        ),
                        value="managers",
                        pt="xs",
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_agents.to_string()), h=200
                        ),
                        value="agents",
                        pt="xs",
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_brends.to_string()), h=200
                        ),
                        value="brends",
                        pt="xs",
                    ),
                    dmc.TabsPanel(
                        children=dmc.ScrollArea(
                            html.Pre(df_new_collections.to_string()), h=200
                        ),
                        value="collections",
                        pt="xs",
                    ),
                ],
            )
            # формируем красивый вывод
            return (
                dmc.Stack(
                    [
                        dmc.Alert(f"Файл {filename} успешно загружен", color="green",id='alert'),
                        summary_list,
                        details,
                        # dmc.ScrollArea(
                        #     html.Pre(df.head().to_string()),
                        #     h=200
                        # )
                    ]
                ),
               
            ), False, updater.new_manufactures, updater.new_managers, updater.new_agents, updater.new_itemes, updater.new_stores, updater.new_brends, updater.new_collection 
            
        except Exception as e:
            return dmc.Alert(str(e), color="red", title="Ошибка")

    
    @app.callback(
        Output('dummy','data'),
        Output("alert", "children"),
        Input('btn','n_clicks'),
        State('new_manu','data'),
        State('new_items','data'),
        State('new_agents','data'),
        State('new_stores','data'),
        State('new_managers','data'),
        State('new_brends','data'),
        State('new_collection','data'),
        prevent_initial_call=True   
       
    )
    def upload(nclick,new_manu,new_items,new_agents,new_stores,new_managers,new_brends,new_collection ):
        if nclick:
            d = {}
            if new_manu:
                d["ItemManufacturer"] = new_manu
            if new_stores:
                d["Stores"] = new_stores
            if new_items:
                d["Items"] = new_items
            if new_agents:
                d["Agents"] = new_agents
            if new_managers:
                d["Managers"] = new_managers
            if new_brends:
                d["ItemBrend"] = new_brends
            if new_collection:
                d["ItemCollections"] = new_collection

            succsee_list = set_data(d)    
            
            summary_list = dmc.List(
                icon=dmc.ThemeIcon(
                    DashIconify(icon="radix-icons:check-circled", width=16),
                    radius="xl",
                    color="teal",
                    size=24,
                ),
                size="sm",
                spacing="sm",
                children=[dmc.ListItem(f"{v}") for v in succsee_list],
            )

            
             
            return '',summary_list
        else:
            return ''
        
        
    
    
    return app.server
