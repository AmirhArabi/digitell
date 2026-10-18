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

    # فیلدهای تکمیلی و بازاریابی
    national_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="کد ملی"
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ تولد"
    )
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'مرد'),
            ('female', 'زن'),
            ('other', 'سایر / تمایلی به اعلام ندارم'),
        ],
        blank=True,
        default="",
        verbose_name="جنسیت"
    )
    job_title = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="شغل یا زمینه فعالیت"
    )
    sheba_number = models.CharField(
        max_length=26,
        blank=True,
        default="",
        verbose_name="شماره شبا (IBAN)"
    )
    card_number = models.CharField(
        max_length=19,
        blank=True,
        default="",
        verbose_name="شماره کارت بانکی"
    )
    sms_marketing_subscribed = models.BooleanField(
        default=True,
        verbose_name="عضویت در باشگاه پیامکی و دریافت تخفیف‌ها"
    )
    email_marketing_subscribed = models.BooleanField(
        default=False,
        verbose_name="دریافت خبرنامه و تخفیف‌های ایمیلی"
    )

    @property
    def jalali_birth_date(self):
        """نمایش تاریخ تولد به صورت رشته شمسی."""
        if not self.birth_date:
            return ""
        try:
            import jdatetime
            jd = jdatetime.date.fromgregorian(date=self.birth_date)
            return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
        except Exception:
            return self.birth_date.strftime("%Y/%m/%d")

    @property
    def is_profile_complete(self):
        """آیا فیلدهای اساسی پروفایل تکمیل شده است؟"""
        return bool(
            self.first_name and self.last_name and
            self.national_code and self.birth_date
        )

    @property
    def profile_completion_percentage(self):
        """محاسبه درصد تکمیل پروفایل کاربر."""
        fields = [
            bool(self.first_name and self.last_name),
            bool(self.phone_number),
            bool(self.email),
            bool(self.national_code),
            bool(self.birth_date),
            bool(self.gender),
            bool(self.job_title),
            bool(self.sheba_number or self.card_number),
        ]
        completed = sum(1 for f in fields if f)
        return int((completed / len(fields)) * 100)

    @property
    def missing_fields_list(self):
        """فهرست عناوین فیلدهای ناقص کاربر جهت نمایش هشدار تکمیل پروفایل."""
        missing = []
        if not (self.first_name and self.last_name):
            missing.append("نام و نام خانوادگی")
        if not self.national_code:
            missing.append("کد ملی")
        if not self.birth_date:
            missing.append("تاریخ تولد")
        if not self.email:
            missing.append("ایمیل")
        if not (self.sheba_number or self.card_number):
            missing.append("شماره شبا یا کارت")
        return missing

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


