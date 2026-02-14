# Это layout для daily sales

from dash import  html
import pandas as pd
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from utils.dash_components.common import CommonComponents as CC
from utils.dash_components.dftotable import df_dmc_table
import locale
import dash_ag_grid as dag

from django.urls import reverse, NoReverseMatch  # <-- ДОБАВИЛИ

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

from .data import get_orders_details


FORMATERS = {
    "Выручка": lambda v: f"₽{v:,.0f}",
    "Кол-во": lambda v: f"{v:,.0f} ед",
    "Заказы": lambda v: f"{v:,.0f} ед",
    "Ср. чек": lambda v: f"₽{v:,.0f}",
    "Продажи": lambda v: f"₽{v:,.0f}",
    "Возвраты": lambda v: f"₽{v:,.0f}",
    "К возвратов": lambda v: f"{v:,.0f}%" if v > 0 else f"({abs(v):,.0f})%",
    "Δ абс.": lambda v: html.Span(
        f"+ {v:,.0f}" if v > 0 else f"- {abs(v):,.0f}" if v < 0 else "0",
        className="pos" if v > 0 else "neg" if v < 0 else "",
    ),
    "Δ отн.": lambda v: html.Span(
        f"+ {v:,.0f}%" if v > 0 else f"- {abs(v):,.0f}%" if v < 0 else "0%",
        className="pos" if v > 0 else "neg" if v < 0 else "",
    ),
}

RENAMING_COLS = {
    "amount": "Выручка",
    "quant": "Кол-во",
    "orders": "Заказы",
    "dt": "Продажи",
    "cr": "Возвраты",
}


class MainWindow:
    def __init__(self, orders_id=None):
        self.orders_id = orders_id
        
        
        self.grid_id = 'orders-ag-grid-unique-id'

    #Делаем детали заказа
    def make_order_ag_grid(self):
        if not self.orders_id:
            return dmc.Text('Не найдено инфы по данному заказу')

        data = get_orders_details(self.orders_id).to_dict('records')

        columnDefs = [
            {"headerName": "Дата", "field": "date", "minWidth": 110,
             "filter": "agDateColumnFilter", "sort": "desc"},

            {"headerName": "Товар", "field": "fullname", "minWidth": 280,
             "filter": "agTextColumnFilter", "tooltipField": "fullname"},

            {"headerName": "Артикул", "field": "article", "minWidth": 140,
             "filter": "agTextColumnFilter"},

            {"headerName": "Штрихкод", "field": "barcode", "minWidth": 160,
             "filter": "agTextColumnFilter"},

            {"headerName": "Менеджер", "field": "manager_name", "minWidth": 170,
             "filter": "agTextColumnFilter"},

            {"headerName": "Агент", "field": "agent_name", "minWidth": 170,
             "filter": "agTextColumnFilter"},

            {"headerName": "Склад", "field": "warehouse", "minWidth": 160,
             "filter": "agTextColumnFilter"},

            {"headerName": "Магазин", "field": "store_group", "minWidth": 140,
             "filter": "agTextColumnFilter"},

            {"headerName": "Продано", "field": "dt", "minWidth": 110,
             "type": "numericColumn", "filter": "agNumberColumnFilter"},

            {"headerName": "Возвращено", "field": "cr", "minWidth": 110,
             "type": "numericColumn", "filter": "agNumberColumnFilter"},

            {"headerName": "Кол-во продано", "field": "quant_dt", "minWidth": 120,
             "type": "numericColumn", "filter": "agNumberColumnFilter"},

            {"headerName": "Кол-во возвращено", "field": "quant_cr", "minWidth": 120,
             "type": "numericColumn", "filter": "agNumberColumnFilter"},

            {"headerName": "Спец.", "field": "spec", "minWidth": 220,
             "filter": "agTextColumnFilter", "wrapText": True, "autoHeight": True},
        ]

        defaultColDef = {
            "sortable": True,
            "resizable": True,
            "filter": True,
            "floatingFilter": True,
            "wrapHeaderText": True,
            "autoHeaderHeight": True,
        }

        dashGridOptions = {
            "animateRows": True,
            "rowSelection": "multiple",
            "suppressRowClickSelection": True,
            "pagination": True,
            "paginationPageSize": 50,
            "tooltipShowDelay": 200,
        }

        return dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text(f"Детали заказа: {self.orders_id}", fw=600),
                        dmc.Badge(f"Строк: {len(data)}", variant="light"),
                    ],
                    justify="space-between",
                ),
                dag.AgGrid(
                    id=self.grid_id,
                    rowData=data,
                    columnDefs=columnDefs,
                    defaultColDef=defaultColDef,
                    dashGridOptions=dashGridOptions,
                    style={"height": "70vh", "width": "100%"},
                    className="ag-theme-alpine",
                ),
            ],
            gap="sm",
        )
        
        
        


    def layout(self):        

        try:
            back_url = reverse("admin:mvsalesorder_changelist")
        except NoReverseMatch:
            
            try:
                back_url = reverse("admin:mvsalesorder_changelist")
            except NoReverseMatch:
                back_url = "/admin/sales/mvsalesorder/"

        la = dmc.AppShell(
            [
                dmc.AppShellHeader(
                    dmc.Group(
                        [
                            # --- КНОПКА НАЗАД (работает стабильно) ---
                            dmc.Anchor(
                                dmc.Button(
                                    [DashIconify(icon="tabler:arrow-left", width=18), "Назад"],
                                    variant="subtle",
                                    size="sm",
                                ),
                                href=back_url,
                                target="_top",  
                                style={"textDecoration": "none"},
                            ),
                            

                            DashIconify(
                                icon="streamline-freehand:cash-payment-bag-1",
                                width=40,
                                color="blue",
                            ),
                            CC.report_title(f"ОТЧЕТ ПО ЗАКАЗУ ID {self.orders_id}"),
                        ],
                        h="100%",
                        px="md",
                        mb="lg",
                        justify="flex-start",
                        gap="md",
                        wrap="nowrap",
                    )
                ),

                dmc.AppShellMain(
                    [
                        
                        dmc.Space(h=30),
                        self.make_order_ag_grid()
                        

                    ]
                ),
            ],
            header={"height": 60},
            padding=0,
        )

        return dmc.Container([la], fluid=True)
