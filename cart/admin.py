from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, RecoveryCampaign, RecoveryAttempt


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'line_total', 'created_at')
    can_delete = False

    def line_total(self, obj):
        return f"{obj.line_total:,} تومان"
    line_total.short_description = "مبلغ کل قلم"


class RecoveryAttemptInline(admin.TabularInline):
    model = RecoveryAttempt
    extra = 0
    readonly_fields = ('step', 'channel', 'message_type', 'status', 'recipient_phone', 'sent_at', 'coupon', 'converted_order')
    can_delete = False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_info',
        'customer_phone_display',
        'items_count',
        'total_amount_display',
        'lifecycle_display',
        'recovery_status',
        'attempts_count_display',
        'updated_at',
    )
    list_filter = ('recovery_status', 'created_at', 'updated_at')
    search_fields = ('id', 'user__username', 'user__first_name', 'user__last_name', 'user__phone_number', 'session_key')
    readonly_fields = (
        'created_at',
        'updated_at',
        'recovery_token',
        'recovery_token_expires_at',
        'converted_order',
        'total_items',
        'formatted_total_price',
    )
    inlines = [CartItemInline, RecoveryAttemptInline]

    def customer_info(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name() or obj.user.username}"
        return f"مهمان ({obj.session_key[:8]}...)" if obj.session_key else "مهمان"
    customer_info.short_description = "مشتری"

    def customer_phone_display(self, obj):
        return obj.customer_phone or "-"
    customer_phone_display.short_description = "شماره موبایل"

    def items_count(self, obj):
        return obj.total_items
    items_count.short_description = "تعداد اقلام"

    def total_amount_display(self, obj):
        return f"{obj.formatted_total_price} تومان"
    total_amount_display.short_description = "ارزش تخمینی"

    def lifecycle_display(self, obj):
        status = obj.lifecycle_status
        badges = {
            'active': '<span style="color:green;font-weight:bold;">فعال</span>',
            'abandoned': '<span style="color:#d97706;font-weight:bold;">رهاشده</span>',
            'converted': '<span style="color:#2563eb;font-weight:bold;">تبدیل‌شده</span>',
            'empty': '<span style="color:gray;">خالی</span>',
        }
        return format_html(badges.get(status, status))
    lifecycle_display.short_description = "چرخه عمر"

    def attempts_count_display(self, obj):
        return obj.attempts_count
    attempts_count_display.short_description = "پیامک‌های ارسالی"


@admin.register(RecoveryCampaign)
class RecoveryCampaignAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'campaign_type',
        'is_active',
        'abandonment_threshold_hours',
        'discount_type',
        'discount_value',
        'created_at',
    )
    list_filter = ('is_active', 'campaign_type', 'discount_type')
    search_fields = ('name',)


@admin.register(RecoveryAttempt)
class RecoveryAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cart',
        'campaign',
        'step',
        'status',
        'recipient_phone',
        'coupon',
        'converted_order',
        'created_at',
        'sent_at',
    )
    list_filter = ('status', 'channel', 'message_type', 'created_at')
    search_fields = ('cart__id', 'recipient_phone', 'provider_message_id', 'idempotency_key')
    readonly_fields = (
        'cart',
        'campaign',
        'step',
        'channel',
        'message_type',
        'status',
        'recipient_phone',
        'message_text',
        'provider_message_id',
        'error_code',
        'error_detail',
        'skip_reason',
        'coupon',
        'converted_order',
        'converted_at',
        'idempotency_key',
        'created_at',
        'sent_at',
    )
