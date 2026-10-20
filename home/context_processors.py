from django.core.cache import cache

from .models import SiteSetting
from products.models import Category
from utils.cache import CACHE_PREFIX, CACHE_TTL_STATIC


def site_settings_processor(request):
    """
    Context processor بهینه‌شده با کش.
    تنظیمات سایت و دسته‌بندی‌ها به‌ندرت تغییر می‌کنند
    و نیازی به کوئری مکرر در هر درخواست نیست.
    """
    # کش تنظیمات سایت — ۱ ساعت
    settings_cache_key = f'{CACHE_PREFIX}:ctx:site_settings'
    settings_obj = cache.get(settings_cache_key)
    if settings_obj is None:
        try:
            settings_obj = SiteSetting.get_settings()
        except Exception:
            settings_obj = None
        # حتی None را کش کن تا کوئری تکراری نزنیم
        cache.set(settings_cache_key, settings_obj, CACHE_TTL_STATIC)

    # کش دسته‌بندی‌های ناوبری — ۱ ساعت
    nav_cache_key = f'{CACHE_PREFIX}:ctx:nav_categories'
    nav_categories = cache.get(nav_cache_key)
    if nav_categories is None:
        try:
            nav_categories = list(
                Category.objects.filter(is_active=True, parent__isnull=True).order_by('order')[:12]
            )
        except Exception:
            nav_categories = []
        cache.set(nav_cache_key, nav_categories, CACHE_TTL_STATIC)

    return {
        'site_settings': settings_obj,
        'nav_categories': nav_categories,
    }
