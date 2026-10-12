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
