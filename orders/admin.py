from django.contrib import admin
from .models import Order, OrderItem, Coupon


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_title', 'product_sku', 'unit_price', 'quantity', 'total_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'recipient_name', 'recipient_phone', 'status', 'payment_status', 'final_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'shipping_method', 'created_at')
    search_fields = ('order_number', 'recipient_name', 'recipient_phone', 'tracking_code')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'for_user', 'source', 'max_uses', 'used_count', 'is_active', 'valid_until')
    list_filter = ('discount_type', 'is_active', 'source', 'created_at')
    search_fields = ('code', 'title', 'for_user__username', 'for_user__phone_number')
