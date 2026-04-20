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
from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import UploadForm, UploadAllOrdersForm


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