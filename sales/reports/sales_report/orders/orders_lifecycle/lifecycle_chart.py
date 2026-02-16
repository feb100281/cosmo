import io
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def build_lifecycle_svg(avg_curve, df_top):

    fig, ax = plt.subplots(figsize=(9, 4.5))

    # --- топ заказы (тонкие линии)
    for oid, g in df_top.groupby("orders_id"):
        ax.plot(
            g["age_day"],
            g["cum_net"],
            alpha=0.25,
            linewidth=1,
        )

    # --- средняя кривая (жирная)
    ax.plot(
        avg_curve["age_day"],
        avg_curve["cum_net"],
        linewidth=3,
        label="Средний заказ",
    )

    # --- формат денег на оси Y
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda x, pos: f"{int(x):,}".replace(",", " "))
    )

    ax.set_title("Жизненный цикл заказа — накопленная выручка")
    ax.set_xlabel("Дней с момента заказа")
    ax.set_ylabel("Выручка")

    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()

    # --- сохраняем в SVG строку
    buffer = io.StringIO()
    fig.savefig(buffer, format="svg")
    plt.close(fig)

    return buffer.getvalue()
