from django.conf import settings
from django.db import models, transaction
from django.db.models import Avg, BooleanField, Case, F, Value, When
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    name_en = models.CharField(max_length=100, blank=True, verbose_name="نام انگلیسی")
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="دسته‌بندی والد"
    )
    icon_svg = models.TextField(blank=True, verbose_name="کد SVG آیکون")
    image = models.ImageField(upload_to="categories/", null=True, blank=True, verbose_name="تصویر دسته‌بندی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_absolute_url(self):
        return reverse('products:category_detail', kwargs={'slug': self.slug})


class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام برند")
    name_en = models.CharField(max_length=100, blank=True, verbose_name="نام انگلیسی")
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    logo = models.ImageField(upload_to="brands/", null=True, blank=True, verbose_name="لوگو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def logo_url(self):
        if self.logo:
            return self.logo.url
        return "/static/img/brands/default-brand.svg"



class CategoryAttribute(models.Model):
    """ویژگی قابل استفاده برای محصولات یک دسته (مثلاً «حافظه داخلی» برای دسته موبایل)."""

    TYPE_CHOICES = [
        ('text', 'متن آزاد'),
        ('number', 'عدد'),
        ('select', 'انتخابی از بین گزینه‌ها'),
        ('boolean', 'بله / خیر'),
    ]

    name = models.CharField(max_length=100, verbose_name="نام ویژگی")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attributes",
        verbose_name="دسته‌بندی"
    )
    unit = models.CharField(max_length=30, blank=True, verbose_name="واحد (اختیاری)")
    type = models.CharField(max_length=15, choices=TYPE_CHOICES, default='text', verbose_name="نوع مقدار")
    options = models.TextField(
        blank=True,
        verbose_name="گزینه‌ها",
        help_text="برای نوع انتخابی، هر گزینه را در یک خط جدید بنویسید."
    )
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "ویژگی‌ها و مشخصات"
        ordering = ['category__name', 'order', 'name']

    def __str__(self):
        scope = self.category.name if self.category else "عمومی"
        return f"{self.name} ({scope})"

    @property
    def options_list(self):
        return [line.strip() for line in self.options.splitlines() if line.strip()]


class Product(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان محصول")
    title_en = models.CharField(max_length=255, blank=True, verbose_name="عنوان انگلیسی")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    sku = models.CharField(max_length=50, unique=True, verbose_name="کد محصول (SKU)")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="دسته‌بندی"
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="برند"
    )
    short_description = models.TextField(blank=True, verbose_name="توضیحات کوتاه")
    description = models.TextField(blank=True, verbose_name="توضیحات کامل")

    # Prices in Toman
    price = models.BigIntegerField(verbose_name="قیمت فروش (تومان)")
    compare_at_price = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="قیمت اصلی قبل از تخفیف (تومان)"
    )
    discount_pct = models.PositiveIntegerField(default=0, verbose_name="درصد تخفیف")

    stock_qty = models.PositiveIntegerField(default=10, verbose_name="موجودی انبار")
    reserved_qty = models.PositiveIntegerField(
        default=0,
        verbose_name="موجودی رزروشده",
        help_text="تعداد رزروشده برای سفارش‌های در انتظار پرداخت"
    )
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name="حد هشدار کسری موجودی")
    is_available = models.BooleanField(default=True, verbose_name="موجود در انبار")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_featured = models.BooleanField(default=False, verbose_name="محصول ویژه (صفحه اصلی)")
    is_special_offer = models.BooleanField(default=False, verbose_name="پیشنهاد شگفت‌انگیز")

    warranty = models.CharField(max_length=100, default="۱۸ ماه گارانتی شرکتی", verbose_name="گارانتی")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5, verbose_name="امتیاز")
    views_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Generate slug from title if not set
        if not self.slug:
            self.slug = slugify(self.title)
            # slugify only transliterates ASCII; fall back to a unique ASCII-based slug
            if not self.slug:
                self.slug = f"product-{self.pk}" if self.pk else "unnamed-product"
                counter = 1
                while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                    counter += 1
                    self.slug = f"product-{self.pk}-{counter}" if self.pk else f"unnamed-product-{counter}"

        # Calculate discount percentage automatically if compare_at_price is higher
        if self.compare_at_price and self.compare_at_price > self.price:
            diff = self.compare_at_price - self.price
            self.discount_pct = round((diff / self.compare_at_price) * 100)
        else:
            self.discount_pct = 0

        self.is_available = self.available_qty > 0
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # رزرو اتمیک موجودی
    #
    # همهٔ به‌روزرسانی‌ها با یک شرط روی مقدار فعلی ردیف انجام می‌شود تا دو سفارش
    # هم‌زمان نتوانند یک واحد آخر را بفروشند (جلوگیری از فروش بیش از موجودی).
    # ------------------------------------------------------------------
    def _sync_availability(self):
        """هم‌گام‌سازی پرچم is_available با موجودی قابل فروش (تک‌عبارتی و بدون شرط مسابقه)."""
        Product.objects.filter(pk=self.pk).update(
            is_available=Case(
                When(stock_qty__gt=F('reserved_qty'), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    def reserve_stock(self, quantity):
        """رزرو موجودی برای یک سفارش پرداخت‌نشده؛ اگر موجودی آزاد کافی نباشد False."""
        quantity = int(quantity)
        if quantity <= 0:
            return False
        with transaction.atomic():
            updated = Product.objects.filter(
                pk=self.pk,
                stock_qty__gte=F('reserved_qty') + quantity,
            ).update(reserved_qty=F('reserved_qty') + quantity)
            if not updated:
                return False
            self._sync_availability()
        self.refresh_from_db(fields=['reserved_qty', 'is_available'])
        return True

    def release_stock(self, quantity):
        """آزادسازی موجودی رزروشده (لغو یا ناموفق بودن پرداخت)."""
        quantity = int(quantity)
        if quantity <= 0:
            return False
        with transaction.atomic():
            updated = Product.objects.filter(
                pk=self.pk,
                reserved_qty__gte=quantity,
            ).update(reserved_qty=F('reserved_qty') - quantity)
            if not updated:
                return False
            self._sync_availability()
        self.refresh_from_db(fields=['reserved_qty', 'is_available'])
        return True

    def commit_stock(self, quantity):
        """تبدیل رزرو به خروج قطعی کالا از انبار (پرداخت موفق یا پرداخت درب منزل)."""
        quantity = int(quantity)
        if quantity <= 0:
            return False
        with transaction.atomic():
            updated = Product.objects.filter(
                pk=self.pk,
                reserved_qty__gte=quantity,
            ).update(
                stock_qty=F('stock_qty') - quantity,
                reserved_qty=F('reserved_qty') - quantity,
            )
            if not updated:
                return False
            self._sync_availability()
        self.refresh_from_db(fields=['stock_qty', 'reserved_qty', 'is_available'])
        return True

    def restock(self, quantity):
        """بازگشت کالای فروش‌رفته به انبار (لغو سفارش پرداخت‌شده)."""
        quantity = int(quantity)
        if quantity <= 0:
            return False
        with transaction.atomic():
            updated = Product.objects.filter(pk=self.pk).update(stock_qty=F('stock_qty') + quantity)
            if not updated:
                return False
            self._sync_availability()
        self.refresh_from_db(fields=['stock_qty', 'is_available'])
        return True

    @property
    def available_qty(self):
        """موجودی قابل فروش = موجودی انبار منهای واحدهای رزروشده."""
        return max(self.stock_qty - self.reserved_qty, 0)

    @property
    def is_in_stock(self):
        return self.available_qty > 0

    @property
    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)

    @property
    def review_count(self):
        """تعداد نظرهای تأییدشده (برای نمایش «تعداد نظرات»)."""
        return self.approved_reviews.count()

    @property
    def review_average(self):
        """میانگین امتیاز نظرهای تأییدشده؛ در نبود نظر، همان rating پیش‌فرض."""
        average = self.approved_reviews.aggregate(value=Avg('rating'))['value']
        if average is None:
            return round(float(self.rating or 0), 1)
        return round(float(average), 1)

    @property
    def primary_image(self):
        first_img = self.images.filter(is_primary=True).first()
        if not first_img:
            first_img = self.images.first()
        return first_img

    @property
    def is_low_stock(self):
        return self.available_qty <= self.low_stock_threshold

    @property
    def formatted_price(self):
        return f"{self.price:,}"

    @property
    def formatted_compare_price(self):
        if self.compare_at_price:
            return f"{self.compare_at_price:,}"
        return None

    @property
    def insurance_fee(self):
        """مبلغ بیمه کالا بر مبنای ۲.۳ درصد از قیمت فروش محصول (گردشده به تومان)."""
        return round(self.price * 0.023)

    @property
    def formatted_insurance_fee(self):
        return f"{self.insurance_fee:,}"

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'pk': self.pk, 'slug': self.slug})


