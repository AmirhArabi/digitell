from .models import SiteSetting
from products.models import Category


def site_settings_processor(request):
    try:
        settings = SiteSetting.get_settings()
    except Exception:
        settings = None

    try:
        nav_categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by('order')[:12]
    except Exception:
        nav_categories = []

    return {
        'site_settings': settings,
        'nav_categories': nav_categories,
    }
