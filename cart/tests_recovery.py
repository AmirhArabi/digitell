from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from products.models import Product, Category, Brand
from orders.models import Coupon, Order
from cart.models import Cart, CartItem, RecoveryCampaign, RecoveryAttempt
from cart.recovery_services import (
    get_abandoned_carts,
    is_cart_eligible_for_recovery,
    generate_recovery_token,
    build_recovery_url,
    create_recovery_coupon,
    send_recovery_attempt,
    process_automated_campaign,
    track_order_recovery,
)


class CartRecoveryModelAndServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='موبایل', slug='mobile')
        self.brand = Brand.objects.create(name='سامسونگ', slug='samsung')
        self.product = Product.objects.create(
            title='سامسونگ گلکسی S24',
            slug='samsung-s24',
            sku='S24-001',
            price=50_000_000,
            stock_qty=10,
            category=self.category,
            brand=self.brand,
        )

        self.user_subscribed = User.objects.create_user(
            username='user1',
            phone_number='09121111111',
            password='password123',
            sms_marketing_subscribed=True,
        )

        self.user_opted_out = User.objects.create_user(
            username='user2',
            phone_number='09122222222',
            password='password123',
            sms_marketing_subscribed=False,
        )

        self.campaign = RecoveryCampaign.objects.create(
            name='کمپین تست',
            is_active=True,
            abandonment_threshold_hours=24,
            step1_delay_hours=12,
            step2_delay_hours=24,
            discount_type='percent',
            discount_value=15,
            discount_validity_hours=48,
            max_attempts_per_cart=2,
            min_cart_value=10_000_000,
        )

    def test_empty_cart_never_eligible(self):
        """سبد خالی هرگز برای بازیابی انتخاب نشود."""
        cart = Cart.objects.create(user=self.user_subscribed)
        self.assertTrue(cart.is_empty)
        eligible, reason = is_cart_eligible_for_recovery(cart, self.campaign)
        self.assertFalse(eligible)
        self.assertIn("خالی", reason)

    def test_fresh_cart_not_abandoned(self):
        """سبد تازه ایجاد/فعال‌شده رهاشده تلقی نشود."""
        cart = Cart.objects.create(user=self.user_subscribed)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.assertEqual(cart.lifecycle_status, 'active')
        abandoned_carts = get_abandoned_carts(threshold_hours=24)
        self.assertNotIn(cart, abandoned_carts)

    def test_abandoned_cart_detection(self):
        """سبدی که ۲۴ ساعت از آخرین فعالیت آن گذشته، رهاشده تلقی شود."""
        cart = Cart.objects.create(user=self.user_subscribed)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        # عقب بردن زمان به‌روزرسانی
        Cart.objects.filter(pk=cart.pk).update(updated_at=timezone.now() - timedelta(hours=25))
        cart.refresh_from_db()
        self.assertEqual(cart.lifecycle_status, 'abandoned')
        abandoned = get_abandoned_carts(threshold_hours=24)
        self.assertIn(cart, abandoned)

    def test_opted_out_user_rejected(self):
        """کاربری که از پیامک بازاریابی انصراف داده نباید مشمول ارسال پیامک شود."""
        cart = Cart.objects.create(user=self.user_opted_out)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        eligible, reason = is_cart_eligible_for_recovery(cart, self.campaign)
        self.assertFalse(eligible)
        self.assertIn("انصراف", reason)

    def test_guest_without_phone_rejected(self):
        """سبد مهمان بدون شماره موبایل نباید واجد شرایط ارسال پیامک شود."""
        cart = Cart.objects.create(session_key='guest_session_xyz')
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        eligible, reason = is_cart_eligible_for_recovery(cart, self.campaign)
        self.assertFalse(eligible)
        self.assertIn("شماره موبایل", reason)

    def test_converted_cart_rejected(self):
        """سبدی که به سفارش تبدیل شده پیام جدید دریافت نکند."""
        order = Order.objects.create(
            user=self.user_subscribed,
            recipient_name='علی رضایی',
            recipient_phone='09121111111',
            city='تهران',
            province='تهران',
            shipping_address='خیابان آزادی',
            postal_code='1234567890',
            final_amount=50_000_000,
        )
        cart = Cart.objects.create(user=self.user_subscribed, converted_order=order)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        eligible, reason = is_cart_eligible_for_recovery(cart, self.campaign)
        self.assertFalse(eligible)
        self.assertEqual(cart.lifecycle_status, 'converted')

    def test_recovery_token_generation_and_expiry(self):
        """تولید و اعتبارسنجی توکن تصادفی بازگشت به سبد."""
        cart = Cart.objects.create(user=self.user_subscribed)
        token = generate_recovery_token(cart, validity_hours=24)
        self.assertIsNotNone(token)
        self.assertEqual(cart.recovery_token, token)
        self.assertGreater(cart.recovery_token_expires_at, timezone.now())

    def test_personal_coupon_ownership(self):
        """کد تخفیف اختصاصی کاربر نباید توسط کاربر دیگر پذیرفته شود."""
        coupon = create_recovery_coupon(
            cart=Cart.objects.create(user=self.user_subscribed),
            campaign=self.campaign,
        )
        self.assertTrue(coupon.code.startswith('RET-'))
        self.assertEqual(coupon.for_user, self.user_subscribed)
        self.assertEqual(coupon.source, 'cart_recovery')

        # استفاده توسط کاربر مجاز
        valid, msg, discount = coupon.validate_for(50_000_000, user=self.user_subscribed)
        self.assertTrue(valid)
        self.assertGreater(discount, 0)

        # تلاش برای استفاده توسط کاربر دیگر
        valid2, msg2, discount2 = coupon.validate_for(50_000_000, user=self.user_opted_out)
        self.assertFalse(valid2)
        self.assertIn("ویژه", msg2)

    def test_send_recovery_attempt_flow(self):
        """جریان کامل ارسال یک مرحله پیامک و ثبت سابقه."""
        cart = Cart.objects.create(user=self.user_subscribed)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        ok, msg, attempt = send_recovery_attempt(
            cart=cart,
            campaign=self.campaign,
            step=1,
            message_type='reminder',
        )
        self.assertTrue(ok)
        self.assertEqual(attempt.status, 'sent')
        self.assertEqual(cart.recovery_status, 'contacted')
        self.assertEqual(cart.attempts_count, 1)

    def test_order_attribution(self):
        """انتساب صحیح سفارش به سبد و سابقه بازیابی."""
        cart = Cart.objects.create(user=self.user_subscribed, recovery_status='contacted')
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        send_recovery_attempt(cart=cart, campaign=self.campaign, step=1)

        order = Order.objects.create(
            user=self.user_subscribed,
            recipient_name='علی رضایی',
            recipient_phone='09121111111',
            city='تهران',
            province='تهران',
            shipping_address='تهران خیابان انقلاب',
            postal_code='1234567890',
            final_amount=50_000_000,
        )

        attributed = track_order_recovery(order, cart)
        self.assertTrue(attributed)
        cart.refresh_from_db()
        self.assertEqual(cart.recovery_status, 'recovered')
        self.assertEqual(cart.converted_order, order)


class CartDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff_admin',
            phone_number='09129999999',
            password='adminpassword',
            is_staff=True,
            is_superuser=True,
        )
        self.customer = User.objects.create_user(
            username='customer1',
            phone_number='09123333333',
            password='customerpass',
            sms_marketing_subscribed=True,
        )
        self.category = Category.objects.create(name='لپ‌تاپ', slug='laptop')
        self.brand = Brand.objects.create(name='ایسوس', slug='asus')
        self.product = Product.objects.create(
            title='لپ‌تاپ ذن‌بوک ۱۴',
            slug='zenbook-14',
            sku='ASUS-ZB14',
            price=45_000_000,
            stock_qty=5,
            category=self.category,
            brand=self.brand,
        )
        self.cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_dashboard_cart_list_view(self):
        self.client.login(username='staff_admin', password='adminpassword')
        response = self.client.get(reverse('dashboard:cart_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لپ‌تاپ ذن‌بوک ۱۴')
        self.assertContains(response, 'customer1')

    def test_dashboard_cart_list_filter_authenticated_users(self):
        self.client.login(username='staff_admin', password='adminpassword')
        guest_cart = Cart.objects.create(session_key='guest_session_12345678')
        response = self.client.get(reverse('dashboard:cart_list') + '?customer=authenticated')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'customer1')
        self.assertNotContains(response, 'guest_session_12345678')

    def test_dashboard_cart_list_filter_guest_users(self):
        self.client.login(username='staff_admin', password='adminpassword')
        guest_cart = Cart.objects.create(session_key='guest_session_87654321')
        response = self.client.get(reverse('dashboard:cart_list') + '?customer=guest')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'guest_session_87654321')
        self.assertNotContains(response, 'customer1')

    def test_dashboard_cart_detail_view(self):
        self.client.login(username='staff_admin', password='adminpassword')
        response = self.client.get(reverse('dashboard:cart_detail', kwargs={'pk': self.cart.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ASUS-ZB14')
        self.assertContains(response, 'ارسال پیامک بازیابی')

    def test_dashboard_send_manual_sms(self):
        self.client.login(username='staff_admin', password='adminpassword')
        url = reverse('dashboard:cart_send_sms', kwargs={'pk': self.cart.pk})
        response = self.client.post(url, {
            'message_type': 'reminder',
            'custom_text': 'سلام {name} عزیز، سبد شما محفوظ است: {cart_url}',
            'dry_run': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.recovery_status, 'contacted')
        self.assertEqual(self.cart.attempts_count, 1)

    def test_dashboard_bulk_sms_view(self):
        self.client.login(username='staff_admin', password='adminpassword')
        url = reverse('dashboard:cart_bulk_sms')
        response = self.client.post(url, {
            'carts': [self.cart.id],
            'message': 'پیامک تست گروهی',
            'dry_run': 'on',
        })
        self.assertEqual(response.status_code, 302)

    def test_dashboard_campaign_view(self):
        self.client.login(username='staff_admin', password='adminpassword')
        url = reverse('dashboard:cart_recovery_campaign')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'قواعد و پیام‌های کمپین')


class CartRecoverViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(
            username='user_rec',
            phone_number='09125555555',
            password='password123',
        )
        self.category = Category.objects.create(name='هدفون', slug='headphones')
        self.brand = Brand.objects.create(name='سونی', slug='sony')
        self.product = Product.objects.create(
            title='هدفون سونی WH-1000XM5',
            slug='sony-xm5',
            sku='SNY-XM5',
            price=18_000_000,
            stock_qty=8,
            category=self.category,
            brand=self.brand,
        )
        self.cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        self.token = generate_recovery_token(self.cart, validity_hours=24)

    def test_recover_view_redirects_unauthenticated_user_to_login(self):
        url = reverse('cart:cart_recover', kwargs={'token': self.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_recover_view_logged_in_user(self):
        self.client.login(username='user_rec', password='password123')
        url = reverse('cart:cart_recover', kwargs={'token': self.token})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'هدفون سونی WH-1000XM5')

    def test_recover_view_invalid_token(self):
        url = reverse('cart:cart_recover', kwargs={'token': 'non_existent_token_123'})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نامعتبر')
