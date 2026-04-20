from django import forms


class UploadForm(forms.Form):
    file = forms.FileField()


class UploadAllOrdersForm(forms.Form):
    orders_file = forms.FileField(label="Файл заказов", required=True)
    cf_file = forms.FileField(label="Файл оплат / CF", required=True)
    sales_file = forms.FileField(label="Файл продаж", required=True)