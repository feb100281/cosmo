import dash 
from dash import Dash, html, dash_table, dcc, ctx, callback
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash import dash_table
from dash.dash_table.Format import Format, Group, Scheme, Trim
import numpy as np
from datetime import date
from datetime import datetime, timedelta
import dash_auth
import xlsxwriter
from io import BytesIO
from flask import request
import redis
import io
from dash_bootstrap_templates import load_figure_template
import dash_daq as daq
import os



r = redis.Redis(host='localhost', port=6379, decode_responses=True)

load_figure_template("superhero_dark")

class SharedData:
    def __init__(self) -> None:
        self.global_user_name = {'value': None}
        self.la_file_folder = '/assets/la/'        
        self.gl_permission_deny = html.Div(
        dbc.Container(
        [
            html.H1("Нет доступа !!!", className="display-3"),
            html.P(
                "У вас нет доступа к данной странице. ",
                className="lead",
            ),
            html.Hr(className="my-2"),
            html.P(
                "Обратитесь к менеджменту ООО МАНУФАКТУРА ОФИСОВ с запросом доступа"
                
            ),
            html.P(
                dbc.Button("Home", color="primary", href="/", external_link=True), className="lead"
                    ), 'comp_greeting'
        ],
        fluid=True,
        className="py-3 text-center",  # Adjust text alignment to center
    ),
    className="p-3 bg-light rounded-3",
    style={"position": "absolute", "top": "50%", "left": "50%", "transform": "translate(-50%, -50%)"} # Centering the jumbotron
)
    def name_adj(self,name,cut='False'):            
                
                exceptions = {}
                exceptions['МАНУФАКТУРА ОФИСОВ ООО'] = 'МАНУФАКТУРА'
                exceptions['МИСТРАЛЬ ТРЕЙДИНГ ООО'] = 'МИСТРАЛЬ ТРЕЙД.'
                exceptions['РАБОЧЕЕ ПРОСТРАНСТВО ООО'] = 'РАБ. ПРОСТРАНСТВО'
                exceptions['СК СБЕРБАНК СТРАХОВАНИЕ ЖИЗНИ ООО'] = 'СБЕРБАНК СТРАХ. ЖИЗНИ'
                exceptions['СК СБЕРБАНК СТРАХОВАНИЕ ООО'] = 'СБЕРБАНК СТРАХОВАНИЕ'
                    
                text = str(name) 
                    
                if cut == 'False':
                    for key in exceptions:
                        if key == text:
                            return exceptions[key]            
                        
                dig = 25
                ending = ['ООО','ПАО','АО','ЗАО']
                text = str(name) 
                three = text[-3:]
                adjust_name = ''
                if name == 'Прочие':
                    return name
                for i in ending:
                    if i in three:
                        adjust_name = text.replace(i,'')
                        if len(adjust_name) > dig:
                            return adjust_name[:dig] +'.'
                        else:
                            return adjust_name        
                parts = text.split(' ')
                return parts[0] + ' ' + parts[1][:1] + '.' + parts[2][:1]+'.'
    def la_adj(self,name):
        exceptions = {'Соглашение о замене сторон по договору':'', 'Соглашение о замене сторон':''}
        adjusted_name = name
        for key in exceptions:
            if key in adjusted_name:
                adjusted_name = adjusted_name.replace(key, exceptions[key])
        return adjusted_name

sd = SharedData()

class Homepage:
    
    def __init__(self) -> None:         
         self.comp_greeting = html.Div(
             children='Welcomenn',style={"margin-top": "50px"},id='comp_greeting'
         )
         
         self.greetings_jumbo = html.Div(
    dbc.Container(
        [
            html.H1("Нет доступа !!!", className="display-3"),
            html.P(
                "У вас нет доступа к данной странице. ",
                className="lead",
            ),
            html.Hr(className="my-2"),
            html.P(
                "Обратитесь к менеджменту ООО МАНУФАКТУРА ОФИСОВ с запросом доступа"
                
            ),
            html.P(
                dbc.Button("Home", color="primary", href="/", external_link=True), className="lead"
                    ),
        ],
        fluid=True,
        className="py-3 text-center",  # Adjust text alignment to center
    ),
    className="p-3 bg-light rounded-3",
    style={"position": "absolute", "top": "50%", "left": "50%", "transform": "translate(-50%, -50%)"} # Centering the jumbotron
)
         
         
         self.home_carusel = dbc.Carousel( items= [
             {"key": "page1", "Caption": "This is the first slide"},
             {"key": "page2", "Caption": "This is the second slide"},
         ]
             
         )
        
         self.user_first_name = html.H2(id='user_first')
         
         self.home_main_layout = dbc.Container(
             html.Div([
                 dbc.Row(
                     dbc.Col(self.user_first_name,width={"size":8,"offset":4},align="center",),justify='center'
                 ),
                 dbc.Row(
                     dbc.Col(html.P('Добро пожаловать на информационный портал Poklonka Place'),width={"size":8,"offset":4},align='center')
                 ),
                 dbc.Row(
                     dbc.Col(html.P('Выберите интересующий раздел в меню "Разделы"'),width={"size":8,"offset":4},align='center')
                 ),
             ]),style={"padding-top": "170px"}
             
         )
         
         
         
    def layout(self,):        
        main_layout = self.home_main_layout                        
        return main_layout
        
 
    def hp_callbacks(self,app):
        @app.callback(
            Output('user_first', 'children'),
            Input('user_store', 'data'),            
        )
        def display_user(data):
            first_name = r.hget(f"user:{data}","first")  
            return f"{first_name} !"

hp = Homepage()

