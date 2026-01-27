"""
WSGI config for fr project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

# import os

# from django.core.wsgi import get_wsgi_application



# application = get_wsgi_application()

import os
from django.core.wsgi import get_wsgi_application
from werkzeug.middleware.dispatcher import DispatcherMiddleware # type: ignore
# from dashboard.sales_dash import create_dash_app, create_dash_app_test
from dashboard.salespanel.app import salespanel
from utils.upload_form import upload_form
from utils.redis_form import redis_form_uplaoder

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fr.settings")

django_app = get_wsgi_application()
# dash_app = create_dash_app()
# dash_app_test = create_dash_app_test()
upload_frm = upload_form()
redis_uploader = redis_form_uplaoder()
sales_panel = salespanel()



application = DispatcherMiddleware(django_app, {
    # '/my-dash-app': dash_app,
    # '/my-dash-app-test': dash_app_test,
    '/upload-form': upload_frm,
    '/redis-form': redis_uploader,
    '/salespanel':sales_panel
})