import redis
import pickle
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


mantine_colors = [
    "indigo.6", "teal.6", "gray.6", "blue.6", "cyan.6", "pink.6",
    "lime.6", "orange.6", "violet.6", "grape.6", "red.6", "green.6",
    "yellow.6", "sky.6", "purple.6", "brand.6", "dark.6", "brown.6",
    "azure.6", "magenta.6"
]

from django.conf import settings

# 🔌 Загрузка данных из Redis
# r = redis.Redis(host='localhost', port=6379, db=0, )


r = settings.REDIS_CLIENT


raw_data = r.get("sales_data")
df_full:pd.DataFrame = pickle.loads(raw_data) if raw_data else pd.DataFrame()
last_date = r.get("last_date")
last_date = last_date.decode("utf-8")
last_date = pd.to_datetime(last_date)
first_date = r.get("first_date")
first_date = first_date.decode("utf-8")
first_date = pd.to_datetime(first_date)

class SalesReportMonthly:
    def __init__(self,ld = last_date, fd=first_date,  dff = df_full):
        self.ld = pd.to_datetime(ld)
        self.fd = pd.to_datetime(fd)
        self.df :pd.DataFrame = dff
        self.init_annual_data = self.get_annual_data()
        self.init_monthly_data = self.get_monthly_data()
        self.month_marks = (
            dff[["month_id", "month_name_ru"]]  # Выбираем нужные колонки
            .drop_duplicates()                 # Убираем дубликаты (если есть)
            .sort_values("month_id")           # Сортируем по month_id
            .assign(
                value=lambda x: x["month_id"], 
                label=lambda x: x["month_name_ru"]
            )                                  # Переименовываем колонки
            [["value", "label"]]               # Оставляем только value и label
            .to_dict("records")                # Конвертируем в список словарей
        )        
        self.max_month_id = dff.month_id.max()
        
        self.short_marks = [mark.copy() for mark in self.month_marks]  # Копируем month_marks
        
        self.in_construction = dmc.Badge(
            [
            dmc.Group(
                [
                  dmc.Center(DashIconify(icon="twemoji:hammer-and-wrench")),
                  dmc.Center(' В разработке'),  
                ]                
            ),
           
            ],
            variant="outline",
            color="red",
            size="md",
            radius="xs",
        )

        
        self.cat_numbers = self.prepare_dataset(periods=[self.max_month_id-12, self.max_month_id])['fullname'].nunique()
        
        
        # Индексы месяцев, которые сохраняют label (первый, последний, середина)
        keep_indices = {
            0,  # Первый месяц
            12,
            24,
            36,
            
            self.max_month_id - 1,  # Последний месяц
            #self.max_month_id - 12,  # Середина
            # Опционально: добавить другие точки (например, 1/3 и 2/3)
            #self.max_month_id // 12,
            #2 * self.max_month_id // 3,
        }

        # Очищаем label для остальных месяцев
        for i in range(self.max_month_id):
            if i not in keep_indices:
                self.short_marks[i]["label"] = ""
                
        
        self.stores_list = dff['store_gr_name'].unique()
        self.cat_list = dff['parent_cat'].unique()
        
