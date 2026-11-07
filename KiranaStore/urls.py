"""
KiranaStore Production Django URL Configuration
"""
from django.urls import path, re_path
from KiranaStore.views import (
    safe_healthcheck,
    home_view,
    catalog_view,
    history_view,
    analyzer_view,
    about_view,
    contact_view,
    api_dispatcher,
)

urlpatterns = [
    # Render & Load Balancer Healthchecks
    path("healthz", safe_healthcheck, name="healthz"),
    path("healthz/", safe_healthcheck, name="healthz_slash"),
    path("health", safe_healthcheck, name="health"),
    path("health/", safe_healthcheck, name="health_slash"),
    path("ping", safe_healthcheck, name="ping"),
    path("ping/", safe_healthcheck, name="ping_slash"),

    # Main UI Routes
    path("", home_view, name="home"),
    path("catalog", catalog_view, name="catalog"),
    path("catalog/", catalog_view, name="catalog_slash"),
    path("history", history_view, name="history"),
    path("history/", history_view, name="history_slash"),
    path("analyzer", analyzer_view, name="analyzer"),
    path("analyzer/", analyzer_view, name="analyzer_slash"),
    path("about", about_view, name="about"),
    path("about/", about_view, name="about_slash"),
    path("contact", contact_view, name="contact"),
    path("contact/", contact_view, name="contact_slash"),

    # Synchronous API Routing
    re_path(r"^api/(?P<path>.*)$", api_dispatcher, name="api_dispatcher"),
]
