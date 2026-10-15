import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from products.models import Product


class Coupon(models.Model):
    """کد تخفیف قابل اعمال در فرآیند خرید."""

    TYPE_CHOICES = [
        ('percent', 'درصدی'),
        ('amount', 'مبلغ ثابت (تومان)'),
    ]

    code = models.CharField(max_length=30, unique=True, verbose_name="کد تخفیف")
    title = models.CharField(max_length=120, blank=True, verbose_name="عنوان کمپین")
    discount_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='percent', verbose_name="نوع تخفیف")
    value = models.BigIntegerField(validators=[MinValueValidator(1)], verbose_name="مقدار تخفیف")
    min_order_amount = models.BigIntegerField(default=0, verbose_name="حداقل مبلغ سفارش (تومان)")
    max_discount_amount = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="سقف تخفیف (تومان)",
        help_text="فقط برای تخفیف درصدی؛ خالی = بدون سقف"
    )
    max_uses = models.PositiveIntegerField(default=0, verbose_name="سقف تعداد استفاده", help_text="۰ = بدون محدودیت")
    used_count = models.PositiveIntegerField(default=0, verbose_name="تعداد استفاده شده")
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name="شروع اعتبار")
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name="پایان اعتبار")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "کد تخفیف"
        verbose_name_plural = "کدهای تخفیف"
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.now())

    @property
    def usage_left(self):
        if not self.max_uses:
            return None
        return max(self.max_uses - self.used_count, 0)

    def validate_for(self, amount):
        """(مجاز بودن، پیام خطا، مبلغ تخفیف) را برمی‌گرداند."""
        now = timezone.now()
        if not self.is_active:
            return False, "این کد تخفیف غیرفعال است.", 0
        if self.valid_from and self.valid_from > now:
            return False, "زمان استفاده از این کد تخفیف فرا نرسیده است.", 0
        if self.valid_until and self.valid_until < now:
            return False, "مهلت استفاده از این کد تخفیف به پایان رسیده است.", 0
        if self.max_uses and self.used_count >= self.max_uses:
            return False, "ظرفیت استفاده از این کد تخفیف تکمیل شده است.", 0
        if amount < self.min_order_amount:
            return False, f"حداقل مبلغ سفارش برای این کد {self.min_order_amount:,} تومان است.", 0

        if self.discount_type == 'percent':
            discount = (amount * self.value) // 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.value

        discount = min(discount, amount)
        return True, "", int(discount)


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده و در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mock_gateway', 'پرداخت آنلاین (درگاه آزمایشی)'),
        ('cod', 'پرداخت درب منزل'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('successful', 'پرداخت موفق'),
        ('failed', 'پرداخت ناموفق'),
    ]

    SHIPPING_CHOICES = [
        ('post', 'پست پیشتاز'),
        ('tipax', 'تیپاکس'),
        ('courier', 'پیک درون‌شهری'),
        ('pickup', 'تحویل حضوری در فروشگاه'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False, verbose_name="شماره سفارش")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="کاربر"
    )

    # Shipping details
    recipient_name = models.CharField(max_length=100, verbose_name="نام تحویل‌گیرنده")
    recipient_phone = models.CharField(max_length=15, verbose_name="شماره تماس")
    province = models.CharField(max_length=50, verbose_name="استان")
    city = models.CharField(max_length=50, verbose_name="شهر")
    shipping_address = models.TextField(verbose_name="آدرس پستی")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")

    # Financials (Toman)
    products_total = models.BigIntegerField(default=0, verbose_name="جمع مبالغ کالاها")
    discount_amount = models.BigIntegerField(default=0, verbose_name="سود و تخفیف مشتری")
    shipping_cost = models.BigIntegerField(default=49000, verbose_name="هزینه ارسال")
    final_amount = models.BigIntegerField(default=0, verbose_name="مبلغ نهایی قابل پرداخت")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت سفارش")
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='mock_gateway',
        verbose_name="روش پرداخت"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت پرداخت"
    )
    transaction_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="کد پیگیری تراکنش")

    # Discounts & shipping extras
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="کد تخفیف"
    )
    coupon_code = models.CharField(max_length=30, blank=True, verbose_name="کد تخفیف استفاده‌شده")
    coupon_discount = models.BigIntegerField(default=0, verbose_name="تخفیف کد تخفیف")
    shipping_method = models.CharField(
        max_length=20,
        choices=SHIPPING_CHOICES,
        default='post',
        verbose_name="روش ارسال"
    )
    tracking_code = models.CharField(max_length=50, blank=True, verbose_name="کد رهگیری مرسوله")

    notes = models.TextField(blank=True, verbose_name="یادداشت مشتری")
    admin_note = models.TextField(blank=True, verbose_name="یادداشت داخلی پنل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت سفارش")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"سفارش {self.order_number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate readable order number e.g. ZT-20261011-4821
            short_uuid = uuid.uuid4().hex[:6].upper()
            self.order_number = f"ZT-{short_uuid}"
        super().save(*args, **kwargs)

    @property
    def formatted_final_amount(self):
        return f"{self.final_amount:,}"

    @property
    def formatted_products_total(self):
        return f"{self.products_total:,}"

    @property
    def formatted_shipping_cost(self):
        return f"{self.shipping_cost:,}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="سفارش"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="محصول"
    )
    product_title = models.CharField(max_length=255, verbose_name="عنوان محصول در زمان خرید")
    product_sku = models.CharField(max_length=50, blank=True, verbose_name="کد کالا")
    unit_price = models.BigIntegerField(verbose_name="قیمت واحد (تومان)")
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    total_price = models.BigIntegerField(verbose_name="مبلغ کل (تومان)")

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"

    def __str__(self):
        return f"{self.quantity} x {self.product_title}"

    @property
    def formatted_unit_price(self):
        return f"{self.unit_price:,}"

    @property
    def formatted_total_price(self):
        return f"{self.total_price:,}"
