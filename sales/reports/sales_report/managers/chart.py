# import io
# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib.ticker import FuncFormatter


# def build_managers_bar_svg(
#     rows,
#     title="ТОП менеджеров по чистой выручке",
#     top_n=10
# ):
#     if not rows:
#         return ""

#     df = pd.DataFrame(rows).copy()
#     if df.empty or "share" not in df.columns or "amount" not in df.columns:
#         return ""

#     def _parse_amount(v):
#         if v is None:
#             return 0.0

#         s = str(v).replace("\u00A0", " ").strip().lower()

#         if "млн" in s:
#             num = s.replace("млн", "").replace("руб.", "").replace("₽", "").replace(" ", "").replace(",", ".")
#             try:
#                 return float(num) * 1_000_000
#             except Exception:
#                 return 0.0

#         if "тыс" in s:
#             num = s.replace("тыс", "").replace("руб.", "").replace("₽", "").replace(" ", "").replace(",", ".")
#             try:
#                 return float(num) * 1_000
#             except Exception:
#                 return 0.0

#         s = s.replace("руб.", "").replace("₽", "").replace(" ", "").replace(",", ".")
#         try:
#             return float(s)
#         except Exception:
#             return 0.0

#     def _format_axis_rub(x, pos):
#         if x >= 1_000_000:
#             return f"{x / 1_000_000:.1f}".replace(".", ",") + " млн руб."
#         if x >= 1_000:
#             return f"{x / 1_000:.0f}".replace(".", ",") + " тыс. руб."
#         return f"{int(x):,}".replace(",", " ") + " руб."

#     df["amount_num"] = df["amount"].apply(_parse_amount)

#     # Подстрахуемся по названию менеджера
#     if "manager_l1" in df.columns:
#         df["manager_name"] = df["manager_l1"].fillna("—")
#     else:
#         df["manager_name"] = "—"

#     # берем топ
#     df = df.sort_values("amount_num", ascending=False).head(top_n)

#     # Для barh обычно удобнее показывать сверху вниз от большего к меньшему
#     df = df.sort_values("amount_num", ascending=True)

#     if df.empty:
#         return ""

#     # Динамическая высота — так график лучше смотрится при разном top_n
#     fig_height = max(4.8, len(df) * 0.5)
#     fig, ax = plt.subplots(figsize=(10.5, fig_height))

#     # Деловая палитра: все столбцы спокойные, лидер — акцентный
#     base_color = "#B0B7C3"
#     accent_color = "#2F5D8A"
#     colors = [base_color] * len(df)
#     if len(colors) > 0:
#         colors[-1] = accent_color  # самый большой, т.к. df отсортирован ascending

#     bars = ax.barh(
#         df["manager_name"],
#         df["amount_num"],
#         color=colors,
#         height=0.62,
#         edgecolor="none"
#     )

#     ax.set_title(title, fontsize=14, fontweight="bold", pad=16)
#     ax.set_xlabel("Чистая выручка, руб.", fontsize=10)
#     ax.set_ylabel("")

#     # Убираем scientific notation
#     ax.ticklabel_format(style="plain", axis="x")
#     ax.xaxis.set_major_formatter(FuncFormatter(_format_axis_rub))

#     # Сетка только по X, спокойная
#     ax.grid(axis="x", alpha=0.18, linestyle="-", linewidth=0.8)
#     ax.set_axisbelow(True)

#     # Чистим рамки
#     ax.spines["top"].set_visible(False)
#     ax.spines["right"].set_visible(False)
#     ax.spines["left"].set_visible(False)
#     ax.spines["bottom"].set_color("#D9DDE3")

#     # Подписи осей
#     ax.tick_params(axis="y", labelsize=10, length=0)
#     ax.tick_params(axis="x", labelsize=9)

#     max_val = float(df["amount_num"].max()) if len(df) else 0
#     x_offset = max_val * 0.015 if max_val else 0

#     # небольшой запас справа под подписи
#     ax.set_xlim(0, max_val * 1.18 if max_val else 1)

#     for i, (_, row) in enumerate(df.iterrows()):
#         share = row.get("share", 0)
#         amount_label = str(row["amount"]).replace("₽", "руб.")
#         label = f'{amount_label} ({share:.1f}%)'.replace(".", ",")

#         ax.text(
#             float(row["amount_num"]) + x_offset,
#             i,
#             label,
#             va="center",
#             ha="left",
#             fontsize=9,
#             color="#2B2B2B"
#         )

#     plt.tight_layout()

#     buf = io.BytesIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight")
#     plt.close(fig)
#     buf.seek(0)

#     return buf.getvalue().decode("utf-8")



import io
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def build_managers_bar_svg(rows, title="ТОП менеджеров по чистой выручке", top_n=10):

    if not rows:
        return ""

    df = pd.DataFrame(rows).copy()
    if df.empty or "share" not in df.columns:
        return ""

    def _parse_amount(v):
        if v is None:
            return 0.0
        s = str(v).replace("\u00A0", " ").strip().lower()

        if "млн" in s:
            num = s.replace("млн", "").replace("руб.", "").replace("₽", "").replace(" ", "").replace(",", ".")
            return float(num) * 1_000_000

        if "тыс" in s:
            num = s.replace("тыс", "").replace("руб.", "").replace("₽", "").replace(" ", "").replace(",", ".")
            return float(num) * 1_000

        s = s.replace("руб.", "").replace("₽", "").replace(" ", "").replace(",", ".")
        return float(s)

    df["amount_num"] = df["amount"].apply(_parse_amount)
    df["manager_name"] = df["manager_l1"]

    df = df.sort_values("amount_num", ascending=False).head(top_n)
    df = df.sort_values("amount_num")

    fig, ax = plt.subplots(figsize=(10, 5))

    # строгая палитра
    base_color = "#BFC7D5"
    highlight_color = "#1F4E79"

    colors = [base_color] * len(df)
    colors[-1] = highlight_color

    ax.barh(df["manager_name"], df["amount_num"], color=colors, height=0.6)

    # формат оси
    def fmt(x, pos):
        if x >= 1_000_000:
            return f"{x/1_000_000:.1f}".replace(".", ",") + " млн"
        if x >= 1000:
            return f"{int(x/1000)} тыс"
        return str(int(x))

    ax.xaxis.set_major_formatter(FuncFormatter(fmt))

    ax.set_title(title, fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Чистая выручка, руб.")

    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_val = df["amount_num"].max()

    for i, (_, row) in enumerate(df.iterrows()):
        amount = str(row["amount"]).replace("₽", "").strip()
        label = f'{amount} руб. ({row["share"]:.1f}%)'.replace(".", ",")
        ax.text(row["amount_num"] + max_val * 0.01, i, label, va="center")

    ax.set_xlim(0, max_val * 1.15)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return buf.getvalue().decode("utf-8")