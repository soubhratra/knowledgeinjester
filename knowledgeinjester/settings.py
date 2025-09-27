from pathlib import Path
import os
from dotenv import load_dotenv
from django.urls import reverse_lazy
from django.templatetags.static import static
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
# The load_dotenv() function will automatically look for a .env file
# in the current directory or parent directories.
load_dotenv(os.path.join(BASE_DIR, '.env'))

def _split_env(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

# ---- Static files (important for Unfold styling) ----
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')            # collectstatic output
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'),]          # your project-level static folder

ENV = os.getenv("ENV", "dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Structured JSON Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d %(funcName)s %(process)d %(thread)d'
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if ENV == 'production' else 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'api.log'),
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'apps.api': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-not-for-prod")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = _split_env("DJANGO_ALLOWED_HOSTS", ".spectrumsense.co")
CSRF_TRUSTED_ORIGINS = _split_env("DJANGO_CSRF_TRUSTED_ORIGINS", "https://*.spectrumsense.co")

# ---- Proxy/HTTPS (recommended behind Northflank) ----
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "unfold",  # Must be before django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",  # CORS support
    "ninja_extra",
    # Core apps
    "apps.core",
    "apps.crawler",
    "apps.extractor", 
    "apps.vectorizer",
    "apps.pipelines",
    "apps.tenants",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS middleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = "knowledgeinjester.urls"
WSGI_APPLICATION = "knowledgeinjester.wsgi.application"
ASGI_APPLICATION = "knowledgeinjester.asgi.application"

DATABASES = {
    # "default": {
    #     "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
    #     "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
    #     "USER": os.getenv("DB_USER", ""),
    #     "PASSWORD": os.getenv("DB_PASSWORD", ""),
    #     "HOST": os.getenv("DB_HOST", ""),
    #     "PORT": os.getenv("DB_PORT", ""),
    # }
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {"sslmode": "require"},
    }
}

# Celery (optional)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

LANGCHAIN_TRACING_V2 = True
LANGCHAIN_ENDPOINT = "https://api.smith.langchain.com"
LANGSMITH_API_KEY = os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT = "spectrum-chat"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "6"))
MIN_SIM_SCORE = float(os.getenv("MIN_SIM_SCORE", "0.35"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# Django Unfold Configuration
UNFOLD = {
    "SITE_TITLE": "Knowledge Injester Admin",
    "SITE_HEADER": "Knowledge Injester",
    "SITE_URL": "/",
    "SITE_SYMBOL": "speed",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "Knowledge Injester",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

# CORS Configuration
# Allow all origins for testing and initial deployment
CORS_ALLOW_ALL_ORIGINS = True

# IMPORTANT: When CORS_ALLOW_ALL_ORIGINS = True, CORS_ALLOW_CREDENTIALS must be False
# for security reasons. If you need credentials, specify exact origins instead.
CORS_ALLOW_CREDENTIALS = False

# Allow common headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