class GL:
    def __init__(self) -> None:
        self.col = col = [
    dict(id='id',name = 'Контрагент'),    
    dict(id='status',name = 'Статус',hideable = True),  
    dict(id='debt',name = 'Дт задол. текущая', hideable = False, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='dt13',name = 'Начислено',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),    
    dict(id='cr13',name = 'Оплачено',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='cr26',name = 'Задолженность',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='dt29',name = 'Переплата',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='due_to',name = 'К оплате',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='dt30',name = 'Депозит',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='ap',name = 'Кт. задол. текущая',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='dta13',name = 'Начисл. аванс',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
    dict(id='ad_due',name = 'Аванс к оплате',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),
]

        self.data_tbl = html.Div([
    dash_table.DataTable(
    id='data_tbl',       
    columns=col,
    data=[],
    editable=False,
    filter_action='native',
    #style_filter={'backgroundColor': 'white',  },
    sort_action='native',
    sort_mode='single',    
    row_selectable='multi',
    
    selected_rows=[],
       
    page_action="native",   
    fixed_columns={'headers': True, 'data': 1},
    style_table={'overflowX': 'auto', 'maxWidth': '100%', 'width': '100%'},

    style_data={
        'whiteSpace': 'normal',
        'height': 'auto',
    },
    
    style_cell={'fontSize': '12px'},
    
     
    style_cell_conditional=[#add i new code
    {'if': {'column_id': 'id'}, 'textAlign': 'left'},  # Set text-align to right for the first column
] + [
    {'if': {'column_id': col_id['id']}, 'textAlign': 'center'} for col_id in col[1:]  # Set text-align to center for other columns
],
    
    
    
    tooltip_header={
        'id': 'Наименование арендатора',
        'status':'Статус арендатора',
        'debt': f'Текущая дебиторская задолженность на выбранную дату',
        'dt13': 'Начисления за текущий месяц',
        'cr13': 'Оплаты и зачеты депозитов за текущий месяц',
        'cr26': 'Дебиторская задолженность на начало месяца',
        'dt29': 'Кредиторская задолженность на начало месяца',
        'due_to': 'Всего минимальная сумма к оплате в текущем месяце с учетом Дт. и Кт. задолженности',
        'dt30': 'Текущий размер обеспечительного депозита',
        'ap': 'Кредиторская задолженность на текущею дату',
        'dta13':'Начисленный аванс на следующий месяц',
        'ad_due':'Остаток оплаты аванса на следуюший месяц'
    },
        
)
],className="dbc dbc-row-selectable"),
        
        self.accural1 = html.P(children=[''],style={'textAlign':'left','marginTop': 12},)
        self.adv_accural1 = html.P(children=[''],style={'textAlign':'left',},id='adv_accural')
        
        self.progress = dbc.Progress(label="", value=0, style={"height": "30px"})
        self.adv_progress = dbc.Progress(label="", value=0, style={"height": "30px"},color="info",id='adv_progress')
        
        self.left_title = html.H2('Payments', className='display-4')
        self.right_title = html.H2('Взаиморасчеты c арендаторами', className='display-4')
        self.summ_string = html.H5(children='Собрано на ')
        self.adv_summ_string = html.H5(children='Собрано на ')
        
        self.rest_label = html.P(children='Осталось собрать')
        self.adv_rest_label = html.P(children='Осталось собрать')
        
        self.info_label = html.P(children='')
        self.info_label2 = html.P(children='')
        
        self.gl_stat_layout = html.Div(
            
            
        )
        
        self.date_picker = dcc.DatePickerSingle(
    id='date_picker',
    min_date_allowed=date(2022,3,1),
    initial_visible_month= date.today(),
    display_format='D MMM Y',
    max_date_allowed=date.today(), 
    date=date.today()      
)
        
        self.accord = html.Div(
    [dbc.Accordion(
        id='accordion-content',
        children=[],  # Initially empty
        start_collapsed=True
    ),
    #dbc.Tooltip(
    #"Оплаты и зачет депозитов на выбранную дату. Список должников.",
    #target="accordion-content",
    #style={'font-family':'serif', 'font-size':'14px'}
     #                     )
    ]
)
        
        self.dl_badge = dbc.Badge(children='4',
                     color="primary",                     
                     text_color="dark",
                     className="ms-1")
        
        self.dnl_button = dbc.Button([
    " Скачать  ",
    self.dl_badge,    
    dbc.Tooltip(
    "Скачать таблицу и расчеты сверок с выделенными арендаторами (Excel)",
    target="dnl_btn",
    style={'font-family':'serif', 'font-size':'14px'}
                          )
    ], 
    id='dnl_btn',    
    color="primary",
    outline="primary",
    style={
        'border': '2px solid #your_border_color_code',  
        'border-radius': '5px',  
        'float': 'top'
    },
     className="ms-auto",   

)

        self.clear_button = dbc.Button([
    " Очистить ",
    
    dbc.Tooltip(
    "Снять выделения с выбранных контрагентов",
    target="clear_all_btn",
    style={'font-family':'serif', 'font-size':'14px'}
                          )
    ], 
    id='clear_all_btn',    
    color="primary",
    outline="primary",
    style={
        'border': '2px solid #your_border_color_code',  
        'border-radius': '5px',  
        'float': 'top'
    },
     className="ms-auto",   

)
        
        self.show_all = dbc.Button([
    " Показать ",
    dbc.Tooltip(
    "Показать выбранных контрагентов",
    target="show_all_btn",
    style={'font-family':'serif', 'font-size':'14px'}
                          )
    ], 
    id='show_all_btn',    
    color="primary",
    outline="primary",
    style={
        'border': '2px solid #your_border_color_code',  
        'border-radius': '5px',  
        'float': 'top'
    },
     className="ms-auto",   

)
        
        self.gl_modal = html.Div(
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(f"Арендаторы {self.getMonthName(str(self.date_picker.date))}")),
            dbc.ModalBody(dbc.ListGroup(''),id='gl_modal_text'),
            dbc.ModalFooter(
                [
                    dbc.Button("Скачать сверку", id="close_gl_modal", className="ms-auto", n_clicks=0),
                    dcc.Download(id="download-excel")
                ]
            )
        ],
        id='gl_modal',
        is_open=False
    )
)

        self.selection_storge = dcc.Store(id='selected_row_ids', storage_type='session')  
        
        self.right_graph = dcc.Graph(figure={})

        self.main_layout = dbc.Container(
    html.Div(
    [
        dbc.Row([
            dbc.Col(self.left_title,width=4),
            dbc.Col(self.right_title,width=8)
    ],style={"margin-top": "20px"}),        
        dbc.Row([
            dbc.Col(html.Hr(),width=4),
            dbc.Col(html.Hr(),width=8)
    ]),
        dbc.Row([
            dbc.Col(html.H5('Выбор даты'),width=4),
            dbc.Col(self.summ_string,width=8)
    ]),
        dbc.Row([
            dbc.Col(self.date_picker,width=4),
            dbc.Col(self.accural1,width=8)
    ],className="dbc"),
        dbc.Row([
            dbc.Col(self.progress,width={"size":4,"offset":4}),
            dbc.Col(self.rest_label,width={"size":3,"offset":0}),            
    ]),
        
        #advance stat
         dbc.Row([
            
            dbc.Col(html.Hr(),width={"size":8,"offset":4})
    ]),
        
        dbc.Row(
            dbc.Col(self.adv_summ_string,width={"size":8,"offset":4}),            
        ),
        
        dbc.Row(
            dbc.Col(self.adv_accural1,width={"size":8,"offset":4}),            
        ),
        dbc.Row([
            dbc.Col(self.adv_progress,width={"size":4,"offset":4}),
            dbc.Col(self.adv_rest_label,width={"size":3,"offset":0}),            
        ]),
       
        
        dbc.Row([
            dbc.Col(html.Hr(),width=4),
            dbc.Col(html.Hr(),width=8)
    ]),
        dbc.Row([
            dbc.Col(self.accord,width=4), 
            dbc.Col(self.right_graph,width=8), 
                       
    ],style={"margin-top": "0px"}),
        dbc.Row([       
            dbc.Col([self.dnl_button,self.clear_button]),            
            dbc.Col(self.data_tbl,width=12),  
            dbc.Col(self.gl_modal,width=12),  
            dbc.Col(self.selection_storge,width=12),            
            
                 
    ],style={"margin-top": "20px"},),
        
    ],style={"padding-top": "70px"}
  
)
)

    def set_badge(self,text):    
            return dbc.Badge(text, color="danger", pill=True, text_color="white",) 
    
    def layout(self):
        return self.main_layout
    
    def get_dates(self,date):
        cur_date = datetime.strptime(date,'%Y-%m-%d')
        month_first_date = datetime(cur_date.year,cur_date.month,1)
        next_month = month_first_date + timedelta(days=33)
        next_month = datetime(next_month.year,next_month.month,1)
        next_next_month = next_month + timedelta(days=33)
        next_next_month = datetime(next_next_month.year,next_next_month.month,1)
        next_month_last_day = next_next_month - timedelta(days=1)
        month_last_day = next_month - timedelta(days=1)
        last_month_end_day = month_first_date - timedelta(days=1)
        last_month_first_day = datetime(last_month_end_day.year,last_month_end_day.month,1)    
        date_tupple = (month_first_date.strftime('%Y-%m-%d'),month_last_day.strftime('%Y-%m-%d'), last_month_first_day.strftime('%Y-%m-%d'), last_month_end_day.strftime('%Y-%m-%d'),next_month.strftime('%Y-%m-%d'),next_month_last_day.strftime('%Y-%m-%d'))
        
        return date_tupple

    def getMonthName(self,date):
            MONTHES = {
            '1':'Январь', '2':'Февраль', '3':'Март', '4':'Апрель', '5':'Май', '6':'Июнь', '7':'Июль', '8':'Август', '9':'Сентябрь', '10':'Октябрь', '11':'Ноябрь', '12':'Декабрь',
            }    
            cur_date = datetime.strptime(date, '%Y-%m-%d')
            monthName = f"{MONTHES[str(cur_date.month)]} {cur_date.year}"
            return monthName

    def cr13(self,date):
        
        date_tupple = self.get_dates(date)
        start_date = date_tupple[0]
        end_date = date    
        acc_id = '13'
        
        dates_set = r.zrangebyscore("dates",start_date.replace('-',''),end_date.replace('-',''))
        acc_id  = r.smembers("acc:"+acc_id)
        ids = acc_id.intersection(dates_set)
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        
        if df.empty:
            empty_row = {'id_acc':'13','name':' ','cr':0.0,'dt':0.0}
            data_list = [(empty_row['id_acc'], empty_row['name'], empty_row['cr'], empty_row['dt'])]
            df = pd.DataFrame(data_list, columns=['id_acc', 'name', 'cr', 'dt'], index=[0])
            return df

        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df = df.groupby(['id_acc', 'name']).agg({'cr': 'sum', 'dt': lambda x: 0})
        df.reset_index(inplace=True)        
    
        return df

    def dt13(self,date):
        
        date_tupple = self.get_dates(date)
        start_date = date_tupple[0]
        end_date = date_tupple[1]    
        acc_id = '13'
            
        dates_set = r.zrangebyscore("dates",start_date.replace('-',''),end_date.replace('-',''))
        acc_id  = r.smembers("acc:"+acc_id)
        ids = acc_id.intersection(dates_set)
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        
        if df.empty:
            empty_row = {'id_acc':'13','name':' ','cr':0.0,'dt':0.0}
            data_list = [(empty_row['id_acc'], empty_row['name'], empty_row['cr'], empty_row['dt'])]
            df = pd.DataFrame(data_list, columns=['id_acc', 'name', 'cr', 'dt'], index=[0])
            return df

        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df = df.groupby(['id_acc', 'name']).agg({'cr': lambda x: 0, 'dt': 'sum'})
        df.reset_index(inplace=True)
            
        return df

    def acc26(self,date):
        date_tupple = self.get_dates(date)
        start_date = date_tupple[2]
        end_date = date_tupple[3]  
        acc_id = '26'
        
        #am = r.zrangebyscore('cr','2.00','+inf')
        dates_set = r.zrangebyscore("dates",start_date.replace('-',''),end_date.replace('-',''))
        acc_id  = r.smembers("acc:"+acc_id)
        ids = acc_id.intersection(dates_set)
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        
        if df.empty:
            empty_row = {'id_acc':'26','name':' ','cr':0.0,'dt':0.0}
            data_list = [(empty_row['id_acc'], empty_row['name'], empty_row['cr'], empty_row['dt'])]
            df = pd.DataFrame(data_list, columns=['id_acc', 'name', 'cr', 'dt'], index=[0])
            return df

        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df = df.groupby(['id_acc', 'name']).agg({'cr': 'sum', 'dt': 'sum'})
        df.reset_index(inplace=True)
        df = df[df['cr'] > 2]
            
        return df
    
    def acc29(self,date):
        date_tupple = self.get_dates(date)
        start_date = date_tupple[2]
        end_date = date_tupple[3]  
        acc_id = '29'
        
        dates_set = r.zrangebyscore("dates",start_date.replace('-',''),end_date.replace('-',''))
        acc_id  = r.smembers("acc:"+acc_id)
        ids = acc_id.intersection(dates_set)
        
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        
        if df.empty:
            empty_row = {'id_acc':'29','name':' ','cr':0.0,'dt':0.0}
            data_list = [(empty_row['id_acc'], empty_row['name'], empty_row['cr'], empty_row['dt'])]
            df = pd.DataFrame(data_list, columns=['id_acc', 'name', 'cr', 'dt'], index=[0])
            return df

        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df = df.groupby(['id_acc', 'name']).agg({'cr': 'sum', 'dt': 'sum'})    
        df.reset_index(inplace=True)
        df = df[df['dt'] > 2]
        
        return df

    def acc30(self,date):
        date_tupple = self.get_dates(date)
        start_date = date_tupple[0]
        end_date = date_tupple[1]  
        acc_id = '30'
        
        dates_set = r.zrangebyscore("dates",start_date.replace('-',''),end_date.replace('-',''))    
        acc_id  = r.smembers("acc:"+acc_id)    
        ids = acc_id.intersection(dates_set)
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        
        if df.empty:
            empty_row = {'id_acc':'30','name':' ','cr':0.0,'dt':0.0}
            data_list = [(empty_row['id_acc'], empty_row['name'], empty_row['cr'], empty_row['dt'])]
            df = pd.DataFrame(data_list, columns=['id_acc', 'name', 'cr', 'dt'], index=[0])
            return df

        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df = df.groupby(['id_acc', 'name']).agg({'cr': 'sum', 'dt': 'sum'})
        df.reset_index(inplace=True)
        df = df[df['dt'] > 2]

        
        return df

    def a13(self,date):
        date_tupple = self.get_dates(date)
        start_date = date_tupple[4]
        end_date = date_tupple[5]    
        acc_id = '13'
        
        
        dates_set = r.zrangebyscore("dates",start_date.replace('-',''),end_date.replace('-',''))
        acc_id  = r.smembers("acc:"+acc_id)
        ids = acc_id.intersection(dates_set)
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        
        if df.empty:
            empty_row = {'id_acc':'a13','name':' ','cr':0.0,'dt':0.0}
            data_list = [(empty_row['id_acc'], empty_row['name'], empty_row['cr'], empty_row['dt'])]
            df = pd.DataFrame(data_list, columns=['id_acc', 'name', 'cr', 'dt'], index=[0])
            return df

        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df = df.groupby(['id_acc', 'name']).agg({'cr': lambda x: 0, 'dt': 'sum'})
        df.reset_index(inplace=True)
        
        df['id_acc']='a13'
        
        
        
        return df




    def table_df(self, date):
        def running_ap(ap, accural, pmt,ar):
            
            runnind_ap = ap + pmt
            runnig_ar = accural + ar
            if runnind_ap <= runnig_ar:
                return 0.0
            else:
                return runnind_ap-runnig_ar
        
        def rest(due,paid):
            if due <= paid:
                return 0.0
            else:
                return round(due-paid,0)
        
        def due(accural,ar,ap,pmt):
            due_tot = accural + ar   
        
            if ap >= due_tot:
                return 0.0
            else:
                return round(due_tot-ap,0)
        
        def set_status(name):
            name_adj = str(name).replace(' ','_')
            fme = self.get_dates(date)
            redis_key = f"sts:{fme[1]}:{name_adj}"         
            status = r.get(redis_key)
            return status
        
        def ad_due(a13,dt30):
            if a13 <= dt30:
                return 0.0
            else:
                return a13-dt30
        
        
        df_13_cr = self.cr13(date)
        df_13_dt = self.dt13(date)
        df_acc26 = self.acc26(date)
        df_acc29 = self.acc29(date)
        df_acc30 = self.acc30(date)
        df_a13 = self.a13(date)    
            
        df = pd.concat([df_13_cr, df_13_dt, df_acc26, df_acc29, df_acc30, df_a13], axis=0)
        
        df = df.pivot_table(index='name',columns='id_acc',values=['dt','cr'],aggfunc='sum').fillna(0)
        
        df = df[[('dt', '13'), ('cr', '26'), ('dt', '29'), ('cr', '13'), ('dt', '30'),('dt','a13') ]]
        df.reset_index(inplace=True)
        df.columns = [''.join(map(str, col)).strip() for col in df.columns.values]
        
        df['due_to'] = df.apply(lambda row: due(row['dt13'],row['cr26'],row['dt29'],row['cr13']),axis=1)
        df['debt'] = df.apply(lambda row: rest(row['due_to'],row['cr13']),axis=1)
        df['ap'] = df.apply(lambda row: running_ap(row['dt29'],row['dt13'],row['cr13'],row['cr26']),axis=1)
        df['status'] = df['name'].apply(set_status)
        df['ad_due'] = df.apply(lambda row: ad_due(row['dta13'], row['ap']),axis=1)
        df['id'] = df['name']    
        df.set_index('id', inplace=True, drop=False)
        
        return df

    def day_settlements(self,date):     
        
        def set_badge(amount, id_leaseTerms, temp):
            if id_leaseTerms == '':
                parts = str(temp).split(' ')
                return parts[0]
            elif amount > 0:
                return 'Оплата'
            elif amount < 0:
                return 'Возврат'
            else:
                return temp

        acc_ids = '17'
        dates_set = r.zrangebyscore("dates",date.replace('-',''),date.replace('-',''))    
        acc_id = r.smembers("acc:" + acc_ids)   
        ids = acc_id.intersection(dates_set)
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        if df.empty:
            return df
        
        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        
        df['amount'] = df['cr'] - df['dt']
        df['badge'] = df.apply(lambda row: set_badge( row['amount'], row['id_leaseTerms'], row['temp']),axis=1)
        
        return df[['name','amount','badge']]

    def day_payments(self,date):
        
        def set_badge(la):
            if la == 2700000:
                return 'Перемен. часть'
            elif la == 5900000:
                return 'Процент'
            else:
                return ''
        
        acc_ids = '16'
        dates_set = r.zrangebyscore("dates",date.replace('-',''),date.replace('-',''))    
        acc_id = r.smembers("acc:" + acc_ids)   
        ids = acc_id.intersection(dates_set)
        
        data_list = []
        for id in ids:
            key = f"gl:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'id': id, **hash_data})       

        df = pd.DataFrame(data_list)
        if df.empty:
            return df
        
        df['dt'] = df['dt'].astype(float)
        df['cr'] = df['cr'].astype(float)
        df['id_leaseTerms'] = pd.to_numeric(df['id_leaseTerms'], errors='coerce')
        df['id_leaseTerms'] = round(df['id_leaseTerms'], 0).astype('Int64')  
        df['badge'] = df['id_leaseTerms'].apply(set_badge)
        
        lt_filter = [2600000,5900000,2700000]
        
        df['amount'] = df['cr'] + df['dt']
        
        
        df = df[df['id_leaseTerms'].isin(lt_filter)]
        
        
        return df[['name','amount','badge']]    

    def gl_datePicker_callback(self,app):
        @app.callback(
            Output(self.summ_string,component_property='children'),
            Output(self.accural1,component_property='children'),
            Output(self.progress,component_property='value'),
            Output(self.progress,component_property='label'),
            Output('accordion-content', 'children'),
            Output(self.date_picker,component_property='max_date_allowed'),
            Output('data_tbl',component_property='data'),
            Output(self.left_title,component_property='children'),
            Output(self.rest_label,component_property='children'), 
            Output(self.right_graph,component_property='figure'), 
            Output(self.adv_summ_string,component_property='children'),
            Output(self.adv_accural1, component_property='children'),
            Output(self.adv_progress,component_property='value'),
            Output(self.adv_progress,component_property='label'),
            Output(self.adv_rest_label,component_property='children'),
             

            Input(self.date_picker,component_property='date')
            )
        def date_change(val):    
            check_df = self.dt13(val)   
            data_tbl = self.table_df(val)
            
            due = data_tbl['due_to'].sum()
            rest = data_tbl['debt'].sum()
            due_rest = due - rest    
            
            adv_charge = data_tbl['dta13'].sum()
            adv_due = data_tbl['ad_due'].sum()
            adv_paid = adv_charge - adv_due
            if adv_charge == 0:
                adv_progress_val =0
                adv_progress_lbl =''
            else:
                adv_progress_val = round(adv_paid/adv_charge * 100,0)
                adv_progress_lbl = f"{(adv_paid/adv_charge):.1%}"
                        
            
            def summ_string(date):
                b = datetime.strptime(date,'%Y-%m-%d')
                a = datetime.strftime(b,'%d.%m.%Y') 
                return f"Собрано арендных платежей и задолженности на: {a}"
            
            def accural_string():        
                if check_df.empty:
                    return 'Ожидание данных по начислениям'
                else:       
                    return f"{due_rest:,.0f} / {due:,.0f} рублей"
            
            def progress_bar_value():
                if check_df.empty:
                    return 0
                else:       
                    return round(due_rest/due*100,0)
                
            def progeress_bar_label():
                if check_df.empty:
                    return ''
                else:       
                    return f"{due_rest/due:.1%}"
            
            def acc_payments_items(date):
                
                df = self.day_payments(date)
                df.fillna('')
                    
                accordion_items = []
                if df.empty:
                    accordion_items = [
                    dbc.AccordionItem(
                    [],
                    title="Оплаты",   
                    )]
                    
                else:
                    label = df['amount'].sum()
                    accordion_content = []
                    for index, row in df.iterrows():
                        name = row['name']
                        amount = row['amount']
                        badge = row['badge']    
                        entry = f"{name}: {amount:,.0f} руб. "                
                        accordion_content.append(html.P([entry,dbc.Badge(badge, color="danger", pill=True, text_color="white",)]) )            
                    accordion_items.append(dbc.AccordionItem(accordion_content,title=f"Оплаты: {label:,.0f} руб."))
                
                df = self.day_settlements(date)
                df.fillna('') 

                if df.empty:
                    accordion_items.append( 
                    dbc.AccordionItem(
                    [],
                    title="Депозиты",   
                    ))
                else:
                    label = df['amount'].sum()
                    accordion_content = []
                    for index, row in df.iterrows():
                        name = row['name']
                        amount = row['amount']
                        badge = row['badge']    
                        entry = f"{name}: {amount:,.0f} руб. "                
                        accordion_content.append(html.P([entry,dbc.Badge(badge, color="danger", pill=True, text_color="white",)]) )            
                    accordion_items.append(dbc.AccordionItem(accordion_content,title=f"Депозиты: {label:,.0f} руб."))    
                
                def get_badge(name):
                    name_adj = str(name).replace(' ','_')
                    fme = self.get_dates(date)
                    redis_key = f"sts:{fme[1]}:{name_adj}"         
                    badge = r.get(redis_key)
                    if badge == 'Активный':
                        return ''
                    else:
                        return badge   
                    
                cond = data_tbl['debt']>2
                df = data_tbl[cond]
                if df.empty:
                    accordion_items.append( 
                    dbc.AccordionItem(
                    [],
                    title="Должники",   
                    ))
                else:
                    df = df[['name','debt']]       
                    df['badge'] = df['name'].apply(get_badge)
                    df = df.sort_values(by='debt',ascending=False)
                    label = df['debt'].count()
                    accordion_content = []
                    for index, row in df.iterrows():
                        name = row['name']
                        amount = row['debt']
                        badge = row['badge']    
                        entry = f"{name}: {amount:,.0f} руб. "                
                        accordion_content.append(html.P([entry,dbc.Badge(badge, color="danger", pill=True, text_color="white",)]) ) 
                    accordion_items.append(dbc.AccordionItem(accordion_content,title=f"Должники: {label:,.0f}"))      
            
                return accordion_items
            
            def date_picker_max_date():
                return date.today()
            
            def r_figure(date):
                def chart_data(date):
                    
                    mom_date = self.get_dates(date)
                    l_month_date = mom_date[3]
                    
                    fme_name = self.getMonthName(date)     
                    mom_name = self.getMonthName(l_month_date)
                    
                    fme_df = data_tbl
                    mom_df = self.table_df(l_month_date)
                    
                    stages = ['Поступления','Начисления', 'Дт. задолженность','Кт. задолженность','Депозиты']
                    
                    df_mom = pd.DataFrame(dict(
                        number = [
                            mom_df['cr13'].sum(),
                            mom_df['dt13'].sum(),
                            fme_df['cr26'].sum(),
                            fme_df['dt29'].sum(),
                            mom_df['dt30'].sum(),
                        ],stage=stages)           
                    )
                    
                    df_fme = pd.DataFrame(dict(
                        number = [
                            fme_df['cr13'].sum(),
                            fme_df['dt13'].sum(),
                            fme_df['debt'].sum(),
                            fme_df['ap'].sum(),
                            fme_df['dt30'].sum(),
                        ],stage=stages
                        
                    ))
                    
                    df_mom['Месяц'] = mom_name
                    df_fme['Месяц'] = fme_name
                    
                    df = pd.concat([df_mom,df_fme], axis=0)
                    df['number'] = round(df['number']/1000000,2)

                    return df
                
                rfig_df = chart_data(date)
                r_fig = px.funnel(rfig_df, x='number', y='stage', color='Месяц',)
                r_fig.update_layout(
                plot_bgcolor='rgb(20, 36, 53)',  # Set plot background color
                paper_bgcolor='rgb(20, 36, 53)',  # Set figure (paper) background color
                font=dict(
                    color='rgb(232, 232, 232)'     # Set text color
                    )
                )
                r_fig.update_yaxes(title_text="",)
                r_fig.update_layout(title_text="Взаиморасчеты (млн. руб.)")
                
                return r_fig
        
            def data_tbl_sub():
                if check_df.empty:
                    df = pd.DataFrame()
                    return df.to_dict('records')          
                else:       
                    return data_tbl.to_dict('records')
            
            def rest_label():
                if check_df.empty:
                    return ''
                else:
                    f"Осталось собрать руб."
                
            arg1 = summ_string(val)
            arg2 = accural_string()
            arg3 = progress_bar_value()
            arg4 = progeress_bar_label()
            arg5 = acc_payments_items(val)
            arg6 = date_picker_max_date()
            arg7 = data_tbl_sub()
            arg8 = self.getMonthName(val)
            arg9 = f"Осталось собрать {rest:,.0f} руб."
            arg10 = r_figure(val) 
            arg11 = 'Собрано авансов на следующий месяц'
            arg12 =  f"{adv_paid:,.0f} / {adv_charge:,.0f} рублей"
            arg13 = adv_progress_val
            arg14 = adv_progress_lbl
            agr15 = f"Осталось собрать {adv_due:,.0f} руб."
            
            return arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9,arg10,arg11,arg12,arg13,arg14,agr15
     
    def gl_table_callback(self,app):
        @app.callback(
        [Output(self.dl_badge, 'children'),
        Output('gl_modal_text', 'children'),
        Output('selected_row_ids', 'data')],
        [Input('data_tbl', 'derived_virtual_selected_row_ids')],
        prevent_initial_call=True
        )
        def table_select(rows):
            selected_row_ids = rows  # Update the selected row IDs

            # Set counter for selected rows
            counter_text = ''
            if selected_row_ids:
                counter_text = str(len(selected_row_ids))

            # Set modal body content
            model_body_content = []
            if selected_row_ids:
                model_body_content = [dbc.ListGroupItem(item) for item in selected_row_ids]

            # Return outputs
            return counter_text, model_body_content, selected_row_ids
        
    def gl_clearall_callback(self,app):
        @app.callback(
        Output('data_tbl', 'selected_rows'),
        Output('data_tbl', 'selected_columns'),    
        Input('clear_all_btn', 'n_clicks'),
        prevent_initial_call=True
    )
        def clear_selection(n_clicks):
            if n_clicks is not None and n_clicks > 0:
                return [], []
            else:
                raise dash.exceptions.PreventUpdate
    
    def gl_dnlButton_callback(self,app):
        @app.callback(
        Output("gl_modal", "is_open"),
        [Input("dnl_btn", "n_clicks")],
        [State("gl_modal", "is_open")]
    )
        def toggle_modal(n1, is_open):
            if n1:
                return not is_open
            return is_open

    def gl_dnlExcell_callback(self,app):
        @app.callback(
        Output('download-excel','data'),
        Input("close_gl_modal", "n_clicks"),
        Input("selected_row_ids","data"),
        prevent_initial_call=True
        )
        def download_excel(n_clicks,data):    
            excel_content = {}
            def name_adj(name,cut='False'):            
                
                exceptions = {}
                exceptions['МАНУФАКТУРА ОФИСОВ ООО'] = 'МАНУФАКТУРА'
                exceptions['МИСТРАЛЬ ТРЕЙДИНГ ООО'] = 'МИСТРАЛЬ ТРЕЙД.'
                exceptions['РАБОЧЕЕ ПРОСТРАНСТВО ООО'] = 'РАБ. ПРОСТРАНСТВО'
                exceptions['СК СБЕРБАНК СТРАХОВАНИЕ ЖИЗНИ ООО'] = 'СБЕРБАНК СТРАХ. ЖИЗНИ'
                exceptions['СК СБЕРБАНК СТРАХОВАНИЕ ООО'] = 'СБЕРБАНК СТРАХОВАНИЕ'
                    
                text = str(name) 
                    
                if cut == 'False':
                    for key in exceptions:
                        if key == text:
                            return exceptions[key]            
                        
                dig = 25
                ending = ['ООО','ПАО','АО','ЗАО']
                text = str(name) 
                three = text[-3:]
                adjust_name = ''
                if name == 'Прочие':
                    return name
                for i in ending:
                    if i in three:
                        adjust_name = text.replace(i,'')
                        if len(adjust_name) > dig:
                            return adjust_name[:dig] +'.'
                        else:
                            return adjust_name        
                parts = text.split(' ')
                return parts[0] + ' ' + parts[1][:1] + '.' + parts[2][:1]+'.'
        
            def summary_sheet():       
                df = self.table_df(str(self.date_picker.date))
                df = df[['status','name','debt','dt13','cr13','cr26','due_to','dt29','dt30','ap','dta13','ad_due']]
                new_col_name = {'dt13':'Начислено за месяц',
                                'cr26':'Дт. задол. на нач. месяца',
                                'dt29':'Кт. задол. на нач месяца',
                                'cr13':'Оплачено (зачтено) на дату',
                                'debt':'Дт. задол. текущая',  
                                'due_to':'Всего начислений с учетом Дт. и Кт. задолженности',                       
                                'dt30': 'Депозит текущий',
                                'ap':'Кт. задол. текущая',
                                'dta13':'Начислен. аванс',
                                'ad_due':'Аванс к оплате'                       
                                }
                df = df.rename(columns=new_col_name)
                    
                excel_content['summary'] = df            

            def get_all(data):
                stored_data = data        
                if len(stored_data) == 0:
                    return
                
                for item in stored_data:
                    sheet_name = name_adj(item)           
                    date_tupple = self.get_dates(str(self.date_picker.date))
                    names = f"names:{item}"
                    
                    fme = date_tupple[1]
                    id_acc = '13'
                    acc_id  = r.smembers("acc:"+id_acc)
                    fmes = r.smembers("fme:"+fme)
                    tenets = r.smembers(names)
                                
                    ids = acc_id.intersection(fmes,tenets)
                    
                    data_list = []
                    for id in ids:
                        key = f"gl:{id}"
                        hash_data = r.hgetall(key)
                        data_list.append({'id': id, **hash_data})       

                    df = pd.DataFrame(data_list).fillna('')
                    if df.empty:
                        df1 = df
                    else:
                        df['dt'] = df['dt'].astype(float)
                        df['cr'] = df['cr'].astype(float)
                    
                        df1 = df[['date','la','la_a','cost_item','dt','cr','comments']]
                    
                    fme = date_tupple[3]
                    id_acc = '26'
                    acc_id  = r.smembers("acc:"+id_acc)
                    fmes = r.smembers("fme:"+fme)
                    tenets = r.smembers(names)
                                
                    ids = acc_id.intersection(fmes,tenets)
                    
                    data_list = []
                    for id in ids:
                        key = f"gl:{id}"
                        hash_data = r.hgetall(key)
                        data_list.append({'id': id, **hash_data})       

                    df = pd.DataFrame(data_list).fillna('')
                    if df.empty:
                        df2 = df
                    else:
                        df['dt'] = df['dt'].astype(float)
                        df['cr'] = df['cr'].astype(float)
                        df['dt'] = df['cr']
                        df['cr'] = 0.0 
                    
                        df2 = df[['date','la','la_a','cost_item','dt','cr','comments']]
                    
                    fme = date_tupple[3]
                    id_acc = '29'
                    acc_id  = r.smembers("acc:"+id_acc)
                    fmes = r.smembers("fme:"+fme)
                    tenets = r.smembers(names)
                                
                    ids = acc_id.intersection(fmes,tenets)
                    
                    data_list = []
                    for id in ids:
                        key = f"gl:{id}"
                        hash_data = r.hgetall(key)
                        data_list.append({'id': id, **hash_data})       

                    df = pd.DataFrame(data_list).fillna('')
                    if df.empty:
                        df3 = df
                    else:
                        df['dt'] = df['dt'].astype(float)
                        df['cr'] = df['cr'].astype(float)
                        df['cr'] = df['dt']
                        df['dt'] = 0.0
                        
                    
                        df3 = df[['date','la','la_a','cost_item','dt','cr','comments']]
                    
                    
                    df = pd.concat([df3,df2,df1],axis=0)
                    
                    if df.empty:
                        excel_content[sheet_name] = df
                    
                    sum_dt = df['dt'].sum()
                    sum_cr = df['cr'].sum()
                    
                    sum_row = pd.DataFrame({
                    'date': ['ИТОГО:'],
                    'la': [''],
                    'la_a': [''],
                    'cost_item': [''],
                    'dt': [sum_dt],
                    'cr': [sum_cr],
                    'comments': ['']
                        })


                    df_combine = pd.concat([df, sum_row], axis=0)
                    new_col_name = {'date':'Дата',
                                'la':'Договор',
                                'la_a':'Доп_сщглашение',
                                'cost_item':'Статья',
                                'dt':'Начислено',  
                                'cr':'Оплачено',                       
                                'comments': 'Комментарий_расчет'                                              
                                }
                    df_combine = df_combine.rename(columns=new_col_name)
                        
                            
                    
                    excel_content[sheet_name] = df_combine
                    
            
            if n_clicks:          
                
                
                # Create an in-memory Excel file buffer
                excel_buffer = io.BytesIO()
                file = f"{str(self.date_picker.date)}_data.xlsx"
                
                summary_sheet()
                get_all(data)
                

                # Write the DataFrame to the buffer using ExcelWriter
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    for key in excel_content:
                        df = excel_content[key]       
                        df.to_excel(writer, index=False, sheet_name=key)

                # Seek to the beginning of the buffer
                excel_buffer.seek(0)

                # Return the Excel file as bytes for download
                return dcc.send_bytes(excel_buffer.getvalue(), filename=file)

