"""
سیستم کش مرکزی دیجی‌تل (Digitell Cache System)
=================================================
ابزارهای کش و بهینه‌سازی سرعت سایت شامل:
- دکوراتور view_cache: کش خودکار ویوها با پشتیبانی از ETag و نشانگر کش
- تولیدکننده کلید کش هوشمند: بر اساس path + query params + وضعیت کاربر
- توابع invalidation: بی‌اعتبارسازی هوشمند کش بعد از تغییرات مدل
- context_cache: کش داده‌های context processor
"""

import functools
import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.cache import patch_response_headers

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# ثابت‌ها و نسخه‌بندی کش
# ──────────────────────────────────────────────────────────────────────
CACHE_VERSION = getattr(settings, 'DIGITELL_CACHE_VERSION', 'v1')

# زمان‌های کش پیش‌فرض (ثانیه)
CACHE_TTL_SHORT = 60           # ۱ دقیقه — داده‌های پرتغییر (سبد خرید)
CACHE_TTL_MEDIUM = 300         # ۵ دقیقه — صفحات لیستی (فروشگاه، بلاگ)
CACHE_TTL_LONG = 900           # ۱۵ دقیقه — صفحه اصلی
CACHE_TTL_STATIC = 3600        # ۱ ساعت — داده‌های کم‌تغییر (تنظیمات سایت)
CACHE_TTL_FOREVER = 86400 * 7  # ۱ هفته — فرگمنت‌های کاملاً ثابت

# پیشوند کلید کش
CACHE_PREFIX = f'digitell:{CACHE_VERSION}'


# ──────────────────────────────────────────────────────────────────────
# تولید کلید کش
# ──────────────────────────────────────────────────────────────────────
def make_cache_key(prefix, request=None, extra=''):
    """
    ساخت کلید یکتای کش بر اساس درخواست (path + query + auth).

    نمونه خروجی:
        digitell:v1:home:index:/|sort=newest&page=2|anon
    """
    parts = [CACHE_PREFIX, prefix]

    if request is not None:
        parts.append(request.path)
        # ترتیب پارامترها مهم است — مرتب‌سازی الفبایی
        qs_items = sorted(request.GET.items())
        qs_str = '&'.join(f'{k}={v}' for k, v in qs_items)
        parts.append(qs_str)
        # کاربر وارد شده / ناشناس
        parts.append('auth' if request.user.is_authenticated else 'anon')

    if extra:
        parts.append(str(extra))

    raw_key = '|'.join(parts)
    # کلید بلند؟ → MD5 به حداکثر ۲۵۰ کاراکتر
    if len(raw_key) > 200:
        hashed = hashlib.md5(raw_key.encode('utf-8')).hexdigest()
        return f'{CACHE_PREFIX}:{prefix}:{hashed}'
    return raw_key


def make_etag(content):
    """ساخت ETag از محتوای پاسخ."""
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.md5(content).hexdigest()


