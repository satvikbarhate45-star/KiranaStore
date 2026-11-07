"""
WSGI & ASGI application entrypoint for Gunicorn / Render production deployment.
Supports both standard WSGI workers (via a2wsgi) and UvicornWorker (ASGI).
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from app.main import app

# Expose ASGI application
asgi_application = app

# Expose WSGI application using a2wsgi
try:
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(app)
except Exception:
    application = app
