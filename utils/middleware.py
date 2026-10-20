"""
میدلور بهینه‌سازی سرعت دیجی‌تل (Digitell Performance Middleware)
================================================================
شامل:
- GZipMinifyMiddleware: فشرده‌سازی GZip + حذف فضاهای خالی اضافی HTML
- CacheHeaderMiddleware: تنظیم هدرهای Cache-Control برای فایل‌های استاتیک
- PerformanceMonitorMiddleware: اندازه‌گیری زمان پاسخ و لاگ درخواست‌های کند
"""

import logging
import re
import time

from django.conf import settings
from django.utils.cache import patch_cache_control

logger = logging.getLogger(__name__)

# آستانه زمان پاسخ کند (میلی‌ثانیه) — بالاتر لاگ می‌شود
SLOW_REQUEST_THRESHOLD_MS = getattr(settings, 'DIGITELL_SLOW_REQUEST_MS', 500)


# ──────────────────────────────────────────────────────────────────────
# حذف فضاهای خالی اضافی HTML (Minification سبک)
# ──────────────────────────────────────────────────────────────────────
# الگوهای regex برای minify سبک HTML
_RE_MULTI_SPACES = re.compile(r'[ \t]+')
_RE_BLANK_LINES = re.compile(r'\n\s*\n')
_RE_TRIM_TAGS = re.compile(r'>\s+<')


def _minify_html(content):
    """حداقل‌سازی سبک HTML: حذف فضاهای خالی اضافه بدون شکستن ساختار."""
    if not content:
        return content
    # حذف خطوط خالی
    content = _RE_BLANK_LINES.sub('\n', content)
    # حذف فضاهای بین تگ‌ها
    content = _RE_TRIM_TAGS.sub('><', content)
    return content


class HtmlMinifyMiddleware:
    """
    میدلور فشرده‌سازی سبک HTML.

    فقط پاسخ‌های HTML با کد ۲۰۰ را minify می‌کند.
    در حالت DEBUG فعال نیست مگر DIGITELL_MINIFY_DEBUG=True باشد.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = not settings.DEBUG or getattr(settings, 'DIGITELL_MINIFY_DEBUG', False)

    def __call__(self, request):
        response = self.get_response(request)

        if not self.enabled:
            return response

        content_type = response.get('Content-Type', '')
        if (response.status_code == 200
                and 'text/html' in content_type
                and hasattr(response, 'content')):
            try:
                original_size = len(response.content)
                minified = _minify_html(response.content.decode('utf-8'))
                response.content = minified.encode('utf-8')
                new_size = len(response.content)
                savings = original_size - new_size
                if savings > 0:
                    logger.debug(
                        "HTML minify: %s → %d بایت کاهش یافت (%.1f%%)",
                        request.path, savings,
                        (savings / original_size * 100) if original_size else 0,
                    )
            except Exception:
                pass  # در صورت خطا محتوای اصلی بازگردانده می‌شود

        return response


class CacheHeaderMiddleware:
    """
    تنظیم هدرهای Cache-Control بهینه برای انواع مختلف پاسخ.

    - فایل‌های استاتیک: کش طولانی (۱ سال)
    - فایل‌های مدیا: کش میان‌مدت (۳۰ روز)
    - صفحات HTML: no-cache (اجازه بررسی با ETag)
    """

    # پسوندهای فایل استاتیک
    STATIC_EXTENSIONS = frozenset([
        '.css', '.js', '.woff', '.woff2', '.ttf', '.otf', '.eot',
        '.svg', '.ico',
    ])

    IMAGE_EXTENSIONS = frozenset([
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.bmp',
    ])

    MEDIA_EXTENSIONS = frozenset([
        '.mp4', '.webm', '.mp3', '.ogg', '.wav',
    ])

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path.lower()

        # فایل‌های استاتیک: ۱ سال
        if path.startswith('/static/'):
            ext = self._get_extension(path)
            if ext in self.STATIC_EXTENSIONS or ext in self.IMAGE_EXTENSIONS:
                patch_cache_control(
                    response,
                    public=True,
                    max_age=31536000,  # ۱ سال
                    immutable=True,
                )
            return response

        # فایل‌های مدیا: ۳۰ روز
        if path.startswith('/media/'):
            patch_cache_control(
                response,
                public=True,
                max_age=2592000,  # ۳۰ روز
            )
            return response

        # صفحات HTML: اجازه ETag ولی revalidate
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type:
            patch_cache_control(
                response,
                no_cache=True,
                must_revalidate=True,
            )

        return response

    @staticmethod
    def _get_extension(path):
        dot_index = path.rfind('.')
        if dot_index == -1:
            return ''
        return path[dot_index:]


class PerformanceMonitorMiddleware:
    """
    اندازه‌گیری زمان پاسخ هر درخواست.

    - هدر X-Response-Time به پاسخ اضافه می‌شود
    - درخواست‌های کندتر از آستانه لاگ می‌شوند
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()

        response = self.get_response(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response['X-Response-Time'] = f'{elapsed_ms:.1f}ms'

        if elapsed_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "⚠️ درخواست کند: %s %s — %.0fms (آستانه: %dms)",
                request.method,
                request.get_full_path(),
                elapsed_ms,
                SLOW_REQUEST_THRESHOLD_MS,
            )

        return response
