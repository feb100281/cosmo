# import base64
# import io
# import pandas as pd
# import numpy as np
# import dash
# from dash import dcc, html, Input, Output, State, _dash_renderer, clientside_callback,no_update
# import dash_ag_grid as dag
# import dash_mantine_components as dmc
# import plotly.express as px
# from dash_iconify import DashIconify
# import locale

# locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
# from utils.updater import Updater, set_data




# def upload_form():
#     _dash_renderer._set_react_version("18.2.0")
#     app = dash.Dash(
#         __name__,
#         requests_pathname_prefix="/upload-form/",
#         external_stylesheets=dmc.styles.ALL,
#         suppress_callback_exceptions=True,
#     )

#     app.enable_dev_tools(
#         debug=True,
#         dev_tools_ui=True,
#         dev_tools_props_check=True,
#         dev_tools_hot_reload=True,
#     )

#     # ==== компоненты формы

    

#     upload_area = dcc.Upload(
#         id="upload-data",
#         children=html.Div(["Перетащите или ", html.A("выберите файл данных")]),
#         style={
#             "width": "100%",
#             "height": "60px",
#             "lineHeight": "60px",
#             "borderWidth": "1px",
#             "borderStyle": "dashed",
#             "borderRadius": "5px",
#             "textAlign": "center",
#             "margin": "10px",
#         },
#         multiple=False,  # если один файл
#     )

#     title = dmc.Title("Загрузка данных", order=1, c="blue")

#     disclamer = dmc.Text(
#         "Файл данных о продажах из 1С должен быть в формате excel и строиться из отчета ..... Важно - нужно загружать данные на польный день.",
#         size="xs",
#     )

#     button = dmc.Button(
#         children="Загрузить",
#         variant="filled",
#         color="#5c7cfa",
#         size="sm",
#         radius="sm",
#         loading=False,
#         disabled=True,
#         id="btn",
#         # other props...
#     )

#     # ==== Контейнера

#     upload_conteiner = dmc.Container(
#         dmc.Stack([title, disclamer, dmc.Group([upload_area, button])]), fluid=True
#     )

#     # Layouts

#     app.layout = dmc.MantineProvider(
#         id="mantine-provider",
#         theme={"colorScheme": "light"},
#         children=[upload_conteiner, dmc.Container(id="output-data-upload", fluid=True),
#                   dcc.Store(id='dummy'),
#                   dcc.Store(id='new_manu'),
#                   dcc.Store(id='new_managers'),
#                   dcc.Store(id='new_agents'),
#                   dcc.Store(id='new_items'),
#                   dcc.Store(id='new_stores'),    
#                   dcc.Store(id='new_brends'),
#                   dcc.Store(id='new_collection')              
#                   ],
#     )

#     @app.callback(
#         Output("output-data-upload", "children"),
#         Output("btn", "disabled"),
        
#         Output("new_manu", "data"),
#         Output("new_managers", "data"),
#         Output("new_agents", "data"),
#         Output("new_items", "data"),
#         Output("new_stores", "data"),     
#         Output("new_brends", "data"), 
#         Output("new_collection", "data"),   
        
#         Input("upload-data", "contents"),
#         State("upload-data", "filename"),
#         prevent_initial_call=True
#     )
#     def update_output(contents, filename,background_callback_manager=None, **kwargs):
#         print('hello')
#         if contents is None:
#             return (
#                 dmc.Alert("Файл не загружен", color="red", title="Ошибка"),
#                 True,                 # btn.disabled
#                 no_update, no_update, no_update, no_update, no_update, no_update, no_update
#             )

#         # try:
#         # достаем base64
#         content_type, content_string = contents.split(",")
#         decoded = base64.b64decode(content_string)
#         file_obj = io.BytesIO(decoded)

#         # обработка через Updater
#         updater = Updater(file_obj)

        
#         df = updater.get_data()
#         # print(df)
#         df_new_manu = df[df["manufacturer"].isin(updater.new_manufactures)]
#         if not df_new_manu.empty:
#             df_new_manu = (
#                 df_new_manu.pivot_table(
#                     index="manufacturer",
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )

#         df_new_stores = df[df["store_name"].isin(updater.new_stores)]
#         if not df_new_stores.empty:
#             df_new_stores = (
#                 df_new_stores.pivot_table(
#                     index="store_name",
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )

