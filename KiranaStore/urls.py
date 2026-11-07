"""
KiranaStore URL Configuration & Lightweight Zero-DB Healthcheck
"""
from django.urls import path
from django.http import HttpResponse

def ping_view(request):
    return HttpResponse("KiranaStore Live", content_type="text/plain", status=200)

urlpatterns = [
    path("healthz", ping_view, name="healthz"),
    path("healthz/", ping_view, name="healthz_slash"),
    path("health", ping_view, name="health"),
    path("health/", ping_view, name="health_slash"),
    path("ping", ping_view, name="ping"),
    path("ping/", ping_view, name="ping_slash"),
]
