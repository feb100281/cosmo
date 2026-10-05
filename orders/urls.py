# # orders/urls.py
# from django.urls import path
# from .views import upload_orders_view,upload_cf_view,upload_sales_view,  upload_all_orders_view


# urlpatterns = [
#     path("upload-orders/", upload_orders_view),
#     path("upload-cf/", upload_cf_view),
#     path("upload-sales/", upload_sales_view),
#     path("upload-all-orders/", upload_all_orders_view, name="upload_all_orders"),
# ]


# orders/urls.py

from django.urls import path

from .views import (
    upload_orders_view,
    upload_cf_view,
    upload_sales_view,
    upload_all_orders_view,
    upload_stocks_view,
    download_receipts_check_view,
    download_price_changes_view,
    download_receipts_view,
)


urlpatterns = [
    path(
        "upload-orders/",
        upload_orders_view,
    ),
    path(
        "upload-cf/",
        upload_cf_view,
    ),
    path(
        "upload-sales/",
        upload_sales_view,
    ),
    path(
        "upload-all-orders/",
        upload_all_orders_view,
        name="upload_all_orders",
    ),

    # Отдельный загрузчик остатков
    path(
        "upload-stocks/",
        upload_stocks_view,
        name="upload_stocks",
    ),
    path(
        "receipts-check/",
        download_receipts_check_view,
        name="receipts_check",
    ),
    path(
        "price-changes/",
        download_price_changes_view,
        name="price_changes",
    ),
    path(
        "receipts-export/",
        download_receipts_view,
        name="receipts_export",
    ),
]