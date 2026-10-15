"""تست‌های رزرو موجودی و جلوگیری از فروش بیش از موجودی.

سناریوی اصلی: دو مشتری هم‌زمان آخرین واحد یک کالا را می‌خواهند؛ فقط یکی از آن‌ها
باید بتواند سفارش ثبت کند و موجودی هرگز منفی یا بیش‌فروش نشود.
"""
import json

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from cart.models import Cart, CartItem
from orders.models import Coupon, InsufficientStockError, Order, OrderItem
from products.models import Brand, Category, Product

CHECKOUT_DATA = {
    'recipient_name': 'مریم رضایی',
    'recipient_phone': '09121234567',
    'province': 'تهران',
    'city': 'تهران',
    'shipping_address': 'خیابان ولیعصر، پلاک ۱',
    'postal_code': '1234567890',
}


class StockReservationBase(TestCase):
    """پایهٔ مشترک: یک کالا با ۳ عدد موجودی و ابزارهای سبد/تسویه."""

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='هدفون و هندزفری', slug='headphones')
        self.brand = Brand.objects.create(name='تی سی اچ', slug='tch')
        self.product = Product.objects.create(
            title='هندزفری بی‌سیم TCH مدل Blade L10',
            slug='tch-blade-l10',
            sku='TCH-L10',
            category=self.category,
            brand=self.brand,
            price=1_899_000,
            compare_at_price=3_200_000,
            stock_qty=3,
            low_stock_threshold=1,
        )

    # ------------------------------------------------------------------
    # ابزارهای کمکی
    # ------------------------------------------------------------------
    def add_to_cart(self, quantity=1, product=None):
        product = product or self.product
        return self.client.post(
            reverse('cart:cart_add', kwargs={'product_id': product.pk}),
            {'quantity': quantity},
        )

    def add_to_cart_htmx(self, quantity=1, product=None):
        product = product or self.product
        return self.client.post(
            reverse('cart:cart_add', kwargs={'product_id': product.pk}),
            {'quantity': quantity},
            HTTP_HX_REQUEST='true',
        )

    def force_cart_item(self, product, quantity):
        """افزودن مستقیم به سبد (شبیه‌سازی سبد قدیمی که کالایش ناموجود شده است)."""
        cart = Cart.objects.first()
        if cart is None:
            cart = Cart.objects.create(session_key=self.client.session.session_key)
        return CartItem.objects.create(cart=cart, product=product, quantity=quantity)

    def checkout(self, **overrides):
        data = dict(CHECKOUT_DATA)
        data.update(overrides)
        return self.client.post(reverse('orders:checkout'), data=data)

    def make_order(self, quantity=2, status='pending', payment_status='pending',
                   payment_method='mock_gateway', product=None, reserve=False):
        product = product or self.product
        order = Order.objects.create(
            recipient_name=CHECKOUT_DATA['recipient_name'],
            recipient_phone=CHECKOUT_DATA['recipient_phone'],
            province=CHECKOUT_DATA['province'],
            city=CHECKOUT_DATA['city'],
            shipping_address=CHECKOUT_DATA['shipping_address'],
            postal_code=CHECKOUT_DATA['postal_code'],
            products_total=product.price * quantity,
            final_amount=product.price * quantity,
            status=status,
            payment_status=payment_status,
            payment_method=payment_method,
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_title=product.title,
            product_sku=product.sku,
            unit_price=product.price,
            quantity=quantity,
            total_price=product.price * quantity,
        )
        if reserve:
            order.reserve_stock()
        return order


