from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        verbose_name="شماره موبایل"
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        verbose_name="تصویر پروفایل"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="تأیید هویت"
    )

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username or self.phone_number or f"User #{self.id}"


class Address(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="کاربر"
    )
    title = models.CharField(max_length=50, default="خانه", verbose_name="عنوان آدرس")
    recipient_name = models.CharField(max_length=100, verbose_name="نام تحویل‌گیرنده")
    recipient_phone = models.CharField(max_length=15, verbose_name="تلفن تماس")
    province = models.CharField(max_length=50, verbose_name="استان")
    city = models.CharField(max_length=50, verbose_name="شهر")
    postal_address = models.TextField(verbose_name="آدرس پستی")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"

    def __str__(self):
        return f"{self.title}: {self.city} - {self.postal_address[:30]}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="کاربر"
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="محصول"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.product}"


class OTPCode(models.Model):
    phone_number = models.CharField(max_length=15, db_index=True, verbose_name="شماره موبایل")
    code = models.CharField(max_length=6, verbose_name="کد تأیید")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    expires_at = models.DateTimeField(verbose_name="زمان انقضا")
    is_used = models.BooleanField(default=False, verbose_name="استفاده شده")

    class Meta:
        verbose_name = "کد تأیید یکبار مصرف (OTP)"
        verbose_name_plural = "کدهای تأیید یکبار مصرف (OTP)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number}: {self.code}"

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() <= self.expires_at


