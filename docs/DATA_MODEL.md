# مدل داده --- Zitro Shop

این سند مدل‌های گزارش‌شده در PRD را توصیف می‌کند؛ جزئیات نوع ستون‌ها و
گزینه‌ها را در `models.py` و migrationها بررسی کنید.

## روابط اصلی

``` text
User ─< Address
User ─< Cart ─< CartItem >─ Product
User ─< Order ─< OrderItem >─ Product (SET_NULL)
Coupon ─< Order (SET_NULL)
Category ─< Product; Category ─< Category (parent/children)
Category ─< CategoryAttribute
Product ─< ProductImage; Product ─< ProductSpecification
Product ─< ProductReview >─ User (SET_NULL)
Brand ─< Product (SET_NULL)
BlogCategory ─< Post; User ─< Post (author, SET_NULL)
User ─< Ticket ─< TicketMessage
User ─< Ticket (assigned_to, SET_NULL)
Banner; SiteSetting (singleton-style)
```

## accounts

-   **User**: `AbstractUser` سفارشی؛ `phone_number` یکتا و nullable،
    `avatar`، `is_verified` (پیش‌فرض False). `is_verified` در جریان عادی
    برنامه تنظیم نمی‌شود.
-   **Address**: FK به User با CASCADE؛ عنوان، گیرنده، تلفن، استان، شهر،
    نشانی، کد پستی، `is_default` و timestamp. CRUD مشتری ندارد.

## products

-   **Category**: نام فارسی/انگلیسی، slug یکتا، parent self-FK با
    CASCADE، SVG، تصویر، ترتیب و وضعیت فعال.
-   **Brand**: نام فارسی/انگلیسی، slug، لوگو، وضعیت فعال و ترتیب.
-   **CategoryAttribute**: تعریف ویژگی دسته، واحد، نوع
    `text/number/select/boolean`، گزینه‌ها، ترتیب و فعال بودن؛ مقدار
    ویژگی روی Product ذخیره نمی‌شود.
-   **Product**: عنوان‌ها، slug، SKU یکتا، Category با PROTECT، Brand با
    SET_NULL، توضیحات، قیمت/قیمت مقایسه‌ای، درصد تخفیف، stock و
    threshold، flags فعال/ویژه/پیشنهاد، ضمانت، rating، views و
    timestampها.
-   **ProductImage**: FK محصول، فایل، alt text، primary و ترتیب.
-   **ProductSpecification**: FK محصول، نام/مقدار/ترتیب. فیلترهای ویژگی
    صفحهٔ فروشگاه به‌صورت داده‌محور از همین رکوردها ساخته می‌شوند.
-   **ProductReview**: FK محصول (CASCADE) و FK کاربر (`SET_NULL`)،
    `author_name`، `rating` (۱ تا ۵)، عنوان/متن، `is_approved` (پیش‌فرض
    True)، `is_verified_purchase` و timestampها؛ قید یکتا برای هر
    (محصول، کاربر). میانگین و تعداد نمایشی از نظرهای تأییدشده محاسبه
    می‌شود (`Product.review_average`/`review_count`) و `Product.rating`
    فقط در نبود نظر به‌عنوان مقدار پیش‌فرض به کار می‌رود.

## cart

-   **Cart**: session key یکتا و nullable، user nullable و timestampها؛
    محاسبه تعداد، قیمت و صرفه‌جویی.
-   **CartItem**: FK سبد و محصول با CASCADE، quantity، timestamp؛ قید
    یکتایی `(cart, product)`.

## orders

-   **Coupon**: code یکتا و uppercase، نوع percent/amount، value، حداقل
    سفارش، سقف تخفیف/تعداد استفاده، تعداد استفاده، بازه اعتبار و active؛
    `validate_for(amount)`.
-   **Order**: شماره `ZT-` + 6 hex؛ کاربر SET_NULL، گیرنده/نشانی،
    totals، وضعیت سفارش `pending/paid/shipped/delivered/cancelled`، روش
    `mock_gateway/cod`، وضعیت پرداخت `pending/successful/failed`،
    transaction ID، کوپن، تخفیف کوپن، ارسال `post/tipax/courier/pickup`،
    tracking، notes و timestamp.
-   **OrderItem**: FK سفارش CASCADE، محصول SET_NULL، snapshot
    عنوان/SKU/قیمت واحد/تعداد/مبلغ.

## blog, home, tickets

-   **BlogCategory**: name، slug، order.
-   **Post**: title، slug، category/author با SET_NULL، cover،
    excerpt/content، published، views و timestamps.
-   **Banner**: title/subtitle، image، link، button text، position
    `hero/banner_pair/banner_wide/sidebar`، order و active.
-   **SiteSetting**: نام فروشگاه، شعار، تماس، نشانی، شبکه اجتماعی، هزینه
    ارسال، آستانه ارسال رایگان، about و footer.
-   **Ticket**: شماره `TK-` + 8 hex، user، subject، category، priority،
    order number، status، assigned_to، unread flags و timestamps.
-   **TicketMessage**: ticket، sender، snapshot نام، staff flag، body و
    created_at.

## قیود و شکاف‌ها

-   `dashboard` مدل یا migration مستقل ندارد.
-   snapshot اقلام سفارش، تاریخچه را از تغییر بعدی محصول جدا می‌کند.
-   حذف دسته دارای محصول در پنل مسدود است؛ FK محصول PROTECT است.
-   ادغام سبد مهمان با کاربر وجود ندارد؛ موجودی در خرید کسر نمی‌شود.
-   پرچم `is_approved` نظرها وجود دارد اما صفحهٔ moderation در پنل ادمین
    پیاده نشده است؛ ثبت نظر پیش‌فرض منتشر می‌شود.
-   رفتار `Address.is_default` تکمیل نشده.
-   شمارش دیتابیس توسعه در ممیزی: 13 محصول، 9 دسته، 10 برند، 11 سفارش، 1
    کوپن و 1 تیکت؛ این مقادیر الزام محصول نیستند.
