from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# متغیرهای محیطی از فایل .env خوانده می‌شوند (در تولید لازم نیست؛ مستقیم export کنید).
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - در محیط تولید نصب نبودن آن مشکلی ایجاد نمی‌کند
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(BASE_DIR / '.env')


ENV_TRUE_VALUES = ('1', 'true', 'yes', 'on')


def env_bool(name, default=False):
    """خواندن یک متغیر محیطی بولی؛ مقدار خالی یا نامعتبر به default برمی‌گردد."""
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return value.strip().lower() in ENV_TRUE_VALUES


def env_int(name, default=0):
    value = os.environ.get(name, '').strip()
    try:
        return int(value)
    except ValueError:
        return default


def env_list(name, default=None):
    """خواندن لیست جداشده با کاما از متغیر محیطی."""
    items = [item.strip() for item in os.environ.get(name, '').split(',') if item.strip()]
    return items or list(default or [])


DEBUG = env_bool('DJANGO_DEBUG', True)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            'در حالت DEBUG=False متغیر محیطی DJANGO_SECRET_KEY الزامی است.'
        )
    # کلید ناامن فقط برای اجرای محلی؛ در تولید باید DJANGO_SECRET_KEY تنظیم شود.
    SECRET_KEY = 'django-insecure-zitro-shop-local-development-only'

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', ['*'] if DEBUG else [])

CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

# تنظیمات امنیتی پشت پرچم محیطی؛ پیش‌فرض در DEBUG=False روشن می‌شوند.
SECURE = env_bool('DJANGO_SECURE', not DEBUG)
SESSION_COOKIE_SECURE = SECURE
CSRF_COOKIE_SECURE = SECURE
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', SECURE)
SECURE_HSTS_SECONDS = env_int('DJANGO_SECURE_HSTS_SECONDS', 31536000 if SECURE else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE
SECURE_HSTS_PRELOAD = SECURE
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = env_bool('DJANGO_USE_X_FORWARDED_HOST', SECURE)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'django_htmx',

    # Local apps
    'accounts',
    'products',
    'cart',
    'orders',
    'blog',
    'home',
    'dashboard',
    'tickets',
    'sms',
]

AUTH_USER_MODEL = 'accounts.User'

# تنظیمات سامانه پیامک (SMS.ir v2)
SMS_IR_API_KEY = os.environ.get('SMS_IR_API_KEY', '').strip()
SMS_IR_LINE_NUMBER = os.environ.get('SMS_IR_LINE_NUMBER', '').strip()
SMS_IR_OTP_TEMPLATE_ID = os.environ.get('SMS_IR_OTP_TEMPLATE_ID', '').strip()

MIDDLEWARE = [
    'utils.middleware.PerformanceMonitorMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'utils.middleware.CacheHeaderMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'utils.middleware.HtmlMinifyMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart_processor',
                'home.context_processors.site_settings_processor',
                'tickets.context_processors.ticket_badge_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fa'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'digitell-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        },
    }
}

# ──────────────────────────────────────────────────────────────
# تنظیمات بهینه‌سازی سرعت دیجی‌تل
# ──────────────────────────────────────────────────────────────

# WhiteNoise: فشرده‌سازی و هش‌گذاری فایل‌های استاتیک
# در محیط تولید: CompressedManifest (نیاز به collectstatic)
# در محیط توسعه: CompressedStaticFiles (بدون نیاز به manifest)
if not DEBUG:
    STORAGES = {
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# نسخه کش (تغییر دهید تا کش بی‌اعتبار شود)
DIGITELL_CACHE_VERSION = 'v1'

# آستانه لاگ درخواست‌های کند (میلی‌ثانیه)
DIGITELL_SLOW_REQUEST_MS = 500

# فعال‌سازی minify در حالت debug
DIGITELL_MINIFY_DEBUG = False

# ──────────────────────────────────────────────────────────────
# لاگینگ
# ──────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'utils.cache': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'utils.middleware': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'home:index'
LOGOUT_REDIRECT_URL = 'home:index'