# ──────────────────────────────────────────────────────────────────────
# دکوراتور کش ویو
# ──────────────────────────────────────────────────────────────────────
def view_cache(timeout=CACHE_TTL_MEDIUM, prefix='view', cache_anon_only=False):
    """
    دکوراتور کش برای ویوهای Django.

    ویژگی‌ها:
    - کش خودکار پاسخ HTML بر اساس URL و پارامترها
    - پشتیبانی از ETag و هدر Cache-Control
    - امکان محدودسازی فقط به کاربران ناشناس
    - نادیده‌گرفتن متدهای غیر-GET و درخواست‌های HTMX
    - لاگ هیت/میس کش

    استفاده:
        @view_cache(timeout=300, prefix='shop')
        def shop_view(request, slug=None):
            ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # فقط GET را کش کن
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)

            # درخواست‌های HTMX معمولاً partial هستند — کش نکن
            if getattr(request, 'htmx', False):
                return view_func(request, *args, **kwargs)

            # فقط کاربران ناشناس؟
            if cache_anon_only and request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            # ساخت کلید
            extra = ':'.join(str(a) for a in args) if args else ''
            if kwargs:
                extra += ':' + ':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))
            cache_key = make_cache_key(prefix, request, extra)

            # جستجو در کش
            cached = cache.get(cache_key)
            if cached is not None:
                response, etag = cached
                logger.debug("کش هیت: %s", cache_key)

                # بررسی ETag — اگر مرورگر نسخه‌ای یکسان دارد 304 برگردان
                if_none_match = request.META.get('HTTP_IF_NONE_MATCH', '')
                if etag and if_none_match == f'"{etag}"':
                    return HttpResponse(status=304)

                resp = HttpResponse(
                    content=response,
                    content_type='text/html; charset=utf-8',
                )
                resp['ETag'] = f'"{etag}"'
                patch_response_headers(resp, cache_timeout=timeout)
                return resp

            # کش میس — اجرای ویو
            logger.debug("کش میس: %s", cache_key)
            response = view_func(request, *args, **kwargs)

            # فقط پاسخ‌های ۲۰۰ را کش کن
            if response.status_code == 200 and hasattr(response, 'content'):
                etag = make_etag(response.content)
                cache.set(cache_key, (response.content, etag), timeout)
                response['ETag'] = f'"{etag}"'
                patch_response_headers(response, cache_timeout=timeout)

            return response
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────────────
# کش context processor
# ──────────────────────────────────────────────────────────────────────
def cached_context(key, timeout=CACHE_TTL_STATIC):
    """
    دکوراتور برای کش‌کردن خروجی context processor.

    استفاده:
        @cached_context('site_settings', timeout=3600)
        def site_settings_processor(request):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            cache_key = f'{CACHE_PREFIX}:ctx:{key}'
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = func(request, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────────────
# Invalidation (بی‌اعتبارسازی کش)
# ──────────────────────────────────────────────────────────────────────
# نقشه مدل → کلیدهای کشی که باید پاک شوند
_MODEL_CACHE_MAP = {
    'products.Product': ['view:shop', 'view:home', 'ctx:nav_categories'],
    'products.Category': ['view:shop', 'view:home', 'ctx:nav_categories', 'ctx:site_settings'],
    'products.Brand': ['view:shop', 'view:home'],
    'blog.Post': ['view:blog', 'view:home'],
    'home.Banner': ['view:home'],
    'home.SiteSetting': ['ctx:site_settings'],
}


def invalidate_model_cache(model_label):
    """
    پاک‌کردن کش مرتبط با یک مدل بعد از ذخیره/حذف.

    استفاده:
        invalidate_model_cache('products.Product')
    """
    keys_to_clear = _MODEL_CACHE_MAP.get(model_label, [])
    if not keys_to_clear:
        return

    # پاک‌کردن تمام کلیدهای مرتبط
    for key_pattern in keys_to_clear:
        full_pattern = f'{CACHE_PREFIX}:{key_pattern}'
        # LocMemCache از delete_pattern پشتیبانی نمی‌کند — کلید دقیق حذف
        cache.delete(full_pattern)

    logger.info("کش بی‌اعتبار شد برای مدل %s: %s", model_label, keys_to_clear)


def invalidate_all():
    """پاک‌کردن تمام کش‌های دیجی‌تل."""
    cache.clear()
    logger.info("تمام کش‌های دیجی‌تل پاک شد.")


def invalidate_view_cache(prefix):
    """پاک‌کردن کش یک ویوی خاص."""
    pattern = f'{CACHE_PREFIX}:{prefix}'
    cache.delete(pattern)
    logger.info("کش ویو پاک شد: %s", prefix)


# ──────────────────────────────────────────────────────────────────────
# سیگنال‌های خودکار بی‌اعتبارسازی
# ──────────────────────────────────────────────────────────────────────
def _auto_invalidate(sender, instance, **kwargs):
    """سیگنال post_save/post_delete برای بی‌اعتبارسازی خودکار کش."""
    model_label = f'{sender._meta.app_label}.{sender.__name__}'
    invalidate_model_cache(model_label)


def register_cache_signals():
    """
    اتصال خودکار سیگنال‌های بی‌اعتبارسازی کش به مدل‌های مرتبط.
    باید در AppConfig.ready() فراخوانی شود.
    """
    from django.apps import apps
    from django.db.models.signals import post_save, post_delete

    registered = []
    for model_label in _MODEL_CACHE_MAP:
        try:
            model = apps.get_model(model_label)
            post_save.connect(_auto_invalidate, sender=model, weak=False)
            post_delete.connect(_auto_invalidate, sender=model, weak=False)
            registered.append(model_label)
        except LookupError:
            logger.warning("مدل %s یافت نشد — سیگنال کش ثبت نشد.", model_label)

    logger.info("سیگنال‌های بی‌اعتبارسازی کش ثبت شد برای: %s", registered)
