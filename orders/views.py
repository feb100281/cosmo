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
    UploadReceiptsForm,
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


def _push_log(request, prefix, log):
    for line in str(log or "").split(";"):
        line = line.strip()
        if line:
            messages.success(request, f"{prefix}: {line}")


def upload_all_orders_view(request):
    """Файлы необязательны. Порядок: CF, продажи, заказы; витрина заказов — один раз в конце."""
    if request.method == "POST":
        form = UploadAllOrdersForm(request.POST, request.FILES)

        if form.is_valid():
            orders_file = form.cleaned_data.get("orders_file")
            cf_file = form.cleaned_data.get("cf_file")
            sales_file = form.cleaned_data.get("sales_file")

            has_error = False
            loaded_any = False

            if cf_file:
                from utils.orders_cf import main as cf_main
                try:
                    _push_log(request, "CF", cf_main(cf_file))
                    loaded_any = True
                except Exception as e:
                    has_error = True
                    messages.error(request, f"Ошибка загрузки CF: {e}")

            if sales_file:
                from utils.new_updater import main as sales_main
                try:
                    _push_log(request, "Продажи", sales_main(sales_file))
                    loaded_any = True
                except Exception as e:
                    has_error = True
                    messages.error(request, f"Ошибка загрузки продаж: {e}")

            if orders_file:
                from utils.orders_updater import main as orders_main
                try:
                    _push_log(request, "Заказы", orders_main(orders_file, rebuild_mv=False))
                    loaded_any = True
                except Exception as e:
                    has_error = True
                    messages.error(request, f"Ошибка загрузки заказов: {e}")

            if loaded_any:
                from utils.orders_reporter import main as rebuild_orders_mv
                try:
                    _push_log(request, "Витрина заказов", rebuild_orders_mv())
                except Exception as e:
                    has_error = True
                    messages.error(request, f"Ошибка пересборки витрины заказов: {e}")

            if not has_error:
                messages.success(request, "Все выбранные файлы успешно обработаны.")

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

    receipts_form = UploadReceiptsForm()

    if request.method == "POST" and request.POST.get("upload_kind") == "receipts":
        receipts_form = UploadReceiptsForm(request.POST, request.FILES)
        if receipts_form.is_valid():
            from utils.import_receipts import import_receipts

            f = receipts_form.cleaned_data["receipts_file"]
            try:
                log = import_receipts(f)
                for line in str(log).split(";"):
                    line = line.strip()
                    if line:
                        messages.success(request, f"Приходы: {line}")
                messages.success(request, f"Файл «{f.name}» обработан. Приходы загружены.")
                return redirect(request.path)
            except Exception as exc:
                messages.error(request, f"Ошибка загрузки приходов: {exc}")

        return render(
            request,
            "upload_stocks.html",
            {"form": UploadStocksForm(), "receipts_form": receipts_form},
        )

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
            "receipts_form": receipts_form,
        },
    )