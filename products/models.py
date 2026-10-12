from django.db import models
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
        # Calculate discount percentage automatically if compare_at_price is higher
        if self.compare_at_price and self.compare_at_price > self.price:
            diff = self.compare_at_price - self.price
            self.discount_pct = round((diff / self.compare_at_price) * 100)
        else:
            self.discount_pct = 0

        self.is_available = self.stock_qty > 0
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        first_img = self.images.filter(is_primary=True).first()
        if not first_img:
            first_img = self.images.first()
        return first_img

    @property
    def formatted_price(self):
        return f"{self.price:,}"

    @property
    def formatted_compare_price(self):
        if self.compare_at_price:
            return f"{self.compare_at_price:,}"
        return None

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'pk': self.pk, 'slug': self.slug})


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