class ProductReservationTests(StockReservationBase):
    """رزرو در سطح خود محصول و اتمیک بودن آن."""

    def test_available_qty_excludes_reserved_units(self):
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 3)
        self.assertTrue(self.product.is_in_stock)
        self.assertTrue(self.product.is_available)

        self.assertTrue(self.product.reserve_stock(2))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.reserved_qty, 2)
        self.assertEqual(self.product.available_qty, 1)

    def test_reserve_rejects_more_than_available(self):
        self.assertTrue(self.product.reserve_stock(3))
        self.assertFalse(self.product.reserve_stock(1))
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 3)
        self.assertEqual(self.product.available_qty, 0)
        self.assertFalse(self.product.is_available)
        self.assertFalse(self.product.is_in_stock)

    def test_last_unit_can_only_be_reserved_once(self):
        self.assertTrue(self.product.reserve_stock(2))
        self.assertTrue(self.product.reserve_stock(1))
        self.assertFalse(self.product.reserve_stock(1))
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 3)

    def test_stale_in_memory_reads_cannot_oversell(self):
        """دو نسخهٔ بی‌اطلاع از هم، هر دو موجودی ۳ را می‌بینند؛ فقط یکی رزرو می‌کند."""
        first = Product.objects.get(pk=self.product.pk)
        second = Product.objects.get(pk=self.product.pk)
        self.assertEqual(first.available_qty, 3)
        self.assertEqual(second.available_qty, 3)

        self.assertTrue(first.reserve_stock(3))
        # تصمیم بر اساس مقدار قدیمی گرفته می‌شود، اما شرط SQL موفق نمی‌شود.
        self.assertFalse(second.reserve_stock(1))

        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 3)
        self.assertEqual(self.product.available_qty, 0)

    def test_commit_moves_reservation_out_of_warehouse(self):
        self.assertTrue(self.product.reserve_stock(2))
        self.assertTrue(self.product.commit_stock(2))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 1)
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 1)

    def test_release_returns_units_to_available_pool(self):
        self.assertTrue(self.product.reserve_stock(3))
        self.assertTrue(self.product.release_stock(3))
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 3)
        self.assertFalse(self.product.release_stock(1))

    def test_restock_returns_sold_goods_to_warehouse(self):
        self.product.reserve_stock(2)
        self.product.commit_stock(2)
        self.assertTrue(self.product.restock(2))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.available_qty, 3)

    def test_low_stock_uses_sellable_units(self):
        self.product.low_stock_threshold = 2
        self.product.save()
        self.assertFalse(self.product.is_low_stock)
        self.product.reserve_stock(1)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_low_stock)


class CartStockLimitTests(StockReservationBase):
    """سبد خرید نباید اجازهٔ درخواست بیش از موجودی قابل فروش بدهد."""

    def test_add_to_cart_is_capped_at_available_stock(self):
        self.add_to_cart_htmx(quantity=5)
        cart = Cart.objects.first()
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 3)
        self.assertEqual(cart.total_items, 3)

    def test_add_to_cart_reports_stock_limit(self):
        response = self.add_to_cart_htmx(quantity=5)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response['HX-Trigger'])
        self.assertIn('حداکثر 3 عدد موجود است', payload['zitro:toast']['message'])
        self.assertEqual(payload['zitro:toast']['tone'], 'warning')

    def test_add_to_cart_sends_success_toast(self):
        response = self.add_to_cart_htmx(quantity=1)
        payload = json.loads(response['HX-Trigger'])
        self.assertIn('به سبد خرید اضافه شد', payload['zitro:toast']['message'])
        self.assertEqual(payload['zitro:toast']['tone'], 'success')

    def test_add_to_cart_refuses_out_of_stock_product(self):
        self.product.reserve_stock(3)
        self.add_to_cart_htmx(quantity=1)
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertEqual(Cart.objects.first().total_items, 0)

    def test_add_to_cart_respects_units_already_in_cart(self):
        self.add_to_cart_htmx(quantity=2)
        self.add_to_cart_htmx(quantity=2)
        item = CartItem.objects.get(product=self.product)
        self.assertEqual(item.quantity, 3)

    def test_cart_increase_never_exceeds_available_stock(self):
        self.add_to_cart_htmx(quantity=2)
        item = CartItem.objects.get(product=self.product)
        url = reverse('cart:cart_update', kwargs={'item_id': item.pk})
        for _ in range(5):
            self.client.post(url, {'action': 'increase'}, HTTP_HX_REQUEST='true')
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

    def test_cart_add_redirect_still_caps_the_quantity(self):
        response = self.client.post(
            reverse('cart:cart_add', kwargs={'product_id': self.product.pk}),
            {'quantity': 9},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'بیشتر از موجودی انبار نمی‌توانید سفارش دهید')
        cart = Cart.objects.first()
        self.assertEqual(cart.items.first().quantity, 3)


