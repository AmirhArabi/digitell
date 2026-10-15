from django.db import models


class Banner(models.Model):
    POSITION_CHOICES = [
        ('hero', 'اسلایدر بزرگ صفحه اصلی'),
        ('banner_pair', 'بنر دوقلو میانی'),
        ('banner_wide', 'بنر عریض تمام‌عرض'),
        ('sidebar', 'بنر سایدبار'),
    ]

    title = models.CharField(max_length=150, verbose_name="عنوان بنر")
    subtitle = models.CharField(max_length=250, blank=True, verbose_name="زیرعنوان / متن کمکی")
    image = models.ImageField(upload_to="banners/", verbose_name="تصویر بنر")
    link_url = models.CharField(max_length=255, default="/", verbose_name="لینک هدف")
    button_text = models.CharField(max_length=50, blank=True, verbose_name="متن دکمه (اختیاری)")
    position = models.CharField(max_length=30, choices=POSITION_CHOICES, default='hero', verbose_name="جایگاه")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "بنر و اسلایدر"
        verbose_name_plural = "بنرها و اسلایدرها"
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.title} ({self.get_position_display()})"


class SiteSetting(models.Model):
    store_name = models.CharField(max_length=100, default="فروشگاه زیترو", verbose_name="نام فروشگاه")
    slogan = models.CharField(
        max_length=200,
        default="خرید اقساطی آسان انواع کالای دیجیتال و لوازم جانبی",
        verbose_name="شعار فروشگاه"
    )
    phone = models.CharField(max_length=20, default="۰۲۱-۹۱۰۹۰۰۰۰", verbose_name="شماره تماس")
    email = models.EmailField(default="info@zitro.ir", verbose_name="ایمیل پشتیبانی")
    address = models.CharField(max_length=255, default="تهران، خیابان ولیعصر، تقاطع انقلاب", verbose_name="آدرس فروشگاه")
    working_hours = models.CharField(max_length=100, default="شنبه تا چهارشنبه ۱۰:۳۰ الی ۱۸", verbose_name="ساعات کاری")

    telegram = models.CharField(max_length=100, blank=True, default="@zitro_ir", verbose_name="تلگرام")
    instagram = models.CharField(max_length=100, blank=True, default="zitro_ir", verbose_name="اینستاگرام")
    whatsapp = models.CharField(max_length=100, blank=True, verbose_name="واتساپ")

    shipping_cost = models.BigIntegerField(default=49000, verbose_name="هزینه ارسال پیش‌فرض (تومان)")
    free_shipping_threshold = models.BigIntegerField(
        default=0,
        verbose_name="آستانه ارسال رایگان (تومان)",
        help_text="سفارش‌های بالاتر از این مبلغ ارسال رایگان دارند؛ ۰ = غیرفعال"
    )
    about_us = models.TextField(blank=True, verbose_name="درباره فروشگاه")
    footer_note = models.CharField(max_length=255, blank=True, verbose_name="متن پاورقی سایت")

    class Meta:
        verbose_name = "تنظیمات عمومی سایت"
        verbose_name_plural = "تنظیمات عمومی سایت"

    def __str__(self):
        return self.store_name

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj
