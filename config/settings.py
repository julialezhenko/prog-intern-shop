import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-commercelab-key")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "config.apps.CommerceLabAdminConfig",  # django.contrib.admin with a KPI dashboard on the index page
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "accounts",
    "catalog",
    "sales",
    "operations",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "catalog.context_processors.storefront",
    ]},
}]

WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("POSTGRES_DB"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "storefront"
LOGOUT_REDIRECT_URL = "storefront"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT.mkdir(exist_ok=True)  # whitenoise warns when the collectstatic target is missing in local dev
WHITENOISE_USE_FINDERS = DEBUG     # serve from static/ directly without collectstatic while developing
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))

SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "hello@sondermark.coffee")

# Payments: "simulated" ships with the project; real providers register themselves in sales/payments.py.
PAYMENT_GATEWAY = os.getenv("PAYMENT_GATEWAY", "simulated")
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
ORDER_PAYMENT_TIMEOUT_HOURS = int(os.getenv("ORDER_PAYMENT_TIMEOUT_HOURS", "24"))
CART_RETENTION_DAYS = int(os.getenv("CART_RETENTION_DAYS", "30"))

# Background jobs: without a broker Celery tasks run inline (eager), so local development needs no Redis.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "")
CELERY_TASK_ALWAYS_EAGER = not CELERY_BROKER_URL
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = "Europe/Madrid"
CELERY_BEAT_SCHEDULE = {
    "expire-unpaid-orders": {"task": "sales.expire_unpaid_orders", "schedule": 15 * 60},
    "cleanup-abandoned-carts": {"task": "sales.cleanup_abandoned_carts", "schedule": 24 * 60 * 60},
}

STOREFRONT_PAGE_SIZE = int(os.getenv("STOREFRONT_PAGE_SIZE", "12"))
STORE_NAME = os.getenv("STORE_NAME", "Sondermark Coffee Roasters")
STORE_SHORT_NAME = os.getenv("STORE_SHORT_NAME", "Sondermark")
STORE_TAGLINE = "Small-batch specialty coffee, roasted to order in Valencia"
STORE_CURRENCY = os.getenv("STORE_CURRENCY", "€")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sondermark Coffee API",
    "DESCRIPTION": (
        "Commerce, inventory and analytics API behind the Sondermark Coffee Roasters store "
        "(CommerceLab platform).\n\n"
        "**Transactional endpoints** (`/api/sales/carts/`, `/api/sales/orders/`, `/api/catalog/`) drive the shop.\n\n"
        "**Reporting datasets** are read-only and need the `Analyst`, `Store Manager`, `Marketing Manager` or "
        "`Admin` role: order lines, order status history, payments, refunds, shipments, subscriptions, coupon "
        "redemptions, customer profiles, behavioural events, campaign day metrics and stock snapshots. They all "
        "support multi-value filters (`?status=PAID,SHIPPED`), date-range bounds (`?created_at_after=`, "
        "`?created_at_before=`), `?ordering=`, `?search=` and `?page_size=` up to 2000.\n\n"
        "**Grouping endpoints** under `/api/analytics/` return raw sums and counts by day, week or month and by "
        "one or two dimensions. They deliberately do **not** serve conversion rates, average order value, "
        "lifetime value, retention or cohort matrices, ROAS/CPC/CAC, churn or period-over-period deltas — those "
        "are meant to be derived by whoever consumes the data. `GET /api/analytics/dimensions/` lists what is "
        "available and what is intentionally withheld.\n\n"
        "Money is stored in the currency the customer was charged in; multiply by `fx_rate` for euros."
    ),
    "VERSION": "2.0.0",
    "TAGS": [
        {"name": "catalog", "description": "Products, variants, categories, tags, reviews and their history."},
        {"name": "sales", "description": "Carts, orders and the transactional and reporting datasets around them."},
        {"name": "operations", "description": "Warehouses, stock, suppliers, campaigns and behavioural events."},
        {"name": "customers", "description": "Customer dimension: geography, acquisition and segmentation."},
        {"name": "analytics", "description": "Grouped sums and counts. No derived rates or ratios."},
    ],
}
