from django.db import models
from django.conf import settings


class SmsTemplate(models.Model):
    """الگوها و قالب‌های پیامکی برای استفاده در اعلان‌ها، پترن‌ها و ارسال‌های سریع."""

    TEMPLATE_TYPE_CHOICES = [
        ('otp', 'کد تایید هویت (OTP)'),
        ('pattern', 'الگوی خدماتی تأییدشده (پترن SMS.ir)'),
        ('text', 'متن عادی / دلخواه'),
        ('order', 'اعلان وضعیت سفارش'),
        ('cart', 'یادآوری سبد خرید رهاشده'),
        ('marketing', 'کمپین و بازاریابی'),
    ]

    title = models.CharField(max_length=150, verbose_name="عنوان الگو")
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default='pattern',
        verbose_name="نوع الگو"
    )
    template_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="شناسه الگو در SMS.ir (TemplateId)",
        help_text="برای الگوهای خدماتی اعتبارسنجی پترن SMS.ir وارد کنید"
    )
    text = models.TextField(
        verbose_name="متن الگو / پیام",
        help_text="برای الگوهای پترن متغیرها را به صورت {Code} یا {Name} مشخص کنید"
    )
    parameters_hint = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="راهنمای متغیرها",
        help_text="مثال: Code, Name, OrderId"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "الگوی پیامک"
        verbose_name_plural = "الگوهای پیامک"
        ordering = ['-created_at']

    def __str__(self):
        tid = f" (کد پترن: {self.template_id})" if self.template_id else ""
        return f"{self.title}{tid}"


class SmsLog(models.Model):
    """تاریخچه کامل پیامک‌های ارسالی با جزئیات وضعیت و پاسخ پنل."""

    STATUS_CHOICES = [
        ('sent', 'ارسال شده (موفق)'),
        ('failed', 'ناموفق / خطا'),
        ('pending', 'در حال پردازش'),
        ('simulated', 'شبیه‌سازی شده (توسعه/تست)'),
    ]

    SMS_TYPE_CHOICES = [
        ('otp', 'کد تأیید OTP'),
        ('pattern', 'ارسال با الگو (پترن)'),
        ('single', 'پیامک دلخواه به کاربر'),
        ('bulk', 'ارسال انبوه / همگانی'),
        ('campaign', 'کمپین تبلیغاتی'),
        ('cart_recovery', 'بازیابی سبد خرید'),
        ('order', 'اعلان وضعیت سفارش'),
        ('ticket', 'اعلان تیکت پشتیبانی'),
    ]

    recipient = models.CharField(max_length=20, db_index=True, verbose_name="شماره گیرنده")
    message = models.TextField(verbose_name="متن پیامک")
    sms_type = models.CharField(max_length=25, choices=SMS_TYPE_CHOICES, default='single', verbose_name="نوع پیامک")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name="وضعیت")
    template = models.ForeignKey(
        SmsTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
        verbose_name="الگوی استفاده شده"
    )
    pattern_template_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="شناسه الگو (TemplateId)")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="هزینه/تعرفه (ریال)")
    message_id = models.BigIntegerField(null=True, blank=True, verbose_name="شناسه پیام در پنل")
    pack_id = models.BigIntegerField(null=True, blank=True, verbose_name="شناسه بسته ارسال")
    response_data = models.TextField(blank=True, verbose_name="پاسخ خام پنل")
    error_message = models.TextField(blank=True, verbose_name="پیام خطا")
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_sms_logs",
        verbose_name="کاربر ارسال‌کننده"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="زمان ارسال")

    class Meta:
        verbose_name = "لاگ پیامک"
        verbose_name_plural = "تاریخچه و لاگ‌های پیامک"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient} - {self.get_sms_type_display()} ({self.get_status_display()})"


class SmsCampaign(models.Model):
    """کمپین‌های پیامکی برای ارسال‌های انبوه و بازاریابی."""

    AUDIENCE_CHOICES = [
        ('all', 'تمام کاربران ثبت‌نام شده'),
        ('marketing', 'مشترکین خبرنامه پیامکی'),
        ('buyers', 'مشتریان دارای حداقل یک سفارش موفق'),
        ('abandoned_carts', 'کاربران دارای سبد خرید رهاشده'),
        ('custom', 'لیست شماره‌های دستی / سفارشی'),
    ]

    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('sent', 'ارسال شده'),
        ('failed', 'ناموفق'),
    ]

    title = models.CharField(max_length=200, verbose_name="عنوان کمپین")
    audience = models.CharField(max_length=30, choices=AUDIENCE_CHOICES, default='all', verbose_name="مخاطبان هدف")
    message = models.TextField(verbose_name="متن پیام کمپین")
    template = models.ForeignKey(
        SmsTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
        verbose_name="قالب پیامک"
    )
    total_recipients = models.PositiveIntegerField(default=0, verbose_name="تعداد گیرندگان")
    successful_count = models.PositiveIntegerField(default=0, verbose_name="تعداد موفق")
    failed_count = models.PositiveIntegerField(default=0, verbose_name="تعداد ناموفق")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="ایجادکننده"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "کمپین پیامکی"
        verbose_name_plural = "کمپین‌های پیامکی"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.total_recipients} گیرنده)"