class ProductReview(models.Model):
    """نظر و امتیاز کاربران روی یک محصول.

    امتیاز نمایشی محصول از میانگین نظرهای تأییدشده محاسبه می‌شود؛ فیلد
    ``Product.rating`` تنها مقدار پیش‌فرض/دستی است و وقتی نظری ثبت نشده باشد
    به کار می‌رود.
    """

    RATING_CHOICES = [(value, str(value)) for value in range(1, 6)]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="محصول"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_reviews",
        verbose_name="کاربر"
    )
    author_name = models.CharField(max_length=120, verbose_name="نام نمایشی")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name="امتیاز")
    title = models.CharField(max_length=150, blank=True, verbose_name="عنوان نظر")
    body = models.TextField(verbose_name="متن نظر")
    is_approved = models.BooleanField(default=True, verbose_name="تأییدشده")
    is_verified_purchase = models.BooleanField(default=False, verbose_name="خریدار محصول")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ ویرایش")

    class Meta:
        verbose_name = "نظر محصول"
        verbose_name_plural = "نظرات محصولات"
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_review_per_product_per_user',
            )
        ]

    def __str__(self):
        return f"{self.product.title} — {self.rating}/5"

    @property
    def star_range(self):
        """۱ تا امتیاز ثبت‌شده (برای رندر ستاره‌ها در قالب)."""
        return range(self.rating)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="محصول"
    )
    image = models.ImageField(upload_to="products/%Y/%m/", verbose_name="تصویر")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="متن جایگزین (Alt)")
    is_primary = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصولات"
        ordering = ['order', 'id']

    def __str__(self):
        return f"تصویر {self.product.title}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specifications",
        verbose_name="محصول"
    )
    name = models.CharField(max_length=100, verbose_name="عنوان مشخصه")
    value = models.CharField(max_length=255, verbose_name="مقدار")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "مشخصه فنی"
        verbose_name_plural = "مشخصات فنی"
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.name}: {self.value}"
