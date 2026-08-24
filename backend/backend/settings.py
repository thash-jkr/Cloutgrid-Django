from pathlib import Path
from datetime import timedelta
import os
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


# Zepto Mail
SECRET_KEY = env("DJANGO_SECRET_KEY")
ZEPTO_API_KEY = env("ZEPTO_API_KEY")
OTP_TEMPLATE_KEY = env("OTP_TEMPLATE_KEY")
RESET_TEMPLATE_KEY = env("RESET_TEMPLATE_KEY")


# Stream chat
STREAM_API_KEY = env("STREAM_API_KEY")
STREAM_API_SECRET = env("STREAM_API_SECRET")


# Facebook login and Instagram integration
FB_APP_ID = env("FB_APP_ID")
FB_APP_SECRET = env("FB_APP_SECRET")
FB_API_VERSION = env("FB_API_VERSION")
FB_REDIRECT_URI = env("FB_REDIRECT_URI")
FB_FRONTEND_REDIRECT_URI = env("FB_FRONTEND_REDIRECT_URI")
FB_SCOPES = env.list("FB_SCOPES", default=[])

# Instagram Auth
IG_APP_ID = env("IG_APP_ID")
IG_APP_SECRET = env("IG_APP_SECRET")
IG_REDIRECT_URI = env("IG_REDIRECT_URI")
IG_FRONTEND_REDIRECT_URI = env("IG_FRONTEND_REDIRECT_URI")
IG_APP_REDIRECT_URI = env("IG_APP_REDIRECT_URI")
IG_SCOPES = env("IG_SCOPES")


# Google login and YouTube integration
G_CLIENT_ID = env("G_CLIENT_ID")
G_CLIENT_SECRET = env("G_CLIENT_SECRET")
G_REDIRECT_URI = env("G_REDIRECT_URI")
G_FRONTEND_REDIRECT_URI = env("G_FRONTEND_REDIRECT_URI")
G_APP_REDIRECT_URI = env("G_APP_REDIRECT_URI")
G_SCOPES = env("G_SCOPES", default="")


# Cron Jobs
CRONJOBS = [
    (
        "0 */6 * * *",
        "users.jobs.refresh_all_social_integrations",
        ">> /app/logs/cron.log 2>&1",
    ),
]


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "/app/logs/django.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])


# Application definition
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "users",
    "jobs",
    "feed",
    "rest_framework_simplejwt.token_blacklist",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "messaging",
    "channels",
    "django_crontab",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = env.bool("CORS_ORIGIN_ALLOW_ALL", default=False)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_HTTPONLY = env.bool("CSRF_COOKIE_HTTPONLY", default=True)
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://192.168.0.232:3000",
    "http://192.168.0.232:8000",
    "exp://192.168.0.232:8081",
    "https://cloutgrid.com",
    "https://api.cloutgrid.com",
    "https://www.cloutgrid.com",
]


secure_proxy_value = env("SECURE_PROXY_SSL_HEADER", default=False)

if secure_proxy_value and secure_proxy_value.lower() != "false":
    SECURE_PROXY_SSL_HEADER = tuple(secure_proxy_value.split(","))
else:
    SECURE_PROXY_SSL_HEADER = False


ROOT_URLCONF = "backend.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


ASGI_APPLICATION = "backend.asgi.application"
WSGI_APPLICATION = "backend.wsgi.application"


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
            "symmetric_encryption_keys": [],
        },
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 10,
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_ACCESS_TOKEN_LIFETIME_DAYS", default=1)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        weeks=env.int("JWT_REFRESH_TOKEN_LIFETIME_WEEKS", default=1)
    ),
    "ROTATE_REFRESH_TOKENS": env.bool("JWT_ROTATE_REFRESH_TOKENS", default=True),
    "BLACKLIST_AFTER_ROTATION": env.bool("JWT_BLACKLIST_AFTER_ROTATION", default=True),
}


DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env("DB_NAME", default="cloutgrid"),
        "USER": env("DB_USER", default=""),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "Australia/Adelaide"
USE_I18N = True
USE_TZ = True


STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"


# Django Allauth settings
SITE_ID = 1


AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)


ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"


# Email backend for testing (console)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)


# Max upload size (in bytes)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