#         df_new_items = df[df["fullname"].isin(updater.new_itemes)]
#         if not df_new_items.empty:
#             df_new_items = (
#                 df_new_items.pivot_table(
#                     index=["fullname"],
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )

#         df_new_managers = df[df["manager"].isin(updater.new_managers)]
#         if not df_new_managers.empty:
#             df_new_managers = (
#                 df_new_managers.pivot_table(
#                     index=["manager"],
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )

#         df_new_agents = df[df["agent"].isin(updater.new_agents)]
#         if not df_new_agents.empty:
#             df_new_agents = (
#                 df_new_agents.pivot_table(
#                     index=["agent"],
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )
        
#         df_new_brends = df[df["brend"].isin(updater.new_brends)]
#         if not df_new_brends.empty:
#             df_new_brends = (
#                 df_new_brends.pivot_table(
#                     index=["brend"],
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )
        
#         df_new_collections = df[df["collection"].isin(updater.new_collection)]
#         if not df_new_collections.empty:
#             df_new_collections = (
#                 df_new_collections.pivot_table(
#                     index=["collection"],
#                     values=["date", "client_order_date"],
#                     aggfunc="min",
#                 )
#                 .sort_values(by="date")
#                 .reset_index()
#             )

#         summary_list = dmc.List(
#             icon=dmc.ThemeIcon(
#                 DashIconify(icon="radix-icons:check-circled", width=16),
#                 radius="xl",
#                 color="teal",
#                 size=24,
#             ),
#             size="sm",
#             spacing="sm",
#             children=[dmc.ListItem(f"{k}: {v}") for k, v in updater.log.items()],
#         )

#         details = dmc.Tabs(
#             color="teal",
#             value="manu",
#             children=[
#                 dmc.TabsList(
#                     children=[
#                         dmc.TabsTab("Новые производители", value="manu"),
#                         dmc.TabsTab(
#                             "Новые подраздения", value="stores", color="blue"
#                         ),
#                         dmc.TabsTab(
#                             "Новые номенклатуры", value="items", color="blue"
#                         ),
#                         dmc.TabsTab(
#                             "Новые менеджеры", value="managers", color="blue"
#                         ),
#                         dmc.TabsTab("Новые агенты", value="agents", color="blue"
#                         ),
#                         dmc.TabsTab("Новые бренды", value="brends", color="blue"
#                         ),
#                         dmc.TabsTab("Новые колеекции", value="collections", color="blue"
#                         )
                        
#                     ]
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_manu.to_string()), h=200
#                     ),
#                     value="manu",
#                     pt="xs",
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_stores.to_string()), h=200
#                     ),
#                     value="stores",
#                     pt="xs",
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_items.to_string()), h=200
#                     ),
#                     value="items",
#                     pt="xs",
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_managers.to_string()), h=200
#                     ),
#                     value="managers",
#                     pt="xs",
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_agents.to_string()), h=200
#                     ),
#                     value="agents",
#                     pt="xs",
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_brends.to_string()), h=200
#                     ),
#                     value="brends",
#                     pt="xs",
#                 ),
#                 dmc.TabsPanel(
#                     children=dmc.ScrollArea(
#                         html.Pre(df_new_collections.to_string()), h=200
#                     ),
#                     value="collections",
#                     pt="xs",
#                 ),
#             ],
#         )
#         # формируем красивый вывод
#         return (
#             dmc.Stack(
#                 [
#                     dmc.Alert(f"Файл {filename} успешно загружен", color="green"),
#                     summary_list,
#                     details,
#                 ]
#             ),
#             False,
#             updater.new_manufactures,
#             updater.new_managers,
#             updater.new_agents,
#             updater.new_itemes,
#             updater.new_stores,
#             updater.new_brends,
#             updater.new_collection,
#         )

#         # except Exception as e:
#         #     return (
#         #         dmc.Alert(str(e), color="red", title="Ошибка"),
#         #         True,
#         #         no_update, no_update, no_update, no_update, no_update, no_update, no_update
#         #     )

    
#     @app.callback(
#         Output('dummy','data'),
#         # Output("alert", "children"),
#         Input('btn','n_clicks'),
#         State('new_manu','data'),
#         State('new_items','data'),
#         State('new_agents','data'),
#         State('new_stores','data'),
#         State('new_managers','data'),
#         State('new_brends','data'),
#         State('new_collection','data'),
#         prevent_initial_call=True   
       
