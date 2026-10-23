from django.conf import settings
from django.db import models
from django.urls import reverse


class BlogCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="عنوان دسته‌بندی")
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "دسته‌بندی مقاله"
        verbose_name_plural = "دسته‌بندی‌های مقالات"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان مقاله")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="دسته‌بندی"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_posts",
        verbose_name="نویسنده"
    )
    cover_image = models.ImageField(upload_to="blog/%Y/%m/", null=True, blank=True, verbose_name="تصویر شاخص")
    excerpt = models.TextField(blank=True, verbose_name="چکیده")
    content = models.TextField(verbose_name="متن کامل مقاله")
    is_published = models.BooleanField(default=True, verbose_name="منتشر شده")
    views_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")

    related_products = models.ManyToManyField(
        'products.Product',
        blank=True,
        related_name="blog_posts",
        verbose_name="محصولات مرتبط با مقاله"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ نگارش")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ ویرایش")

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    @property
    def reading_time(self):
        """تخمین زمان مطالعه بر اساس تعداد کلمات متن (حدود ۲۰۰ کلمه در دقیقه)."""
        words = len((self.content or "").split())
        minutes = max(1, round(words / 200))
        return f"{minutes} دقیقه"

    @property
    def persian_date(self):
        """نمایش تاریخ به صورت شمسی (مثلاً: ۲۴ مهر ۱۴۰۵)."""
        if not self.created_at:
            return ""
        try:
            import jdatetime
            jd = jdatetime.datetime.fromgregorian(datetime=self.created_at)
            months = [
                "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
            ]
            return f"{jd.day} {months[jd.month - 1]} {jd.year}"
        except Exception:
            return self.created_at.strftime("%Y/%m/%d")

    @property
    def comments_count(self):
        return self.comments.filter(is_approved=True).count()


class BlogComment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="مقاله"
    )
    author_name = models.CharField(max_length=100, verbose_name="نام و نام خانوادگی")
    author_email = models.EmailField(verbose_name="نشانی ایمیل")
    website = models.URLField(blank=True, verbose_name="وب‌سایت")
    content = models.TextField(verbose_name="متن دیدگاه")
    is_approved = models.BooleanField(default=True, verbose_name="تأیید شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "دیدگاه مقاله"
        verbose_name_plural = "دیدگاه‌های مقالات"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author_name} - {self.post.title}"

    @property
    def persian_date(self):
        if not self.created_at:
            return ""
        try:
            import jdatetime
            jd = jdatetime.datetime.fromgregorian(datetime=self.created_at)
            months = [
                "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
            ]
            return f"{jd.day} {months[jd.month - 1]} {jd.year}"
        except Exception:
            return self.created_at.strftime("%Y/%m/%d")