# ---- КОМПОНЕНТЫ СТРАНИЦЫ ---------
               

        self.header_logo = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MDAiIGhlaWdodD0iNDAwIiB2aWV3Qm94PSIwIDAgNDAwIDQwMCI+PHBhdGggZmlsbD0iIzQyNWQzNyIgZD0iTTM3Ni44MzQgMTk2LjI2MWMtMTguOTEyLTE4LjE3Mi0xMTMuNDg2LTI5LjUxNy0xNDMuMzI3LTMyLjgxOWE4OCA4OCAwIDAgMCAzLjY5Mi0xMC41OGM0LjA2OC0xLjc4IDguNDYtMy40MzggMTMtNC44MjJjLjU1MyAxLjYzMiAzLjE1OSA3Ljg4NSA0LjY0NCAxMC44NTNjNjAuMDA0IDEuNjU1IDYzLjA4NS00NC41OTEgNjUuNTI1LTU3LjI2YzIuMzg3LTEyLjM4OSAyLjI2NS0yNC4zNTkgMjIuODQ3LTQ2LjI0MWMtMzAuNjYzLTguOTM2LTc0Ljc1OSAxMy44NS04OS41MyA0Ny43NjJjLTUuNTUtMi4wOC0xMS4xMTQtMy42MTUtMTYuNjE1LTQuNTY1Yy0zLjk0My0xNS45MDUtMjQuNDc0LTYwLjIxNS03OC4zNTItNjAuMjE1Yy02OC4yMTUgMC0xNDIuNTY3IDU2LjI3Ni0xNDIuNTY3IDE1MS41NDJjMCA4MC4wNzggNTQuNjcyIDE1MC4yNTggODUuNTU5IDE1MC4yNThjMTMuNDkgMCAyNS4wOTQtMTAuMTAzIDI3LjgxOC0xOS4xNThjMi4yODQgNi4yMDkgOS4yOTIgMjUuNTEgMTEuNTkzIDMwLjQyNGMzLjQwMiA3LjI2NyAxOS4xMzQgMTMuNTU0IDI2LjAxOCA2LjAxNGM4Ljg1MiA0LjkxNyAyNS4wOTUgNy44OCAzMy45NDctNS4yMzVjMTcuMDQ5IDMuNjA2IDMyLjEyLTYuNTYgMzIuNDUtMTguNjkxYzguMzY1LS40NDcgMTIuNDY5LTEyLjE5MyAxMC42NDItMjEuNTQ3Yy0xLjM0Ni02Ljg4Ny0xNS43MzItMzEuNTk5LTIxLjM0My00MC4xM2MxMS4xMDggOS4wMzUgMzkuMjQzIDExLjU5MyA0Mi42Ni4wMDZjMTcuOTA5IDE0LjA1NyA0NS44MTcgNi42NzkgNDguMDMtNC43NTNjMjEuNzYxIDUuNjU0IDQ2LjcyLTYuNzY0IDQyLjYyMS0yMS44MDNjMzQuOTU4LTIuNDE4IDMwLjQ4My0zOS42MTEgMjAuNjc1LTQ5LjAzN3oiLz48cGF0aCBmaWxsPSIjMDNhOWY0IiBkPSJNMjc5LjQ5NCAxMTYuOTM1YzcuNTI5LTE0LjkzOCAxNi45OS0zMS4yNSAyOC45NC00MS4zNGMtMTMuMTUzIDUuMy0yNi4xMzkgMjEuMTQ2LTMzLjgxNyAzOC4wODNhMTE4IDExOCAwIDAgMC0xMS44OTMtNi42NDZjMTAuNzEtMjIuODYyIDM1LjU5OC00MS45NTUgNjMuMDI1LTQzLjQ0N2MtMTguMzcgMTYuNjYyLTExLjg1IDUxLjI5LTI2Ljk1NCA2OS42MjNjLTQuMzIyLTQuMzQyLTE0LjI0Ny0xMi43Mi0xOS4zMDEtMTYuMjczbS0xMS44NzYgMjQuMzI2Yy4wMDgtLjU3Mi4yMjItNC45ODEuNjI0LTYuOTk0Yy0xLjA1NC0uMjQ4LTcuNjAxLTEuNTI5LTExLjAxNS0xLjQ0OWMtLjI0OSA0LjI4OCAxLjgwMiAxMS41ODEgMy44MjggMTUuOTcyYzEzLjk1Ni0uMjkyIDI0LjAzNi00LjQ3MiAyOS45NjktOC4zMTRjLTUuMDUxLTIuMzU0LTEzLjY3LTQuNDQ4LTIwLjIyNC01LjdjLS43MzIgMS41MTMtMi41MzEgNS4zNjgtMy4xODIgNi40ODUiLz48ZyBzdHJva2Utd2lkdGg9IjAuOTczIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxMC45ODkgMzIuNzMpc2NhbGUoLjgxNzMzKSI+PHBhdGggZmlsbD0iIzRjYWY1MCIgZD0iTTI1MC41NCAyNzcuMzljLjAwNC4wMjQuMDE1LjA1Ny4wMTguMDgyYy0yLjE2NS00LjY1Ny00LjQ2My0xMC4zMTQtNy4yMDgtMTcuNzA4YzEwLjY4OCAxNS41NTcgNDQuMTg0IDcuNTMzIDQyLjQyNy02LjQwN2MxNi4zOTUgMTIuMzM2IDUwLjE0My0yLjA1NSA0Mi40NzEtMTkuMzUzYzE2LjQyMyA3LjY1MyAzNS4xNjgtNy43NDUgMzAuOTY0LTE0LjQ1NWMyOCA1LjQgNTQuODMyIDEwLjc4MyA2My4yNTYgMTIuOTM4Yy01LjU5NSA5LjEyMy0xOC4zMzkgMTUuNTY2LTM3LjU0OSAxMS4wODljMTAuMzggMTQuMTQtOS43NzMgMzEuMTA1LTM3Ljg0NCAyMS43NmM2LjE4IDEzLjg4My0xOC44MTQgMjYuMzgtNDcuMjIgMTEuOTFjLjM2MSAxMy44ODktMzUuMjQgMTUuNDg4LTQ5LjMxNS4xNDN6bTU1LjU0My03MC4xOTRjMzIuNDk3IDIuNDk1IDg2LjIzOCA3LjM0IDExOS41MSAxMS45OTdjLTIuMTAyLTEwLjgyOC03Ljg0NC0xMy45MjEtMjUuOTA1LTE4Ljc3MmMtMTkuNDI1IDIuMDcyLTY4LjcwNiA2LjkxMy05My42MDQgNi43NzZ6Ii8+PHBhdGggZmlsbD0iI2ZmY2EyOCIgZD0iTTI4NS43OCAyNTMuMzZjMTYuMzk1IDEyLjMzNiA1MC4xNDMtMi4wNTUgNDIuNDcxLTE5LjM1M2MxNi40MjMgNy42NTMgMzUuMTY4LTcuNzQ1IDMwLjk2NC0xNC40NTVjLTMzLjEwMy02LjM4My02Ny44NC0xMi43ODgtNzUuNzE5LTEzLjkwOGM0Ljc4LjI1NCAxMi43MDIuNzk3IDIyLjU5IDEuNTU2YzI0Ljg5OS4xMzcgNzQuMTgtNC43MDQgOTMuNjA0LTYuNzc1Yy0zMS40NTItNy45NzUtOTUuNjY2LTE5LjYxMy0xNDAuMDEtMjIuNDhjLTIuMDU1IDMuMDAzLTUuODMzIDguMDk3LTEyLjQxMyAxMy41MWMtMTkuNDAzIDQxLjA1My01NC41NTcgNjguMzQtOTMuNDU0IDY4LjM0Yy0xMS4zMzUgMC0yNC4wMTgtMS45MTItMzguMjMzLTYuNDU2Yy04Ljg2NSA5LjQ5Ny00Ni42NjEgMTYuNjk0LTc3LjMyOSAxLjY0MWMyNC4zMjYgNTYuOTYxIDgwLjc0IDk0Ljk4NCAxNDMuMTkgOTQuOTg0YzUyLjU5MSAwIDc1LjkxMi01My43MDQgNzAuODA4LTY3LjkxNGMtMS4yMzgtMy40NS02LjE0NS0xNC44ODktOC44OTEtMjIuMjgzYzEwLjY4OSAxNS41NTYgNDQuMTg1IDcuNTMyIDQyLjQyOS02LjQwOHoiLz48cGF0aCBmaWxsPSIjZTBlMGUwIiBkPSJNMjUzLjkxIDE0NS4yN2M0LjY0NC0yLjUyNiAyMC42OS0xMi4yNTMgMzUuOTgxLTE1LjkwOGE2OCA2OCAwIDAgMS0uNTM2LTUuMTJjLTEwLjAzMiAyLjQwMy0yOC45NDUgMTAuNTEtMzkuNzg0LS42NjFjMjIuODY2IDYuOSAzNC4yODMtNi4xNDkgNTEuMDktNi4xNDljMTAuMDE0IDAgMjQuMzA1IDIuNzk4IDM1LjU3IDcuMjJjLTkuMDYxLTguMzctMzguNzcyLTMzLjYzLTc1LjU1OC0zMy43MTdjLTguMjEzIDkuOTU3LTE3LjA5IDMxLjUyNi02Ljc2NCA1NC4zMzR6Ii8+PHBhdGggZmlsbD0iI2Y0MWUzNCIgZD0iTTExNS41OCAyNTMuMzNjMTQuMjE1IDQuNTQ0IDI2Ljg5OCA2LjQ1NyAzOC4yMzMgNi40NTdjMzguODk2IDAgNzQuMDUtMjcuMjkgOTMuNDU0LTY4LjM0MWMtMTQuMzUxIDExLjk3OC0zOS4yOTEgMjIuMjI4LTc4LjI0MSAyMi4yMjhjMzQuNjk0LTcuODY2IDY0LjU2LTI1LjE1NiA3OS43NTMtNTAuNDI3Yy0xMC42OC0xNi45OTgtMjIuMjYzLTU0LjYwMyA3LjA3LTg0LjMzYy00LjUxMi0xNC40OTctMjYuNDc1LTUyLjc2Ni03NS4wOTUtNTIuNzY2Yy04NC44NSAwLTE1NS4xNyA3MS4wMDEtMTU1LjE3IDE2Ni4xNWMwIDIyLjUyNSA0LjU0NyA0My42NSAxMi42NyA2Mi42NjRjMzAuNjY2IDE1LjA1NCA2OC40NjIgNy44NTggNzcuMzI3LTEuNjR6Ii8+PHBhdGggZmlsbD0iI2ZmY2EyOCIgZD0iTTE0MS4wMyAxMDguNDVjMCAyMS42NDQgMTcuNTQ2IDM5LjE5MSAzOS4xOSAzOS4xOTFzMzkuMTkyLTE3LjU0OCAzOS4xOTItMzkuMTkxcy0xNy41NDgtMzkuMTkxLTM5LjE5Mi0zOS4xOTFzLTM5LjE5IDE3LjU0Ny0zOS4xOSAzOS4xOTEiLz48cGF0aCBmaWxsPSIjNDI1ZDM3IiBkPSJNMTU2Ljc2IDEwOC40NWMwIDEyLjk1OCAxMC41MDcgMjMuNDYzIDIzLjQ2MyAyMy40NjNjMTIuOTYgMCAyMy40NjQtMTAuNTA2IDIzLjQ2NC0yMy40NjNjMC0xMi45NTktMTAuNTA0LTIzLjQ2NC0yMy40NjQtMjMuNDY0Yy0xMi45NTcgMC0yMy40NjMgMTAuNTA2LTIzLjQ2MyAyMy40NjQiLz48ZWxsaXBzZSBjeD0iMTgwLjIyIiBjeT0iOTguMDQ0IiBmaWxsPSIjZmFmYWZhIiByeD0iMTMuNjczIiByeT0iOC41MDEiLz48L2c+PC9zdmc+"

        self.theme_store = dcc.Store(id="theme-store", data={"colorScheme": "dark"})
        
        self.theme_switch = dmc.Switch(
        id="theme-switch",
        label="",
        checked=True,
        onLabel=dmc.Text("☀️", size="lg"),
        offLabel=dmc.Text("🌙", size="lg"),
        size="lg",
        radius="sm",
        color="lime",  # временно — нужный цвет зададим стилем
        style={
            "alignSelf": "center",
            "--switch-checked-bg": "rgb(165, 199, 77)",  # 💚 цвет фона когда включено
            "--switch-thumb-color": "#ffffff"            # цвет круглого бегунка
        }
        )
        
        self.logo_dark = html.Img(
        src="/static/assets/logo.png",
        height="28px",
        style={"marginRight": "0.5rem", "filter": "invert(1)"}
        )

        self.logo_light = html.Img(
        src="/static/assets/logo.png",
        height="28px",
        style={"marginRight": "0.5rem"}    
        )
         
        self.site_title = html.Div(
                [
                    html.Img(
                        src=self.header_logo,  # укоротила для примера
                        height="70px",
                        style={"marginRight": "0.5rem"}
                    ),
                    dmc.Title(f"Отчет по продажам за {str(ld.strftime('%b %Y')).capitalize()}", id='title_1', order=1, mt="lg", style={"marginBottom": 0})
                ],
                style={"display": "flex", "alignItems": "center"}
            )      
        
        
        self.alaisis_link = dmc.Anchor("Анализ продаж", href="#areachart", underline=False)
        
        self.cat_title = ''
        
        self.month_picker = dmc.MonthPickerInput(
            label="Выберите дату",
            placeholder="Укажите месяц",
            valueFormat="YYYY MMM",   
            leftSection=DashIconify(icon="fa:calendar"),
            id='month_pick',
            minDate=self.fd,  # минимальная дата
            maxDate=self.ld
        )
        
        self.sep = dmc.Divider(label=f"Обновлено {ld.strftime('%d.%m.%Y')}", labelPosition="right", color="dark", variant='dashed', size="xs")
                
        self.annotation_annual = self.init_annual_data[2]
        
        self.annotation_monthly = self.init_monthly_data[2]

        self.annual_donats = dmc.DonutChart(data=self.init_annual_data[0], 
                                            startAngle=180, 
                                            endAngle=0,
                                            id='annual_donut',
                                            #withLabelsLine=True,
                                            #withLabels=True,
                                            size=300,
	                                        thickness=30,
                                            strokeWidth=3,
                                            chartLabel=self.init_annual_data[1],
                                            
                                            
                                            )
        self.month_donats = dmc.DonutChart(data=self.init_monthly_data[0], 
                                           startAngle=180, 
                                           endAngle=0,
                                           id='monthly_donut', 
                                           #withLabelsLine=True,
                                           #withLabels=True,
                                           size=300,
	                                       thickness=30,
                                           strokeWidth=3,
                                           chartLabel=self.init_monthly_data[1],
                                           
                                           )
        
        self.title_annual = dmc.Title(f"С начала {ld.year} года", order=4, id = 'title_annual'),
        self.title_monthly = dmc.Title(f"За {str(ld.strftime('%b')).capitalize()} {ld.year} года", order=4, id = 'title_monthly'),
        
        self.bar_chart_annual = dmc.BarChart(
                h=100,
                 w=350,
                dataKey="item",
                data=self.init_annual_data[3],
                withBarValueLabel=True,
                orientation="vertical",
                yAxisProps={"width": 80},
                barProps={"radius": 50},
                series=[{"name": "Чистая выручка", "color": "violet.6"}],
                valueFormatter={'function':'formatNumberIntl'},
                               
                id = 'bar_chart_annual',
                gridAxis="none",
	            withXAxis=False,
	            #withYAxis=False,

            )
        
        self.bar_chart_monthly = dmc.BarChart(
                h=100,
                w=350,
                dataKey="item",
                data=self.init_monthly_data[3],
                withBarValueLabel=True,
                orientation="vertical",
                yAxisProps={"width": 80},
                barProps={"radius": 50},
                series=[{"name": "Чистая выручка", "color": "teal.6"}],
                valueFormatter={'function':'formatNumberIntl'},
                                
                id = 'bar_chart_monthly',
                gridAxis="none",
	            withXAxis=False,
	            #withYAxis=False,
            )
       
        self.retail_switch = dmc.Switch(
                onLabel="ON", offLabel="OFF",
                labelPosition="right",
                label="только ритейл",
                size="sm",
                radius="md",
                color="#5c7cfa",
                disabled=False,
                withThumbIndicator=True,
                id = 'retail_switch'                
            )
        
        self.online_switch = dmc.Switch(
                onLabel="ON", offLabel="OFF",
                labelPosition="right",
                label="только онлайн",
                size="sm",
                radius="md",
                color="#5c7cfa",
                disabled=False,
                withThumbIndicator=True,
                id = 'online_switch'                
            )
        
        self.percent_switch = dmc.Switch(
                onLabel="ON", offLabel="OFF",
                labelPosition="right",
                label="показать   в %",
                size="sm",
                radius="md",
                color="#5c7cfa",
                disabled=False,
                withThumbIndicator=True,
                id = 'percent_switch'                
            )
        
        self.stacked_switch = dmc.Switch(
                onLabel="ON", offLabel="OFF",
                labelPosition="right",
                label="нак. итог",
                size="sm",
                radius="md",
                color="#5c7cfa",
                disabled=False,
                withThumbIndicator=True,
                id = 'stack_switch'                
            )
        
        
        self.store_filter = dmc.MultiSelect(
            placeholder="Магазин",           
            variant="default",
            size="xs",
            radius="sm",
            data=self.stores_list,
            withAsterisk=False,
            disabled=False,
            clearable=True,
            id = 'store_filter',
        )
        self.cat_filter = dmc.MultiSelect(
            placeholder="Категория",            
            variant="default",
            size="xs",
            data=self.cat_list,
            radius="sm",
            withAsterisk=False,
            disabled=False,
            clearable=True,
            id = 'cat_filter',
        )
        
        self.switch_group = dmc.Stack(           
            children=[
                dmc.Text("Быстрые фильтры", size="sm",),
                dmc.SimpleGrid(
                    cols=6,
                    spacing="md",
	                verticalSpacing="md",                    
                    children=[
                        self.retail_switch,
                        self.online_switch,
                        self.percent_switch,
                        self.stacked_switch,
                        self.store_filter,
                        self.cat_filter
                    ]
                )
            ]
        )
        
        self.month_slider = dmc.RangeSlider(
            id="month_slider",
            value=[self.max_month_id-12, self.max_month_id],
            marks=self.short_marks,
            mb=35,
            min=1,
            max=self.max_month_id,
            minRange=2,
            labelAlwaysOn=True,
            size=10,
            mt="xl",
            styles={"thumb": {"borderWidth": 2, "padding": 3}},
            #color="red",
            thumbSize=26,
            thumbChildren=[
            DashIconify(icon="mdi:heart", width=16),
            DashIconify(icon="mdi:heart", width=16),],
            label={
                "function": "formatMonthLabel",  # Наша JS-функция
                "options": {
                    "monthDict": {  
                        month["value"]: month["label"] 
                        for month in self.month_marks
                    }
                }
            }
        )
        
        
        
        
        
        area_chart_radio_data = [["general", "Общее"], ["channel", "Каналы"], ["stores", "Магазины"], ["cats", "Категории"],['regions','Регионы']]
        
        self.area_chart_radio = dmc.Group([dmc.RadioGroup(
            children=dmc.Group([dmc.Radio(l, value=k) for k, l in area_chart_radio_data], my=10),
            id="radiogroup-simple",
            value="general",
            label="Выбирете данные",
            size="sm",
            mb=10,
        ),
        
       
        ]
        )
        
        ranging_creteria = [["revenue", "Выручка"], ["quant", "Количество"], ["margin", "Маржинальность"]]
        
        
        self.creteria_radio = dmc.Group([dmc.RadioGroup(
            children=dmc.Group([dmc.Radio(l, value=k) for k, l in ranging_creteria], my=10),
            id="radiogroup-creteria",
            value="revenue",
            label="Выбирете критерий",
            size="sm",
            mb=10,
        ),   
       
        ]
        )
        
        storing_creteria = [["all", "Все"], ["RETAIL", "Ритейл"], ["ONLINE", "Онлайн"]]
        
        
        self.storing_radio = dmc.Group([dmc.RadioGroup(
            children=dmc.Group([dmc.Radio(l, value=k) for k, l in storing_creteria], my=10),
            id="storing_radio",
            value="all",
            label="Выбирете датасет",
            size="sm",
            mb=10,
        ),   
       
        ]
        )
        
        
        self.area_chart = dmc.Box(
            [ 
                self.month_slider, 
                self.switch_group, 
                                          
                self.area_chart_radio,
                dmc.AreaChart(
                    id="areachart",
                    h=400,
                    dataKey="month",
                    data=self.build_area_chart()[0],
                    tooltipAnimationDuration=500,
                    areaProps={
                        "isAnimationActive": True,
                        "animationDuration": 500,
                        "animationEasing": "ease-in-out",
                        "animationBegin": 500,
                    },
                    series = self.build_area_chart()[1], 
                    valueFormatter={'function':'formatNumberIntl'},
                    #type="stacked",
                    withLegend=True,
                    legendProps={"verticalAlign": "bottom"},
                    type="default",
                    
                ),
            ]
        )
                    