#     )
#     def upload(nclick,new_manu,new_items,new_agents,new_stores,new_managers,new_brends,new_collection, background_callback_manager=None, **kwargs ):
#         print("CALLBACK FIRED, n_clicks =", nclick)
#         if nclick:
#             print('hello')

#             d = {}
#             if new_manu:
#                 d["ItemManufacturer"] = new_manu
#             if new_stores:
#                 d["Stores"] = new_stores
#             if new_items:
#                 d["Items"] = new_items
#             if new_agents:
#                 d["Agents"] = new_agents
#             if new_managers:
#                 d["Managers"] = new_managers
#             if new_brends:
#                 d["ItemBrend"] = new_brends
#             if new_collection:
#                 d["ItemCollections"] = new_collection
                
            

#             succsee_list = set_data(d)    
            
#             summary_list = dmc.List(
#                 icon=dmc.ThemeIcon(
#                     DashIconify(icon="radix-icons:check-circled", width=16),
#                     radius="xl",
#                     color="teal",
#                     size=24,
#                 ),
#                 size="sm",
#                 spacing="sm",
#                 children=[dmc.ListItem(f"{v}") for v in succsee_list],
#             )

            
             
#             return summary_list
#         else:
#             return no_update
        
        
    
    
#     return app.server



import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, no_update, _dash_renderer
import dash_mantine_components as dmc
import dash_ag_grid as dag
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

    app.enable_dev_tools(
        debug=True,
        dev_tools_ui=True,
        dev_tools_props_check=True,
        dev_tools_hot_reload=True,
    )

    # -----------------------------
    # Helpers
    # -----------------------------
    def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def _grid(df: pd.DataFrame, height: int = 320):
        if df is None or df.empty:
            return dmc.Center(
                h=height,
                children=dmc.Stack(
                    align="center",
                    gap="xs",
                    children=[
                        dmc.ThemeIcon(
                            DashIconify(icon="tabler:inbox", width=22),
                            radius="xl",
                            variant="light",
                            color="gray",
                            size=46,
                        ),
                        dmc.Text("Нет новых записей", c="dimmed"),
                    ],
                ),
            )

        col_defs = [{"field": c, "filter": True, "sortable": True, "resizable": True} for c in df.columns]

        return dag.AgGrid(
            columnDefs=col_defs,
            rowData=df.to_dict("records"),
            defaultColDef={
                "flex": 1,
                "minWidth": 140,
                "wrapText": True,
                "autoHeight": True,
            },
            dashGridOptions={
                "animateRows": True,
                "pagination": True,
                "paginationPageSize": 20,
            },
            className="ag-theme-alpine",
            style={"height": f"{height}px", "width": "100%"},
        )


    def tab_label(title: str, icon: str, value: int):
        return dmc.Group(
            gap=8,
            children=[
                DashIconify(icon=icon, width=16),
                dmc.Text(title, size="sm", fw=600),
                dmc.Badge(
                    str(int(value)),
                    variant="light" if value > 0 else "outline",
                    color="blue" if value > 0 else "gray",
                    radius="sm",
                    size="sm",
                ),
            ],
        )

    # -----------------------------
    # Layout
    # -----------------------------
    app.layout = dmc.MantineProvider(
        theme={"colorScheme": "light", "primaryColor": "blue", "defaultRadius": "md"},
        children=dmc.AppShell(
            header={"height": 70},
            padding="md",
            children=[
                # HEADER
                dmc.AppShellHeader(
                    px="md",
                    children=[
                        dmc.Group(
                            h=70,
                            justify="space-between",
                            children=[
                                dmc.Group(
                                    gap="sm",
                                    children=[
                                        dmc.ThemeIcon(
                                            DashIconify(icon="tabler:database-import", width=20),
                                            radius="md",
                                            variant="filled",
                                            color="dark",
                                            size=42,
                                        ),
                                        dmc.Stack(
                                            gap=0,
                                            children=[
                                                dmc.Text("Загрузка данных", fw=800, size="lg"),
                                                dmc.Text(
                                                    "Проверка новых справочников перед записью",
                                                    size="sm",
                                                    c="dimmed",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),

                            ],
                        )
                    ],
                ),

                # MAIN
                dmc.AppShellMain(
                    children=[
                        dcc.Store(id="dummy"),
                        dcc.Store(id="new_manu"),
                        dcc.Store(id="new_managers"),
                        dcc.Store(id="new_agents"),
                        dcc.Store(id="new_items"),
                        dcc.Store(id="new_stores"),
                        dcc.Store(id="new_brends"),
                        dcc.Store(id="new_collection"),

                        dmc.Container(
                            size="lg",
                            pt="md",
                            children=dmc.Stack(
                                gap="md",
                                children=[
                                    dmc.Alert(
                                        title="Требования к файлу",
                                        color="blue",
                                        radius="lg",
                                        variant="light",
                                        children=dmc.Text(
                                            "Файл данных о продажах из 1С должен быть в формате Excel. "
                                            "Важно: загружайте данные за полный день.",
                                            size="sm",
                                        ),
                                    ),

                                    dmc.Paper(
                                        withBorder=True,
                                        radius="lg",
                                        p="lg",
                                        children=dmc.Stack(
                                            gap="md",
                                            children=[
                                                dmc.Group(
                                                    justify="space-between",
                                                    children=[
                                                        dmc.Stack(
                                                            gap=2,
                                                            children=[
                                                                dmc.Text("Загрузите файл", fw=700, size="lg"),
                                                                dmc.Text(
                                                                    "Мы найдём новые элементы и покажем их по вкладкам.",
                                                                    c="dimmed",
                                                                    size="sm",
                                                                ),
                                                            ],
                                                        ),
                                                        dmc.Button(
                                                            "Загрузить",
                                                            id="btn",
                                                            leftSection=DashIconify(icon="tabler:upload", width=18),
                                                            radius="md",
                                                            disabled=True,
                                                        ),
                                                    ],
                                                ),

                                                dcc.Upload(
                                                    id="upload-data",
                                                    multiple=False,
                                                    children=dmc.Paper(
                                                        withBorder=True,
                                                        radius="lg",
                                                        p="md",
                                                        style={"borderStyle": "dashed", "cursor": "pointer"},
                                                        children=dmc.Group(
                                                            justify="space-between",
                                                            children=[
                                                                dmc.Group(
                                                                    gap="sm",
                                                                    children=[
                                                                        dmc.ThemeIcon(
                                                                            DashIconify(
                                                                                icon="tabler:cloud-upload", width=20
                                                                            ),
                                                                            radius="md",
                                                                            variant="light",
                                                                            color="blue",
                                                                            size=42,
                                                                        ),
                                                                        dmc.Stack(
                                                                            gap=2,
                                                                            children=[
                                                                                dmc.Text("Перетащите файл сюда", fw=600),
                                                                                dmc.Text(
                                                                                    "или нажмите, чтобы выбрать Excel",
                                                                                    size="sm",
                                                                                    c="dimmed",
                                                                                ),
                                                                            ],
                                                                        ),
                                                                    ],
                                                                ),
                                                                dmc.Badge(
                                                                    "XLSX",
                                                                    variant="light",
                                                                    color="blue",
                                                                    radius="sm",
                                                                    size="lg",
                                                                ),
                                                            ],
                                                        ),
                                                    ),
                                                    style={"width": "100%"},
                                                ),

                                                dmc.LoadingOverlay(
                                                    visible=False,
                                                    id="upload-loading",
                                                    overlayProps={"radius": "lg", "blur": 2},
                                                    loaderProps={"type": "bars"},
                                                    zIndex=10,
                                                ),
                                                html.Div(id="output-data-upload"),
       
                                                dmc.LoadingOverlay(
                                                    visible=False,
                                                    id="setdata-loading",
                                                    overlayProps={"radius": "lg", "blur": 2},
                                                    loaderProps={"type": "bars"},
                                                    zIndex=10,
                                                ),
                                                html.Div(id="setdata-result"),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ]
                ),
            ],
        ),
    )

    # -----------------------------
    # Callbacks
    # -----------------------------
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
        Output("upload-loading", "visible"),
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        prevent_initial_call=True,
    )
    def update_output(contents, filename, **kwargs):
        if contents is None:
            return (
                dmc.Alert("Файл не загружен", color="red", title="Ошибка", radius="lg"),
                True,
                no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                False,
            )

        try:
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            file_obj = io.BytesIO(decoded)

            updater = Updater(file_obj)
            df = updater.get_data()

            manufacturer_col = _pick_col(df, ["manufacturer"])
            store_col = _pick_col(df, ["store_name"])
            manager_col = _pick_col(df, ["manager"])
            agent_col = _pick_col(df, ["agent"])
            brend_col = _pick_col(df, ["brend"])
            collection_col = _pick_col(df, ["collection"])


            item_col = _pick_col(df, ["contr_name", "fullname"])

            required_cols = ["date", "client_order_date"]
            for rc in required_cols:
                if rc not in df.columns:
                    raise ValueError(f"В файле нет обязательной колонки: {rc}")

            def build_new_df(col_name: str | None, new_list: list, index_name: str):
                if not col_name:
                    return pd.DataFrame(columns=[index_name, "date", "client_order_date"])
                dff = df[df[col_name].isin(new_list)]
                if dff.empty:
                    return pd.DataFrame(columns=[index_name, "date", "client_order_date"])
                return (
                    dff.pivot_table(
                        index=col_name,
                        values=["date", "client_order_date"],
                        aggfunc="min",
                    )
                    .sort_values(by="date")
                    .reset_index()
                    .rename(columns={col_name: index_name})
                )

            df_new_manu = build_new_df(manufacturer_col, updater.new_manufactures, "manufacturer")
            df_new_stores = build_new_df(store_col, updater.new_stores, "store_name")
            df_new_items = build_new_df(item_col, updater.new_itemes, "item_name")
            df_new_managers = build_new_df(manager_col, updater.new_managers, "manager")
            df_new_agents = build_new_df(agent_col, updater.new_agents, "agent")
            df_new_brends = build_new_df(brend_col, updater.new_brends, "brend")
            df_new_collections = build_new_df(collection_col, updater.new_collection, "collection")

            counts = {
                "Производители": len(updater.new_manufactures or []),
                "Подразделения": len(updater.new_stores or []),
                "Номенклатуры": len(updater.new_itemes or []),
                "Менеджеры": len(updater.new_managers or []),
                "Агенты": len(updater.new_agents or []),
                "Бренды": len(updater.new_brends or []),
                "Коллекции": len(updater.new_collection or []),
            }

            log_block = None
            if getattr(updater, "log", None):
                log_block = dmc.Paper(
                    withBorder=True,
                    radius="lg",
                    p="md",
                    children=dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Text("Сводка обработки", fw=700),
                            dmc.List(
                                icon=dmc.ThemeIcon(
                                    DashIconify(icon="radix-icons:check-circled", width=16),
                                    radius="xl",
                                    color="teal",
                                    size=24,
                                ),
                                size="sm",
                                spacing="xs",
                                children=[dmc.ListItem(f"{k}: {v}") for k, v in updater.log.items()],
                            ),
                        ],
                    ),
                )

            tabs = dmc.Tabs(
                value="manu",
                radius="md",
                variant="default",
                children=[
                    # --- Горизонтальный скролл для табов
                    html.Div(
                        style={
                            "overflowX": "auto",
                            "overflowY": "hidden",
                            "whiteSpace": "nowrap",
                            "paddingBottom": "6px",   
                        },
                        children=[
                            dmc.TabsList(
                                style={
                                    "display": "inline-flex",
                                    "gap": "14px",
                                    "flexWrap": "nowrap",
                                    "whiteSpace": "nowrap",
                                    "minWidth": "max-content",
                                },
                                children=[
                                    dmc.TabsTab(
                                        value="manu",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Производители", "tabler:building-factory-2", counts["Производители"]),
                                    ),
                                    dmc.TabsTab(
                                        value="stores",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Подразделения", "tabler:building-store", counts["Подразделения"]),
                                    ),
                                    dmc.TabsTab(
                                        value="items",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Номенклатуры", "tabler:tag", counts["Номенклатуры"]),
                                    ),
                                    dmc.TabsTab(
                                        value="managers",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Менеджеры", "tabler:user-star", counts["Менеджеры"]),
                                    ),
                                    dmc.TabsTab(
                                        value="agents",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Агенты", "tabler:users", counts["Агенты"]),
                                    ),
                                    dmc.TabsTab(
                                        value="brends",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Бренды", "tabler:brand-threads", counts["Бренды"]),
                                    ),
                                    dmc.TabsTab(
                                        value="collections",
                                        style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
                                        children=tab_label("Коллекции", "tabler:stack-2", counts["Коллекции"]),
                                    ),
                                ],
                            )
                        ],
                    ),

                    dmc.TabsPanel(_grid(df_new_manu), value="manu", pt="md"),
                    dmc.TabsPanel(_grid(df_new_stores), value="stores", pt="md"),
                    dmc.TabsPanel(_grid(df_new_items), value="items", pt="md"),
                    dmc.TabsPanel(_grid(df_new_managers), value="managers", pt="md"),
                    dmc.TabsPanel(_grid(df_new_agents), value="agents", pt="md"),
                    dmc.TabsPanel(_grid(df_new_brends), value="brends", pt="md"),
                    dmc.TabsPanel(_grid(df_new_collections), value="collections", pt="md"),
                ],
            )



            has_any = any(v > 0 for v in counts.values())

            result_ui = dmc.Stack(
                gap="md",
                children=[
                    dmc.Text(f"Файл {filename} успешно прочитан", c="dimmed"),
                    log_block if log_block else html.Div(),
                    dmc.Paper(withBorder=True, radius="lg", p="md", children=tabs),
                ],
            )


            return (
                result_ui,
                (not has_any),
                updater.new_manufactures,
                updater.new_managers,
                updater.new_agents,
                updater.new_itemes,
                updater.new_stores,
                updater.new_brends,
                updater.new_collection,
                False,
            )

        except Exception as e:
            return (
                dmc.Alert(
                    title="Ошибка обработки файла",
                    color="red",
                    radius="lg",
                    variant="light",
                    icon=DashIconify(icon="tabler:alert-triangle", width=18),
                    children=dmc.Text(str(e), size="sm"),
                ),
                True,
                no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                False,
            )

    @app.callback(
        Output("setdata-result", "children"),
        Output("setdata-loading", "visible"),
        Input("btn", "n_clicks"),
        State("new_manu", "data"),
        State("new_items", "data"),
        State("new_agents", "data"),
        State("new_stores", "data"),
        State("new_managers", "data"),
        State("new_brends", "data"),
        State("new_collection", "data"),
        prevent_initial_call=True,
    )
    def upload(nclick, new_manu, new_items, new_agents, new_stores, new_managers, new_brends, new_collection, **kwargs):
        if not nclick:
            return no_update, False

        try:
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

            if not d:
                return (
                    dmc.Alert(
                        title="Нечего загружать",
                        color="yellow",
                        radius="lg",
                        variant="light",
                        icon=DashIconify(icon="tabler:info-circle", width=18),
                        children=dmc.Text("Новые элементы не найдены."),
                    ),
                    False,
                )

            succsee_list = set_data(d)

            ui = dmc.Alert(
                title="Запись выполнена",
                color="green",
                radius="lg",
                variant="light",
                icon=DashIconify(icon="tabler:circle-check", width=18),
                children=dmc.Stack(
                    gap="xs",
                    children=[
                        dmc.Text("Добавленные элементы:", fw=600),
                        dmc.List(
                            icon=dmc.ThemeIcon(
                                DashIconify(icon="radix-icons:check-circled", width=16),
                                radius="xl",
                                color="teal",
                                size=24,
                            ),
                            size="sm",
                            spacing="xs",
                            children=[dmc.ListItem(str(v)) for v in succsee_list],
                        ),
                    ],
                ),
            )

            return ui, False

        except Exception as e:
            return (
                dmc.Alert(
                    title="Ошибка записи",
                    color="red",
                    radius="lg",
                    variant="light",
                    icon=DashIconify(icon="tabler:alert-triangle", width=18),
                    children=dmc.Text(str(e), size="sm"),
                ),
                False,
            )

    return app.server
