# Это layout для daily sales

from dash import  html
import pandas as pd
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from utils.dash_components.common import CommonComponents as CC
from utils.dash_components.dftotable import df_dmc_table
import locale

from django.urls import reverse, NoReverseMatch  # <-- ДОБАВИЛИ

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

from .data import get_month_data, get_ytd_data


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
    def __init__(self, date=None):
        self.date = date
        self.data = get_month_data(date)
        self.ytd_data = get_ytd_data(date)

    def make_dayly_summary(self):
        df = self.data.copy(deep=True)
        df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("MTD %b %y").str.upper()
        df = df.drop(columns=["date"])
        df = df.groupby("month", as_index=False).sum()

        df["Ср. чек"] = df["amount"] / df["orders"].replace(0, pd.NA)
        df["Ср. чек"] = df["Ср. чек"].fillna(0)
        df["К возвратов"] = df["cr"] / df["dt"] * 100

        df = df.rename(columns=RENAMING_COLS)

        df_long = df.melt(
            id_vars="month",
            value_vars=["Выручка", "Кол-во", "Заказы", "Ср. чек", "Продажи", "Возвраты", "К возвратов"],
            var_name="Метрика",
            value_name="value",
        )

        df_pivot = df_long.pivot_table(index="Метрика", columns="month", values="value", aggfunc="first")

        c0, c1 = df_pivot.columns[:2]
        df_pivot["Δ абс."] = df_pivot[c1] - df_pivot[c0]
        df_pivot["Δ отн."] = df_pivot["Δ абс."] / df_pivot[c0].replace(0, pd.NA) * 100

        if "К возвратов" in df_pivot.index:
            df_pivot.loc["К возвратов", ["Δ абс.", "Δ отн."]] *= -1

        i_order = list(FORMATERS)[:-2]
        return df_pivot.reindex(i_order)

    def make_ytd_summary(self):
        df = self.ytd_data.copy(deep=True)
        df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("YTD %Y").str.upper()
        df = df.drop(columns=["date"])
        df = df.groupby("month", as_index=False).sum()

        df["Ср. чек"] = df["amount"] / df["orders"].replace(0, pd.NA)
        df["Ср. чек"] = df["Ср. чек"].fillna(0)
        df["К возвратов"] = df["cr"] / df["dt"].replace(0, pd.NA) * 100

        df = df.rename(columns=RENAMING_COLS)

        df_long = df.melt(
            id_vars="month",
            value_vars=["Выручка", "Кол-во", "Заказы", "Ср. чек", "Продажи", "Возвраты", "К возвратов"],
            var_name="Метрика",
            value_name="value",
        )

        df_pivot = df_long.pivot_table(index="Метрика", columns="month", values="value", aggfunc="first")

        c0, c1 = df_pivot.columns[:2]
        df_pivot["Δ абс."] = df_pivot[c1] - df_pivot[c0]
        df_pivot["Δ отн."] = df_pivot["Δ абс."] / df_pivot[c0].replace(0, pd.NA) * 100

        if "К возвратов" in df_pivot.index:
            df_pivot.loc["К возвратов", ["Δ абс.", "Δ отн."]] *= -1

        i_order = list(FORMATERS)[:-2]
        return df_pivot.reindex(i_order)

    def layout(self):
        dt = pd.to_datetime(self.date)
        str_date = f"{dt.day} {dt.strftime('%B %Y')}"

        try:
            back_url = reverse("admin:sales_mv_daily_sales_changelist")
        except NoReverseMatch:
            
            try:
                back_url = reverse("admin:sales_dailysales_changelist")
            except NoReverseMatch:
                back_url = "/admin/sales/mv_daily_sales/"

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
                            CC.report_title(f"ОТЧЕТ ПО ПРОДАЖАМ ЗА {str_date.upper()}"),
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
                        df_dmc_table(self.make_dayly_summary(), formaters=FORMATERS, className="classic-table"),
                        dmc.Space(h=30),
                        df_dmc_table(self.make_ytd_summary(), formaters=FORMATERS, className="classic-table"),
                        

                    ]
                ),
            ],
            header={"height": 60},
            padding=0,
        )

        return dmc.Container([la], fluid=True)
