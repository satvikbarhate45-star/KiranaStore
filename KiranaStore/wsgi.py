"""
WSGI application entrypoint for KiranaStore production deployment on Render.
Serves full KiranaStore application with WhiteNoise static caching.
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

# Wrap FastAPI ASGI app into standard WSGI application for Gunicorn sync workers
wsgi_app = ASGIMiddleware(app)

# Wrap with WhiteNoise to serve static files reliably with caching & compression
staticfiles_dir = BASE_DIR / "staticfiles"
if staticfiles_dir.exists():
    application = WhiteNoise(wsgi_app, root=str(staticfiles_dir), prefix="static/")
else:
    static_src = BASE_DIR / "app" / "static"
    application = WhiteNoise(wsgi_app, root=str(static_src), prefix="static/")

asgi_application = app
