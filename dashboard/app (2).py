import redis
import pickle
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
import dash_mantine_components as dmc
import plotly.express as px
from dash_iconify import DashIconify
import locale
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


# 🔌 Загрузка данных из Redis
r = redis.Redis(host='localhost', port=6379, db=0)
raw_data = r.get("sales_data")
df_full:pd.DataFrame = pickle.loads(raw_data) if raw_data else pd.DataFrame()
last_date = r.get("last_date")
last_date = last_date.decode("utf-8")
last_date = pd.to_datetime(last_date)
first_date = r.get("first_date")
first_date = first_date.decode("utf-8")
first_date = pd.to_datetime(first_date)

print(df_full)

# # 📊 Функция графика
# def create_sales_chart(data, theme="dark"):
#     df_grouped = data.groupby("Магазин")["Сумма"].sum().reset_index()
#     template = "plotly_dark" if theme == "dark" else "plotly_white"
#     fig = px.bar(df_grouped, x="Магазин", y="Сумма", title="Суммарные продажи по магазинам")
#     fig.update_layout(template=template)
#     return fig


class SalesReportMonthly:
    def __init__(self,ld = last_date, fd=first_date,  dff = df_full):
        self.ld = pd.to_datetime(ld)
        self.fd = pd.to_datetime(fd)
        self.df :pd.DataFrame = dff
        self.init_annual_data = self.get_annual_data()
        self.init_monthly_data = self.get_monthly_data()
        
