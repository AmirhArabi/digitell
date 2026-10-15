# معماری فنی --- Zitro Shop

## نمای کلی

Zitro یک Django monolith با رندر سمت سرور است. Django Templates صفحات را
می‌سازند و HTMX برای partial refresh استفاده می‌شود. SPA جدا، REST/GraphQL
API، headless CMS، Celery و Redis در ممیزی وجود نداشتند.

``` text
Browser → Django URLs → app views → Django ORM → SQLite (development)
                         ↓
                  Django templates / HTMX partials
Static: Tailwind build, HTMX config, local Chart.js
Media: MEDIA_ROOT / MEDIA_URL
```

## پشته تأییدشده

-   Python 3.14.6 و Django 6.1.1 در محیط ممیزی.
-   SQLite (`db.sqlite3`) به‌عنوان دیتابیس فعلی.
-   Django Templates، `django_htmx` و HTMX.
-   Tailwind CSS 4.3.3 با CLI.
-   Chart.js محلی، WhiteNoise، Vazirmatn و timezone `Asia/Tehran`.

در ممیزی DRF، serializers، `forms.py`، Celery، Redis، PSP واقعی،
provider پیامک/ایمیل، `requirements.txt`، Dockerfile و CI config یافت
نشدند.

## اپلیکیشن‌ها

-   `config`: settings و URLهای سطح پروژه.
-   `accounts`: User، ورود/ثبت‌نام، پروفایل و Address.
-   `products`: Category، Brand، CategoryAttribute، Product،
    ProductImage، ProductSpecification و کاتالوگ.
-   `cart`: Cart و CartItem.
-   `orders`: Coupon، Order، OrderItem، checkout و mock payment.
-   `home`: Banner، SiteSetting و صفحات محتوایی.
-   `blog`: BlogCategory و Post.
-   `tickets`: Ticket و TicketMessage.
-   `dashboard`: views، URLs، templates و tests؛ مدل مستقل ندارد.

## الگوی درخواست

URL به view resolve می‌شود؛ view مجوز را بررسی می‌کند، داده را با ORM
می‌خواند/تغییر می‌دهد و قالب کامل یا partial HTMX برمی‌گرداند. اعتبارسنجی
عمدتاً دستی در viewهاست و `forms.py` وجود ندارد.

## اصول توسعه معماری

-   monolith و SSR حفظ شوند مگر نیاز اندازه‌گیری‌شده‌ای برای جداسازی وجود
    داشته باشد.
-   قیمت، کوپن، سفارش و موجودی در سمت سرور و لایه قابل آزمون پیاده شوند.
-   عملیات چندمدلی حساس با transaction و کنترل رقابت طراحی شوند.
-   مجوزها در سرور اعمال شوند، نه صرفاً با مخفی‌کردن UI.
-   secretها از environment بیایند.
-   queryها و عملکرد قبل از افزودن cache یا معماری توزیع‌شده اندازه‌گیری
    شوند.

## وضعیت migration

PRD گزارش کرده `makemigrations --check --dry-run` بدون تغییر بوده است.
سه migration در زمان ممیزی untracked بودند: `home/0002`, `orders/0002`,
`products/0003`; پیش از merge وضعیت Git باید بررسی شود.

## محدودیت‌ها

دیتابیس تولید و میزبان مشخص نیست؛ SQLite فقط وضعیت فعلی را نشان می‌دهد.
تنظیمات production و dependency manifest کامل نیستند. تست بار، مرورگر
واقعی و هم‌زمانی checkout انجام نشده‌اند.