# ---- Контейнера и разметка -------

        self.content = dmc.GridCol(
            children=[
                self.site_title,
                self.sep,
                self.month_picker,                
            ]
        )
        self.content2 = dmc.Grid(
            justify="space-between",
            children=[
                dmc.Paper(self.annual_donats, style={"width": "45%"}),  # примерно половина с отступом
                dmc.Paper(self.month_donats, style={"width": "45%"}),
            ]
        )
        
        self.titles_grid = dmc.Grid(
                        gutter="md",
                        mt="xl",    
                        children=[
                                dmc.GridCol(
                                    span=6,
                                    children=self.title_annual,
                                ),
                                dmc.GridCol(
                                    span=6,
                                    children=self.title_monthly,
                                ),
                        ]
                        
                    ),
        
        self.layout = dmc.AppShell(
            [
                dmc.AppShellHeader(
                    dmc.Group(
                        self.logo_dark,
                        id = ''
                    )
                    
                )
            ]
        )
        
# ========= Функции обработки данных ===========

    def get_annual_data(self,date=None):
        date = self.ld if date is None else date
        date = pd.to_datetime(date)
        df = self.df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year 
        start = pd.Timestamp(year=date.year, month=1, day=1)          # начало года
        end = date + pd.offsets.MonthEnd(0)                           # конец месяца для даты

        # Фильтр: даты от начала года до конца месяца включительно
        df_year = df[(df['date'] >= start) & (df['date'] <= end)]
        
                # Аналогичный период прошлого года
        prev_year_start = pd.Timestamp(year=date.year - 1, month=1, day=1)
        prev_year_end = pd.Timestamp(year=date.year - 1, month=date.month, day=1) + pd.offsets.MonthEnd(0)

        df_prev_year = df[(df['date'] >= prev_year_start) & (df['date'] <= prev_year_end)]
        
        
        sales =  df_year['dt'].sum() #/ 1_000_000
        pyear_revenue = (df_prev_year.dt.sum() - df_prev_year.cr.sum()) #/1_000_000
        ret = df_year['cr'].sum() #/ 1_000_000
        net_revenue = sales - ret        
        net_revenue_str = f"Чистая выручка ₽{net_revenue/1_000_000:,.2f} млн"
        
        annotation_annual = dmc.List(
            size="sm",
            spacing="sm",
            children= [
                dmc.ListItem(f'Продажи ₽{sales/1_000_000:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="icon-park-outline:sales-report", width=16),
                radius="xl",
                color="blue",
                size=30,
            ),),
            dmc.ListItem(f'Возвраты ₽{ret/1_000_000:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="gridicons:refund", width=16),
                radius="xl",
                color="blue",
                size=30,
            ),),
            dmc.ListItem(f'Чистая выручка ₽{net_revenue/1_000_000:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="game-icons:profit", width=16),
                radius="xl",
                color="blue",
                size=30,
            ),),
            dmc.ListItem(f'Процент возвратов {ret/sales*100:,.2f}% ',icon=dmc.ThemeIcon(
                DashIconify(icon="arcticons:appsales", width=16),
                radius="xl",
                color="blue",
                size=30,
            ),),
            ]
        )
        
        data = [
            {'name':'Продажи', 'value':float(sales),"color": "indigo.6"},
            {'name':'Возвраты', 'value':float(ret),"color": "yellow.6"}
        ]
        
        bar_data = [
            {'item':f'Факт {date.month} мес {date.strftime("%y")}','Чистая выручка':float(net_revenue)},
            {'item':f'План {date.month} мес {date.strftime("%y")}','Чистая выручка':float(net_revenue)},
            {'item':f'Факт {date.month} мес {(date.year -1) % 100:02d}','Чистая выручка':float(pyear_revenue)},
            
        ]
        
        return data,net_revenue_str,annotation_annual,bar_data
    
    def get_monthly_data(self,date=None):
        date = self.ld if date is None else date
        date = pd.to_datetime(date)        
        date_minus_one_year = date - pd.DateOffset(years=1)
        start_prev_year_month = pd.Timestamp(year=date_minus_one_year.year, month=date_minus_one_year.month, day=1)
        end_prev_year_date = date_minus_one_year + pd.offsets.MonthEnd(0)
        df = self.df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month 
        df_mom = df[(df['date'] >= start_prev_year_month) & (df['date'] <= end_prev_year_date)]   

  
        pyear_revenue = (df_mom.dt.sum() - df_mom.cr.sum()) #/1_000_000 
        
        
        year = date.year           
        month = date.month        
        df_year = df[(df['date'].dt.year == year) & (df['date'].dt.month == month)]
 

        
        sales =  df_year['dt'].sum() #/ 1_000_000
        ret = df_year['cr'].sum() #/ 1_000_000
        net_revenue = sales - ret        
        net_revenue_str = f"Чистая выручка ₽{net_revenue/1_000_000:,.2f} млн"
        
        data = [
            {'name':'Продажи', 'value':sales,"color": "teal.6"},
            {'name':'Возвраты', 'value':ret,"color": "gray.6"}
        ]
        bar_data = [
            {'item':f'Факт {date.strftime("%b%y")}','Чистая выручка':float(net_revenue)},
            {'item':f'План {date.strftime("%b%y")}','Чистая выручка':float(net_revenue)},
            {'item':f'Факт {date_minus_one_year.strftime("%b%y")}','Чистая выручка':float(pyear_revenue)},
            
        ]
        
        annotation_monthly = dmc.List(
            size="sm",
            spacing="sm",
            children= [
                dmc.ListItem(f'Продажи ₽{sales/1_000_000:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="icon-park-outline:sales-report", width=16),
                radius="xl",
                color="teal.6",
                size=30,
            ),),
            dmc.ListItem(f'Возвраты ₽{ret/1_000_000:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="gridicons:refund", width=16),
                radius="xl",
                color="teal.6",
                size=30,
            ),),
            dmc.ListItem(f'Чистая выручка ₽{net_revenue/1_000_000:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="game-icons:profit", width=16),
                radius="xl",
                color="teal.6",
                size=30,
            ),),
            dmc.ListItem(f'Процент возвратов {ret/sales*100:,.2f}% ',icon=dmc.ThemeIcon(
                DashIconify(icon="arcticons:appsales", width=16),
                radius="xl",
                color="teal",
                size=30,
            ),),
            ]
        )
        
        
        return data,net_revenue_str,annotation_monthly, bar_data
        
    def build_area_chart(self,periods=None,option='general',retail=None,online=None,store_filter=None,cat_filter=None,percent_switch=None):
        
        selected_range = [self.max_month_id-11,self.max_month_id] if periods is None else periods
        
        df = self.df[
            (self.df['month_id'] >= selected_range[0]) & 
            (self.df['month_id'] <= selected_range[1])
        ].copy()
        
        # Фильтрация по каналу продаж
        if retail and online is None:
            df = df[df['chanel_name'] == 'RETAIL']  # Исправлено: было присваивание вместо сравнения
        elif online and retail is None:
            df = df[df['chanel_name'] == 'ONLINE']
        elif online and retail:        
            df = df[df['chanel_name'].isin(['RETAIL', 'ONLINE'])]
        else:
            # Если ни один не выбран - оставляем все каналы
            pass
        
        if store_filter:
           df = df[df['store_gr_name'].isin(store_filter)] 
        
        if cat_filter:
           df = df[df['parent_cat'].isin(cat_filter)] 
        
        df['date'] = pd.to_datetime(df.date)
        df['me'] = df['date'] + pd.offsets.MonthEnd(0)       
        
        df['amount'] = df.dt - df.cr
        
        if option == 'general':
           df = df.pivot_table(
               index='me',
               values=['dt','cr','amount'],
               aggfunc='sum'                              
           ).fillna(0)
           if percent_switch:                
                df['amount'] = df['amount'] / df['dt'] * 100
                df['cr'] = df['cr'] / df['dt'] * 100
                df['dt'] = df['dt'] / df['dt'] * 100
           df = df.reset_index() 
           df = df.sort_values(by='me')
           df = df[df['amount'] > 0]
           df = df.rename(columns={'amount':'Чистая выручка','dt':'Продажи','cr':'Возвраты'})
           df['month'] = df.me.dt.strftime('%b %y')
           data = df.to_dict(orient='records')
           columns = [col for col in df.columns if col not in ['month','me'] ]       
           series = [
            {"name": col, "color": mantine_colors[i % len(mantine_colors)]}
            for i, col in enumerate(columns)
           ]
           return data, series
        
        elif option == 'channel':
             df = df.pivot_table(
               index='me',
               columns='chanel_name',
               values='amount',
               aggfunc='sum'                              
           ).fillna(0)
             cols_to_keep = [col for col in df.columns if df[col].sum() != 0]
             df = df[cols_to_keep]
             if percent_switch:
                df = df.div(df.sum(axis=1), axis=0).fillna(0) * 100               
             df = df.reset_index() 
             df = df.sort_values(by='me')
             
             df['month'] = df.me.dt.strftime('%b %y')
                    
        
             data = df.to_dict(orient='records')
             columns = [col for col in df.columns if col not in ['month','me'] ]       
             series = [
                {"name": col, "color": mantine_colors[i % len(mantine_colors)]}
                for i, col in enumerate(columns)
             ]
             return data, series
         
        elif option == 'stores':
             df = df.pivot_table(
               index='me',
               columns='store_gr_name',
               values='amount',
               aggfunc='sum'                              
           ).fillna(0)
             
             cols_to_keep = [col for col in df.columns if df[col].sum() != 0]
             df = df[cols_to_keep]
             if percent_switch:
                df = df.div(df.sum(axis=1), axis=0).fillna(0) * 100  
             df = df.reset_index() 
             df = df.sort_values(by='me')

             df['month'] = df['me'].dt.strftime('%b %y')
        
             data = df.to_dict(orient='records')
             columns = [col for col in df.columns if col not in ['month','me'] ]       
             series = [
                {"name": col, "color": mantine_colors[i % len(mantine_colors)]}
                for i, col in enumerate(columns)
             ]
             return data, series
        
        elif option == 'cats':
             df = df.pivot_table(
               index='me',
               columns='parent_cat',
               values='amount',
               aggfunc='sum'                              
           ).fillna(0)
             cols_to_keep = [col for col in df.columns if df[col].sum() != 0]
             df = df[cols_to_keep]
             if percent_switch:
                df = df.div(df.sum(axis=1), axis=0).fillna(0) * 100  
             df = df.reset_index() 
             df = df.sort_values(by='me')
             
             df['month'] = df.me.dt.strftime('%b %y')
                    
        
             data = df.to_dict(orient='records')
             columns = [col for col in df.columns if col not in ['month','me'] ]       
             series = [
                {"name": col, "color": mantine_colors[i % len(mantine_colors)]}
                for i, col in enumerate(columns)
             ]
             return data, series
         
        elif option == 'regions':
             df = df.pivot_table(
               index='me',
               columns='region',
               values='amount',
               aggfunc='sum'                              
           ).fillna(0)
             if percent_switch:
                df = df.div(df.sum(axis=1), axis=0).fillna(0) * 100   
             df = df.reset_index() 
             df = df.sort_values(by='me')
             
             df['month'] = df.me.dt.strftime('%b %y')
                    
        
             data = df.to_dict(orient='records')
             columns = [col for col in df.columns if col not in ['month','me'] ]       
             series = [
                {"name": col, "color": mantine_colors[i % len(mantine_colors)]}
                for i, col in enumerate(columns)
             ]
             return data, series
    
    def make_cat_area_data(self, periods=None, df: pd.DataFrame = None, parent_cat: dict = None):
        def getting_levels(parent_cat):
            parent_cat = parent_cat['points'][0]
            cur_path = parent_cat.get('currentPath', None)   
            entry = parent_cat.get('entry',None)
            parent = parent_cat.get('parent',None)            
            root = parent_cat.get('root',None)                   
            lev_id = parent_cat.get('id', None)
            parts = lev_id.split('/') if lev_id else []
            #print('root:',root,'cur_path:',cur_path,'parts:',parts,'entry:',entry,'parent:',parent)
            
            return len(parts), parts, parent, entry, cur_path

            

        selected_range = [self.max_month_id - 11, self.max_month_id] if periods is None else periods

        df = self.df[
            (self.df['month_id'] >= selected_range[0]) &
            (self.df['month_id'] <= selected_range[1])
        ].copy()

        df['date'] = pd.to_datetime(df.date)
        df['me'] = df['date'] + pd.offsets.MonthEnd(0)
        df['amount'] = df.dt - df.cr
        

        # Определяем уровень фильтрации и группировки
        cols = 'parent_cat'
        if parent_cat:
            level, parts, parent, entry, cur_path  = getting_levels(parent_cat)
            
            if entry != '' and entry != parts[0]:                
                level = level - 1 
            if entry != '' and entry == parts[0] and len(parts) == 1: 
                level = level - 1 
            
            
            print('level',level,parts,entry)

            if level == 0:
                df = df.pivot_table(
                    index='me',
                    columns='parent_cat',
                    values='amount',
                    aggfunc='sum'
                ).fillna(0) 
            
            elif level == 1:
                df = df[df['parent_cat'] == parts[0]]
                df = df.pivot_table(
                    index='me',
                    columns='cat_name',
                    values='amount',
                    aggfunc='sum'
                ).fillna(0) 
            elif level == 2: 
                df = df[df['parent_cat'] == parts[0]]
                df = df[df['cat_name'] == parts[1]]
                df = df.pivot_table(
                    index='me',
                    columns='sub_cat',
                    values='amount',
                    aggfunc='sum'
                ).fillna(0) 
            elif level == 3:
                df = df[df['parent_cat'] == parts[0]]
                df = df[df['cat_name'] == parts[1]]
                df = df[df['sub_cat'] == parts[2]]
                df = df.pivot_table(
                    index='me',
                    columns='sub_cat',
                    values='amount',
                    aggfunc='sum'
                ).fillna(0) 
            
                
        else:
            df = df.pivot_table(
                    index='me',
                    columns='parent_cat',
                    values='amount',
                    aggfunc='sum'
                ).fillna(0) 
                
        
        # # Пивотим
        # df = df.pivot_table(
        #     index='me',
        #     columns='parent_cat',
        #     values='amount',
        #     aggfunc='sum'
        # ).fillna(0)

        # Удаляем пустые категории
        cols_to_keep = [col for col in df.columns if df[col].sum() != 0]
        df = df[cols_to_keep]

        # Финальная подготовка
        df = df.reset_index()
        df = df.sort_values(by='me')
        df['month'] = df.me.dt.strftime('%b %y')

        data = df.to_dict(orient='records')
        columns = [col for col in df.columns if col not in ['month', 'me']]

        series = [
            {"name": col, "color": mantine_colors[i % len(mantine_colors)]}
            for i, col in enumerate(columns)
        ]

        return data, series
            
            
        
    
    
    def get_sub_cat(self, cat_list=None):  # Лучше использовать None как значение по умолчанию
        if not cat_list:  # Проверка на None и пустой список
            return []
        
        df = self.df.copy()
        
        # Безопасная фильтрация (на случай отсутствия колонок)
        try:
            filtered_df = df[df['parent_cat'].isin(cat_list)]
            return filtered_df['cat_name'].unique().tolist()
        except KeyError:
            print("Ошибка: отсутствуют колонки 'parent_cat' или 'cat_name'")
            return []
        
    def get_add_cat(self,subcat=None):
        if not subcat:  # Проверка на None и пустой список
            return []
        
        df = self.df.copy()
        
        # Безопасная фильтрация (на случай отсутствия колонок)
        try:
            filtered_df = df[df['cat_name'].isin(subcat)]
            return filtered_df['sub_cat'].unique().tolist()
        except KeyError:
            print("Ошибка: отсутствуют колонки 'parent_cat' или 'cat_name'")
            return []
           
    def prepare_dataset(self,periods=None, cat_filter=None, subcat_filter=None,add_cat_filter=None,f_filter='all'):
        selected_range = [self.max_month_id-11,self.max_month_id] if periods is None else periods
        
        df = self.df[
            (self.df['month_id'] >= selected_range[0]) & 
            (self.df['month_id'] <= selected_range[1])
        ].copy()
        
        if cat_filter:
           df = df[df['parent_cat'].isin(cat_filter)] 
           
        if subcat_filter:
            df = df[df['cat_name'].isin(subcat_filter)]  
        
        if add_cat_filter:
            df = df[df['sub_cat'].isin(add_cat_filter)]  
        
        if f_filter == 'all':
            return df
        else:
            return df[df['chanel_name']==f_filter]
    
    def prepare_matrix(self,df:pd.DataFrame,a=25,b=25,x=100,y=200):
        
        
        if df.empty:
            return pd.DataFrame()
        
        a = a
        x_limit = x / 100
        y_limit = y / 100
        
        xyz_df = df[df['dt'] > 0].copy()

        # Создаем уникальный период "год-месяц" для правильной группировки
        xyz_df['year_month'] = xyz_df['date'].dt.strftime('%Y-%m')  # Формат "2023-01"

        xyz = xyz_df.pivot_table(
            index=['parent_cat', 'cat_name', 'fullname'],
            columns='year_month',
            values='quant_dt',
            aggfunc='sum',
            fill_value=0
        )

        # Рассчитываем статистики
        xyz['xyz_mean'] = xyz.mean(axis=1)
        xyz['xyz_std'] = xyz.std(axis=1)

        # Безопасный расчет коэффициента вариации
        mask = (xyz['xyz_mean'] > 0) & xyz['xyz_std'].notna()
        xyz['cv'] = np.where(mask, xyz['xyz_std'] / xyz['xyz_mean'], np.nan)

        # XYZ-классификация (можно настроить пороги)
        conditions = [
            (xyz['cv'].notna()) & (xyz['cv'] < x_limit),  # X - стабильные
            (xyz['cv'].notna()) & (xyz['cv'] >= x_limit) & (xyz['cv'] < y_limit),  # Y - сезонные
            (xyz['cv'].notna()) & (xyz['cv'] >= y_limit)  # Z - нестабильные
        ]

        choices = ['X', 'Y', 'Z']

        xyz['xyz_class'] = np.select(conditions, choices, default='N/A')
        
        xyz_stats = xyz[['xyz_mean', 'xyz_std', 'cv', 'xyz_class']].reset_index()
        
        
        # Основная группировка (все записи)
        grouped = df.groupby(['parent_cat', 'cat_name', 'fullname'])
        
        # 1. Основные метрики (все записи)
        main_stats = grouped.agg({
            'dt': 'sum',
            'cr': 'sum',
            'quant_dt': 'sum',
            'quant_cr': 'sum',
            'date': ['min', 'max']
        })
        main_stats.columns = ['_'.join(col) for col in main_stats.columns]
        
        # 2. Статистики по ценам (только dt > 0)
        sales_df = df[df['dt'] > 0].copy()
        if not sales_df.empty:
            sales_df['price'] = sales_df['dt'] / sales_df['quant_dt'].replace(0, 1)
            price_stats = sales_df.groupby(['parent_cat', 'cat_name', 'fullname'])[['price', 'quant_dt']].agg(
                ['min', 'max', 'mean', 'median']
            )
            price_stats.columns = [f'{col[0]}_{col[1]}' for col in price_stats.columns]

            
            # Объединение с сохранением всех строк
            result = main_stats.join(price_stats, how='left')
        else:
            result = main_stats.copy()
            for col in ['price_min', 'price_max', 'price_mean', 'price_median']:
                result[col] = None
        
        result = result.merge(xyz_stats, on=['parent_cat', 'cat_name', 'fullname'], how='left')
        # Добавляем расчетные поля
        result = result.reset_index()
        result['amount'] = result['dt_sum'] - result['cr_sum']
        result['quant'] = result['quant_dt_sum'] - result['quant_cr_sum']
        result['return_ratio'] = np.where(
            result['cr_sum'] == 0, np.nan, result['cr_sum'] / result['dt_sum'] * 100  
        )
        
        tot_amount =  result['amount'].sum()
        result['amount_share'] = result['amount'] / tot_amount * 100
        result = result.sort_values(by='amount_share',ascending=False)
        result['amount_cum'] =  result['amount_share'].cumsum()
        result['date_min'] =  result['date_min'].dt.strftime('%d %b %Y')  
        result['date_max'] =  result['date_max'].dt.strftime('%d %b %Y')              
        
        if len(result) < 4:
            result['abc_rank'] = None  # Используем None вместо np.nan для строковых значений
        else:
           
            conditions = [
                (result['amount_cum'] <= a),
                (result['amount_cum'] > a) & (result['amount_cum'] <= (a+b)),
                (result['amount_cum'] > b)
            ]
            choices = ['A', 'B', 'C'] 
            
            # Вариант 1: Используем строковое значение по умолчанию
            result['abc_rank'] = np.select(conditions, choices, default=None)
        
        result['tot_rank'] = np.where(
            result['xyz_class'].notna, result['abc_rank'].astype(str) + result['xyz_class'].astype(str),np.nan
        )
        return result
        
    def make_price_distribution(self, df: pd.DataFrame, bins_n=7):
        if df.empty:
            return None
        
        n = len(df)
        bins = int(1 + np.log2(n)) if n > 0 else 5
        
        dff = df.copy()
        price_col = 'price_median'
        quant_col = 'quant'
        
        # Определяем границы бинов
        min_price = dff[price_col].min()
        max_price = dff[price_col].max()
        bin_edges = np.linspace(min_price, max_price, bins + 1)
        
        # Создаем понятные подписи для бинов
        bin_labels = []
        for i in range(bins):
            if i == 0:
                label = f"менее ₽{bin_edges[i+1]/1_000:,.1f} тыс"
            elif i == bins_n - 1:
                label = f"более ₽{bin_edges[i]/1_000:,.1f} тыс"
            else:
                label = f"от ₽{bin_edges[i]//1_000:,.1f} до ₽{bin_edges[i+1]/1_000:,.1f} тыс"
            bin_labels.append(label)
        
        # Применяем бины
        dff['bins'] = pd.cut(
            dff[price_col],
            bins=bin_edges,
            labels=bin_labels,
            include_lowest=True
        )
        
        # Группируем и суммируем количество
        result = dff.groupby('bins', observed=True)[quant_col].sum().reset_index()
        result_revenue = dff.groupby('bins', observed=True)['amount'].sum().reset_index()
        # Добавляем столбец с границами бинов для сортировки
        result['bin_order'] = result['bins'].apply(
            lambda x: float(
                x.split('₽')[-1]  # Берем часть после знака рубля
                .replace('тыс', '')  # Удаляем "K"
                .split()[0]       # Берем первое число (для "от X до Y")
                .strip()
            )
        )
        result = result.sort_values('bin_order').drop('bin_order', axis=1)
        
        return result, result_revenue

    def make_month_slider(self,id):
            return dmc.RangeSlider(
            id=id,
            value=[self.max_month_id-12, self.max_month_id],
            marks=self.short_marks,
            mb=35,
            min=1,
            max=self.max_month_id,
            minRange=2,
            labelAlwaysOn=True,
            size=10,
            mt="xl",
            styles={"thumb": {"borderWidth": 2, "padding": 3}},
            #color="red",
            thumbSize=26,
            thumbChildren=[
            DashIconify(icon="mdi:heart", width=16),
            DashIconify(icon="mdi:heart", width=16),],
            label={
                "function": "formatMonthLabel",  # Наша JS-функция
                "options": {
                    "monthDict": {  
                        month["value"]: month["label"] 
                        for month in self.month_marks
                    }
                }
            }
        )
    
    def make_sunburst_cat(self,df:pd.DataFrame=None,option='revenue'):
        if df is None:
            df = self.prepare_dataset()

        df['revenue'] = df.dt - df.cr
        df['quant'] = df.quant_dt - df.quant_cr

        if option == 'equ':  # равные доли
            dff = df[['parent_cat', 'cat_name', 'sub_cat']].drop_duplicates()
            fig = px.sunburst(
                dff,
                path=["parent_cat", "cat_name", "sub_cat"]
                # без values → равные доли
            )
        else:
            dff = df.pivot_table(
                index=['parent_cat', 'cat_name', 'sub_cat'],
                values=option,
                aggfunc='sum'
            ).fillna(0).reset_index()

            fig = px.sunburst(
                dff,
                path=["parent_cat", "cat_name", "sub_cat"],
                values=option
            )

        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        return fig
            
    
    
