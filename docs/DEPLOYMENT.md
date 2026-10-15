# راهنمای استقرار --- Zitro Shop

> PRD بستر تولید را مشخص نکرده؛ این سند چک‌لیست پیشنهادی است، نه ادعای
> آماده‌بودن پیکربندی فعلی.

## وضعیت فعلی

WhiteNoise و `STATIC_ROOT` وجود دارند؛ دیتابیس فعلی SQLite است. در ممیزی
`requirements.txt`، Dockerfile، CI config و تنظیم نهایی WSGI/production
مشخص نبودند. `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, HTTPS و cookie
hardening کامل/تأییدشده نیستند. میزبان، دامنه و دیتابیس هدف تعیین
نشده‌اند.

## پیش‌نیازها

-   [ ] انتخاب میزبان، دامنه، TLS، WSGI server و دیتابیس.
-   [ ] افزودن dependency manifest با نسخه‌های دقیق.
-   [ ] انتقال secretها به environment/secret manager.
-   [ ] `DEBUG=False`, `ALLOWED_HOSTS` محدود و اجرای
    `python manage.py check --deploy`.
-   [ ] HTTPS، secure cookies، CSRF trusted origins و HSTS.
-   [ ] مسیر پایدار media، backup و سیاست بازیابی.
-   [ ] logging، error monitoring و health checks.
-   [ ] رفع دسترسی عمومی ناامن سفارش/فاکتور، ارتقای staff و password
    validation.
-   [ ] تعیین تکلیف موجودی/COD و ممنوعیت معرفی mock به‌عنوان پرداخت
    واقعی.

## متغیرهای محیطی پیشنهادی

``` text
SECRET_KEY=<secret-from-environment>
DEBUG=False
ALLOWED_HOSTS=<explicit-host-list>
DATABASE_URL=<only-if-implemented>
EMAIL_HOST=<if-configured>
EMAIL_PORT=<provider-port>
EMAIL_HOST_USER=<provider-user>
EMAIL_HOST_PASSWORD=<secret>
EMAIL_USE_TLS=<provider-specific>
```

وجود `DATABASE_URL` در این نمونه به معنای پشتیبانی فعلی نیست؛ settings
باید برای خواندن آن پیاده‌سازی شود.

## انتشار پیشنهادی

1.  ساخت release از commit تمیز و مشخص.
2.  نصب dependencyها از manifest pin‌شده.
3.  اجرای `manage.py check --deploy`، آزمون‌ها و
    `makemigrations --check --dry-run`.
4.  backup دیتابیس و media.
5.  اجرای `python manage.py migrate`.
6.  build CSS با script واقعی `package.json`.
7.  اجرای `python manage.py collectstatic --noinput`.
8.  راه‌اندازی با WSGI server و reverse proxy/TLS متناسب با میزبان
    انتخابی.
9.  smoke test مسیرهای خانه، کاتالوگ، login staff، checkout آزمایشی و
    گزارش.
10. بررسی logها و آماده‌بودن rollback.

فرمان دقیق WSGI/reverse proxy تا انتخاب پلتفرم مشخص نیست و نباید حدس زده
شود.

## Static/media

در production، DEBUG خاموش باشد و از serving توسعه برای static/media
استفاده نشود. تنظیم نهایی WhiteNoise باید با `check --deploy` و آزمون
محیط واقعی تأیید شود. media باید از نظر نوع/حجم، backup و دسترسی بررسی
شود؛ avatar ممکن است داده شخصی باشد.

## Backup و rollback

پیش از migration backup بگیرید؛ restore را در محیط جداگانه آزمایش کنید.
migrationهای `home/0002`, `orders/0002`, `products/0003` در زمان ممیزی
untracked گزارش شده‌اند و باید در release commit بررسی شوند. ثبت نسخه،
migrationها، smoke test و rollback جزو چک‌لیست release باشد.

## تصمیم‌های لازم

بستر و WSGI server، دیتابیس production، PSP و providerهای پیام،
دامنه/TLS، RPO/RTO، تناوب backup و سیاست نگهداری داده.