class CheckoutReservationTests(StockReservationBase):
    """ثبت سفارش، رزرو اتمیک موجودی و جلوگیری از فروش بیش از موجودی."""

    def test_checkout_reserves_stock_without_deducting_warehouse(self):
        self.add_to_cart_htmx(quantity=2)
        response = self.checkout()
        self.assertEqual(response.status_code, 302)

        order = Order.objects.get()
        self.assertEqual(order.stock_state, 'reserved')
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 2)
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.available_qty, 1)

    def test_checkout_blocks_oversell_when_stock_is_taken_meanwhile(self):
        """کاربر اول ۳ عدد در سبد دارد؛ مشتری دوم پیش از تسویه آن‌ها را رزرو می‌کند."""
        self.add_to_cart_htmx(quantity=3)
        rival = Product.objects.get(pk=self.product.pk)
        self.assertTrue(rival.reserve_stock(3))

        response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'موجودی انبار کافی نیست')

        # هیچ سفارش/آیتمی ثبت نمی‌شود و سبد خرید دست‌نخورده می‌ماند.
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Cart.objects.first().items.count(), 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 3)
        self.assertEqual(self.product.available_qty, 0)

    def test_partial_reservation_rolls_back_the_whole_order(self):
        """اگر یک قلم کمبود داشته باشد، رزرو اقلام دیگر هم برمی‌گردد."""
        sold_out = Product.objects.create(
            title='هدفون ناموجود',
            slug='sold-out',
            sku='SO-1',
            category=self.category,
            price=500_000,
            stock_qty=0,
        )
        self.add_to_cart_htmx(quantity=2)
        self.force_cart_item(sold_out, 1)

        response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'موجودی انبار کافی نیست')
        self.assertContains(response, '«هدفون ناموجود» موجود نیست.')

        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 3)

    def test_second_customer_cannot_buy_the_last_units(self):
        """۳ عدد موجودی به مشتری اول می‌رسد؛ مشتری دوم نه سبد پر می‌کند نه سفارش."""
        self.add_to_cart_htmx(quantity=3)
        self.assertEqual(self.checkout().status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 3)
        self.assertEqual(self.product.available_qty, 0)

        second_client = Client()
        second_client.post(
            reverse('cart:cart_add', kwargs={'product_id': self.product.pk}),
            {'quantity': 3},
        )
        second_cart = Cart.objects.exclude(pk=Cart.objects.first().pk).first()
        self.assertEqual(second_cart.items.count(), 0)

        response = second_client.post(reverse('orders:checkout'), data=CHECKOUT_DATA)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.available_qty, 0)

    def test_empty_cart_is_redirected(self):
        response = self.checkout()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    def test_reserve_stock_is_not_repeated_for_same_order(self):
        order = self.make_order(quantity=2)
        order.reserve_stock()
        order.reserve_stock()
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 2)

    def test_reserve_stock_raises_with_shortage_details(self):
        order = self.make_order(quantity=5)
        with self.assertRaises(InsufficientStockError) as ctx:
            order.reserve_stock()
        self.assertEqual(len(ctx.exception.shortages), 1)
        self.assertEqual(ctx.exception.shortages[0]['requested'], 5)
        self.assertEqual(ctx.exception.shortages[0]['available'], 3)
        order.refresh_from_db()
        self.assertEqual(order.stock_state, 'none')
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 0)


class PaymentAndReleaseTests(StockReservationBase):
    """چرخهٔ پرداخت: تبدیل رزرو به کسر انبار یا آزادسازی آن."""

    def _order_from_checkout(self, quantity=2, payment_method='mock_gateway'):
        self.add_to_cart_htmx(quantity=quantity)
        self.checkout(payment_method=payment_method)
        return Order.objects.get()

    def test_successful_payment_commits_stock_and_clears_cart(self):
        order = self._order_from_checkout(quantity=2)
        response = self.client.post(
            reverse('orders:mock_payment', kwargs={'order_number': order.order_number}),
            {'action': 'success'},
        )
        self.assertEqual(response.status_code, 302)

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.stock_state, 'committed')
        self.assertEqual(order.status, 'paid')
        self.assertEqual(self.product.stock_qty, 1)
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 1)
        self.assertEqual(Cart.objects.first().items.count(), 0)

    def test_failed_payment_releases_reserved_stock(self):
        order = self._order_from_checkout(quantity=2)
        response = self.client.post(
            reverse('orders:mock_payment', kwargs={'order_number': order.order_number}),
            {'action': 'cancel'},
        )
        self.assertEqual(response.status_code, 302)

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.stock_state, 'released')
        self.assertEqual(order.payment_status, 'failed')
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 3)

    def test_released_stock_can_be_sold_to_the_next_customer(self):
        first = self._order_from_checkout(quantity=3)
        self.client.post(
            reverse('orders:mock_payment', kwargs={'order_number': first.order_number}),
            {'action': 'cancel'},
        )

        second_client = Client()
        second_client.post(
            reverse('cart:cart_add', kwargs={'product_id': self.product.pk}),
            {'quantity': 3},
        )
        self.assertEqual(second_client.post(reverse('orders:checkout'), data=CHECKOUT_DATA).status_code, 302)
        self.assertEqual(Order.objects.count(), 2)

    def test_cash_on_delivery_commits_stock_immediately(self):
        order = self._order_from_checkout(quantity=1, payment_method='cod')
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.stock_state, 'committed')
        self.assertEqual(order.status, 'paid')
        self.assertEqual(self.product.stock_qty, 2)
        self.assertEqual(self.product.reserved_qty, 0)

    def test_commit_stock_is_idempotent(self):
        order = self.make_order(quantity=2, reserve=True)
        self.assertTrue(order.commit_stock())
        self.assertFalse(order.commit_stock())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 1)
        self.assertEqual(self.product.reserved_qty, 0)

    def test_release_stock_is_idempotent(self):
        order = self.make_order(quantity=2, reserve=True)
        self.assertTrue(order.release_stock())
        self.assertFalse(order.release_stock())
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.stock_qty, 3)

    def test_legacy_order_without_reservation_is_left_untouched(self):
        order = self.make_order(quantity=1)
        self.assertEqual(order.stock_state, 'none')
        self.assertFalse(order.commit_stock())
        self.assertFalse(order.release_stock())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.reserved_qty, 0)

    def test_coupon_usage_is_still_recorded(self):
        coupon = Coupon.objects.create(code='zitro10', discount_type='percent', value=10)
        self.add_to_cart_htmx(quantity=1)
        self.client.post(reverse('orders:apply_coupon'), {'coupon_code': 'zitro10'})
        self.checkout()
        order = Order.objects.get()
        self.assertEqual(order.coupon_code, 'ZITRO10')
        self.client.post(
            reverse('orders:mock_payment', kwargs={'order_number': order.order_number}),
            {'action': 'success'},
        )
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)


