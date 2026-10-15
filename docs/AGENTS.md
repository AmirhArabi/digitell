# دستورالعمل عامل‌های کدنویسی --- Zitro Shop

## منبع حقیقت

-   قبل از تغییر، کد، URLها، مدل‌ها، migrationها و آزمون‌های واقعی را
    بررسی کن.
-   `Implemented`, `Partially Implemented`, `UI Only / Backend Missing`,
    `Planned`, `Unverified` را از هم جدا نگه دار.
-   mock gateway را PSP واقعی، متن اقساط را اتصال SnappPay، tracking را
    اتصال حمل‌ونقل و rating را review واقعی معرفی نکن.
-   تعارض سند/کد را گزارش کن؛ بی‌صدا اصلاح یا حدس نزن.
-   چیزی را که اجرا نکرده‌ای، اجراشده گزارش نکن.

## معماری و محدودیت‌ها

-   معماری فعلی Django monolith + Django Templates + HTMX است.
-   دیتابیس فعلی SQLite است؛ میزبان و دیتابیس production مشخص نیست.
-   DRF، API، Celery، Redis، `forms.py`، PSP/SMS/email واقعی،
    `requirements.txt`، Dockerfile و CI در ممیزی وجود نداشتند.
-   UI فارسی RTL، مبالغ تومان و timezone تهران است.

## گردش کار

1.  مسئله را به معیار پذیرش آزمون‌پذیر تبدیل کن.
2.  کوچک‌ترین تغییر سازگار را پیاده کن.
3.  اعتبارسنجی و authorization را سمت سرور انجام بده.
4.  برای تغییر رفتاری آزمون regression اضافه کن.
5.  migration تولید و بررسی کن.
6.  اجرا کن: `python manage.py check`,
    `python manage.py makemigrations --check --dry-run`,
    `python manage.py test`.
7.  نتایج واقعی، تنظیمات لازم، محدودیت‌ها و اسناد به‌روزشده را گزارش کن.

## مناطق پرریسک

-   موجودی هنگام خرید کسر نمی‌شود؛ overselling ممکن است.
-   COD وضعیت `status=paid` ولی `payment_status=pending` دارد.
-   فاکتور/tracking عمومی‌اند.
-   staff عادی می‌تواند دیگران را staff کند.
-   password validators در ثبت‌نام اجرا نمی‌شوند.
-   SVG خام با `safe` رندر می‌شود.
-   migrationهای `home/0002`, `orders/0002`, `products/0003` در ممیزی
    untracked گزارش شده‌اند.
-   ماژول تیکت در ممیزی تست خودکار نداشت.

## قواعد کدنویسی

-   اعتبارسنجی را به HTML/JS واگذار نکن.
-   مجوز با مخفی‌کردن دکمه تأمین نمی‌شود.
-   تغییرات مالی/موجودی نسبت به خطا و race condition امن باشند.
-   وابستگی یا معماری جدید بدون نیاز مستند اضافه نشود.
-   از تغییر غیرمرتبط در UI، seed data و migration خودداری کن.

## گزارش پایان کار

**تغییرات**، **آزمون‌ها و خروجی واقعی**، **migration/config**، **ریسک‌های
باقی‌مانده** و **اسناد به‌روزشده** را فهرست کن.
