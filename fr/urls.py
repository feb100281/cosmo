"""
URL configuration for fr project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, re_path, include
from dashboard.views import DashProxyView

from django.conf import settings
from django.conf.urls.static import static
from django.urls import  include
from . import views


urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('go-to-admin/', views.redirect_to_admin, name='go_to_admin'),
    path("admin/", admin.site.urls),
    path("apps/", include('django_plotly_dash.urls')), #ДЛЯ PLOTLY DASH
    
    path("dashboard/", include("dashboard.urls")),  # ваш прокси-роут для /dashboard/dash/
    # ---- проксируем корневые урлы, которые генерирует Dash (static + служебные) ----
    re_path(r"^_dash-(?P<path>.*)$", DashProxyView.as_view()),
    re_path(r"^_favicon\.ico$", DashProxyView.as_view()),
    re_path(r"^assets/(?P<path>.*)$", DashProxyView.as_view()),     # <- ВАЖНО: custom.js / custom.css / html2canvas и т.п.
    re_path(r"^_reload-hash$", DashProxyView.as_view()),
   
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)