from django.conf import settings
from django.db import models
from products.models import Product


class Cart(models.Model):
    session_key = models.CharField(max_length=40, unique=True, null=True, blank=True, verbose_name="کلید سشن")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
        verbose_name="کاربر"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    RECOVERY_CHOICES = [
        ('none', 'پیگیری نشده'),
        ('scheduled', 'برنامه‌ریزی شده'),
        ('contacted', 'در حال پیگیری'),
        ('recovered', 'بازیابی شده'),
        ('failed', 'ناموفق'),
        ('excluded', 'مستثنا / انصراف'),
    ]

    recovery_status = models.CharField(
        max_length=20,
        choices=RECOVERY_CHOICES,
        default='none',
        verbose_name="وضعیت بازیابی"
    )
    recovery_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="توکن بازیابی"
    )
    recovery_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="انقضای توکن بازیابی"
    )
    converted_order = models.ForeignKey(
        'orders.Order',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovered_carts",
        verbose_name="سفارش نهایی تبدیل‌شده"
    )
    admin_note = models.TextField(
        blank=True,
        verbose_name="یادداشت داخلی مدیر"
    )

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self):
        if self.user:
            return f"سبد خرید {self.user}"
        return f"سبد خرید مهمان ({self.session_key})"

    @property
    def is_empty(self):
        return not self.items.exists()

    @property
    def lifecycle_status(self):
        if self.converted_order_id:
            return 'converted'
        if self.is_empty:
            return 'empty'
        from django.utils import timezone
        from datetime import timedelta
        # Default 24 hours for abandoned
        if timezone.now() - self.updated_at >= timedelta(hours=24):
            return 'abandoned'
        return 'active'

    @property
    def lifecycle_status_display(self):
        mapping = {
            'active': 'فعال',
            'abandoned': 'رهاشده',
            'converted': 'تبدیل‌شده به سفارش',
            'empty': 'خالی',
        }
        return mapping.get(self.lifecycle_status, 'نامشخص')

    @property
    def customer_phone(self):
        if self.user and hasattr(self.user, 'phone_number') and self.user.phone_number:
            return self.user.phone_number
        return None

    @property
    def customer_display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username or self.user.phone_number
        return "کاربر مهمان"

    @property
    def attempts_count(self):
        return self.recovery_attempts.count()

    @property
    def last_attempt(self):
        return self.recovery_attempts.order_by('-created_at').first()

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_compare_price(self):
        return sum(item.line_compare_total for item in self.items.all())

    @property
    def total_discount(self):
        diff = self.total_compare_price - self.total_price
        return max(diff, 0)

    @property
    def formatted_total_price(self):
        return f"{self.total_price:,}"

    @property
    def formatted_total_discount(self):
        return f"{self.total_discount:,}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="سبد خرید"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="محصول"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ افزودن")

    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم‌های سبد خرید"
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} عدد {self.product.title}"

    @property
    def line_total(self):
        return self.quantity * self.product.price

    @property
    def line_compare_total(self):
        orig_price = self.product.compare_at_price if self.product.compare_at_price else self.product.price
        return self.quantity * orig_price

    @property
    def formatted_line_total(self):
        return f"{self.line_total:,}"