gl = GL()

class LeaseAgreements:
    def __init__(self) -> None:
        #Componets declarations
        
        self.la_modal_see = html.Div(
        dbc.Modal(id='la_modal_see',size='xl',is_open=False)
            )

        self.la_table_download = dcc.Download(id='la_table_download')
        
        self.la_see_button = dbc.Button("Просмотр договора ", color="primary", outline="primary", style={'border': '2px solid', 'border-radius': '5px', 'float': 'top'},  className="me-1",id='la_see_btn')
        self.la_dnl_button = dbc.Button("Скачать таблицу", color="primary", outline="primary", style={'border': '2px solid', 'border-radius': '5px', 'float': 'top'},  className="me-1",id='la_dnl_button')     
        self.la_fig1_btn = dbc.Button("Договоры Gantt", color="secondary",  className="me-1",id='la_fig1_btn')   
        self.la_fig2_btn = dbc.Button("Договоры Icicle", color="secondary",  className="me-1",id='la_fig2_btn')   
        self.la_accord = html.Div([
            dbc.Accordion([
                dbc.AccordionItem([
                    self.la_fig1_btn,
                    self.la_fig2_btn,
                ],title="Визуализация")
            ],start_collapsed=True)
        ],style={"margin-top": "100px"})
        
        self.group_switchs = html.Div(
        [
        dbc.Label("Группировка"),
        dbc.Checklist(
            options=[
                {"label": "Группировать по договорам", "value": 1},
                {"label": "Показать все периоды", "value": 2},                
            ],
            
            id="la_group_switch",
            switch=True,
            ),
        ]
        )
        self.la_quick_filter = html.Div(
            [
            dbc.Label("Быстрый фильтр"),
            dbc.RadioItems(
            options=[
                {'label': 'Все договоры', 'value': 1},
                {'label': 'Завершенные', 'value': 2},
                {'label': 'Новые', 'value': 3},
                {'label': 'Продленные', 'value': 4}
            ],
            value= 1,  
            id="la_quick_filter",          
            inline=True,            
            style={'margin-right': '20px'},  
            )
        ]
        )
        
        self.la_comparison_dropdown = html.Div([
            dcc.Dropdown(id='la_tennet_dropdown',multi=True)
                    ],className="dbc"         
        )
        
        self.la_max_date = self.get_max_month()
        
        self.la_date_picker = dcc.DatePickerSingle(
        id='la_date_picker',
        min_date_allowed=date(2022,3,1),
        initial_visible_month= date.today(),
        display_format='D MMM Y',
        max_date_allowed=datetime.strftime(self.la_max_date,'%Y-%m-%d'), 
        date=date.today()      
        )
        
        self.la_month_label = html.H2('Month', className='display-4',id='la_la_month_label')
        self.la_label = html.H2('Договоры с арендаторами', className='display-4')
        self.active_la_table = html.Div(id='active_la_table')
        col = [
                dict(id='id',name = '_id',), 
                dict(id='name_',name = 'Арендатор',hideable = False,),
                dict(id='la_',name = 'Договор',hideable = False),
                dict(id='la_a_',name = 'Доп. соглашение',hideable = False),
                dict(id='premis_type_',name = 'Тип помещения',hideable = True),
                dict(id='count_',name = 'Количество',hideable = True),
                dict(id='area_',name = 'Расч. площадь',hideable = True),
                dict(id='date_start_',name = 'Начало',hideable = True),
                dict(id='date_finish_',name = 'Завершение',hideable = True),
                dict(id='la_date_start_',name = 'Начало дог.',hideable = True),
                dict(id='la_date_finish_',name = 'Завершение дог.',hideable = True),                                
                dict(id='value_БАП за ОП',name = 'БАП за ОП',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),   
                dict(id='value_ЭП за ОП',name = 'ЭП за ОП',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),  
                dict(id='value_ЕП за ММ общий',name = 'ЕП за ММ общий',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),  
                dict(id='value_ЕП за 1 ММ',name = 'ЕП за 1 ММ',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),  
                dict(id='value_БАП за CП',name = 'БАП за CП',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),  
                dict(id='value_Проц. с оборота за ОП',name = 'Проц. с оборота за ОП',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),  
                dict(id='value_Проц. с оборота прочие',name = 'Проц. с оборота прочие',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),  
                dict(id='value_ЕП прочие',name = 'ЕП прочие',hideable = True, type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer).group(True)),         
        ]
        
        self.la_table = html.Div(dash_table.DataTable(
        id='la_data_tbl',       
        columns=col,
        data=[],
        editable=False,
        filter_action='native',
        #style_filter={'backgroundColor': 'white',  },
        sort_action='native',
        sort_mode='multi',              
        page_action="native",   
        #fixed_columns={'headers': True, 'data': 3},
        style_table={'overflowX': 'auto', 'maxWidth': '100%', 'width': '100%'},  
        style_cell={'fontSize': '12px'},
        style_cell_conditional=
        [
        {'if': {'column_id': 'id',},'display': 'None',},
        ]
        +
        [        
        {'if': {'column_id': 'name_'}, 'textAlign': 'left'},  
        ] + 
        [
           {'if': {'column_id': 'la_'}, 'textAlign': 'left'},   
        ]
        +
        [
           {'if': {'column_id': 'la_a_'}, 'textAlign': 'left'},   
        ]
        +
        [
        {'if': {'column_id': col_id['id']}, 'textAlign': 'center'} for col_id in col[4:]  # Set text-align to center for other columns
        ],
    

        
        tooltip_header={
        'name_': 'Наименование арендатора',
        'la_':'Наименование договора (нажмите для просмотра)',
        'la_a_': 'Наименование доп соглашения (нажмите для просмотра)',
        'premis_type_': 'Тип помешения: ОП - офисы, ММ - машино-места, СП - склады',
        'count_': 'Количество помещений по договору',
        'area_': 'Площадь помещений по договорору',
        'date_start_': 'Дата начала условий',
        'date_finish_': 'Дата окончания условий',
        'la_date_start_': 'Дата начала договора',
        'la_date_finish_': 'Дата завершения договора',
        'value_БАП за ОП': 'БАП - базовая арендная плата (руб с НДС / м2 / год)',
        'value_ЭП за ОП': 'ЭП - эксплуатационные платежи (руб с НДС / м2 / год)',
        'value_ЕП за ММ общий': 'ЕП - ежемесячные платежи  (руб с НДС / месяц)',
        'value_ЕП за 1 ММ': 'ЕП - ежемесячные платежи за 1 машино-место (руб с НДС / месяц)',
        'value_Проц. с оборота за ОП': 'Процент от выручки арендатора с НДС',
        
        }
        
          
        
        ),className="dbc dbc-row-selectable")
        
        #Stat lables
        self.la_stat_month_label = html.H5(children='Статистика',id='la_stat_month_label')
        self.la_progeress_active = dbc.Progress(value=100,color="warning", id='la_progress_active')
        self.la_label_active = html.Div(html.P(['Активные договоры  ', dbc.Badge('100', color="primary", pill=True, id='la_label_active', className="me-1"),
                                                dbc.Badge(' Офисы:   100', color="success", pill=False, id='la_label_active_op', className="me-1"),
                                                dbc.Badge(' Машино-места:   100', color="info", pill=False, id='la_label_active_pp', className="me-1"),
                                                dbc.Badge(' Склады:   100', color="light", pill=False, id='la_label_active_wh', className="me-1"),
                                                dbc.Badge(' Прочие:   100', color="secondary", pill=False, id='la_label_active_other', className="me-1"),
                                                ]),style={"margin-top": "20px"})
        self.la_progeress_finished = dbc.Progress(value=20,color="danger",id='la_progress_finished')
        self.la_label_finished = html.Div(html.P(['Завершенные договоры  ', dbc.Badge('100', color="primary", pill=True, id='la_label_finished', className="me-1"),
                                                dbc.Badge(' Офисы:   100', color="success", pill=False, id='la_label_finished_op', className="me-1"),
                                                dbc.Badge(' Машино-места:   100', color="info", pill=False, id='la_label_finished_pp', className="me-1"),
                                                dbc.Badge(' Склады:   100', color="light", pill=False, id='la_label_finished_wh', className="me-1"),
                                                dbc.Badge(' Прочие:   100', color="secondary", pill=False, id='la_label_finished_other', className="me-1"),                                                                                                  
                                                  ]),style={"margin-top": "20px"})
        self.la_progeress_new = dbc.Progress(value=20,color="success",id='la_progress_new')
        self.la_label_new = html.Div(html.P(['Новые договоры  ', dbc.Badge('100', color="primary", pill=True, id='la_label_new', className="me-1"),
                                                dbc.Badge(' Офисы:   100', color="success", pill=False, id='la_label_new_op', className="me-1"),
                                                dbc.Badge(' Машино-места:   100', color="info", pill=False, id='la_label_new_pp', className="me-1"),
                                                dbc.Badge(' Склады:   100', color="light", pill=False, id='la_label_new_wh', className="me-1"),
                                                dbc.Badge(' Прочие:   100', color="secondary", pill=False, id='la_label_new_other', className="me-1"), 
                                             ]),style={"margin-top": "20px"})
        
        
        
        self.la_progeress_extend = dbc.Progress(value=20,color="info",id='la_progress_ext')
        
        self.la_label_extend = html.Div(html.P(['Продленные / изменненые договоры (условия)  ', dbc.Badge('100', color="primary", pill=True, id='la_label_extended', className="me-1"),
                                                dbc.Badge(' Офисы:   100', color="success", pill=False, id='la_label_extended_op', className="me-1"),
                                                dbc.Badge(' Машино-места:   100', color="info", pill=False, id='la_label_extended_pp', className="me-1"),
                                                dbc.Badge(' Склады:   100', color="light", pill=False, id='la_label_extended_wh', className="me-1"),
                                                dbc.Badge(' Прочие:   100', color="secondary", pill=False, id='la_label_extended_other', className="me-1"), 
                                                                                               
                                                
                                                ]),style={"margin-top": "20px"})
        
        #Stored values
        self.la_group_switch_store = dcc.Store(id='la_group_switch_store')
        self.la_all_switch_store = dcc.Store(id='la_all_switch_store')
        self.la_dropdown_store = dcc.Store(id='la_dropdown_store') 
        self.la_date_picker_store = dcc.Store(id='la_date_picker_store') 
        self.la_data_table_store = dcc.Store(id='la_data_table_store') 
        self.la_chosed_id_agreement = dcc.Store(id='la_chosed_id_agreement') 
        self.la_icicle_store = dcc.Store(id='la_icicle_store') 
       
    #Charts modals
        self.la_gantt_modal = html.Div([
            dbc.Modal([
                dbc.ModalTitle('Договоры Gantt'),
                dbc.ModalHeader(id='la_gantt_header',),
                
                dbc.ModalBody(
                    dcc.Graph(figure={},id='la_gantt',className="dbc")
                ),
                
            ],id='la_gantt_modal',fullscreen=True,scrollable=True,is_open=False)
        ])
        
        self.la_icicle_modal = html.Div([
            dbc.Modal([
                dbc.ModalTitle('Активные договоры - Icicle Chart', id='la_icicle_header'),
                dbc.ModalHeader(dbc.Checklist(options=[{"label": "Группировать по арендаторам", "value": 1},],switch=True,id='la_icicle_switch')),
                dbc.ModalBody(
                    dcc.Graph(figure={},id='la_icicle',className="dbc")
                ),
            ],id='la_icicle_modal',fullscreen=True,scrollable=True,is_open=False)
        ])
        
        
        
        
    #layout
        self.la_main_layout = dbc.Container(
        html.Div(
        [
        dbc.Row([
            dbc.Col(self.la_month_label,width=4),
            dbc.Col(self.la_label,width=8)
        ],style={"margin-top": "20px"}),        
        dbc.Row([
            dbc.Col(html.Hr(),width=4),
            dbc.Col(html.Hr(),width=8)
        ]),
        dbc.Row([
            dbc.Col(html.H5('Выбор даты'),width=4),  
            dbc.Col(self.la_stat_month_label,width=8,), 
                     
        ]),
        dbc.Row([
            dbc.Col([self.la_date_picker,self.la_accord],width=4),
            dbc.Col([dbc.Stack([self.la_label_active,self.la_progeress_active]), dbc.Stack([self.la_label_finished,self.la_progeress_finished]), dbc.Stack([self.la_label_new,self.la_progeress_new]), dbc.Stack([self.la_label_extend,self.la_progeress_extend])
        ]),
                           
        ],className="dbc",),   
        
        dbc.Row([
            dbc.Col(html.Hr(),width=12)
        ]),
        
        dbc.Row([
            dbc.Col(dbc.Stack([html.H5("Поиск по договорам и условиям")]),width=4),          
        ],className="dbc",style={"margin-top": "20px"}),   
                 
        dbc.Row([
            dbc.Col(dbc.Stack([html.P("Выбор арендатора"),self.la_comparison_dropdown]),width=4),
            dbc.Col(self.group_switchs,width=2),
            dbc.Col(self.la_quick_filter,width=6),          
        ],className="dbc",style={"margin-top": "20px"}, align='left'),   
                      
        
        dbc.Row([
            
            dbc.Col(html.Hr(),width=12)
        ]),
        dbc.Row([            
            dbc.Col(html.H4("Данные по договорам и условиям"),width=12)
        ]),
        dbc.Row([            
            dbc.Col([self.la_dnl_button,self.la_see_button],width=12)
        ]),

        dbc.Row([
            dbc.Col(self.la_table,width=12)
        ],style={"margin-top": "20px"}),
        
        dbc.Row([
            dbc.Col([self.la_dropdown_store,self.la_date_picker_store,self.la_group_switch_store,self.la_all_switch_store,self.la_data_table_store, self.la_chosed_id_agreement,self.la_modal_see, self.la_table_download, self.la_gantt_modal, self.la_icicle_modal,self.la_icicle_store],width=12)
        ],style={"margin-top": "20px"}),
        dbc.Row([            
            dbc.Col(html.P(id='dummy'),width=12)
        ]),
        dbc.Row([            
            dbc.Col(html.P('Poklonka Place 2024'),width=12)
        ],style={"margin-top": "50px"}),


        
        
        ],style={"padding-top": "70px"}
  
        )
        )
    
    #data process functions
    
    def replace_nan_pid(self,val):
        if val is None:
            return ''
        else:
            return str(val)
    
    def la_get_data(self,date):
        date_tupple = gl.get_dates(date)
        start = date_tupple[0]
        finish = date_tupple[3] 
        cut_off = date_tupple[1]
    
        int_start = int(start.replace('-',''))
        int_finish = int(finish.replace('-',''))
        int_cutoff = int(cut_off.replace('-',''))
        
        start_date = r.zrangebyscore("la:min_date:", "-inf", int_cutoff)
        finish_date = r.zrangebyscore("la:max_date:", "-inf", int_finish )
    
        min_dates_set = set(start_date)
        max_dates_set = set(finish_date)

        
       
        ids =  min_dates_set - max_dates_set

        data_list = []
        for id in ids:
            key = f"la:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'la': id, **hash_data})       

        df = pd.DataFrame(data_list)        
        
        df['value'] = df['value'].astype(float)
        
        df = df.pivot_table(index=['name','la','la_a','date_start','date_finish','la_date_start','la_date_finish','premis_type','count','area','pid','id_agreement'],columns=['rate_description'],values=['value'],aggfunc='first')
                       
        
        return df
    
    def get_max_month(self):
        max_score = r.zrevrange("la:max_date:", 0, 0, withscores=True)
        max_score_value = max_score[0][1] if max_score else None
        max_score_int = int(max_score_value)
        date_object = datetime.strptime(str(max_score_int), "%Y%m%d")
        return date_object
    
    def la_layout(self):
        return self.la_main_layout
    
    def la_param_query(self,value, g_switch, date, qf_value):
                
        ids = set()
        g_swithch_grouped = False
        g_switch_all = False
        date_set = set()
        contr_set = set()
        
        if g_switch is not None:
            if len(g_switch) !=0:
                if len(g_switch) == 1:
                    a = g_switch[0]
                    if a == 1:
                        g_swithch_grouped = True
                    else:
                        g_switch_all = True
                if len(g_switch) == 2:
                    g_swithch_grouped = True
                    g_switch_all = True
                      
        def get_dates_set(g_switch_all,date):
            
            dates = set()
            if g_switch_all == True:
                dates = r.zrangebyscore("la:max_date:", "-inf", "+inf")
                return dates
            else:
                if qf_value == 1:
                    date_tupple = gl.get_dates(date)
                    finish = date_tupple[3] 
                    cut_off = date_tupple[1]
        
                    int_finish = int(finish.replace('-',''))
                    int_cutoff = int(cut_off.replace('-',''))
        
                    start_date = r.zrangebyscore("la:min_date:", "-inf", int_cutoff)
                    finish_date = r.zrangebyscore("la:max_date:", "-inf", int_finish)
        
                    min_dates_set = set(start_date)
                    max_dates_set = set(finish_date)
        
                    dates = min_dates_set - max_dates_set
                    return dates

                elif qf_value == 2:
                    date_tupple = gl.get_dates(date)
                    finish = date_tupple[0] 
                    cut_off = date_tupple[1]
                    next_month = date_tupple[4]
            
                    int_finish = int(finish.replace('-',''))
                    int_cutoff = int(cut_off.replace('-',''))
                    int_next_month = int(next_month.replace('-',''))
            
                    start_date = r.zrangebyscore("la:max_date:", int_finish, int_cutoff)
                    finish_date = r.zrangebyscore("la:la_max_date:", int_finish, int_cutoff)
            
                    min_dates_set = set(start_date)
                    max_dates_set = set(finish_date)
            
                    dates = min_dates_set.intersection(max_dates_set)
                    return dates
                
                elif qf_value == 3:
                    date_tupple = gl.get_dates(date)
                    finish = date_tupple[0] 
                    cut_off = date_tupple[1]
        
                    int_finish = int(finish.replace('-',''))
                    int_cutoff = int(cut_off.replace('-',''))
        
                    start_date = r.zrangebyscore("la:la_min_date:", int_finish, int_cutoff)
                            
                    min_dates_set = set(start_date)
                    
                    dates = min_dates_set
                    return dates
                else:
                    if qf_value == 4:
                        date_tupple = gl.get_dates(date)
                        finish = date_tupple[0] 
                        cut_off = date_tupple[1]
                        next_month = date_tupple[4]
            
                        int_finish = int(finish.replace('-',''))
                        int_cutoff = int(cut_off.replace('-',''))
                        int_next_month = int(next_month.replace('-',''))
            
                        start_date = r.zrangebyscore("la:max_date:", int_finish, int_cutoff)
                        finish_date = r.zrangebyscore("la:la_max_date:", int_finish, int_cutoff)
            
                        min_dates_set = set(start_date)
                        max_dates_set = set(finish_date)
            
                        dates = min_dates_set - max_dates_set
                        return dates 
                
                
        
        def get_names_set(value):
            names = set()    
            if value is not None:
                if len(value) !=0:
                    for item in value:
                        members = r.smembers(f"la:contr:{item}")
                        names.update(members)
                    return names
                else:
                    return names
            else:
                return names
        
        date_set = get_dates_set(g_switch_all,date)
        contr_set = get_names_set(value)
        
        if len(contr_set) != 0:
            ids = contr_set.intersection(date_set)
        else:
            ids = date_set
        
        data_list = []
        for id in ids:
            key = f"la:{id}"
            hash_data = r.hgetall(key)
            data_list.append({'la': id, **hash_data})       

        
        
        df = pd.DataFrame(data_list)
        
        if df.empty:
            return df
                       
        
        df['value'] = df['value'].astype(float)
        
        if  g_swithch_grouped == False:     
            df = df.pivot_table(index=['name','la','la_a','date_start','date_finish','la_date_start','la_date_finish','premis_type','count','area','pid','id_agreement'],columns=['rate_description'],values=['value'],aggfunc='first')

        else:
            if g_switch_all == False:
                df = df.pivot_table(index=['name','la','la_date_start','la_date_finish','premis_type','count','area','pid','id_agreement'],columns=['rate_description'],values=['value'],aggfunc='first')
            else:
                df = df.pivot_table(index=['name','la','la_date_start','la_date_finish','premis_type','count','area','pid','id_agreement'],columns=['rate_description'],values=['value'],aggfunc='max')
        df = df.reset_index()
        df.columns = ['_'.join(col).strip() for col in df.columns.values] 
        df['id'] = df.index          
        
        return df
 
    #Callbacks
    #DatePicker
    def la_callbacks(self,app):
        @app.callback(            
            Output('la_stat_month_label','children'),
            Output('la_data_tbl','data'),
            Output('la_la_month_label','children'),
            Output('la_label_active','children'),
            Output('la_tennet_dropdown','options'),
            Output('la_date_picker_store','data'),
            Output('la_data_table_store','data'),
            
            Output('la_label_active_op','children'),
            Output('la_label_active_pp','children'),
            Output('la_label_active_wh','children'),
            Output('la_label_active_other','children'),
            
            Output('la_label_finished','children'),
            Output('la_label_finished_op','children'),
            Output('la_label_finished_pp','children'),
            Output('la_label_finished_wh','children'),
            Output('la_label_finished_other','children'),
            
            Output('la_label_new','children'),
            Output('la_label_new_op','children'),
            Output('la_label_new_pp','children'),
            Output('la_label_new_wh','children'),
            Output('la_label_new_other','children'),     
            
            Output('la_label_extended','children'),
            Output('la_label_extended_op','children'),
            Output('la_label_extended_pp','children'),
            Output('la_label_extended_wh','children'),
            Output('la_label_extended_other','children'),            
            
            Output('la_progress_finished','value'),  
            Output('la_progress_new','value'), 
            Output('la_progress_ext','value'), 
            
            
            Input('la_date_picker','date')                
            )        
        def la_date_picker(date):            
            def init_data(date):
                df = self.la_get_data(date)
                df = df.reset_index()
                df.columns = ['_'.join(col).strip() for col in df.columns.values]
                df['id'] = df.index
                return df           
            def get_all_tenets_names():
                gs = [2] 
                df = self.la_param_query(None,gs,date,1)
                return df['name_'].unique().tolist()
            def count_all(date):
                cnt_all ={}
                cnt_all['active'] = {}
                gs = [] 
                df = self.la_param_query(None,gs,date,1)
                cnt_all['active']['total'] = len(df['pid_'].unique())
                df_op = df.query('premis_type_ == "ОП"') 
                cnt_all['active']['op'] = len(df_op['pid_'].unique())
                df_op = df.query('premis_type_ == "ММ"') 
                cnt_all['active']['pp'] = len(df_op['pid_'].unique())
                df_op = df.query('premis_type_ == "СП"') 
                cnt_all['active']['wh'] = len(df_op['pid_'].unique())
                df_op = df.query('premis_type_ == "Прочие"') 
                cnt_all['active']['other'] = len(df_op['pid_'].unique())                
                
                df = self.la_param_query(None,gs,date,2)
                cnt_all['finished'] = {}
                if df.empty:
                    cnt_all['finished']['total'] = 0
                    cnt_all['finished']['op'] = 0
                    cnt_all['finished']['pp'] = 0
                    cnt_all['finished']['wh'] = 0
                    cnt_all['finished']['other'] = 0
                else:                    
                    cnt_all['finished']['total'] = len(df['pid_'].unique())
                    df_op = df.query('premis_type_ == "ОП"') 
                    cnt_all['finished']['op'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "ММ"') 
                    cnt_all['finished']['pp'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "СП"') 
                    cnt_all['finished']['wh'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "Прочие"') 
                    cnt_all['finished']['other'] = len(df_op['pid_'].unique())  
                
                df = self.la_param_query(None,gs,date,3)
                cnt_all['new'] = {}
                if df.empty:
                    cnt_all['new']['total'] = 0
                    cnt_all['new']['op'] = 0
                    cnt_all['new']['pp'] = 0
                    cnt_all['new']['wh'] = 0
                    cnt_all['new']['other'] = 0
                else:                    
                    cnt_all['new']['total'] = len(df['pid_'].unique())
                    df_op = df.query('premis_type_ == "ОП"') 
                    cnt_all['new']['op'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "ММ"') 
                    cnt_all['new']['pp'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "СП"') 
                    cnt_all['new']['wh'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "Прочие"') 
                    cnt_all['new']['other'] = len(df_op['pid_'].unique())  
                
                df = self.la_param_query(None,gs,date,4)
                cnt_all['ext'] = {}
                if df.empty:
                    cnt_all['ext']['total'] = 0
                    cnt_all['ext']['op'] = 0
                    cnt_all['ext']['pp'] = 0
                    cnt_all['ext']['wh'] = 0
                    cnt_all['ext']['other'] = 0
                else:                    
                    cnt_all['ext']['total'] = len(df['pid_'].unique())
                    df_op = df.query('premis_type_ == "ОП"') 
                    cnt_all['ext']['op'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "ММ"') 
                    cnt_all['ext']['pp'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "СП"') 
                    cnt_all['ext']['wh'] = len(df_op['pid_'].unique())
                    df_op = df.query('premis_type_ == "Прочие"') 
                    cnt_all['ext']['other'] = len(df_op['pid_'].unique())  
                               
                
                return cnt_all
            
            month_name = gl.getMonthName(date)
            init_df = init_data(date)           
            change_dict = count_all(date)
            
            
            arg1 = f"Статистика: {month_name}"
            arg2 = init_df.to_dict('records')
            arg3 = month_name
            arg4 = f"Всего :{len(init_df['pid_'].unique())}"
            arg5 = get_all_tenets_names()
            arg6 = date  
            arg7 = arg2
            arg8 = f" Офисы: {change_dict['active']['op']}"
            arg9 = f" Машино-места: {change_dict['active']['pp']}"
            arg10 = f" Склады: {change_dict['active']['wh']}"
            arg11 = f" Прочие: {change_dict['active']['other']}"
            
            arg12 = f" Всего: {change_dict['finished']['total']}"
            arg13 = f" Офисы: {change_dict['finished']['op']}"
            arg14 = f" Машино-места: {change_dict['finished']['pp']}"
            arg15 = f" Склады: {change_dict['finished']['wh']}"
            arg16 = f" Прочие: {change_dict['finished']['other']}"
            
            arg17 = f" Всего: {change_dict['new']['total']}"
            arg18 = f" Офисы: {change_dict['new']['op']}"
            arg19 = f" Машино-места: {change_dict['new']['pp']}"
            arg20 = f" Склады: {change_dict['new']['wh']}"
            arg21 = f" Прочие: {change_dict['new']['other']}"
            
            arg22 = f" Всего: {change_dict['ext']['total']}"
            arg23 = f" Офисы: {change_dict['ext']['op']}"
            arg24 = f" Машино-места: {change_dict['ext']['pp']}"
            arg25 = f" Склады: {change_dict['ext']['wh']}"
            arg26 = f" Прочие: {change_dict['ext']['other']}"
            
            arg27 = round(change_dict['finished']['total'] / change_dict['active']['total']*100,0)
            arg28 = round(change_dict['new']['total'] / change_dict['active']['total']*100,0)
            arg29 = round(change_dict['ext']['total'] / change_dict['active']['total']*100,0)
            
            return arg1, arg2, arg3, arg4, arg5,arg6, arg7, arg8,arg9, arg10, arg11,arg12,arg13, arg14, arg15, arg16, arg17, arg18, arg19, arg20, arg21, arg22, arg23, arg24, arg25, arg26, arg27, arg28, arg29
        
        #LA_Dropdown_filter
        @app.callback( 
            Output('la_dropdown_store','data'),            
            Output('la_data_tbl','data',allow_duplicate=True), 
            Output('la_group_switch_store','data'), 
            Output('la_data_table_store','data', allow_duplicate=True ),
            Input('la_group_switch','value'),            
            Input('la_tennet_dropdown','value'),
            Input('la_quick_filter','value'),
            Input('la_date_picker_store','data'),

            
            prevent_initial_call=True,
            )
        def tennet_change(g_switch,value,qf_value,cur_date):         
            
            dff = self.la_param_query(value,g_switch,cur_date,qf_value)
            
            arg1 = value
            arg2 = dff.to_dict('records')
            arg3 = g_switch                       
            return arg1, arg2, arg3, arg2   
        
        #LA_Table_click
        @app.callback(
        Output('la_chosed_id_agreement','data'),
        Output('la_see_btn','children'),        
        Input('la_data_tbl','active_cell'),
        Input('la_data_table_store','data'),
        prevent_initial_call=True
        )
        def la_table_click(active_cell,df_stored):
            if active_cell is None:
                return None, 'Просмотр договора '
            else:
                if active_cell['column_id'] not in ['la_', 'la_a_']:                                        
                    return None, 'Просмотр договора '
                else:
                    try:
                        df = pd.DataFrame(df_stored)                    
                        row_index = active_cell['row_id']
                        col_index = active_cell['column_id']
                        value = df.iloc[row_index][col_index]
                        comments  = df.iloc[row_index]['name_']
                        
                        la_id = ''
                        
                        if active_cell['column_id'] == 'la_':
                            a = df.iloc[row_index]['pid_']
                            if a == None:
                                la_id = df.iloc[row_index]['id_agreement_']
                            else:
                                la_id = a
                        
                        if active_cell['column_id'] == 'la_a_':
                            la_id = df.iloc[row_index]['id_agreement_']   
                        
                        return la_id, f"Просмотр договора {value} ({comments})"
                    except:
                        return None, 'Просмотр договора '

        #LA_show_la_modal
        @app.callback(
        Output("la_modal_see", "is_open"),
        Output('la_modal_see','children'),
        Input("la_see_btn", "n_clicks"),
        
        [State("la_chosed_id_agreement", "data"),
            State("la_modal_see", "is_open")
         
         ],
        
        prevent_initial_call=True
    )
        def toggle_la_modal(n1, file_data, is_open):
            
            def make_file_dict():
                #folder = 'Portal/assets/la'
                folder = '/home/c86117/manu2345.na4u.ru/app/assets/la'
                file_dict = {}
    
                file_list = os.listdir(folder)    
    
                for file_name in file_list:
                    parts = file_name.split(' ')
                    for part in parts:
                        file_dict[part] = file_name
                return file_dict
            def load_file():
                try:
                    file_dict = make_file_dict()
                    file_name = str(file_dict[file_data])
                    file_path = sd.la_file_folder+file_name           
                    file_inframe = html.Iframe(
                    src=file_path,                    
                    width='100%',
                    height='600',
                    draggable='true'                
                    )
                    return file_inframe
                except:
                    return dbc.ModalBody('Файл не найден')
                
            if n1:
                file = load_file()
                return not is_open, dbc.ModalBody(file)
                            
            return is_open, dbc.ModalBody('Не выбран договор')
        
        #LA_dln_table
        @app.callback(
            Output('la_table_download','data'),
            Input('la_dnl_button','n_clicks'),
            State('la_data_table_store','data'),
            prevent_initial_call=True
        )
        def dnl_la_table(n1, df_stored):
            if n1:
                df = pd.DataFrame(df_stored)
                new_col_name = {'name_':'Арендатор','la_':'Договор','la_a_':'Доп. Соглашение','date_start_':'Дата начала условия','date_finish_':'Дата окончания условия','la_date_start_':'Дата начала договора','la_date_finish_':'Дата окончания договора','premis_type_':'Тип помещения','count_':'Количество','area_':'Площадь (расч.)'}
                df = df.rename(columns=new_col_name)   
                                
                excel_buffer = io.BytesIO()
                file = f"lease_agreements_data.xlsx"
                  
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='la_data')

                # Seek to the beginning of the buffer
                excel_buffer.seek(0)

                # Return the Excel file as bytes for download
                return dcc.send_bytes(excel_buffer.getvalue(), filename=file)
                
        #LA show gantt modal
        @app.callback(
        [Output("la_gantt_modal", "is_open"),
        Output("la_gantt", "figure"),
        Output('la_gantt_header','children')],
        [Input("la_fig1_btn", "n_clicks")],        
        [State("la_gantt_modal", "is_open"),  
        State("la_date_picker_store", "data")],  
        prevent_initial_call=True
        )
        def show_gantt_modal(n1, is_open, date):
            
            def get_gant_data(date):
                cur_date = datetime.strptime(date, '%Y-%m-%d')               
                min_date = datetime(cur_date.year-1,cur_date.month,cur_date.day)   
                max_date = datetime(cur_date.year+1,cur_date.month,cur_date.day)            
                
                min_date_str = min_date.strftime('%Y-%m-%d')
                max_date_str = max_date.strftime('%Y-%m-%d')
                
                min_date_int = int(min_date_str.replace('-',''))
                max_date_int = int(max_date_str.replace('-',''))
                                
                start_after = r.zrangebyscore("la:min_date:", max_date_int,'+inf' )
                finished_before = r.zrangebyscore("la:max_date:", "-inf", min_date_int )
                ids = r.smembers('la:all')
                sa = set(start_after)
                fb = set(finished_before)
                id_s = set(ids)
                
                ids1 = id_s - sa - fb
                
                data_list = []
                for id in ids1:
                    key = f"la:{id}"
                    hash_data = r.hgetall(key)
                    data_list.append({'la': id, **hash_data})      
                df = pd.DataFrame(data_list)   
                df = df.groupby(['name','la','la_a','date_start','date_finish','premis_type']).size().reset_index(name='count')
                df['name'] = df['name'].apply(sd.name_adj)
                df['la'] = df['la'].apply(sd.la_adj)
                
                df['la'] = df['name'] + ': ' + df['la']
                
                df = df[['la', 'date_start', 'date_finish', 'premis_type', 'la_a']]
                
                gantt_chart = px.timeline(df, x_start='date_start', x_end='date_finish', y='la',color='premis_type',text='la_a')

                gantt_chart.update_xaxes(range=[min_date_str,max_date_str])

                
                gantt_chart.add_vrect(
                    x0=date,
                    x1=date,
                    label=dict(
                        text=date,
                        textposition="top right",
                        font=dict(size=12, family="Times New Roman"),
                        ),
                    fillcolor="white",
                    opacity=0.7,
                line_width=1,
                ),

                
                
                gantt_chart.update_yaxes(autorange="reversed")
                

                

                
                gantt_chart.update_layout(height=2000)


                
                return gantt_chart
            
            if n1:
              gantt = get_gant_data(date)
              month = gl.getMonthName(date) 
              return not is_open, gantt, month
            
        #Show LA Icicle Chart
        @app.callback(
        Output("la_icicle_modal", "is_open"),
        Output("la_icicle", "figure"),
        Output('la_icicle_header','children'),
        Output('la_icicle_store','data'),
        Input("la_fig2_btn", "n_clicks"),
        State("la_icicle_modal", "is_open"),  
        State("la_date_picker_store", "data"),  
        prevent_initial_call=True
        )
        def show_icicle_modal(n1, is_open, date):
            
            def set_status(sd,fd,la_sd,la_fd):                
                
                
                cd = datetime.strptime(date,'%Y-%m-%d')
                cd_y = cd.year
                cd_m = cd.month
                
                start_date = datetime.strptime(la_sd,'%Y-%m-%d')
                sd_y = start_date.year
                sd_m = start_date.month
                
                finish_date = datetime.strptime(la_fd,'%Y-%m-%d')
                fd_y = finish_date.year
                fd_m = finish_date.month
                
                fd_int = int(str(fd).replace('-',''))
                lafd_int = int(str(la_fd).replace('-',''))
                
                if sd_y == cd_y and sd_m == cd_m:
                    return 'Новые'
                elif fd_y == cd_y and fd_m == cd_m:                    
                    return 'Завершенные'
                elif fd_int < lafd_int:
                    return 'Продленные'
                else:
                    return 'В процессе'
            
            def set_premis_name(type,cnt,area,bapo,costo,ept,eptu,bapw,perco,percw,epother):
                if type == 'ММ':
                    try:
                        return f"{cnt} - мм. \n Ежемес. платеж - {ept:,.0f} руб. с НДС; \n Цена - {eptu:,.0f} руб. мес с НДС; "
                    except:
                        return f"{cnt} - мм. \n Ежемес. платеж - {ept} руб. с НДС; \n Цена - {eptu} руб. мес с НДС; "
                if type == 'ОП':
                    try:
                        return f"{cnt} - офис. помещ. \n Общ. площадь - {area} кв.м \n БАП - {bapo:,.0f} руб/м2/год с НДС, ЭП - {costo:,.0f} руб/м2/год с НДС"
                    except:
                        return f"{cnt} - офис. помещ. \n Общ. площадь - {area} кв.м \n БАП - {bapo} руб/м2/год с НДС, ЭП - {costo} руб/м2/год с НДС"
                if type == 'СП':
                    try:
                        return f"{cnt} - склад. помещ. Общ. площадь - {area} кв.м \n БАП - {bapw:,.0f} руб/м2/год с НДС"
                    except:
                        return f"{cnt} - склад. помещ. Общ. площадь - {area} кв.м \n БАП - {bapw} руб/м2/год с НДС"
                if type == 'Прочие':
                    ret_str = ''
                    if perco is not None:
                        ret_str = ret_str + f' Процент с оборота офисные помещения - {perco} % '
                    if percw is not None:
                        ret_str = ret_str + f' Процент с оборота прочие помещения - {percw} % '
                    if epother is not None:
                        ret_str = ret_str + f' Ежемесячный платеж - {epother} % '
                    return ret_str
                
            
            df = self.la_get_data(date)
            df = df.reset_index()
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
            
            df['all'] = 'Все договоры'
            df['status'] = df.apply(lambda row: set_status(row['date_start_'],row['date_finish_'],row['la_date_start_'],row['la_date_finish_']),axis=1)
            
            df['descr'] = df.apply(lambda row:  set_premis_name(row['premis_type_'], row['count_'], row['area_'], row['value_БАП за ОП'], row['value_ЭП за ОП'], row['value_ЕП за ММ общий'], row['value_ЕП за 1 ММ'], row['value_БАП за CП'], row['value_Проц. с оборота за ОП'], row['value_Проц. с оборота прочие'], row['value_ЕП прочие']),axis=1)
            
            df = df[['all','status','name_','premis_type_','la_','la_a_','descr']]
            df_to_store = df.to_dict('records')
            
            
            fig = px.icicle(df, path=['all', 'status', 'name_', 'premis_type_' ,'la_', 'la_a_','descr'])
            fig.update_layout(height=1500)
            fig.update_traces(hovertemplate='')

            if n1:              
                
              month = gl.getMonthName(date)  
              
              return not is_open, fig, month,df_to_store
        
        
        @app.callback(
        Output("la_icicle", "figure",allow_duplicate=True),        
        Input("la_icicle_switch", "value"),        
        State("la_icicle_store", "data"),            
        prevent_initial_call=True
        )
        def icicle_switch(value, records):
            df = pd.DataFrame(records)
            a = len(value)
            if a == 1:
                df['all'] = 'Все арендаторы'
                fig =  px.icicle(df, path=['all', 'name_', 'status', 'premis_type_' ,'la_', 'la_a_','descr'])
                fig.update_layout(height=1500)
                fig.update_traces(hovertemplate='')
            else:
                df['all'] = 'Все договора'
                fig =  px.icicle(df, path=['all', 'status', 'name_', 'premis_type_' ,'la_', 'la_a_','descr'])
                fig.update_layout(height=1500)
                fig.update_traces(hovertemplate='')

            
            return fig

la = LeaseAgreements()



#-------------------RUNNING DASH----------------------------------------------------------

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"


app = dash.Dash(
    __name__, external_stylesheets=[dbc.themes.SUPERHERO, dbc_css], use_pages=True, pages_folder="")

server = app.server


app.title = 'Poklonka Place'

dash.register_page("home", path='/', layout=hp.layout())
dash.register_page("Взаиморасчеты", path='/gl', layout=gl.layout())
dash.register_page("Договоры", path='/la', layout=la.la_layout())





#----------------------GETTING LOGINS AND PASSWORDS------------------------------------------------

VALID_USERNAME_PASSWORD_PAIRS = {}

for key in r.scan_iter(match='user:*'):
    login = r.hget(key, "login")
    password = r.hget(key, "psw")    
    VALID_USERNAME_PASSWORD_PAIRS[login] = password

auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)






#----------------------COMPONENTS SECTION------------------------------------------------------------

#STORE




#NAV BAR

navbar = dbc.NavbarSimple(
    dbc.DropdownMenu(
        [
            dbc.DropdownMenuItem(page["name"], href=page["path"])
            for page in dash.page_registry.values()
            if page["module"] != "pages.not_found_404"
        ],
        nav=True,
        label="Разделы",
    ),
    brand="POKLONKA PLACE",
    color="primary",
    dark=True,
    className="mb-2",
    fixed="top"
)

user_store = dcc.Store(id='user_store', storage_type='session')  

initial_store = dcc.Store(id='init_store', storage_type='session') 



app.layout = dbc.Container(html.Div([
    navbar,user_store,initial_store, dash.page_container, 
    
]), fluid=True)

@app.callback(
    Output('user_store','data'),
    Input('init_store','data')
)
def get_user(data):
    user_name = request.authorization['username']
    sd.global_user_name['value'] = user_name
    return user_name



#Callback register
hp.hp_callbacks(app)
gl.gl_datePicker_callback(app)
gl.gl_table_callback(app)
gl.gl_clearall_callback(app)
gl.gl_dnlButton_callback(app)
gl.gl_dnlExcell_callback(app)
la.la_callbacks(app)

if __name__ == '__main__':
    app.run(debug=False)
#app.run(debug=False)
