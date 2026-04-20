from django.contrib import admin
from django.urls import path, re_path, include
from dashboard.views import DashProxyView

from django.conf import settings
from django.conf.urls.static import static
from django.urls import  include
from . import views
from corporate.views_admin import admin_alert_counts


urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('go-to-admin/', views.redirect_to_admin, name='go_to_admin'),
    path("admin/alerts-counts/", admin.site.admin_view(admin_alert_counts), name="admin_alert_counts"),
    path("admin/", admin.site.urls),
    path("apps/", include('django_plotly_dash.urls')), #ДЛЯ PLOTLY DASH
    path("orders/", include("orders.urls")),
    
    path("dashboard/", include("dashboard.urls")),  # ваш прокси-роут для /dashboard/dash/
    # ---- проксируем корневые урлы, которые генерирует Dash (static + служебные) ----
    re_path(r"^_dash-(?P<path>.*)$", DashProxyView.as_view()),
    re_path(r"^_favicon\.ico$", DashProxyView.as_view()),
    re_path(r"^assets/(?P<path>.*)$", DashProxyView.as_view()),     # <- ВАЖНО: custom.js / custom.css / html2canvas и т.п.
    re_path(r"^_reload-hash$", DashProxyView.as_view()),
   
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)