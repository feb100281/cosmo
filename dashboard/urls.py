from django.urls import path, re_path
from .views import DashProxyView

urlpatterns = [
    path("dash/<path:path>", DashProxyView.as_view(), name="dash_proxy"),
    path("dash/", DashProxyView.as_view(), {"path": ""}, name="dash_root"),
    # служебные пути Dash
    re_path(r"^_dash-(?P<path>.*)$", DashProxyView.as_view()),
    re_path(r"^assets/(?P<path>.*)$", DashProxyView.as_view()),
    re_path(r"^_favicon\.ico$", DashProxyView.as_view()),
    re_path(r"^_reload-hash$", DashProxyView.as_view()),
]