def create_dash_app_test():
    _dash_renderer._set_react_version("18.2.0")
    app = dash.Dash(__name__, external_stylesheets=dmc.styles.ALL,suppress_callback_exceptions=True,requests_pathname_prefix='/my-dash-app-test/') #requests_pathname_prefix='/my-dash-app-test/'
    
    srm =  SalesReportMonthly()
    initial_theme = "dark"
    dmc.add_figure_templates(default="mantine_dark")
    
    # ======== Компоненты ============
       
    
    theme_switch1 = dmc.Switch(
        id="color-scheme-toggle",
        label="",
        checked=True,
        onLabel=dmc.Text("☀️", size="lg"),
        offLabel=dmc.Text("🌙", size="lg"),
        size="lg",
        radius="sm",
        color="lime",  # временно — нужный цвет зададим стилем
        style={
            "alignSelf": "center",
            "--switch-checked-bg": "rgb(165, 199, 77)",  # 💚 цвет фона когда включено
            "--switch-thumb-color": "#ffffff"            # цвет круглого бегунка
        }
        )

    
    
    # ===== Компоненты анализа категорий =======
    
    cat_title =  dmc.Title("АНАЛИЗ КАТЕГОРИЙ", c="blue",id = 'cat_title',order=2)
    
    cat_analisis_title = dmc.Title("Описание" ,order=5)
    
    cat_analisis_text = dmc.Text(
    [
        "Анализ категорий необходим для понимания общей тенденции ассортимента в разрезе выручки и количества проданных товаров. Более детальный анализ см. в ",
        dmc.Button(
                            "ассортиментной матрице",
                            id="scroll_link",
                            variant="subtle",
                            #compact=True,
                            color="blue",
                            styles={"root": {"padding": 0}},
                        ),
            "."
    ],
    size='xs' 
    )
    
   
    
    cat_slider = srm.make_month_slider('cat_slider')   
    
    donut_raging = [["revenue", "Выручка"], ["quant", "Количество"], ["equ", "Равные доли"]]
    area_raging = [["revenue", "Выручка"], ["quant", "Количество"],]
    
    donut_radio = dmc.RadioGroup(
            children=dmc.Group([dmc.Radio(l, value=k) for k, l in donut_raging], my=10),
            id="donuts_radio",
            value="revenue",
            label="Выбирете отображение",
            size="sm",
            mb=10,
        )  
    
    cat_sunburst = dcc.Graph(
        id = 'cat_sunburst',
        figure=srm.make_sunburst_cat()        
    ) 
    
    cat_area_radio = dmc.RadioGroup(
            children=dmc.Group([dmc.Radio(l, value=k) for k, l in area_raging], my=10),
            id="cat_area_radio",
            value="revenue",
            label="Выбирете отображение",
            size="sm",
            mb=10,
        )   
   
    
    cat_area = dmc.AreaChart(
                    id="cat_area",
                    h=450,
                    dataKey="month",
                    data=srm.make_cat_area_data()[0],
                    tooltipAnimationDuration=500,
                    areaProps={
                        "isAnimationActive": True,
                        "animationDuration": 500,
                        "animationEasing": "ease-in-out",
                        "animationBegin": 500,
                    },
                    series = srm.make_cat_area_data()[1], 
                    valueFormatter={'function':'formatNumberIntl'},
                    #type="stacked",
                    withLegend=True,
                    legendProps={"verticalAlign": "bottom"},
                    type="default",
                    
                )
    
    
    
    charts_boxes = dmc.Box(
        children=[
            cat_slider,  # Заглушка
            dmc.Grid([
                dmc.GridCol(
                    dmc.Stack(
                        children=[
                            donut_radio,  # Заглушка
                            cat_sunburst,
                        ]
                    ),
                    span=5
                ),
                dmc.GridCol(
                    dmc.Stack(
                        children=[
                            cat_area_radio,
                            cat_area,
                        ]
                    ),
                    span=7
                ),              
                
            ],
                     gutter='xl'
                     )
        ]
    )
        
    
    cat_analisis_box = dmc.Container(
        children=[
            cat_title,
            dmc.Space(h=30),
            dmc.Stack(
                children=[
                    cat_analisis_title,
                    cat_analisis_text,
                    charts_boxes,
                    dmc.Space(h=60),
                ]
            )
        ],
        fluid=True
    )
    
    # ===== Callbacks категория анализ ========
    
    @app.callback(
    Output("cat_area", "data"),
    Output("cat_area", "series"),
    Input("cat_sunburst", "clickData"),
    )
    def updtae_area_chart(val):
        print("Callback triggered")
        print(val)
        data, series = srm.make_cat_area_data(parent_cat=val)
        return data, series
    
    # ===== month slider ======
    @app.callback(
        Output("cat_sunburst", "figure"),        
        Input("cat_slider", "value"),
        Input("donuts_radio", "value"),       
        
        prevent_initial_call=True
    )
    def updtae_area_chart(val,opt):
        ds = srm.prepare_dataset(periods=val)
        figure = srm.make_sunburst_cat(df=ds,option=opt)  
        return figure
    
    
    
    
    # ===== Компоненты матрицы =========
    matrix_title =  html.Div(dmc.Title("АССОРТИМЕНТНАЯ МАТРИЦА", c="blue",order=2),id = 'matrix_title')
    
    abc_group = dmc.Stack([
    dmc.Title('ABC настройки',order=5),
    dmc.NumberInput(
        label="Для категории A",       
        description="Топ продаж в процентах:",
        value=25,
        min=0,
        step=5,
        leftSection=DashIconify(icon="fa6-solid:weight-scale"),
        w=200,
        suffix="%",
        id = 'cat_a'
    ),
    dmc.NumberInput(
        label="Для категории B",
        description="Следующия группа продаж",
        value=25,
        min=0,
        step=5,
        leftSection=DashIconify(icon="fa6-solid:weight-scale"),
        w=200,
        suffix="%",
        id = 'cat_b'
    ),
    dmc.NumberInput(
        label="Для категории C",
        description="Остальные: ",
        value=50,
        min=0,
        step=5,
        leftSection=DashIconify(icon="fa6-solid:weight-scale"),
        w=200,
        suffix="%",
        id = 'cat_c',
        disabled=True,
    ),    
    ]                          
                          )
    
    xyz_group = dmc.Stack([
    dmc.Title('XYZ настройки',order=5),
    dmc.NumberInput(
        label="Для категории X",       
        description="CV меньше или равно",
        value=100,
        min=0,
        step=5,
        leftSection=DashIconify(icon="fa6-solid:weight-scale"),
        w=200,
        suffix="%",
        id = 'cat_x'
    ),
    dmc.NumberInput(
        label="Для категории Y",
        description="CV от X до ",
        value=200,
        min=0,
        step=5,
        leftSection=DashIconify(icon="fa6-solid:weight-scale"),
        w=200,
        suffix="%",
        id = 'cat_y'
    ),
    dmc.NumberInput(
        label="Для категории Z",
        description="CV больше",
        value=200,
        min=0,
        step=5,
        leftSection=DashIconify(icon="fa6-solid:weight-scale"),
        w=200,
        suffix="%",
        id = 'cat_z',
        disabled=True,
    ),    
    ]
    )
    
    cat_filter = dmc.MultiSelect(
            placeholder="Категория",      
            label="Выбирите категорию",        
            variant="default",
            size="xs",
            data=srm.cat_list,
            radius="sm",
            withAsterisk=False,
            disabled=False,
            clearable=True,
            id = 'cat_filter',
        )
    
    sub_cat_filter = dmc.MultiSelect(
            placeholder="Подкатегория", 
            label="Выбирите подкатегию",           
            variant="default",
            size="xs",
            data=[],
            radius="sm",
            withAsterisk=False,
            disabled=False,
            clearable=True,
            id = 'sub_cat_filter',
        )
    
    add_cat_filter = dmc.MultiSelect(
            placeholder="Доп категория", 
            label="Выбирите доп категорию",           
            variant="default",
            size="xs",
            data=[],
            radius="sm",
            withAsterisk=False,
            disabled=False,
            clearable=True,
            id = 'add_cat_filter',
        )
    
    
    cat_options_groups = dmc.Stack(
        [
            dmc.Title('Выбор категорий и подкатегорий', order=5),
            dmc.SimpleGrid(
                cols=3,
                spacing="md",
                verticalSpacing="md",
                children=[
                    cat_filter,
                    sub_cat_filter,  
                    add_cat_filter 
                ],),
            
            dmc.SimpleGrid(
                        cols=1,
                        verticalSpacing="md",
                        children=[dmc.Title('Датасет по продажам', order=5),
                                  srm.storing_radio,                                  
                                  ],
                        
            ), 
            
        ]
    )
    
    calc_btn = dmc.Indicator(
         dmc.Button(
            "Расчитать матрицу",
            justify="center",
            fullWidth=True,
            #leftSection=icon,
            #rightSection=icon,
            variant="outline",
            id = 'calc_button'
        ),
        #inline=True,
        size=16,
        label=f"{srm.cat_numbers} номенклатур", 
        processing=True,
        withBorder=True,
        position="top-center",
        id = 'noms_ind'
        
    )
    
    matrix_box = dmc.Box(
        children=[dmc.Grid(
            children=[
                dmc.GridCol(abc_group, span=3),
                dmc.GridCol(xyz_group, span=3),
                dmc.GridCol(cat_options_groups, span=6),                
            ],
            gutter='xl'
            
        ), 
        dmc.Title('Вибирите период анализа', order=5),
        srm.month_slider,
        calc_btn,        
        ]
    ) 
    
    # ======= Тримап по матрице ========
    
    TreeMap_box = dmc.Box(
        children=[        
        dmc.Title('Анализ матрицы', order=3, c='blue'),
        dcc.Graph(figure=px.treemap(), id = 'tree_map',)
        ],
        px=20 
    )
    
    
    # ========= Ценовое распределение =========
    
    Price_distribution_chart = dmc.BarChart(
    h=300,
    dataKey="bins",  # должно соответствовать названию столбца с бинами
    data=[],
    series=[],
    tickLine="xy",
    gridAxis="x",
    withXAxis=True,
    withYAxis=True,
    id='pd_chart',
    style={"marginBottom": 60},   
    yAxisLabel="Количество",
    
    
   
)
    
    Price_distribution_chart_revenue = dmc.BarChart(
    h=300,
    dataKey="bins",  # должно соответствовать названию столбца с бинами
    data=[],
    series=[{"name": "Выручка", "color": "teal.6", "dataKey": "Выручка"}],
    tickLine="xy",
    gridAxis="x",
    withXAxis=True,
    withYAxis=True,
    id='pd_chart_revenue',
    valueFormatter={'function':'formatNumberIntl'},
    style={"marginBottom": 60},
    yAxisLabel="Выручка",
)
   
    
    mx_store = dcc.Store(id='matrix_store')
    
    price_distibution_box = dmc.Box(
        children=[
            mx_store,          
            dmc.SimpleGrid(
                cols=2,
                children=[
                    dmc.Stack(
                        children = [
                            dmc.Title('Распределение количество по ценовому диапазону',order=5),
                            dmc.Text('График ниже показывае распредления количества проданных товаров по ценовым диапазонам. График нужен что бы оценить различные ценовые сегменты в выбранной матрице',size='xs'),
                            Price_distribution_chart,
                        ]
                    ),
                    dmc.Stack(
                        children = [
                            dmc.Title('Распределение выручки по ценовому диапазону',order=5),
                            Price_distribution_chart_revenue,
                        ]
                    )
                   
                   
                ],
                spacing="xl",
                
            )
        ],
        my="xl", 
    )
    
    
    
    # ========= Data Table (AG GRID) ==========
    
    columnDefs = [
    {
        "field": "fullname", 
        "headerName": "Товар",
        "pinned": "left",
        "lockPosition": True, 
        "width": 400,
        "cellStyle": {"fontWeight": "bold"},
        "filter": True
    },
    {
        "headerName": "Продажи",  # Родительская группа
        "marryChildren": True,   # Колонки двигаются вместе
        "children": [            # Вложенные колонки
            {
                "field": "amount",
                "headerName": "Выручка",
                "type": "numericColumn",
               
                "valueFormatter": {"function": "params.value ? '₽' + d3.format('(,.0f')(params.value) : ''"},
                "filter": True,
                "width": 180,
                'columnGroupShow': 'open',
                 "headerTooltip": "Продажи минус возвраты",
            },
            {
                "field": "amount_share",
                "headerName": "Доля в выручки",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) + '%' : ''"},
                "width": 180,
                'columnGroupShow': 'open',
                 "headerTooltip": "Доля в общей выручки по выбраным категориям и диапозону",
                
            },
            {
                "field": "amount_cum",
                "headerName": "Доля накоп.",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) + '%' : ''"},
                "width": 180,
                'columnGroupShow': 'open',
                "headerTooltip": "Накопленная доля в общей выручки по выбраным категориям и диапозону исходя из сортировки долей в убывающем порядке",
                
            },
                                    
            {
                "field": "dt_sum",
                "headerName": "Продажи",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? '₽' + d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'closed'
            },
            {
                "field": "cr_sum",
                "headerName": "Возвраты",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? '₽' + d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                "cellStyle": {"color": "red"},
                'columnGroupShow': 'closed'
            },
            {
                "field": "return_ratio",
                "headerName": "K возвратов",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) + '%' : ''"},
                "width": 120,
                'columnGroupShow': 'closed',
                "cellStyle": {"color": "red"},
            },
            
            
        ]
    },
    {
     "headerName": "Количество",  # Родительская группа
        "marryChildren": True,   # Колонки двигаются вместе
        "children": [            # Вложенные колонки   
             {
                "field": "quant",
                "headerName": "Общее",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'open',
            },
              {
                "field": "quant_dt_sum",
                "headerName": "Продано",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'open',
            },
              {
                "field": "quant_cr_sum",
                "headerName": "Возвращено",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'open',
                "cellStyle": {"color": "red"},
            },
              #  xyz_stats = xyz[['xyz_mean', 'xyz_std', 'xyz_cv', 'xyz_class']].reset_index()
              {
                "field": "xyz_mean",
                "headerName": "Ср в мес",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'closed',
                 "headerTooltip": "Средние количество за 1 календарный месяц по товару в выбраном диапозоне",
                
            },
              {
                "field": "quant_dt_max",
                "headerName": "Макс. продажи",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'closed',
                 "headerTooltip": "Максимальное количество единоразово проданого товара",
                
            },
              {
                "field": "xyz_std",
                "headerName": "Ст. отклонение",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'closed',
                
            },
               {
                "field": "cv",
                "headerName": "К-т вариации",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? d3.format(',.2f')(params.value) : ''"},
                "width": 120,
                'columnGroupShow': 'closed',
                 "headerTooltip": "Данный коэффициент показывает откошение стандарного отклонения к среднему. Чем меньше, тем спрос стабильнее",
                
            },
           
        ]
    },
    {
        "headerName": "Рейтинг", 
        "marryChildren": True,
         "children": [
              {
                "field": "tot_rank",
                "headerName": "Общий",                
                "width": 120,
                "cellStyle": {"textAlign": "center"},
                "filter": True,
                "headerTooltip": "Общий рейтинг товара", 
            },
              {
                "field": "abc_rank",
                "headerName": "ABC рейтинг",                
                "width": 120,
                "cellStyle": {"textAlign": "center"},
                "filter": True,
                "headerTooltip": "Рейтинг основаный на доли выручки в общей выручке",
            },   
               {
                "field": "xyz_class",
                "headerName": "XYZ рейтинг",                
                "width": 120,
                "cellStyle": {"textAlign": "center"},
                "filter": True,
                "headerTooltip": "Рейтинг основаный на коэффициенте вариации",
            },
               
                          
         ],           
          "headerClass": "ag-center-header"  # Выравнивание заголовка группы
        
        },
    {
        "headerName": "Цены", 
        "marryChildren": True,
        "children": [
            {
                "field": "price_median",
                "headerName": "Медианная",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? '₽' + d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                "headerTooltip": "Медианная цена в выбраном диапазоне", 
            },
            {
                "field": "price_mean",
                "headerName": "Средняя",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? '₽' + d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                "headerTooltip": "Средняя цена в выбраном диапазоне", 
            },
            {
                "field": "price_max",
                "headerName": "Макс.",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? '₽' + d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                "headerTooltip": "Максимальная цена в выбраном диапазоне", 
            },
            {
                "field": "price_min",
                "headerName": "Мин.",
                "type": "numericColumn",
                "valueFormatter": {"function": "params.value ? '₽' + d3.format(',.0f')(params.value) : ''"},
                "width": 120,
                 "headerTooltip": "Минимальная цена в выбраном диапазоне", 
            }
        ]
    },
    {
        "headerName": "Даты",  # Группа для дат
        "children": [
            {
                "field": "date_min",
                "headerName": "Первая",
                "filter": False,
                "sortable": False, 
                "width": 145,
                "headerTooltip": "Дата первой продажи товара в выбраном диапазоне", 
            },
            {
                "field": "date_max",
                "headerName": "Последняя",
                "filter": False,
                "sortable": False, 
                "width": 145,
                "headerTooltip": "Дата последней продажи товара в выбраном диапазоне", 
                
            }
        ]
    }
]
    
    grid = dag.AgGrid(   
    rowData=[],#srm.prepare_dataset().to_dict("records"),
    columnDefs=columnDefs,
    className="ag-theme-alpine-dark",
    #columnSize="sizeToFit",
    id = 'mx_grid'
    )
    
    
    # ========= Акоордионы =============
    
    Items_prop_list = [
        {
            "id": "general",
            "image": "https://img.icons8.com/?size=100&id=35185&format=png&color=000000",
            "label": "Общий анализ матрицы и рейтинги",
            "description": "Морфиус считает всю статистику по матрице и показывает обобщенные данные и рейтинги, которые могут понадобится для анализа выбранных категорий ",
            "content":srm.in_construction
        },
        {
            "id": "tree",
            "image": "https://img.icons8.com/?size=100&id=35184&format=png&color=000000",
            "label": "Анализ Treemap",
            "description": "Нео собирает все данные в обобщенный график по рейтингам ABC и XYZ и создает единый график по каждой номенклатуре. У него не всегда получается ", 
            "content":TreeMap_box
        },
        {
            "id": "price_dist",
            "image": "https://img.icons8.com/?size=100&id=35183&format=png&color=000000",
            "label": "Ценовой анализ",
            "description": "Тринити распределляет матрицу по ценовым категориям на группы по выручке и количеству проданных товаров, что помогает анализировать ценовые сегменты ",
            "content": price_distibution_box
        },
        {
            "id": "dist_chart",
            "image": "https://img.icons8.com/?size=100&id=35598&format=png&color=000000",
            "label": "Схема дистрибуции",
            "description": "Агент Смит анализирует схему дистрибуции выбранных категорий по подразделениям и строит диаграмму Sanky которая позволяет понять каналы дистрибуции ",
            "content": 'В разработке'
        },
        
    ]
    
    def create_accordion_label(label, image, description):
        return dmc.AccordionControl(
            dmc.Group(
                [
                    dmc.Avatar(src=image, radius="xl", size="lg"),
                    html.Div(
                        [
                            dmc.Text(label),
                            dmc.Text(description, size="sm", fw=400, c="dimmed"),
                        ]
                    ),
                ]
            )
        )


    def create_accordion_content(content):
        return dmc.AccordionPanel(dmc.Text(content, size="sm"))


    results_accordion = dmc.Accordion(
        chevronPosition="right",
        variant="contained",
        chevron=DashIconify(icon="streamline-emojis:pill"),
        #disableChevronRotation=True,
        children=[
            dmc.AccordionItem(
                [
                    create_accordion_label(
                        character["label"], character["image"], character["description"]
                    ),
                    create_accordion_content(character["content"]),
                ],
                value=character["id"],
            )
            for character in Items_prop_list
        ],
    )
    
    
    
    
    
    # ========== Контейнера =============
    
    matrix_container = dmc.Container(
        children=[
            matrix_title,
            dmc.Space(h=60),
            matrix_box,
            dcc.Loading(                
            children=[grid], 
            id='lodading',
            type="default",
            ),
            
        ],
        fluid=True,
        #h=500,
        style={"marginBottom": "30px"},
    )
    
    
    
    
    # ========= Layout ===============

    layout = dmc.AppShell(
        [
            dmc.AppShellHeader(
                dmc.Group(
                    [
                        dmc.Group(
                            [
                                srm.logo_dark,                               
                                dmc.Title("СЕГМЕНТНЫЙ АНАЛИЗ", c="blue"),
                            ],
                            id='header_content_group'
                        ),
                        theme_switch1,
                    ],
                    justify="space-between",
                    style={"flex": 1},
                    h="100%",
                    px="md",                    
                    
                   
                ),
                h=60,
            style={
                "position": "fixed",
                "top": 0,
                "left": 0,
                "right": 0,
                "zIndex": 1000,  # чтобы он был поверх остального                
            },
            
            ),
            dmc.AppShellAside("ссылка", withBorder=False),
            dmc.Space(h=60),
            
            dmc.AppShellMain(
            children=[
                cat_analisis_box,
               
                matrix_container,  # Ваш контейнер с таблицей
                dmc.Space(h=60),   # Отступ 60px
            #     dcc.Loading( 
            #     children = [
            #     TreeMap_box,
                
            #     ],
            #     id='lodading2',
            #     type="default",
                
            #     ),
            #     dcc.Loading(                
            # children=[ price_distibution_box], 
            # id='lodading 3',
            # type="default",
            # ),
                results_accordion,
            ],
            
        ),         
            dmc.AppShellFooter('Footer'),
        ],
        header={"height": 60},
        footer={"height": 60}, 
        aside={'width':100},
        padding="md",        
        id="appshell",
        
    )


    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme={"colorScheme": "light"},
        children=[
            dcc.Store(id="scroll_trigger"),
            layout,
            dcc.Store(id='theme-init', storage_type='local'),
            
            # Клиентский callback для обработки hash
            html.Div(id='dummy-output', style={'display': 'none'})
        ]
    )
    
    



