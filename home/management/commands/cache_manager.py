"""
دستور مدیریتی کش دیجی‌تل (Digitell Cache Management Command)
============================================================
استفاده:
    python manage.py cache_manager --action=clear       # پاک‌کردن کل کش
    python manage.py cache_manager --action=status      # وضعیت کش
    python manage.py cache_manager --action=warmup      # پرکردن کش اولیه
"""

import time

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.test import RequestFactory

from utils.cache import (
    CACHE_PREFIX,
    invalidate_all,
    make_cache_key,
)


class Command(BaseCommand):
    help = 'مدیریت کش سایت دیجی‌تل: پاک‌کردن، بررسی وضعیت و پیش‌گرم‌سازی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['clear', 'status', 'warmup'],
            default='status',
            help='عملیات موردنظر: clear=پاک‌کردن، status=وضعیت، warmup=پرکردن اولیه',
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'clear':
            self._clear_cache()
        elif action == 'status':
            self._show_status()
        elif action == 'warmup':
            self._warmup_cache()

    def _clear_cache(self):
        """پاک‌کردن تمام کش‌ها."""
        self.stdout.write('🗑️  در حال پاک‌کردن کش...')
        invalidate_all()
        self.stdout.write(self.style.SUCCESS('✅ تمام کش‌ها پاک شد.'))

    def _show_status(self):
        """بررسی وضعیت کش و نمایش آمار."""
        self.stdout.write(f'\n📊 وضعیت کش دیجی‌تل')
        self.stdout.write(f'{"─" * 50}')
        self.stdout.write(f'  نسخه کش: {CACHE_PREFIX}')

        # بررسی backend کش
        backend = cache.__class__.__name__
        self.stdout.write(f'  بکند کش: {backend}')

        # تست سرعت کش
        start = time.perf_counter()
        test_key = f'{CACHE_PREFIX}:_speed_test'
        cache.set(test_key, 'test_value', 10)
        cache.get(test_key)
        cache.delete(test_key)
        elapsed = (time.perf_counter() - start) * 1000

        self.stdout.write(f'  سرعت عملیات کش: {elapsed:.2f}ms (set+get+delete)')

        # بررسی کلیدهای شناخته‌شده
        known_keys = [
            ('ctx:site_settings', 'تنظیمات سایت'),
            ('ctx:nav_categories', 'دسته‌بندی‌های ناوبری'),
        ]

        self.stdout.write(f'\n  کلیدهای کش:')
        for key, label in known_keys:
            full_key = f'{CACHE_PREFIX}:{key}'
            val = cache.get(full_key)
            status = '✅ موجود' if val is not None else '❌ خالی'
            self.stdout.write(f'    {label}: {status}')

        self.stdout.write(f'{"─" * 50}\n')

    def _warmup_cache(self):
        """پیش‌گرم‌سازی کش با بارگذاری صفحات اصلی."""
        self.stdout.write('🔥 در حال پیش‌گرم‌سازی کش...')

        factory = RequestFactory()

        # گرم‌کردن context processor
        try:
            from home.context_processors import site_settings_processor
            request = factory.get('/')
            # شبیه‌سازی کاربر ناشناس
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()

            site_settings_processor(request)
            self.stdout.write('  ✅ تنظیمات سایت کش شد')
        except Exception as e:
            self.stdout.write(f'  ❌ خطا در کش تنظیمات: {e}')

        # گرم‌کردن ویوهای اصلی
        urls_to_warmup = [
            ('/', 'صفحه اصلی'),
        ]

        from django.test import Client
        client = Client()
        for url, label in urls_to_warmup:
            try:
                start = time.perf_counter()
                client.get(url)
                elapsed = (time.perf_counter() - start) * 1000
                self.stdout.write(f'  ✅ {label}: {elapsed:.0f}ms')
            except Exception as e:
                self.stdout.write(f'  ❌ {label}: {e}')

        self.stdout.write(self.style.SUCCESS('\n✅ پیش‌گرم‌سازی کش تکمیل شد.'))
