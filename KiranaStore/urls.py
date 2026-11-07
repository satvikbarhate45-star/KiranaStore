"""
KiranaStore URL Configuration & Lightweight Zero-DB Healthcheck
"""
from django.urls import path
from django.http import HttpResponse

def safe_healthcheck(request):
    """
    Safe healthcheck handler that immediately returns 200 OK for Render probes (HEAD / GET).
    Guarantees zero database lookups and zero memory consumption.
    """
    try:
        return HttpResponse("KiranaStore Production OK", content_type="text/plain; charset=utf-8", status=200)
    except Exception:
        return HttpResponse("KiranaStore Production OK", status=200)

urlpatterns = [
    path("", safe_healthcheck, name="root_healthcheck"),
    path("healthz", safe_healthcheck, name="healthz"),
    path("healthz/", safe_healthcheck, name="healthz_slash"),
    path("health", safe_healthcheck, name="health"),
    path("health/", safe_healthcheck, name="health_slash"),
    path("ping", safe_healthcheck, name="ping"),
    path("ping/", safe_healthcheck, name="ping_slash"),
]
