# orders/views.py

from django.shortcuts import render
from django.contrib import messages
from django import forms


class UploadForm(forms.Form):
    file = forms.FileField()


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

                for line in log.split(";"):
                    messages.success(request, line.strip())

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = UploadForm()

    return render(request, "upload_orders.html", {"form": form})