# ==== CALLBACKS =======

    # THEME

    @app.callback(
        Output('header_content_group','children'),
        Output('mx_grid','className'),
        Input('color-scheme-toggle','checked'),
        prevent_initial_call=True       
    )
    def theme_switch_change(checked):
        a = [srm.logo_dark, dmc.Title("СЕГМЕНТНЫЙ АНАЛИЗ", c="blue")] if checked else [srm.logo_light, dmc.Title("СЕГМЕНТНЫЙ АНАЛИЗ", c="blue")]
        b = "ag-theme-alpine-dark" if checked else "ag-theme-alpine"
       
        return a,b

    app.clientside_callback(
        """
        function(checked) {
            const theme = checked ? 'dark' : 'light';
            // Применяем тему
            document.documentElement.setAttribute('data-mantine-color-scheme', theme);
            // Сохраняем в localStorage
            localStorage.setItem('dash_theme', theme);
            return window.dash_clientside.no_update;
        }
        """,
        Output('mantine-provider', 'theme'),  # Фиктивный Output
        Input('color-scheme-toggle', 'checked')
    )

    # 6. Колбэк для инициализации темы при загрузке
    app.clientside_callback(
        """
        function() {
            const savedTheme = localStorage.getItem('dash_theme') || 'dark';
            document.documentElement.setAttribute('data-mantine-color-scheme', savedTheme);
            return savedTheme === 'dark';
        }
        """,
        Output('color-scheme-toggle', 'checked'),
        Input('theme-init', 'modified_timestamp')
    )
    
    app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            const el = document.getElementById('matrix_title');
            if (el) {
                el.scrollIntoView({behavior: 'smooth', block: 'start'});
            }
        }
        return null;
    }
    """,
    Output('scroll_trigger', 'data'),
    Input('scroll_link', 'n_clicks')
)
    
    
    # ABC SWITCHER
    
    @app.callback(
        Output('cat_c', 'value'),
        Input('cat_a', 'value'),
        Input('cat_b', 'value'),
        prevent_initial_call=True
    )
    def update_c(a_value, b_value):
        if a_value is None or b_value is None:
            return 50  # Значение по умолчанию
        
        c_value = 100 - a_value - b_value
        c_value = max(0, (c_value // 5) * 5)  # Округляем до ближайшего кратного 5
        return c_value
    
    # ABC XYZ SWITCHER
    
    @app.callback(
        Output('cat_y', 'value'),  # Y обновляется при изменении X
        Output('cat_z', 'value'),  # Z обновляется при изменении Y
        Input('cat_x', 'value'),   # Триггер: изменение X
        Input('cat_y', 'value'),   # Триггер: изменение Y
        prevent_initial_call=True
    )
    def update_xyz(x_value, y_value):
        ctx = dash.callback_context  # Определяем, какой Input вызвал callback

        # Если сработало изменение X → Y = X + 15 (кратно 5)
        if ctx.triggered[0]['prop_id'] == 'cat_x.value':
            if x_value is not None:
                y_new = x_value + 100
                #y_new = (y_new // 5) * 5  # Округление до 5
                return y_new, dash.no_update  # Z не меняем

        # Если сработало изменение Y → Z = Y (кратно 5)
        elif ctx.triggered[0]['prop_id'] == 'cat_y.value':
            if y_value is not None:
                z_new = y_value
                z_new = (z_new // 5) * 5  # Округление до 5
                return dash.no_update, z_new  # Y не меняем

        return dash.no_update, dash.no_update
    
    # SUBCAT SWITCHER
    @app.callback(
        Output('sub_cat_filter', 'data'),  # Ожидает данные для options (скорее всего список)
        Output('noms_ind', 'label'),    # Ожидает компонент для отображения (например, строку)
        Output('add_cat_filter', 'data'),  
        Input('cat_filter', 'value'),      # val
        Input('sub_cat_filter', 'value'),  # sc
        Input('month_slider', 'value'), 
        Input('add_cat_filter', 'value'),# period storing_radio
        Input('storing_radio', 'value'),
        prevent_initial_call=True,
    )
    def change_subcat_data(val, sc, period,ac,ff):
        d: pd.DataFrame = srm.prepare_dataset(periods=period, cat_filter=val, subcat_filter=sc,add_cat_filter=ac,f_filter=ff)
        b = d['fullname'].nunique()
        a = srm.get_sub_cat(val)
        t = srm.get_add_cat(sc)
        return a, f'{b} номенклатур',t  # Порядок соответствует Output
    
    # DATA_LOADER
    @app.callback(
        Output('mx_grid', 'rowData'),
        Output('tree_map','figure'),
        Output('pd_chart','data'),
        Output('pd_chart','series'),
        Output('pd_chart_revenue','data'),
        Output('pd_chart', 'xAxisProps'),
        Output('pd_chart_revenue', 'xAxisProps'),
        Input('calc_button', 'n_clicks'),  # Основной триггер
        State('cat_filter', 'value'),      # Дополнительные параметры
        State('sub_cat_filter', 'value'),
        State('month_slider', 'value'),
        State('add_cat_filter', 'value'),
        State('storing_radio', 'value'),
        State('cat_a', 'value'),
        State('cat_b', 'value'),
        State('cat_x', 'value'),
        State('cat_y', 'value'),
        prevent_initial_call=True,
    )
    def change_mx_data(n_clicks, val, sc, period, ac,ff,a,b,x,y):  # Порядок соответствует декоратору
        d: pd.DataFrame = srm.prepare_dataset(
            periods=period,
            cat_filter=val,
            subcat_filter=sc,
            add_cat_filter=ac,
            f_filter=ff
            
            
        )
        mx = srm.prepare_matrix(d,a,b,x,y)
        mx_fig = mx[['abc_rank', 'xyz_class','fullname', 'amount','amount_share']].dropna()  # выбираем все нужные столбцы
        fig = px.treemap(mx_fig, path=[px.Constant("all"), 'abc_rank', 'xyz_class','fullname'],
        values='amount',)
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),  # убирает внешние отступы
            # убирает внутренние отступы между элементами
        )
            # 4. Подготовка данных для BarChart
        price_data = srm.make_price_distribution(df=mx)[0]
        price_data_revenue =  srm.make_price_distribution(df=mx)[1]
        
        # Преобразуем данные в нужный формат
        chart_data = [{'bins': item['bins'], 'Количество': item['quant']} 
                    for item in price_data.to_dict('records')]
        
        
        chart_data_revenue = [{'bins': item['bins'], 'Выручка': item['amount']} 
                    for item in price_data_revenue.to_dict('records')]
        # Конфигурация серий
        chart_series = [{"name": "Количество", "color": "blue", "dataKey": "Количество"}]
        
        xAxisProps={
            "angle": -45,
            "tickMargin": 10,        # можно задать отступ между метками и осью
            "textAnchor": "end"      # выравнивание по концу
            }
        
        
        return (
            mx.to_dict('records'),
            fig,
            chart_data,  # Обновленные данные
            chart_series,  # Обновленные серии
            chart_data_revenue,
            xAxisProps,
            xAxisProps
        )
    
   
    
    
            
    return app.server


def create_dash_app():
    
    _dash_renderer._set_react_version("18.2.0")
    app = dash.Dash(__name__, requests_pathname_prefix='/my-dash-app/',external_stylesheets=dmc.styles.ALL)

    from .components import GeneralComponents 
    gc = GeneralComponents()
    srm = SalesReportMonthly()

    theme_store = gc.theme_store
    theme_switch = gc.theme_switch
    navbar = gc.navbar

    app.layout = html.Div([
        theme_store,
        dmc.MantineProvider(
            id="mantine-provider",
            theme={"colorScheme": "dark"},
            forceColorScheme="dark",
            children=dmc.Container(
                children=[
                    navbar,
                    dmc.Grid([srm.content], gutter="md"),

                    dmc.Grid(
                        gutter="md",
                        mt="xl",
                        children=[
                            dmc.GridCol(
                                span=6,
                                children=srm.title_annual,
                            ),
                            dmc.GridCol(
                                span=6,
                                children=srm.title_monthly,
                            ),
                        ]
                    ),
                   
                    dmc.Grid(
                        gutter="md",
                        mt="xl",
                        children=[
                            dmc.GridCol(
                                span=2,
                                children=dmc.Paper(srm.annotation_annual, p="md", id='anotation_annual')
                            ),
                            dmc.GridCol(
                                span=4,
                                children=dmc.Paper(srm.annual_donats, p="md")
                            ),
                            dmc.GridCol(
                                span=2,
                                children=dmc.Paper(srm.annotation_monthly, p="md", id='anotation_monthly')
                            ),
                            dmc.GridCol(
                                span=4,
                                children=dmc.Paper(srm.month_donats, p="md")
                            ),
                        ]
                    ),

                    dmc.Grid(
                        gutter="xs",
                        mt="xs",
                        children=[
                            dmc.GridCol(
                                span=6,
                                children=dmc.Paper(srm.bar_chart_annual, p='md')
                            ),
                            dmc.GridCol(
                                span=6,
                                children=dmc.Paper(srm.bar_chart_monthly, p='md')
                            ),
                        ],
                        #fluid=True,
                        px=10,
                        py=3
                    ),
                    
                    dmc.Grid(
                        gutter="xs",
                        mt="xs",
                        children=[
                            dmc.GridCol(
                                span=12,
                                children=dmc.Paper(srm.area_chart, p='md')
                            ),
                           
                        ],
                        #fluid=True,
                        px=10,
                        py=3
                    ),
                    
                    
                ],
                fluid=True,
                        px=50,
                        py=50
            )
        )
    ], id="main-div")

    #----- CallBacks --------



    @app.callback(
        Output("logo", "children"),
        Input("theme-store", "data")
    )
    def theme_logo(data):
        if data['colorScheme'] == 'dark':
            return gc.logo_dark
        else: 
            return gc.logo_light  

    @app.callback(
        Output("mantine-provider", "theme"),
        Output("mantine-provider", "forceColorScheme"),
        #Output("sales_chart", "figure"),
        Input("theme-store", "data")
    )
    def apply_theme(theme_data):
        scheme = theme_data.get("colorScheme", "dark")
        #fig = create_sales_chart(df_full, theme=scheme)
        return {"colorScheme": scheme}, scheme

    @app.callback(
        Output("navbar", "style"),
        Input("theme-store", "data")
    )
    def update_navbar_style(theme_data):
        color_scheme = theme_data.get("colorScheme", "dark")
        if color_scheme == "dark":
            return {
                "backgroundColor": "#202124",
                "borderBottom": "1px solid #2C2E33",
                "marginBottom": "1rem",
                "position": "relative",
                "zIndex": 1000
            }
        else:
            return {
                "backgroundColor": "#f8f9fa",
                "borderBottom": "1px solid #dee2e6",
                "marginBottom": "1rem",
                "position": "relative",
                "zIndex": 1000
            }    

    # 🎯 Callback: переключатель темы
    @app.callback(
        Output("theme-store", "data"),
        Input("theme-switch", "checked")
    )
    def update_theme(checked):
        return {"colorScheme": "dark" if checked else "light"}


    @app.callback(
        Output('title_1','children'),
        Output('annual_donut','data'),
        Output('annual_donut','chartLabel'),
        Output('monthly_donut','data'),
        Output('monthly_donut','chartLabel'),
        Output('anotation_annual','children'),
        Output('anotation_monthly','children'),
        Output('title_annual','children'),
        Output('title_monthly','children'),
        Output('bar_chart_annual','data'),
        Output('bar_chart_monthly','data'),
        
        Input("month_pick", "value"),
        
        prevent_initial_call=True
    )
    def update_output(d):
        if d:
            date = pd.to_datetime(d)
            title = f"Отчет по продажам за {date.strftime('%b %Y').capitalize()} года"
            annual_data = srm.get_annual_data(d)
            monthly_data = srm.get_monthly_data(d)
            return title, annual_data[0], annual_data[1], monthly_data[0], monthly_data[1], annual_data[2],monthly_data[2], f"С начала {date.year} года", f"За {str(date.strftime('%b')).capitalize()} {date.year} года", annual_data[3], monthly_data[3]
        else:
            # Если d нет, то возвращаем что-то по умолчанию (тоже 3 значения)
            return f"Отчет по продажам за {last_date}", None, None, None, None

    
    @app.callback(
            Output('areachart', 'data'),
            Output('areachart', 'series'),
            Output('areachart', 'valueFormatter'),
            Output('areachart', 'type'),            
            Input('radiogroup-simple', 'value'),
            Input('month_slider', 'value'),
            Input('retail_switch',"checked"),
            Input('online_switch',"checked"),
            Input('store_filter',"value"),
            Input('cat_filter',"value"),
            Input('percent_switch',"checked"),
            Input('stack_switch',"checked"),
            prevent_initial_call=True
        )
    def update_chart(radio_val, slider_val,retail_check,online_check,store_filter,cat_filter,percent_check,stack_switch):
            rcheck = True if retail_check else None
            ocheck = True if online_check else None
            pcheck = True if percent_check else None
            ccheck = 'stacked' if stack_switch else 'default'
            if pcheck:
                vFormatter = {'function': 'formatPercentIntl'}
            else:
                vFormatter = {'function': 'formatNumberIntl'}
            a = srm.build_area_chart(option=radio_val, periods=slider_val,retail=rcheck,online=ocheck,store_filter=store_filter,cat_filter=cat_filter,percent_switch=pcheck)
            return a[0], a[1], vFormatter, ccheck
            
    

    return app.server