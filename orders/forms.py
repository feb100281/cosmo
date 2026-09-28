# orders/forms.py
from django import forms


class UploadForm(forms.Form):
    file = forms.FileField()


class UploadAllOrdersForm(forms.Form):
    orders_file = forms.FileField(label="Файл заказов", required=False)
    cf_file = forms.FileField(label="Файл оплат / CF", required=False)
    sales_file = forms.FileField(label="Файл продаж", required=False)

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(f) for f in ("orders_file", "cf_file", "sales_file")):
            raise forms.ValidationError("Выберите хотя бы один файл.")
        return cleaned
    
    

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


class UploadReceiptsForm(forms.Form):
    receipts_file = forms.FileField(
        label="Файл приходов товаров",
        required=True,
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

    def clean_receipts_file(self):
        f = self.cleaned_data["receipts_file"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Выберите файл Excel в формате .xlsx.")
        return f
