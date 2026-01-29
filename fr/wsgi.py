"""
WSGI config for fr project.
"""

import os
from django.core.wsgi import get_wsgi_application
from werkzeug.middleware.dispatcher import DispatcherMiddleware  # type: ignore

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fr.settings")


def get_application():
    django_app = get_wsgi_application()

    # ленивые импорты/создания — НЕ на уровне модуля
    from utils.upload_form import upload_form
    from utils.redis_form import redis_form_uplaoder
    # from dashboard.salespanel.app import salespanel

    upload_frm = upload_form()
    redis_uploader = redis_form_uplaoder()
    # sales_panel = salespanel()

    return DispatcherMiddleware(django_app, {
        "/upload-form": upload_frm,
        "/redis-form": redis_uploader,
        # "/salespanel": sales_panel,
    })


application = get_application()