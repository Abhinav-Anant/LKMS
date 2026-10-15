"""
Django settings for LKMS.

Every secret and deployment-specific value comes from the environment
(or a local `.env` file in development). See `.env.example`.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    # LKMS apps
    "core",
    "users",
    "academics",
    "students",
    "admissions",
    "fees",
    "attendance",
    "assessments",
    "notices",
    "portal",
    "messaging",
    "exams",
    "certificates",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: PostgreSQL via DATABASE_URL. SQLite is allowed only for local development.
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=60)}
elif DEBUG:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    raise ImproperlyConfigured("DATABASE_URL must be set when DJANGO_DEBUG is off")

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = Path(os.getenv("STATIC_ROOT", BASE_DIR / "staticfiles"))

# Student documents and photos. Never served directly by the web server:
# they are streamed through authenticated views (see core.storage).
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
DATA_UPLOAD_MAX_MEMORY_SIZE = (MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440

# Backups (python manage.py backup / restore_backup). See docs/BACKUPS.md.
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", BASE_DIR / "backups"))
BACKUP_KEEP_DAILY = int(os.getenv("BACKUP_KEEP_DAILY", "14"))
BACKUP_KEEP_WEEKLY = int(os.getenv("BACKUP_KEEP_WEEKLY", "8"))
BACKUP_KEEP_MONTHLY = int(os.getenv("BACKUP_KEEP_MONTHLY", "12"))
# Optional command to copy each new backup off the server, e.g. "rclone copy {file} offsite:lkms-backups"
BACKUP_COPY_COMMAND = os.getenv("BACKUP_COPY_COMMAND", "")
BACKUP_MAX_AGE_HOURS = int(os.getenv("BACKUP_MAX_AGE_HOURS", "36"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_RATES": {
        "public_application": os.getenv("THROTTLE_PUBLIC_APPLICATION", "10/hour"),
        "public_tracking": os.getenv("THROTTLE_PUBLIC_TRACKING", "30/hour"),
        "login": os.getenv("THROTTLE_LOGIN", "10/minute"),
        "public_payment": os.getenv("THROTTLE_PUBLIC_PAYMENT", "60/hour"),
        "parent_code": os.getenv("THROTTLE_PARENT_CODE", "20/hour"),
        "captcha": os.getenv("THROTTLE_CAPTCHA", "120/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080")

# Where parents open the React app; used in fee payment links.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:8080").rstrip("/")

# The school's UPI account shown on the parent pay page (QR image: frontend/public/school-upi-qr.jpeg).
# Older installs set the UPI account here; it now lives in the school profile (School settings).
SCHOOL_UPI_ID = os.getenv("SCHOOL_UPI_ID", "")
SCHOOL_UPI_NAME = os.getenv("SCHOOL_UPI_NAME", "")
PAY_LINK_MAX_AGE_DAYS = int(os.getenv("PAY_LINK_MAX_AGE_DAYS", "45"))

SPECTACULAR_SETTINGS = {
    "TITLE": "LKMS API",
    "DESCRIPTION": "LKMS school management system",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": "admissions.models.AdmissionApplication.Status",
        "StudentStatusEnum": "students.models.Student.Status",
        "EnrollmentStatusEnum": "academics.models.Enrollment.Status",
        "RelationshipEnum": "students.choices.Relationship",
        "InvoiceStatusEnum": "fees.models.Invoice.Status",
        "PaymentStatusEnum": "fees.models.Payment.Status",
        "ConcessionStatusEnum": "fees.models.Concession.Status",
        "UpiSubmissionStatusEnum": "fees.models.UpiSubmission.Status",
        "AttendanceStatusEnum": "attendance.models.AttendanceRecord.Status",
    },
}

# WhatsApp (Phase 4): messages go through the Blastup server in whatsapp-server/, on this machine only.
WHATSAPP_ENABLED = env_bool("WHATSAPP_ENABLED", False)
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "http://127.0.0.1:3001")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
WHATSAPP_TIMEOUT_SECONDS = int(os.getenv("WHATSAPP_TIMEOUT_SECONDS", "15"))
# Unofficial WhatsApp Web: send slowly so the school's number is not blocked.
WHATSAPP_RATE_PER_MINUTE = int(os.getenv("WHATSAPP_RATE_PER_MINUTE", "8"))
WHATSAPP_SEND_GAP_SECONDS = float(os.getenv("WHATSAPP_SEND_GAP_SECONDS", "4"))
WHATSAPP_DAILY_LIMIT_PER_NUMBER = int(os.getenv("WHATSAPP_DAILY_LIMIT_PER_NUMBER", "6"))
WHATSAPP_MAX_ATTEMPTS = int(os.getenv("WHATSAPP_MAX_ATTEMPTS", "5"))
# No alerts from 21:00 to 07:00 (sign-in codes still go).
WHATSAPP_QUIET_HOURS = tuple(int(h) for h in os.getenv("WHATSAPP_QUIET_HOURS", "21,7").split(","))

# Production hardening (only applies when DEBUG is off)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
