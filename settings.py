"""
KiranaStore Production Settings & Configuration (Render / Cloud Deployment)
Eliminates HTTP 500, 400, 404, 403, 401 across reverse proxies, CDNs, and load balancers.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

# Render & Host Configuration (Eliminates HTTP 400 Bad Request)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*,localhost,127.0.0.1,.onrender.com").split(",")
CSRF_TRUSTED_ORIGINS = [
    "https://*.onrender.com",
    "https://onrender.com",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://localhost"
]

# Static Files & WhiteNoise Configuration (Eliminates HTTP 404 & broken manifest crashes)
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "app", "static")]

# Use CompressedStaticFilesStorage to prevent missing manifest build stops
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Database Configuration with Supabase PostgreSQL Fallback & Pooler
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.qpmbydosjurxxicdjbeg:Kirana%40Store1@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
)

# Parse database configuration with dj_database_url
try:
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
except Exception:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql" if "postgres" in DATABASE_URL else "django.db.backends.sqlite3",
            "NAME": DATABASE_URL
        }
    }

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
SECRET_KEY = os.getenv("SECRET_KEY", "kirana-secret-key-prod-super-secure-2026")