# ---- КОМПОНЕНТЫ СТРАНИЦЫ ---------
               

        self.header_logo = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MDAiIGhlaWdodD0iNDAwIiB2aWV3Qm94PSIwIDAgNDAwIDQwMCI+PHBhdGggZmlsbD0iIzQyNWQzNyIgZD0iTTM3Ni44MzQgMTk2LjI2MWMtMTguOTEyLTE4LjE3Mi0xMTMuNDg2LTI5LjUxNy0xNDMuMzI3LTMyLjgxOWE4OCA4OCAwIDAgMCAzLjY5Mi0xMC41OGM0LjA2OC0xLjc4IDguNDYtMy40MzggMTMtNC44MjJjLjU1MyAxLjYzMiAzLjE1OSA3Ljg4NSA0LjY0NCAxMC44NTNjNjAuMDA0IDEuNjU1IDYzLjA4NS00NC41OTEgNjUuNTI1LTU3LjI2YzIuMzg3LTEyLjM4OSAyLjI2NS0yNC4zNTkgMjIuODQ3LTQ2LjI0MWMtMzAuNjYzLTguOTM2LTc0Ljc1OSAxMy44NS04OS41MyA0Ny43NjJjLTUuNTUtMi4wOC0xMS4xMTQtMy42MTUtMTYuNjE1LTQuNTY1Yy0zLjk0My0xNS45MDUtMjQuNDc0LTYwLjIxNS03OC4zNTItNjAuMjE1Yy02OC4yMTUgMC0xNDIuNTY3IDU2LjI3Ni0xNDIuNTY3IDE1MS41NDJjMCA4MC4wNzggNTQuNjcyIDE1MC4yNTggODUuNTU5IDE1MC4yNThjMTMuNDkgMCAyNS4wOTQtMTAuMTAzIDI3LjgxOC0xOS4xNThjMi4yODQgNi4yMDkgOS4yOTIgMjUuNTEgMTEuNTkzIDMwLjQyNGMzLjQwMiA3LjI2NyAxOS4xMzQgMTMuNTU0IDI2LjAxOCA2LjAxNGM4Ljg1MiA0LjkxNyAyNS4wOTUgNy44OCAzMy45NDctNS4yMzVjMTcuMDQ5IDMuNjA2IDMyLjEyLTYuNTYgMzIuNDUtMTguNjkxYzguMzY1LS40NDcgMTIuNDY5LTEyLjE5MyAxMC42NDItMjEuNTQ3Yy0xLjM0Ni02Ljg4Ny0xNS43MzItMzEuNTk5LTIxLjM0My00MC4xM2MxMS4xMDggOS4wMzUgMzkuMjQzIDExLjU5MyA0Mi42Ni4wMDZjMTcuOTA5IDE0LjA1NyA0NS44MTcgNi42NzkgNDguMDMtNC43NTNjMjEuNzYxIDUuNjU0IDQ2LjcyLTYuNzY0IDQyLjYyMS0yMS44MDNjMzQuOTU4LTIuNDE4IDMwLjQ4My0zOS42MTEgMjAuNjc1LTQ5LjAzN3oiLz48cGF0aCBmaWxsPSIjMDNhOWY0IiBkPSJNMjc5LjQ5NCAxMTYuOTM1YzcuNTI5LTE0LjkzOCAxNi45OS0zMS4yNSAyOC45NC00MS4zNGMtMTMuMTUzIDUuMy0yNi4xMzkgMjEuMTQ2LTMzLjgxNyAzOC4wODNhMTE4IDExOCAwIDAgMC0xMS44OTMtNi42NDZjMTAuNzEtMjIuODYyIDM1LjU5OC00MS45NTUgNjMuMDI1LTQzLjQ0N2MtMTguMzcgMTYuNjYyLTExLjg1IDUxLjI5LTI2Ljk1NCA2OS42MjNjLTQuMzIyLTQuMzQyLTE0LjI0Ny0xMi43Mi0xOS4zMDEtMTYuMjczbS0xMS44NzYgMjQuMzI2Yy4wMDgtLjU3Mi4yMjItNC45ODEuNjI0LTYuOTk0Yy0xLjA1NC0uMjQ4LTcuNjAxLTEuNTI5LTExLjAxNS0xLjQ0OWMtLjI0OSA0LjI4OCAxLjgwMiAxMS41ODEgMy44MjggMTUuOTcyYzEzLjk1Ni0uMjkyIDI0LjAzNi00LjQ3MiAyOS45NjktOC4zMTRjLTUuMDUxLTIuMzU0LTEzLjY3LTQuNDQ4LTIwLjIyNC01LjdjLS43MzIgMS41MTMtMi41MzEgNS4zNjgtMy4xODIgNi40ODUiLz48ZyBzdHJva2Utd2lkdGg9IjAuOTczIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxMC45ODkgMzIuNzMpc2NhbGUoLjgxNzMzKSI+PHBhdGggZmlsbD0iIzRjYWY1MCIgZD0iTTI1MC41NCAyNzcuMzljLjAwNC4wMjQuMDE1LjA1Ny4wMTguMDgyYy0yLjE2NS00LjY1Ny00LjQ2My0xMC4zMTQtNy4yMDgtMTcuNzA4YzEwLjY4OCAxNS41NTcgNDQuMTg0IDcuNTMzIDQyLjQyNy02LjQwN2MxNi4zOTUgMTIuMzM2IDUwLjE0My0yLjA1NSA0Mi40NzEtMTkuMzUzYzE2LjQyMyA3LjY1MyAzNS4xNjgtNy43NDUgMzAuOTY0LTE0LjQ1NWMyOCA1LjQgNTQuODMyIDEwLjc4MyA2My4yNTYgMTIuOTM4Yy01LjU5NSA5LjEyMy0xOC4zMzkgMTUuNTY2LTM3LjU0OSAxMS4wODljMTAuMzggMTQuMTQtOS43NzMgMzEuMTA1LTM3Ljg0NCAyMS43NmM2LjE4IDEzLjg4My0xOC44MTQgMjYuMzgtNDcuMjIgMTEuOTFjLjM2MSAxMy44ODktMzUuMjQgMTUuNDg4LTQ5LjMxNS4xNDN6bTU1LjU0My03MC4xOTRjMzIuNDk3IDIuNDk1IDg2LjIzOCA3LjM0IDExOS41MSAxMS45OTdjLTIuMTAyLTEwLjgyOC03Ljg0NC0xMy45MjEtMjUuOTA1LTE4Ljc3MmMtMTkuNDI1IDIuMDcyLTY4LjcwNiA2LjkxMy05My42MDQgNi43NzZ6Ii8+PHBhdGggZmlsbD0iI2ZmY2EyOCIgZD0iTTI4NS43OCAyNTMuMzZjMTYuMzk1IDEyLjMzNiA1MC4xNDMtMi4wNTUgNDIuNDcxLTE5LjM1M2MxNi40MjMgNy42NTMgMzUuMTY4LTcuNzQ1IDMwLjk2NC0xNC40NTVjLTMzLjEwMy02LjM4My02Ny44NC0xMi43ODgtNzUuNzE5LTEzLjkwOGM0Ljc4LjI1NCAxMi43MDIuNzk3IDIyLjU5IDEuNTU2YzI0Ljg5OS4xMzcgNzQuMTgtNC43MDQgOTMuNjA0LTYuNzc1Yy0zMS40NTItNy45NzUtOTUuNjY2LTE5LjYxMy0xNDAuMDEtMjIuNDhjLTIuMDU1IDMuMDAzLTUuODMzIDguMDk3LTEyLjQxMyAxMy41MWMtMTkuNDAzIDQxLjA1My01NC41NTcgNjguMzQtOTMuNDU0IDY4LjM0Yy0xMS4zMzUgMC0yNC4wMTgtMS45MTItMzguMjMzLTYuNDU2Yy04Ljg2NSA5LjQ5Ny00Ni42NjEgMTYuNjk0LTc3LjMyOSAxLjY0MWMyNC4zMjYgNTYuOTYxIDgwLjc0IDk0Ljk4NCAxNDMuMTkgOTQuOTg0YzUyLjU5MSAwIDc1LjkxMi01My43MDQgNzAuODA4LTY3LjkxNGMtMS4yMzgtMy40NS02LjE0NS0xNC44ODktOC44OTEtMjIuMjgzYzEwLjY4OSAxNS41NTYgNDQuMTg1IDcuNTMyIDQyLjQyOS02LjQwOHoiLz48cGF0aCBmaWxsPSIjZTBlMGUwIiBkPSJNMjUzLjkxIDE0NS4yN2M0LjY0NC0yLjUyNiAyMC42OS0xMi4yNTMgMzUuOTgxLTE1LjkwOGE2OCA2OCAwIDAgMS0uNTM2LTUuMTJjLTEwLjAzMiAyLjQwMy0yOC45NDUgMTAuNTEtMzkuNzg0LS42NjFjMjIuODY2IDYuOSAzNC4yODMtNi4xNDkgNTEuMDktNi4xNDljMTAuMDE0IDAgMjQuMzA1IDIuNzk4IDM1LjU3IDcuMjJjLTkuMDYxLTguMzctMzguNzcyLTMzLjYzLTc1LjU1OC0zMy43MTdjLTguMjEzIDkuOTU3LTE3LjA5IDMxLjUyNi02Ljc2NCA1NC4zMzR6Ii8+PHBhdGggZmlsbD0iI2Y0MWUzNCIgZD0iTTExNS41OCAyNTMuMzNjMTQuMjE1IDQuNTQ0IDI2Ljg5OCA2LjQ1NyAzOC4yMzMgNi40NTdjMzguODk2IDAgNzQuMDUtMjcuMjkgOTMuNDU0LTY4LjM0MWMtMTQuMzUxIDExLjk3OC0zOS4yOTEgMjIuMjI4LTc4LjI0MSAyMi4yMjhjMzQuNjk0LTcuODY2IDY0LjU2LTI1LjE1NiA3OS43NTMtNTAuNDI3Yy0xMC42OC0xNi45OTgtMjIuMjYzLTU0LjYwMyA3LjA3LTg0LjMzYy00LjUxMi0xNC40OTctMjYuNDc1LTUyLjc2Ni03NS4wOTUtNTIuNzY2Yy04NC44NSAwLTE1NS4xNyA3MS4wMDEtMTU1LjE3IDE2Ni4xNWMwIDIyLjUyNSA0LjU0NyA0My42NSAxMi42NyA2Mi42NjRjMzAuNjY2IDE1LjA1NCA2OC40NjIgNy44NTggNzcuMzI3LTEuNjR6Ii8+PHBhdGggZmlsbD0iI2ZmY2EyOCIgZD0iTTE0MS4wMyAxMDguNDVjMCAyMS42NDQgMTcuNTQ2IDM5LjE5MSAzOS4xOSAzOS4xOTFzMzkuMTkyLTE3LjU0OCAzOS4xOTItMzkuMTkxcy0xNy41NDgtMzkuMTkxLTM5LjE5Mi0zOS4xOTFzLTM5LjE5IDE3LjU0Ny0zOS4xOSAzOS4xOTEiLz48cGF0aCBmaWxsPSIjNDI1ZDM3IiBkPSJNMTU2Ljc2IDEwOC40NWMwIDEyLjk1OCAxMC41MDcgMjMuNDYzIDIzLjQ2MyAyMy40NjNjMTIuOTYgMCAyMy40NjQtMTAuNTA2IDIzLjQ2NC0yMy40NjNjMC0xMi45NTktMTAuNTA0LTIzLjQ2NC0yMy40NjQtMjMuNDY0Yy0xMi45NTcgMC0yMy40NjMgMTAuNTA2LTIzLjQ2MyAyMy40NjQiLz48ZWxsaXBzZSBjeD0iMTgwLjIyIiBjeT0iOTguMDQ0IiBmaWxsPSIjZmFmYWZhIiByeD0iMTMuNjczIiByeT0iOC41MDEiLz48L2c+PC9zdmc+"

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
        self.month_donats = dmc.DonutChart(data=self.init_annual_data[0], 
                                           startAngle=180, 
                                           endAngle=0,
                                           id='monthly_donut', 
                                           #withLabelsLine=True,
                                           #withLabels=True,
                                           size=300,
	                                       thickness=30,
                                           strokeWidth=3,
                                           chartLabel=self.init_annual_data[1],
                                           
                                           )
        
        self.area_chart = dmc.Box(
            [
                dmc.Button("Форматы", id="btn-formats"),
                dmc.AreaChart(
                    id="areachart",
                    h=300,
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

        
# ---- Функции обработки данных ------

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
        
        sales =  df_year['dt'].sum() / 1_000_000
        ret = df_year['cr'].sum() / 1_000_000
        net_revenue = sales - ret        
        net_revenue_str = f"Чистая выручка ₽{net_revenue:,.2f} млн"
        
        annotation_annual = dmc.List(
            size="sm",
            spacing="sm",
            children= [
                dmc.ListItem(f'Продажи ₽{sales:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="icon-park-outline:sales-report", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            dmc.ListItem(f'Возвраты ₽{ret:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="gridicons:refund", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            dmc.ListItem(f'Чистая выручка ₽{net_revenue:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="game-icons:profit", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            dmc.ListItem(f'Процент возвратов {ret/sales*100:,.2f}% ',icon=dmc.ThemeIcon(
                DashIconify(icon="arcticons:appsales", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            ]
        )
        
        data = [
            {'name':'Продажи', 'value':sales,"color": "indigo.6"},
            {'name':'Возвраты', 'value':ret,"color": "yellow.6"}
        ]
        
        return data,net_revenue_str,annotation_annual
    
    def get_monthly_data(self,date=None):
        date = self.ld if date is None else date
        date = pd.to_datetime(date)
        df = self.df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month 
        year = date.year           
        month = date.month
        df_year = df[(df['date'].dt.year == year) & (df['date'].dt.month == month)]
        
        sales =  df_year['dt'].sum() / 1_000_000
        ret = df_year['cr'].sum() / 1_000_000
        net_revenue = sales - ret        
        net_revenue_str = f"Чистая выручка ₽{net_revenue:,.2f} млн"
        
        data = [
            {'name':'Продажи', 'value':sales,"color": "indigo.6"},
            {'name':'Возвраты', 'value':ret,"color": "yellow.6"}
        ]
        
        annotation_monthly = dmc.List(
            size="sm",
            spacing="sm",
            children= [
                dmc.ListItem(f'Продажи ₽{sales:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="icon-park-outline:sales-report", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            dmc.ListItem(f'Возвраты ₽{ret:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="gridicons:refund", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            dmc.ListItem(f'Чистая выручка ₽{net_revenue:,.2f} млн',icon=dmc.ThemeIcon(
                DashIconify(icon="game-icons:profit", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            dmc.ListItem(f'Процент возвратов {ret/sales*100:,.2f}% ',icon=dmc.ThemeIcon(
                DashIconify(icon="arcticons:appsales", width=16),
                radius="xl",
                color="blue",
                size=24,
            ),),
            ]
        )
        
        
        return data,net_revenue_str,annotation_monthly
        
    def build_area_chart(self,periods=12,option=1):
        df = self.df.copy()
        df['date'] = pd.to_datetime(df.date)
        df['month'] = df.date.dt.strftime('%b %y')
        df['amount'] = df.dt - df.cr
        
        if option == 1:
            df = df.pivot_table(
                index='month',
                values=['dt','cr','amount'],
                aggfunc='sum'                              
            ).fillna(0)
            df = df.reset_index() 
        
        data = df.to_dict(orient='records')
        series = [{'name': col} for col in df.columns if col != 'month']
        #print(data,series)

        return data, series
        

# 🎯 Dash-приложение
app = dash.Dash(__name__)
server = app.server

# 📌 Хранилище темы
from components import GeneralComponents 
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
                dmc.Grid([srm.content], gutter="md"),  # content в одну колонку (по умолчанию 1)
                dmc.Grid(
        gutter="md",
        mt="xl",
            children=[
                dmc.GridCol(
                    span=2,
                    children=dmc.Paper(srm.annotation_annual, p="md",id='anotation_annual')
                ),
                dmc.GridCol(
                    span=4,
                    children=dmc.Paper(srm.annual_donats, p="md")
                ),
                dmc.GridCol(
                    span=2,
                    children=dmc.Paper(srm.annotation_monthly, p="md",id='anotation_monthly')  # или снова srm.annotation_annual
                ),
                dmc.GridCol(
                    span=4,
                    children=dmc.Paper(srm.month_donats, p="md")
                ),
            ]
        ),
                srm.area_chart,
                    ],
                    fluid=True,
                    px=50,
                    py=40
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
    Input("month_pick", "value"),
    prevent_initial_call=True
)
def update_output(d):
    if d:
        date = pd.to_datetime(d)
        title = f"Отчет по продажам за {date.strftime('%b %Y').capitalize()} года"
        annual_data = srm.get_annual_data(d)
        monthly_data = srm.get_monthly_data(d)
        return title, annual_data[0], annual_data[1], monthly_data[0], monthly_data[1], annual_data[2],monthly_data[2]
    else:
        # Если d нет, то возвращаем что-то по умолчанию (тоже 3 значения)
        return f"Отчет по продажам за {last_date}", None, None, None, None



# ▶️ Запуск
if __name__ == "__main__":
    app.run(debug=True)
