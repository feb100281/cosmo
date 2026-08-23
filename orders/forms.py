# orders/forms.py
from django import forms


class UploadForm(forms.Form):
    file = forms.FileField()


class UploadAllOrdersForm(forms.Form):
    orders_file = forms.FileField(label="Файл заказов", required=True)
    cf_file = forms.FileField(label="Файл оплат / CF", required=True)
    sales_file = forms.FileField(label="Файл продаж", required=True)
    
    

class UploadStocksForm(forms.Form):
    stocks_file = forms.FileField(
        label="Файл остатков товаров",
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".xlsx",
            }
        ),
    )

    def clean_stocks_file(self):
        stocks_file = self.cleaned_data["stocks_file"]

        if not stocks_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError(
                "Выберите файл Excel в формате .xlsx."
            )

        return stocks_file