class DashboardStockReleaseTests(StockReservationBase):
    """لغو سفارش از پنل مدیریت باید موجودی را آزاد یا به انبار برگرداند."""

    def setUp(self):
        super().setUp()
        self.staff = User.objects.create_user(
            username='manager', password='pass12345', is_staff=True, is_superuser=True
        )
        self.client.force_login(self.staff)

    def test_cancel_releases_reserved_stock(self):
        order = self.make_order(quantity=2, reserve=True)
        self.assertEqual(order.stock_state, 'reserved')

        self.client.post(reverse('dashboard:order_status', args=[order.pk]), {'status': 'cancelled'})

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.stock_state, 'released')
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 3)

    def test_cancel_of_paid_order_returns_goods_to_warehouse(self):
        order = self.make_order(quantity=2, status='paid', payment_status='successful')
        order.reserve_stock()
        order.commit_stock()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 1)

        self.client.post(reverse('dashboard:order_status', args=[order.pk]), {'status': 'cancelled'})

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.stock_state, 'released')
        self.assertEqual(self.product.stock_qty, 3)
        self.assertEqual(self.product.reserved_qty, 0)
        self.assertEqual(self.product.available_qty, 3)

    def test_order_edit_form_cancel_releases_stock(self):
        order = self.make_order(quantity=1, reserve=True)
        self.client.post(reverse('dashboard:order_update', args=[order.pk]), {
            'status': 'cancelled',
            'payment_status': 'failed',
            'shipping_method': 'post',
            'tracking_code': '',
            'admin_note': '',
        })
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.stock_state, 'released')
        self.assertEqual(self.product.reserved_qty, 0)

    def test_shipping_an_order_does_not_touch_stock_again(self):
        order = self.make_order(quantity=2, status='paid', payment_status='successful')
        order.reserve_stock()
        order.commit_stock()

        self.client.post(reverse('dashboard:order_status', args=[order.pk]), {'status': 'shipped'})

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertEqual(order.stock_state, 'committed')
        self.assertEqual(self.product.stock_qty, 1)


class ProductPageAvailabilityTests(StockReservationBase):
    """صفحه محصول باید موجودی قابل فروش را نشان دهد و در نبود آن CTA را ببندد."""

    def test_page_shows_sellable_quantity(self):
        url = reverse('products:product_detail', kwargs={'pk': self.product.pk, 'slug': self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'موجود در انبار (3 عدد)')
        self.assertContains(response, 'max="3"')

    def test_page_disables_add_to_cart_when_fully_reserved(self):
        self.product.reserve_stock(3)
        url = reverse('products:product_detail', kwargs={'pk': self.product.pk, 'slug': self.product.slug})
        response = self.client.get(url)
        self.assertContains(response, 'ناموجود')
        self.assertRegex(response.content.decode(), r'type="submit"\s+disabled')