class RecoveryCampaign(models.Model):
    CAMPAIGN_TYPE_CHOICES = [
        ('reminder', 'یادآوری بدون تخفیف'),
        ('discount', 'پیشنهاد کد تخفیف'),
    ]

    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'درصدی'),
        ('amount', 'مبلغ ثابت (تومان)'),
    ]

    name = models.CharField(max_length=120, verbose_name="نام کمپین")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    campaign_type = models.CharField(
        max_length=20,
        choices=CAMPAIGN_TYPE_CHOICES,
        default='reminder',
        verbose_name="نوع کمپین"
    )
    abandonment_threshold_hours = models.PositiveIntegerField(
        default=24,
        verbose_name="آستانه رهاشدگی (ساعت)",
        help_text="حداقل ساعت عدم فعالیت برای رهاشده تلقی شدن سبد"
    )
    step1_delay_hours = models.PositiveIntegerField(
        default=24,
        verbose_name="تأخیر پیام مرحله ۱ (ساعت)",
        help_text="تأخیر پس از رهاشدگی برای ارسال پیامک یادآوری"
    )
    step2_delay_hours = models.PositiveIntegerField(
        default=48,
        verbose_name="تأخیر پیام مرحله ۲ (ساعت)",
        help_text="تأخیر پس از مرحله ۱ برای ارسال پیشنهاد تخفیف"
    )
    message_template_step1 = models.TextField(
        blank=True,
        default="سلام {name} عزیز، اقلام منتظر شما در سبد خرید دیجی تل محفوظ است: {cart_url}",
        verbose_name="قالب پیام مرحله ۱ (یادآوری)"
    )
    message_template_step2 = models.TextField(
        blank=True,
        default="سلام {name} عزیز، برای تکمیل خرید شما کد تخفیف {coupon_code} با {discount_desc} در نظر گرفته شد: {cart_url}",
        verbose_name="قالب پیام مرحله ۲ (تخفیف)"
    )
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent',
        verbose_name="نوع تخفیف اختصاصی"
    )
    discount_value = models.PositiveIntegerField(
        default=10,
        verbose_name="مقدار تخفیف (درصد یا تومان)"
    )
    discount_max_amount = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر سقف تخفیف (تومان)",
        help_text="برای تخفیف درصدی؛ خالی = بدون سقف"
    )
    discount_min_order = models.BigIntegerField(
        default=0,
        verbose_name="حداقل مبلغ سبد برای اعمال تخفیف (تومان)"
    )
    discount_validity_hours = models.PositiveIntegerField(
        default=48,
        verbose_name="مدت اعتبار کوپن تخفیف (ساعت)"
    )
    max_attempts_per_cart = models.PositiveIntegerField(
        default=2,
        verbose_name="حداکثر دفعات پیامک برای هر سبد"
    )
    min_cart_value = models.BigIntegerField(
        default=0,
        verbose_name="حداقل ارزش سبد برای ورود به کمپین (تومان)"
    )
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name="شروع اعتبار کمپین")
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name="پایان اعتبار کمپین")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="ایجادکننده"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "کمپین بازیابی سبد"
        verbose_name_plural = "کمپین‌های بازیابی سبد"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_currently_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        return True


class RecoveryAttempt(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('sent', 'ارسال شده'),
        ('delivered', 'تحویل شده'),
        ('failed', 'ناموفق'),
        ('skipped', 'رد شده / بدون صلاحیت'),
        ('cancelled', 'لغو شده'),
    ]

    MESSAGE_TYPE_CHOICES = [
        ('reminder', 'یادآوری بدون تخفیف'),
        ('discount', 'پیشنهاد کد تخفیف'),
        ('custom', 'پیام سفارشی اپراتور'),
    ]

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="recovery_attempts",
        verbose_name="سبد خرید"
    )
    campaign = models.ForeignKey(
        RecoveryCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
        verbose_name="کمپین"
    )
    step = models.PositiveIntegerField(default=1, verbose_name="شماره گام/مرحله")
    channel = models.CharField(max_length=20, default='sms', verbose_name="کانال ارتباطی")
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='reminder',
        verbose_name="نوع پیام"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت"
    )
    recipient_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره موبایل گیرنده")
    message_text = models.TextField(blank=True, verbose_name="متن پیامک")
    provider_message_id = models.CharField(max_length=100, blank=True, verbose_name="شناسه درگاه پیامک")
    error_code = models.CharField(max_length=50, blank=True, verbose_name="کد خطا")
    error_detail = models.TextField(blank=True, verbose_name="جزئیات خطا")
    skip_reason = models.CharField(max_length=255, blank=True, verbose_name="دلیل رد یا صرف‌نظر")

    coupon = models.ForeignKey(
        'orders.Coupon',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_attempts",
        verbose_name="کد تخفیف ارائه‌شده"
    )
    converted_order = models.ForeignKey(
        'orders.Order',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_attempts",
        verbose_name="سفارش منتسب"
    )
    converted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ ثبت سفارش منتسب")
    idempotency_key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="کلید یکتایی (Idempotency)"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ ارسال")

    class Meta:
        verbose_name = "تلاش بازیابی سبد"
        verbose_name_plural = "تلاش‌های بازیابی سبد"
        ordering = ['-created_at']

    def __str__(self):
        return f"تلاش {self.id} برای سبد {self.cart_id} - گام {self.step} ({self.get_status_display()})"

