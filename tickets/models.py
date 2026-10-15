import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Ticket(models.Model):
    """تیکت پشتیبانی مشتری؛ گفتگوی چت‌مانند بین مشتری و پشتیبانی."""

    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_ANSWERED = 'answered'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_NEW, 'جدید'),
        (STATUS_IN_PROGRESS, 'در حال بررسی'),
        (STATUS_ANSWERED, 'پاسخ داده شده'),
        (STATUS_CLOSED, 'بسته شده'),
    ]

    CATEGORY_ORDER = 'order'
    CATEGORY_PRODUCT = 'product'
    CATEGORY_TECHNICAL = 'technical'
    CATEGORY_GUIDE = 'guide'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_ORDER, 'مرتبط با سفارش'),
        (CATEGORY_PRODUCT, 'محصول و کالا'),
        (CATEGORY_TECHNICAL, 'مشکل فنی'),
        (CATEGORY_GUIDE, 'راهنمایی و مشاوره'),
        (CATEGORY_OTHER, 'سایر'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'کم'),
        (PRIORITY_NORMAL, 'معمولی'),
        (PRIORITY_HIGH, 'مهم'),
    ]

    ticket_number = models.CharField(max_length=12, unique=True, editable=False, verbose_name="شماره تیکت")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets', verbose_name="مشتری")
    subject = models.CharField(max_length=200, verbose_name="عنوان")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER, verbose_name="دسته")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL, verbose_name="اولویت")
    order_number = models.CharField(max_length=30, blank=True, default='', verbose_name="شماره سفارش")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_NEW, verbose_name="وضعیت")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets', verbose_name="کارشناس پشتیبانی"
    )
    customer_unread = models.BooleanField(default=True, verbose_name="خوانده‌نشده برای مشتری")
    staff_unread = models.BooleanField(default=True, verbose_name="خوانده‌نشده برای پشتیبانی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    last_message_at = models.DateTimeField(default=timezone.now, verbose_name="آخرین پیام")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ بستن")

    class Meta:
        verbose_name = "تیکت"
        verbose_name_plural = "تیکت‌های پشتیبانی"
        ordering = ['-last_message_at']

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = 'TK-' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} — {self.subject}"

    @property
    def is_closed(self):
        return self.status == self.STATUS_CLOSED

    def close(self):
        self.status = self.STATUS_CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])


class TicketMessage(models.Model):
    """یک پیام در گفتگوی تیکت."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages', verbose_name="تیکت")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_messages', verbose_name="فرستنده"
    )
    sender_name = models.CharField(max_length=120, blank=True, default='', verbose_name="نام نمایشی")
    is_staff_message = models.BooleanField(default=False, verbose_name="پیام پشتیبانی")
    body = models.TextField(verbose_name="متن پیام")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ارسال")

    class Meta:
        verbose_name = "پیام تیکت"
        verbose_name_plural = "پیام‌های تیکت"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.ticket_id}: {self.body[:40]}"

    def save(self, *args, **kwargs):
        if not self.sender_name and self.sender_id:
            u = self.sender
            self.sender_name = (u.get_full_name() or u.username or '').strip()
        super().save(*args, **kwargs)
