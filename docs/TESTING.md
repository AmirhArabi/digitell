# راهبرد آزمون --- Zitro Shop

## خط مبنای PRD

در ممیزی commit `fb71e2a`:

``` text
python manage.py check                         → no issues
python manage.py makemigrations --check --dry-run → No changes detected
python manage.py test                          → 35 tests, OK
```

30 تست در `dashboard/tests.py` و 5 تست در `products/tests.py` گزارش شده
است. ماژول `tickets` فایل آزمون ندارد؛ آزمون‌های `accounts`, `cart`,
`blog`, `home`, `orders` خالی/بدون تست گزارش شده‌اند.

## اجرای محلی

``` powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

نسخه‌های محیط ممیزی Python 3.14.6 و Django 6.1.1 بوده‌اند؛ محیط دیگر را
مستقل بررسی کنید.

## پوشش پیشنهادی

-   **Model/unit:** محاسبه تخفیف، Cart totals، Coupon validation،
    شناسه‌ها و قواعد وضعیت.
-   **Integration:** login/register، catalog filters/search، cart،
    checkout، coupon/shipping، mock payment، COD، CSV و CRUD پنل.
-   **Security:** anonymous/non-staff/staff، دسترسی سفارش، password
    validators، rate limit، SVG، ورودی خراب و کوکی‌ها.
-   **Concurrency:** خرید آخرین موجودی، آخرین استفاده کوپن، callback
    تکراری/idempotency.
-   **UI/accessibility:** مرورگر واقعی، HTMX، RTL، موبایل،
    keyboard/focus، label، contrast و chart.

## اولویت آزمون‌های جدید

1.  quantity غیرعددی، صفر، منفی و بیش از stock.
2.  کسر موجودی تراکنشی و rollback.
3.  merge سبد مهمان پس از ورود/ثبت‌نام.
4.  COD و هم‌خوانی status/payment status/گزارش درآمد.
5.  مالکیت فاکتور و tracking و rate limit.
6.  چرخه کامل ticket: create/reply/close/reopen/unread/assignment.
7.  password validation و کنترل تغییر staff.
8.  فرم تماس واقعی و جلوگیری از spam.
9.  seed/migrations در دیتابیس تست.
10. CSV فارسی و UTF-8 BOM.

## معیار قبولی

آزمون مرتبط جدید پیش از merge نوشته شود؛ کل تست‌ها، `check` و
`makemigrations --check` پاس شوند؛ migration بازبینی شود؛ آزمون اجرا‌نشده
پاس‌شده گزارش نشود. تست مرورگر واقعی، load/concurrency و اتصال واقعی
PSP/SMS/email در ممیزی انجام نشده‌اند.
