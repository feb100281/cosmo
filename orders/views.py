# # orders/views.py

# from django.shortcuts import render
# from django.contrib import messages
# from django import forms


# class UploadForm(forms.Form):
#     file = forms.FileField()


# def upload_sales_view(request):
#     if request.method == "POST":
#         form = UploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             f = form.cleaned_data["file"]

#             from utils.new_updater import main

#             try:
#                 log = main(f)
#                 messages.success(request, log)
#             except Exception as e:
#                 messages.error(request, str(e))
#     else:
#         form = UploadForm()

#     return render(request, "upload_orders.html", {"form": form})



# def upload_orders_view(request):
#     if request.method == "POST":
#         form = UploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             f = form.cleaned_data["file"]

#             from utils.orders_updater import main

#             try:
#                 log = main(f)
#                 messages.success(request, log)
#             except Exception as e:
#                 messages.error(request, str(e))
#     else:
#         form = UploadForm()

#     return render(request, "upload_orders.html", {"form": form})




# def upload_cf_view(request):
#     if request.method == "POST":
#         form = UploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             f = form.cleaned_data["file"]

#             from utils.orders_cf import main

#             try:
#                 log = main(f)

#                 for line in log.split(";"):
#                     messages.success(request, line.strip())

#             except Exception as e:
#                 messages.error(request, str(e))
#     else:
#         form = UploadForm()

#     return render(request, "upload_orders.html", {"form": form})

# orders/views.py
import os
import tempfile

from io import StringIO

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.management import call_command

from .forms import (
    UploadForm,
    UploadAllOrdersForm,
    UploadStocksForm,
)


def upload_sales_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]

            from utils.new_updater import main

            try:
                log = main(f)
                messages.success(request, log)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = UploadForm()

    return render(request, "upload_orders.html", {"form": form})


def upload_orders_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]

            from utils.orders_updater import main

            try:
                log = main(f)
                messages.success(request, log)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = UploadForm()

    return render(request, "upload_orders.html", {"form": form})


def upload_cf_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]

            from utils.orders_cf import main

            try:
                log = main(f)

                for line in str(log).split(";"):
                    line = line.strip()
                    if line:
                        messages.success(request, line)

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = UploadForm()

    return render(request, "upload_orders.html", {"form": form})


# def upload_all_orders_view(request):
#     if request.method == "POST":
#         form = UploadAllOrdersForm(request.POST, request.FILES)

#         if form.is_valid():
#             sales_file = form.cleaned_data["sales_file"]

#             from utils.new_updater import main as sales_main

#             try:
#                 sales_log = sales_main(sales_file)

#                 if sales_log:
#                     for line in str(sales_log).split(";"):
#                         line = line.strip()
#                         if line:
#                             messages.success(request, f"Продажи: {line}")

#                 messages.success(request, "Продажи успешно обработаны.")

#             except Exception as e:
#                 messages.error(request, f"Ошибка загрузки продаж: {e}")

#             return redirect(request.path)
#     else:
#         form = UploadAllOrdersForm()

#     return render(request, "upload_all_orders.html", {"form": form})


def upload_all_orders_view(request):
    if request.method == "POST":
        form = UploadAllOrdersForm(request.POST, request.FILES)

        if form.is_valid():
            orders_file = form.cleaned_data["orders_file"]
            cf_file = form.cleaned_data["cf_file"]
            sales_file = form.cleaned_data["sales_file"]

            from utils.orders_updater import main as orders_main
            from utils.orders_cf import main as cf_main
            from utils.new_updater import main as sales_main

            has_error = False

            # 1. Заказы
            try:
                orders_log = orders_main(orders_file)
                if orders_log:
                    for line in str(orders_log).split(";"):
                        line = line.strip()
                        if line:
                            messages.success(request, f"Заказы: {line}")
            except Exception as e:
                has_error = True
                messages.error(request, f"Ошибка загрузки заказов: {e}")

            # 2. CF
            try:
                cf_log = cf_main(cf_file)
                if cf_log:
                    for line in str(cf_log).split(";"):
                        line = line.strip()
                        if line:
                            messages.success(request, f"CF: {line}")
            except Exception as e:
                has_error = True
                messages.error(request, f"Ошибка загрузки CF: {e}")

            # 3. Продажи
            try:
                sales_log = sales_main(sales_file)
                if sales_log:
                    for line in str(sales_log).split(";"):
                        line = line.strip()
                        if line:
                            messages.success(request, f"Продажи: {line}")
            except Exception as e:
                has_error = True
                messages.error(request, f"Ошибка загрузки продаж: {e}")

            if not has_error:
                messages.success(request, "Все файлы успешно обработаны.")

            return redirect(request.path)
    else:
        form = UploadAllOrdersForm()

    return render(request, "upload_all_orders.html", {"form": form})


def upload_stocks_view(request):
    """
    Отдельная загрузка остатков товаров.

    Загруженный Excel временно сохраняется на сервере,
    после чего запускается команда import_stocks.
    """

    if request.method == "POST":
        form = UploadStocksForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            stocks_file = form.cleaned_data[
                "stocks_file"
            ]

            temp_path = None
            command_output = StringIO()

            try:
                # =====================================================
                # СОХРАНЯЕМ EXCEL ВО ВРЕМЕННЫЙ ФАЙЛ
                # =====================================================

                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    suffix=".xlsx",
                    delete=False,
                ) as temp_file:

                    for chunk in stocks_file.chunks():
                        temp_file.write(chunk)

                    temp_path = temp_file.name

                # =====================================================
                # ПЕРВЫЙ ЗАПУСК IMPORT_STOCKS
                # =====================================================

                call_command(
                    "import_stocks",
                    temp_path,
                    stdout=command_output,
                )

                # =====================================================
                # ВТОРОЙ ЗАПУСК IMPORT_STOCKS
                # Оставляем вашу текущую последовательность импорта.
                # =====================================================

                call_command(
                    "import_stocks",
                    temp_path,
                    stdout=command_output,
                )

                # Получаем текст, который вывела команда.
                result = command_output.getvalue()

                # Выводим полезные строки отдельно.
                if result:
                    for line in result.splitlines():
                        line = line.strip()

                        if line:
                            messages.success(
                                request,
                                line,
                            )

                messages.success(
                    request,
                    (
                        f'Файл «{stocks_file.name}» '
                        "успешно обработан. Остатки загружены."
                    ),
                )

                return redirect(request.path)

            except Exception as exc:
                messages.error(
                    request,
                    (
                        "Ошибка загрузки остатков: "
                        f"{exc}"
                    ),
                )

            finally:
                # Временный Excel больше не нужен.
                if (
                    temp_path
                    and os.path.isfile(temp_path)
                ):
                    os.remove(temp_path)

    else:
        form = UploadStocksForm()

    return render(
        request,
        "upload_stocks.html",
        {
            "form": form,
        },
    )