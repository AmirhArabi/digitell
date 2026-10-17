from django.core.management.base import BaseCommand
from accounts.models import User
from products.models import Category, Brand, Product, ProductSpecification
from home.models import Banner, SiteSetting
from blog.models import BlogCategory, Post


class Command(BaseCommand):
    help = "Seed database with initial Zitro store data, categories, and products"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Starting database seed..."))

        # 1. Superuser
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "مدیر",
                "last_name": "دیجی تل",
                "email": "admin@zitro.ir",
                "phone_number": "09120000000",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (admin / admin123)"))

        # 2. Site settings
        settings = SiteSetting.get_settings()
        settings.store_name = "فروشگاه دیجی تل"
        settings.slogan = "خرید آنلاین و اقساطی انواع گوشی موبایل، لپ تاپ و لوازم دیجیتال"
        settings.phone = "۰۲۱-۹۱۰۹۸۷۶۵"
        settings.email = "support@zitro.ir"
        settings.address = "تهران، خیابان جمهوری، تقاطع حافظ، مجتمع چارسو، طبقه ۲"
        settings.save()

        # 3. Brands
        brands_data = [
            ("اپل", "Apple", "apple"),
            ("سامسونگ", "Samsung", "samsung"),
            ("شیائومی", "Xiaomi", "xiaomi"),
            ("انکر", "Anker", "anker"),
            ("ایسوس", "ASUS", "asus"),
            ("جی بی ال", "JBL", "jbl"),
            ("سونی", "Sony", "sony"),
            ("گرین لاین", "Green Lion", "green-lion"),
            ("پرودو", "Porodo", "porodo"),
        ]
        brands = {}
        for name, name_en, slug in brands_data:
            b, _ = Brand.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "name_en": name_en}
            )
            brands[slug] = b

        # 4. Categories
        categories_data = [
            ("گوشی موبایل", "smartphones", 1, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="3" ry="3"></rect><line x1="12" y1="18" x2="12.01" y2="18" stroke-width="2"></line><line x1="10" y1="5" x2="14" y2="5"></line></svg>'),
            ("تبلت", "tablets", 2, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18" stroke-width="2"></line></svg>'),
            ("لپ تاپ", "laptops", 3, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path d="M4 6a2 2 0 012-2h12a2 2 0 012 2v8H4V6z"></path><path d="M2 17a2 2 0 012-2h16a2 2 0 012 2v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1z"></path></svg>'),
            ("ساعت هوشمند", "smartwatches", 4, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><rect x="6" y="7" width="12" height="10" rx="3"></rect><path d="M9 7V3h6v4"></path><path d="M9 17v4h6v-4"></path><circle cx="12" cy="12" r="1.5"></circle></svg>'),
            ("گیمینگ", "gaming", 5, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="12" rx="6"></rect><path d="M6 12h4m-2-2v4"></path><line x1="15" y1="11" x2="15.01" y2="11" stroke-width="2"></line><line x1="18" y1="13" x2="18.01" y2="13" stroke-width="2"></line></svg>'),
            ("هدفون و هندزفری", "headphones", 6, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path d="M3 18v-6a9 9 0 0118 0v6"></path><path d="M21 19a2 2 0 01-2 2h-1a2 2 0 01-2-2v-3a2 2 0 012-2h3zM3 19a2 2 0 002 2h1a2 2 0 002-2v-3a2 2 0 00-2-2H3z"></path></svg>'),
            ("اسپیکر و بلندگو", "speakers", 7, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><rect x="4" y="2" width="16" height="20" rx="3"></rect><circle cx="12" cy="7" r="2"></circle><circle cx="12" cy="15" r="4"></circle><circle cx="12" cy="15" r="1.5"></circle></svg>'),
            ("لوازم جانبی موبایل", "accessories", 8, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path d="M12 2v6m-4-6v6m-3 3h14a1 1 0 011 1v2a6 6 0 01-6 6h-4a6 6 0 01-6-6v-2a1 1 0 011-1z"></path><path d="M12 18v4"></path></svg>'),
            ("تجهیزات ذخیره‌سازی", "storage", 9, '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="6" rx="2"></rect><rect x="3" y="14" width="18" height="6" rx="2"></rect><circle cx="7" cy="7" r="1" fill="currentColor"></circle><circle cx="7" cy="17" r="1" fill="currentColor"></circle><line x1="14" y1="7" x2="17" y2="7"></line><line x1="14" y1="17" x2="17" y2="17"></line></svg>'),
        ]
        categories = {}
        for name, slug, order, icon in categories_data:
            c, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "order": order, "icon_svg": icon}
            )
            categories[slug] = c

        # 5. Products
        products_data = [
            {
                "title": "شارژر دیواری انکر مدل PowerPort III A2149 توان 20 وات",
                "slug": "anker-powerport-iii-a2149-20w",
                "sku": "ANK-A2149-20W",
                "cat": "accessories",
                "brand": "anker",
                "price": 1899000,
                "compare_at": 2020000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۸ ماه گارانتی شرکتی",
                "specs": [("توان خروجی", "۲۰ وات"), ("تعداد پورت", "۱ عدد USB-C"), ("فناوری شارژ", "PowerIQ 3.0 / PD"), ("جنس بدنه", "پلاستیک مقاوم ABS")]
            },
            {
                "title": "شارژر دیواری ۳۳ وات انکر مدل 323 Charger A2331",
                "slug": "anker-323-charger-33w-a2331",
                "sku": "ANK-A2331-33W",
                "cat": "accessories",
                "brand": "anker",
                "price": 3110000,
                "compare_at": 5100000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۸ ماه گارانتی شرکتی",
                "specs": [("توان خروجی", "۳۳ وات"), ("پورت‌ها", "۱ عدد USB-C + ۱ عدد USB-A"), ("فناوری شارژ", "PowerIQ 3.0"), ("پشتیبانی همزمان", "شارژ دو دستگاه همزمان")]
            },
            {
                "title": "گوشی موبایل شیائومی REDMI NOTE 15 PRO 5G حافظه 256 رم 8 گیگابایت",
                "slug": "xiaomi-redmi-note-15-pro-5g-256gb",
                "sku": "XIA-RN15P-256",
                "cat": "smartphones",
                "brand": "xiaomi",
                "price": 116991000,
                "compare_at": 124500000,
                "is_featured": True,
                "is_special": False,
                "warranty": "۱۸ ماه گارانتی جامع شرکتی + کد رجیستری",
                "specs": [("حافظه داخلی", "۲۵۶ گیگابایت"), ("حافظه رم", "۸ گیگابایت"), ("دوربین اصلی", "۲۰۰ مگاپیکسل"), ("باتری", "۵۱۰۰ میلی‌آمپر با شارژ ۶۷ وات"), ("صفحه نمایش", "AMOLED 120Hz")]
            },
            {
                "title": "گوشی موبایل سامسونگ GALAXY A57 5G ظرفیت 512 رم 12 گیگابایت",
                "slug": "samsung-galaxy-a57-5g-512gb",
                "sku": "SAM-A57-512",
                "cat": "smartphones",
                "brand": "samsung",
                "price": 168691000,
                "compare_at": 177500000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۸ ماه گارانتی رسمی سامسونگ ایران",
                "specs": [("حافظه داخلی", "۵۱۲ گیگابایت"), ("حافظه رم", "۱۲ گیگابایت"), ("پردازنده", "Exynos 1580"), ("مقاومت در برابر آب", "IP67"), ("صفحه نمایش", "Super AMOLED Plus 120Hz")]
            },
            {
                "title": "گوشی موبایل اپل iPhone 18 Pro Max ZA/A ظرفیت 256 گیگابایت رم 12",
                "slug": "apple-iphone-18-pro-max-256gb",
                "sku": "APL-IP18PM-256",
                "cat": "smartphones",
                "brand": "apple",
                "price": 464991000,
                "compare_at": 510000000,
                "is_featured": True,
                "is_special": False,
                "warranty": "۱۸ ماه گارانتی شرکتی + رجیستری معتبر",
                "specs": [("پردازنده", "Apple A19 Pro"), ("بدنه", "تیتانیوم گرید ۵"), ("دوربین", "سه‌گانه ۴۸ مگاپیکسل با زوم ۵ برابری پریسکوپی"), ("صفحه نمایش", "Super Retina XDR OLED 120Hz ProMotion")]
            },
            {
                "title": "لپ تاپ ایسوس Vivobook X1504VA صفحه 15.6 اینچ Core 5 120U رم 16 گیگابایت 1TB SSD",
                "slug": "asus-vivobook-x1504va-core5-16gb-1tb",
                "sku": "ASUS-X1504VA-120U",
                "cat": "laptops",
                "brand": "asus",
                "price": 193990000,
                "compare_at": 198000000,
                "is_featured": True,
                "is_special": False,
                "warranty": "۲۴ ماه گارانتی یکپارچه ایسوس",
                "specs": [("پردازنده", "Intel Core 5 120U (10 Cores, up to 5.0GHz)"), ("حافظه رم", "۱۶ گیگابایت DDR5"), ("حافظه داخلی", "۱ ترابایت NVMe PCIe 4.0 SSD"), ("صفحه نمایش", "15.6 inch FHD IPS مات")]
            },
            {
                "title": "کنسول بازی سونی پلی استیشن 5 مدل Slim Digital ظرفیت 825GB",
                "slug": "sony-ps5-slim-digital-825gb",
                "sku": "SNY-PS5-SLIM-DIG",
                "cat": "gaming",
                "brand": "sony",
                "price": 187770000,
                "compare_at": 192000000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۲ ماه گارانتی اصالت و سلامت فیزیکی",
                "specs": [("حافظه ذخیره‌سازی", "۸۲۵ گیگابایت Ultra-High Speed SSD"), ("دسته‌ همراه", "DualSense بی سیم"), ("خروجی تصویر", "پشتیبانی از 4K 120Hz و HDR"), ("نوع کنسول", "دیجیتال (بدون دیسک درایو)")]
            },
            {
                "title": "ساندبار حرفه‌ای جی بی ال مدل JBL BAR 800 MK2 توان 720 وات",
                "slug": "jbl-bar-800-mk2-soundbar",
                "sku": "JBL-BAR800-MK2",
                "cat": "speakers",
                "brand": "jbl",
                "price": 161099000,
                "compare_at": 181000000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۸ ماه گارانتی طلایی تراوک",
                "specs": [("توان کل خروجی", "۷۲۰ وات"), ("اسپیکرهای سوراند", "بی‌سیم جداشونده با باتری داخلی"), ("فناوری صوتی", "Dolby Atmos 3D Surround"), ("اتصالات", "HDMI eARC, Bluetooth 5.3, Wi-Fi")]
            },
            {
                "title": "ساعت هوشمند اپل واچ Apple Watch SE 3 سایز 44 میلی‌متری آلومینیوم",
                "slug": "apple-watch-se-3-44mm",
                "sku": "APL-WATCH-SE3-44",
                "cat": "smartwatches",
                "brand": "apple",
                "price": 63950000,
                "compare_at": 85000000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۸ ماه گارانتی شرکتی آروند",
                "specs": [("سایز بدنه", "۴۴ میلی‌متر"), ("جنس بدنه", "آلومینیوم ۱۰۰٪ بازیافتی"), ("سنسورها", "ضربان قلب، اکسیژن، تشخیص تصادف"), ("مقاومت در برابر آب", "تا عمق ۵۰ متر WR50")]
            },
            {
                "title": "هندزفری بی‌سیم بلوتوثی انکر مدل Soundcore Liberty Buds D1200 با نویز کنسلینگ",
                "slug": "anker-soundcore-liberty-buds-d1200",
                "sku": "ANK-LIB-D1200",
                "cat": "headphones",
                "brand": "anker",
                "price": 13450000,
                "compare_at": 18200000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۱۸ ماه گارانتی تعویض انکر",
                "specs": [("نویزکنسلینگ", "ANC فعال هیبریدی"), ("شارژدهی", "تا ۵۰ ساعت با کیس شارژ"), ("درایور", "۱۰ میلی‌متری با بیس عمیق BassUp"), ("مقاومت", "IPX5 ضد تعریق و قطرات آب")]
            },
            {
                "title": "اس اس دی اینترنال سیلیکون پاور مدل Ace A55 ظرفیت 1 ترابایت SATA III",
                "slug": "silicon-power-ace-a55-1tb-ssd",
                "sku": "SP-A55-1TB",
                "cat": "storage",
                "brand": "asus",
                "price": 38577000,
                "compare_at": 41000000,
                "is_featured": False,
                "is_special": False,
                "warranty": "۳۶ ماه گارانتی داده پرداز رایانه متین",
                "specs": [("ظرفیت", "۱ ترابایت"), ("رابط", "SATA III 6Gb/s"), ("سرعت خواندن", "تا ۵۶۰ مگابایت بر ثانیه"), ("سرعت نوشتن", "تا ۵۳۰ مگابایت بر ثانیه")]
            },
            {
                "title": "پاوربانک ۲۰۰۰۰ میلی‌آمپر شیائومی مدل PB2020MI توان 22.5 وات",
                "slug": "xiaomi-powerbank-20000-pb2020mi",
                "sku": "XIA-PB2020-22W",
                "cat": "accessories",
                "brand": "xiaomi",
                "price": 4899000,
                "compare_at": 6280000,
                "is_featured": True,
                "is_special": True,
                "warranty": "۶ ماه گارانتی شرکتی",
                "specs": [("ظرفیت باتری", "۲۰۰۰۰ میلی‌آمپر ساعت"), ("توان خروجی", "۲۲.۵ وات سوپر فست"), ("تعداد درگاه خروجی", "۳ پورت همزمان"), ("جنس بدنه", "پلی‌کربنات ضد حریق")]
            }
        ]

        for p_data in products_data:
            cat = categories[p_data["cat"]]
            brnd = brands.get(p_data["brand"])
            product, _ = Product.objects.get_or_create(
                slug=p_data["slug"],
                defaults={
                    "title": p_data["title"],
                    "sku": p_data["sku"],
                    "category": cat,
                    "brand": brnd,
                    "price": p_data["price"],
                    "compare_at_price": p_data["compare_at"],
                    "warranty": p_data["warranty"],
                    "is_featured": p_data["is_featured"],
                    "is_special_offer": p_data["is_special"],
                    "stock_qty": 15,
                    "short_description": f"{p_data['title']} با ضمانت اصالت فیزیکی و تحویل فوری دیجی تل.",
                    "description": f"مشخصات و ویژگی‌های اصلی این محصول شامل بهترین متریال، آخرین تکنولوژی روز و گارانتی معتبر شرکتی می‌باشد.",
                }
            )

            # Specs
            for spec_name, spec_val in p_data["specs"]:
                ProductSpecification.objects.get_or_create(
                    product=product,
                    name=spec_name,
                    defaults={"value": spec_val}
                )

        # 6. Blog Categories & Posts
        b_cat, _ = BlogCategory.objects.get_or_create(name="اخبار تکنولوژی", slug="tech-news")
        b_cat2, _ = BlogCategory.objects.get_or_create(name="راهنمای خرید", slug="buying-guides")

        Post.objects.get_or_create(
            slug="which-iphone-to-buy-guide",
            defaults={
                "title": "راهنمای جامع خرید آیفون در سال ۲۰۲۶؛ کدام مدل ارزش خرید دارد؟",
                "category": b_cat2,
                "author": admin,
                "excerpt": "بررسی تفاوت‌های نسل جدید آیفون با مدل‌های قبلی به همراه بررسی ارزش خرید و قیمت در بازار ایران.",
                "content": "با ورود مدل‌های جدید به بازار، انتخاب گوشی مناسب می‌تواند چالش‌برانگیز باشد. در این مقاله به بررسی تخصصی پردازنده، دوربین و باتری مدل‌های مختلف می‌پردازیم.",
            }
        )

        Post.objects.get_or_create(
            slug="zitro-installment-purchase-guide",
            defaults={
                "title": "راهنمای خرید اقساطی گوشی و لپ تاپ از فروشگاه دیجی تل بدون ضامن",
                "category": b_cat,
                "author": admin,
                "excerpt": "شرایط خرید اقساطی کالای دیجیتال از فروشگاه دیجی تل با همکاری سامانه‌های اعتباری و اسنپ‌پی.",
                "content": "در فروشگاه دیجی تل می‌توانید به سادگی و بدون نیاز به چک و ضامن، انواع گوشی، لپ تاپ و لوازم جانبی را به صورت اقساطی تهیه کنید.",
            }
        )

        # ۷. مشتریان و سفارشهای نمایشی (برای پر شدن گزارشات و پرونده مشتریان)
        from orders.models import Order, OrderItem
        from django.utils import timezone
        from datetime import timedelta

        demo_customers = [
            # username, first, last, phone, روزهای قبل از عضویت
            ("customer.zahra", "زهرا", "محمدی", "09121110001", 210),
            ("customer.reza", "رضا", "علوی", "09121110002", 150),
            ("customer.mina", "مینا", "کریمی", "09121110003", 95),
            ("customer.omid", "امید", "نوری", "09121110004", 20),
            ("customer.sara", "سارا", "حسینی", "09121110005", 5),
        ]
        customers = {}
        for username, first, last, phone, joined_days_ago in demo_customers:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone_number": phone,
                    "email": f"{username}@example.com",
                    "is_verified": True,
                }
            )
            if created:
                user.set_password("zitro12345")
                user.save(update_fields=["password"])
                User.objects.filter(pk=user.pk).update(
                    date_joined=timezone.now() - timedelta(days=joined_days_ago)
                )
            customers[username] = user

        # (نام کاربری، [ (روز قبل، تعداد، بخشی از عنوان محصول) …])؛ مبلغ از قیمت خود محصول محاسبه می‌شود
        demo_orders = [
            ("customer.zahra", [
                (75, 1, "iPhone"),
                (40, 2, "پاوربانک"),
                (6, 1, "واچ"),
            ]),
            ("customer.reza", [
                (60, 1, "Vivobook"),
                (12, 1, "پاوربانک"),
            ]),
            ("customer.mina", [
                (45, 1, "ساندبار"),
            ]),
            ("customer.omid", [
                (9, 1, "شارژر"),
            ]),
            ("customer.sara", [
                (2, 1, "پاوربانک"),
            ]),
        ]
        seeded_orders = 0
        for username, orders_data in demo_orders:
            user = customers[username]
            if Order.objects.filter(user=user).exists():
                continue
            for days_ago, qty, title_hint in orders_data:
                product = Product.objects.filter(title__icontains=title_hint).first()
                if product is None:
                    continue
                amount = product.price * qty
                order = Order.objects.create(
                    user=user,
                    recipient_name=f"{user.first_name} {user.last_name}",
                    recipient_phone=user.phone_number,
                    province="تهران",
                    city="تهران",
                    shipping_address="تهران، خیابان ولیعصر، پلاک ۱۲، واحد ۳",
                    postal_code="1987654321",
                    products_total=amount,
                    shipping_cost=0,
                    final_amount=amount,
                    status="delivered",
                    payment_status="successful",
                    shipping_method="post",
                    transaction_id=f"TRX-{user.username}-{days_ago}",
                )
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_title=product.title,
                    product_sku=product.sku,
                    unit_price=product.price,
                    quantity=qty,
                    total_price=amount,
                )
                # سفارش‌های نمایشی باید در روزهای گذشته ثبت شده باشند
                Order.objects.filter(pk=order.pk).update(
                    created_at=timezone.now() - timedelta(days=days_ago)
                )
                seeded_orders += 1
        self.stdout.write(self.style.SUCCESS(
            f"Demo customers ready: {len(customers)} users, {seeded_orders} new orders"
        ))

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with authentic Zitro products and categories!"))
