# راهنمای توسعه --- Zitro Shop

## محیط

نسخه‌های گزارش‌شده: Python 3.14.6، Django 6.1.1 و Tailwind CSS 4.3.3. در
زمان PRD، `requirements.txt`/lockfile پایتون وجود نداشت؛ پیش از نصب
تکرارپذیر، manifest نسخه‌دار اضافه شود.

``` powershell
python --version
python -c "import django; print(django.get_version())"
python manage.py check
python manage.py migrate
python manage.py runserver
```

## رابط کاربری

-   storefront از `templates/base.html` و پنل از
    `templates/dashboard/base_dashboard.html` استفاده می‌کند.
-   UI فارسی RTL و Vazirmatn است.
-   HTMX برای search، grid/cart و polling تیکت استفاده می‌شود.
-   Chart.js محلی و Tailwind CLI در `package.json` تعریف شده‌اند؛ script
    واقعی build را از همان فایل بخوانید.

## الگوی تغییر

1.  مدل، view، URL، template و آزمون‌های مرتبط را بخوانید.
2.  `BUSINESS_RULES.md` و وضعیت PRD را بررسی کنید.
3.  ورودی‌ها را سمت سرور اعتبارسنجی کنید.
4.  عملیات مالی/موجودی را در transaction و با کنترل رقابت طراحی کنید.
5.  برای تغییر مدل migration بسازید و بررسی کنید.
6.  آزمون مثبت، منفی و regression اضافه کنید.
7.  خروجی واقعی فرمان‌ها را گزارش و اسناد مرتبط را به‌روزرسانی کنید.

## داده توسعه

`python manage.py seed_data` و `python manage.py populate_images` وجود
دارند، اما PRD اجرای آن‌ها را در ممیزی انجام نداده است؛ رفتار اجرای مجدد
در آن ممیزی تأیید نشده. پیش از اجرا روی دیتابیس غیرتستی اثر آن را بررسی
کنید. `db.sqlite3` داده توسعه است.

## Git و migration

PRD سه migration untracked را در زمان ممیزی گزارش کرده: `home/0002`,
`orders/0002`, `products/0003`. قبل از merge بررسی کنید که فایل‌ها در
شاخه هدف track شده‌اند. از حذف/بازنویسی migration بدون برنامه خودداری
کنید.

## قرارداد PR

هدف و رفتار تغییر، آزمون‌های اجراشده، migration/config و ریسک‌های حل‌نشده
را توضیح دهید. secret واقعی در کد یا PR قرار نگیرد.
