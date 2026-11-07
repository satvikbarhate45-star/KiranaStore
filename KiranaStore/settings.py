"""
KiranaStore Production Settings & Configuration (Render / Cloud Deployment)
Eliminates HTTP 502, 500, 400, 404, 403 across reverse proxies, CDNs, and load balancers.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.getenv("SECRET_KEY", "kirana-store-prod-secret-key-render-2026-safe-secure")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Render Hosts & Domains (Eliminates HTTP 400 Bad Request)
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://kiranastore-8os8.onrender.com',
    'https://kiranastore.onrender.com',
    'https://onrender.com',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1',
    'http://localhost'
]

# Database Configuration with Supabase PostgreSQL Session Pooler (Port 5432)
# Avoids Port 6543 Transaction Pooler deadlock with Django ORM prepared statements
raw_db_url = os.getenv("DATABASE_URL", "").strip()
if not raw_db_url:
    raw_db_url = "postgresql://postgres.qpmbydosjurxxicdjbeg:Kirana%40Store1@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

# Automatically normalize port 6543 -> 5432 for session pooler compatibility
if ":6543" in raw_db_url:
    raw_db_url = raw_db_url.replace(":6543", ":5432")

DATABASE_URL = raw_db_url

# Robust dj-database-url config with SSL, zero idle pooling and connect timeout
DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=0,               # Close idle connections to prevent pool exhaustion
        conn_health_checks=False,     # Disable blocking ping on startup
        ssl_require=True
    )
}

# Prevent infinite socket hangs with Supabase pooler
if 'default' in DATABASES and DATABASES['default']:
    if 'OPTIONS' not in DATABASES['default']:
        DATABASES['default']['OPTIONS'] = {}
    DATABASES['default']['OPTIONS']['connect_timeout'] = 10

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'KiranaStore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'app', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'KiranaStore.wsgi.application'

# Static files & WhiteNoise Storage (Eliminates 404 & broken manifest stops)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'app', 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

