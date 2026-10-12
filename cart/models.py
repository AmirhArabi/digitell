from django.conf import settings
from django.db import models
from products.models import Product


class Cart(models.Model):
    session_key = models.CharField(max_length=40, unique=True, null=True, blank=True, verbose_name="کلید سشن")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
        verbose_name="کاربر"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self):
        if self.user:
            return f"سبد خرید {self.user}"
        return f"سبد خرید مهمان ({self.session_key})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_compare_price(self):
        return sum(item.line_compare_total for item in self.items.all())

    @property
    def total_discount(self):
        diff = self.total_compare_price - self.total_price
        return max(diff, 0)

    @property
    def formatted_total_price(self):
        return f"{self.total_price:,}"

    @property
    def formatted_total_discount(self):
        return f"{self.total_discount:,}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="سبد خرید"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="محصول"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ افزودن")

    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم‌های سبد خرید"
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} عدد {self.product.title}"

    @property
    def line_total(self):
        return self.quantity * self.product.price

    @property
    def line_compare_total(self):
        orig_price = self.product.compare_at_price if self.product.compare_at_price else self.product.price
        return self.quantity * orig_price

    @property
    def formatted_line_total(self):
        return f"{self.line_total:,}"
