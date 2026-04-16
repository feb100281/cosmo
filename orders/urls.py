# orders/urls.py
from django.urls import path
from .views import upload_orders_view,upload_cf_view,upload_sales_view


urlpatterns = [
    path("upload-orders/", upload_orders_view),
    path("upload-cf/", upload_cf_view),
    path("upload-sales/", upload_sales_view),
]