

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env file automatically if present (root .env takes precedence)
def _load_env():
    for env_path in [BASE_DIR / '.env', BASE_DIR.parent / '.env']:
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip("'\"")

_load_env()


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-equb-ethiopia-platform-dev-key-2026-secure-mvp')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,testserver').split(',')

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Strong password hashing: Argon2id prioritized
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'corsheaders',
    'rest_framework',
    
    # Digital Equb Domain Apps
    'apps.accounts',
    'apps.authorization',
    'apps.groups',
    'apps.rules',
    'apps.contributions',
    'apps.payments',
    'apps.ledger',
    'apps.payouts',
    'apps.disputes',
    'apps.subscriptions',
    'apps.audit_app',
    'apps.common',
    'apps.notifications',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'equb_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'equb_core.wsgi.application'

# PostgreSQL Database Configuration (Local cluster or Neon / Cloud PostgreSQL via DATABASE_URL)
USE_LOCAL_DB = os.environ.get('USE_LOCAL_DB', 'False').lower() in ('true', '1', 't')
DATABASE_URL = os.environ.get('DATABASE_URL') if not USE_LOCAL_DB else None

if DATABASE_URL:
    import urllib.parse
    _parsed = urllib.parse.urlparse(DATABASE_URL)
    _db_name = _parsed.path.lstrip('/')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db_name,
            'USER': _parsed.username or '',
            'PASSWORD': _parsed.password or '',
            'HOST': _parsed.hostname or 'localhost',
            'PORT': str(_parsed.port or 5432),
            'OPTIONS': {
                'sslmode': 'require'
            } if ('sslmode=require' in DATABASE_URL or _parsed.hostname not in ('localhost', '127.0.0.1')) else {},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'digital_equb_db'),
            'USER': os.environ.get('DB_USER', 'equb_admin'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '/home/amanuel/Equb/.postgres_sockets'),
            'PORT': os.environ.get('DB_PORT', '5433'),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'private_media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
}

# CORS & CSRF Settings for React Frontend
CORS_ALLOW_CREDENTIALS = True

default_origins = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

cors_env = os.environ.get('CORS_ALLOWED_ORIGINS')
CORS_ALLOWED_ORIGINS = [orig.strip() for orig in cors_env.split(',') if orig.strip()] if cors_env else default_origins

csrf_env = os.environ.get('CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = [orig.strip() for orig in csrf_env.split(',') if orig.strip()] if csrf_env else default_origins

# Auto-include FRONTEND_BASE_URL if configured in environment
frontend_env_url = os.environ.get('FRONTEND_BASE_URL')
if frontend_env_url:
    clean_frontend_url = frontend_env_url.rstrip('/')
    if clean_frontend_url not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(clean_frontend_url)
    if clean_frontend_url not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(clean_frontend_url)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400 * 7 # 7 days
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

# Chapa Payment Gateway Configuration
CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY', 'CHASECK_TEST-mock-test-key-for-development')
CHAPA_PUBLIC_KEY = os.getenv('CHAPA_PUBLIC_KEY', 'CHAPUBK_TEST-mock-public-key-for-development')
CHAPA_WEBHOOK_SECRET = os.getenv('CHAPA_WEBHOOK_SECRET', 'test-chapa-webhook-secret')
CHAPA_API_URL = os.getenv('CHAPA_API_URL', 'https://api.chapa.co/v1')
CHAPA_SANDBOX_MODE = os.getenv('CHAPA_SANDBOX_MODE', 'True').lower() in ('true', '1', 'yes')
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')
BACKEND_BASE_URL = os.getenv('BACKEND_BASE_URL', 'http://localhost:8000')

# Upload Limits (allow profile photos and receipt uploads up to 10MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
