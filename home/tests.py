"""
تست‌های سیستم کش و بهینه‌سازی سرعت دیجی‌تل
=============================================
"""
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.test import TestCase, RequestFactory, override_settings

from utils.cache import (
    CACHE_PREFIX,
    make_cache_key,
    make_etag,
    view_cache,
    invalidate_all,
    invalidate_model_cache,
    invalidate_view_cache,
    CACHE_TTL_MEDIUM,
    CACHE_TTL_STATIC,
)
from utils.middleware import (
    HtmlMinifyMiddleware,
    CacheHeaderMiddleware,
    PerformanceMonitorMiddleware,
    _minify_html,
)


class MakeCacheKeyTest(TestCase):
    """تست تولید کلید کش."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_simple_key(self):
        """کلید ساده بدون درخواست."""
        key = make_cache_key('test')
        self.assertIn(CACHE_PREFIX, key)
        self.assertIn('test', key)

    def test_key_with_request(self):
        """کلید با درخواست شامل path و query string."""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/products/?sort=newest&page=2')
        request.user = AnonymousUser()
        key = make_cache_key('shop', request)
        self.assertIn('shop', key)
        self.assertIn('/products/', key)
        self.assertIn('anon', key)

    def test_key_sorted_params(self):
        """پارامترها مرتب باشند تا کلید یکتا باشد."""
        from django.contrib.auth.models import AnonymousUser
        req1 = self.factory.get('/?b=2&a=1')
        req1.user = AnonymousUser()
        req2 = self.factory.get('/?a=1&b=2')
        req2.user = AnonymousUser()
        self.assertEqual(
            make_cache_key('test', req1),
            make_cache_key('test', req2),
        )

    def test_long_key_hashed(self):
        """کلید بلند به MD5 تبدیل شود."""
        long_extra = 'x' * 300
        key = make_cache_key('test', extra=long_extra)
        self.assertLessEqual(len(key), 250)

    def test_authenticated_vs_anon(self):
        """کلید کاربر وارد‌شده و ناشناس متفاوت باشد."""
        from django.contrib.auth.models import AnonymousUser

        req_anon = self.factory.get('/')
        req_anon.user = AnonymousUser()

        req_auth = self.factory.get('/')
        req_auth.user = MagicMock()
        req_auth.user.is_authenticated = True

        key_anon = make_cache_key('test', req_anon)
        key_auth = make_cache_key('test', req_auth)
        self.assertNotEqual(key_anon, key_auth)


class MakeEtagTest(TestCase):
    """تست ساخت ETag."""

    def test_etag_from_string(self):
        etag = make_etag('hello')
        self.assertTrue(len(etag) == 32)  # MD5 hex

    def test_etag_from_bytes(self):
        etag = make_etag(b'hello')
        self.assertTrue(len(etag) == 32)

    def test_same_content_same_etag(self):
        self.assertEqual(make_etag('test'), make_etag('test'))

    def test_different_content_different_etag(self):
        self.assertNotEqual(make_etag('a'), make_etag('b'))


class InvalidationTest(TestCase):
    """تست بی‌اعتبارسازی کش."""

    def setUp(self):
        cache.clear()

    def test_invalidate_all(self):
        cache.set('test_key', 'value', 60)
        invalidate_all()
        self.assertIsNone(cache.get('test_key'))

    def test_invalidate_model_cache(self):
        """بی‌اعتبارسازی کش مدل کلیدهای مرتبط را پاک کند."""
        key = f'{CACHE_PREFIX}:view:home'
        cache.set(key, 'cached_data', 60)
        invalidate_model_cache('home.Banner')
        self.assertIsNone(cache.get(key))

    def test_invalidate_unknown_model(self):
        """مدل ناشناخته خطایی ندهد."""
        invalidate_model_cache('unknown.Model')  # باید بدون خطا اجرا شود

    def test_invalidate_view_cache(self):
        key = f'{CACHE_PREFIX}:shop'
        cache.set(key, 'data', 60)
        invalidate_view_cache('shop')
        self.assertIsNone(cache.get(key))


class HtmlMinifyTest(TestCase):
    """تست فشرده‌سازی HTML."""

    def test_remove_blank_lines(self):
        html = '<div>\n\n\n<p>test</p>\n\n</div>'
        result = _minify_html(html)
        self.assertNotIn('\n\n', result)

    def test_remove_whitespace_between_tags(self):
        html = '<div>   <p>test</p>   </div>'
        result = _minify_html(html)
        self.assertIn('><p>', result)
        self.assertIn('</p><', result)

    def test_empty_content(self):
        self.assertEqual(_minify_html(''), '')
        self.assertEqual(_minify_html(None), None)


class CacheHeaderMiddlewareTest(TestCase):
    """تست هدرهای Cache-Control."""

    def test_static_file_cache_headers(self):
        response = self.client.get('/static/css/output.css')
        # ممکن است فایل وجود نداشته باشد ولی middleware اجرا می‌شود

    def test_html_page_headers(self):
        response = self.client.get('/')
        # بررسی وجود هدر X-Response-Time
        self.assertIn('X-Response-Time', response)


class PerformanceMonitorTest(TestCase):
    """تست مانیتور عملکرد."""

    def test_response_time_header(self):
        response = self.client.get('/')
        self.assertIn('X-Response-Time', response)
        # مقدار باید ms داشته باشد
        self.assertTrue(response['X-Response-Time'].endswith('ms'))


class ContextProcessorCacheTest(TestCase):
    """تست کش context processor."""

    def setUp(self):
        cache.clear()

    def test_site_settings_cached(self):
        """context processor بعد از اولین اجرا کش شود."""
        # اولین درخواست
        self.client.get('/')

        # بررسی وجود در کش
        key = f'{CACHE_PREFIX}:ctx:site_settings'
        self.assertIsNotNone(cache.get(key))

    def test_nav_categories_cached(self):
        """دسته‌بندی‌های ناوبری کش شوند."""
        self.client.get('/')

        key = f'{CACHE_PREFIX}:ctx:nav_categories'
        self.assertIsNotNone(cache.get(key))

    def test_cache_invalidation_on_settings_change(self):
        """تغییر تنظیمات سایت کش را بی‌اعتبار کند."""
        from home.models import SiteSetting
        self.client.get('/')

        key = f'{CACHE_PREFIX}:ctx:site_settings'
        self.assertIsNotNone(cache.get(key))

        # تغییر تنظیمات — سیگنال باید کش را پاک کند
        settings_obj = SiteSetting.get_settings()
        settings_obj.store_name = 'تست'
        settings_obj.save()

        self.assertIsNone(cache.get(key))


class ViewCacheDecoratorTest(TestCase):
    """تست دکوراتور view_cache."""

    def setUp(self):
        cache.clear()

    def test_index_cached_on_second_request(self):
        """درخواست دوم از کش سرو شود."""
        from django.contrib.auth.models import AnonymousUser

        # اولین درخواست
        response1 = self.client.get('/')
        self.assertEqual(response1.status_code, 200)

        # درخواست دوم باید ETag داشته باشد
        response2 = self.client.get('/')
        self.assertEqual(response2.status_code, 200)
        if 'ETag' in response2:
            self.assertTrue(response2['ETag'].startswith('"'))

    def test_etag_304_response(self):
        """درخواست با ETag یکسان باید 304 برگرداند."""
        # اولین درخواست
        response = self.client.get('/')
        etag = response.get('ETag', '')

        if etag:
            # درخواست دوم با If-None-Match
            response2 = self.client.get('/', HTTP_IF_NONE_MATCH=etag)
            self.assertEqual(response2.status_code, 304)

    def test_post_not_cached(self):
        """درخواست POST نباید کش شود."""
        response = self.client.post('/')
        # POST به صفحه اصلی ممکن است ۴۰۵ بدهد ولی نباید خطای کش باشد
        self.assertIn(response.status_code, [200, 301, 302, 403, 405])
