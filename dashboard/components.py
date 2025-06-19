from dash import dcc, html, Input, Output, State
import dash_mantine_components as dmc
import plotly.express as px
from dash_iconify import DashIconify
import locale
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

class GeneralComponents:
    def __init__(self):
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
        
        #alaisis_link = dmc.Anchor("Анализ продаж", href="#areachart", underline=False)
        
        self.navbar = html.Div(
        id="navbar",
        children=dmc.Paper(
            dmc.Group(
                [
                    html.Div(
                        [
                            self.logo_dark,
                           
                            #dmc.Text("Cosmo Sales Dashboard", fz="sm", fw=500)
                        ],
                        id = 'logo',
                        style={"display": "flex", "alignItems": "center"}
                    ),
                    self.theme_switch
                ],
                justify="space-between",
                align="center",
                style={"height": "42px", "padding": "0 1rem"}
            ),
            withBorder=True,
            radius=0
        )
    )   
        
        self.month_picker = dmc.MonthPickerInput(
        label="Выберите дату",
        placeholder="Укажите месяц",
        valueFormat="YYYY MMM",   
        leftSection=DashIconify(icon="fa:calendar"),
        id='month_pick'
    )
        