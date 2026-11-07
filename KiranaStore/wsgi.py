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

def application(environ, start_response):
    path_info = environ.get("PATH_INFO", "")
    # Instant Zero-DB Healthcheck for Render Port Detection & Health Monitoring
    if path_info in ("/healthz", "/healthz/", "/ping", "/ping/"):
        status = "200 OK"
        headers = [("Content-Type", "text/plain"), ("Content-Length", "15")]
        start_response(status, headers)
        return [b"KiranaStore Live"]
    return whitenoise_app(environ, start_response)

asgi_application = app
