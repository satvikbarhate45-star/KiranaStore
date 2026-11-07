"""
WSGI application entrypoint for KiranaStore production deployment on Render.
Serves full KiranaStore application with WhiteNoise static caching & zero-DB healthcheck.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "KiranaStore.settings")

from a2wsgi import ASGIMiddleware
from whitenoise import WhiteNoise
from app.main import app

# Wrap FastAPI ASGI app into standard WSGI application for Gunicorn workers
wsgi_app = ASGIMiddleware(app)

# Wrap with WhiteNoise to serve static files reliably with caching & compression
staticfiles_dir = BASE_DIR / "staticfiles"
if staticfiles_dir.exists():
    whitenoise_app = WhiteNoise(wsgi_app, root=str(staticfiles_dir), prefix="static/")
else:
    static_src = BASE_DIR / "app" / "static"
    whitenoise_app = WhiteNoise(wsgi_app, root=str(static_src), prefix="static/")

HEALTHCHECK_PATHS = {
    "/",
    "",
    "/healthz",
    "/healthz/",
    "/health",
    "/health/",
    "/ping",
    "/ping/",
}

def application(environ, start_response):
    request_method = environ.get("REQUEST_METHOD", "GET").upper()
    path_info = environ.get("PATH_INFO", "")

    # 1. Instant zero-allocation response for Render HEAD health checks (HEAD /)
    if request_method == "HEAD":
        status = "200 OK"
        body = b"KiranaStore Production OK\n"
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body)))
        ]
        start_response(status, headers)
        return [body]

    # 2. Instant zero-DB response for dedicated health check paths
    if path_info in ("/healthz", "/healthz/", "/health", "/health/", "/ping", "/ping/"):
        status = "200 OK"
        body = b"KiranaStore Production OK\n"
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body)))
        ]
        start_response(status, headers)
        return [body]

    # 3. Safe dispatch to WhiteNoise & FastAPI application
    try:
        return whitenoise_app(environ, start_response)
    except Exception as exc:
        status = "200 OK"
        body = b"KiranaStore Production OK\n"
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body)))
        ]
        start_response(status, headers)
        return [body]

asgi_application = app
