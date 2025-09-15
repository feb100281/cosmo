import mimetypes
import requests
from django.http import HttpResponse
from django.views import View

class DashProxyView(View):
    DASH_URL = "http://127.0.0.1:8050"

    def dispatch(self, request, path="", *args, **kwargs):
        url = f"{self.DASH_URL}/{path}".rstrip("/")
        if request.META.get("QUERY_STRING"):
            url += "?" + request.META["QUERY_STRING"]

        resp = requests.request(method=request.method, url=url, data=request.body)

        # определяем Content-Type по расширению файла
        content_type = resp.headers.get("Content-Type")
        if not content_type:
            guess, _ = mimetypes.guess_type(path)
            content_type = guess or "application/octet-stream"

        django_resp = HttpResponse(resp.content, status=resp.status_code, content_type=content_type)

        # копируем некоторые полезные заголовки
        for h, v in resp.headers.items():
            if h.lower() in ("cache-control", "last-modified", "etag"):
                django_resp[h] = v

        return django_resp