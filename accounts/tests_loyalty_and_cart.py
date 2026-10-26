from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import CustomerProfile, LoyaltyPoint, Reward, CustomerActivityLog
from cart.models import Cart, CartItem
from products.models import Product, Category, Brand

User = get_user_model()

class LoyaltyClubTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='09120000000',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.profile = CustomerProfile.objects.create(user=self.user, segment='VIP')
        self.reward = Reward.objects.create(name='10% تخفیف', required_points=100, active=True)

    def test_customer_profile_creation(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.segment, 'VIP')
        self.assertTrue(str(self.profile).startswith('پروفایل'))

    def test_loyalty_point_award_and_total(self):
        LoyaltyPoint.objects.create(profile=self.profile, amount=150, source='order')
        LoyaltyPoint.objects.create(profile=self.profile, amount=50, source='signup')
        total_points = sum(p.amount for p in self.profile.points.all())
        self.assertEqual(total_points, 200)

    def test_reward_activation(self):
        self.assertTrue(self.reward.active)
        self.reward.active = False
        self.reward.save()
        self.assertFalse(Reward.objects.get(pk=self.reward.pk).active)

    def test_activity_log_creation(self):
        log = CustomerActivityLog.objects.create(
            profile=self.profile,
            activity_type='purchase',
            description='خرید محصول A'
        )
        self.assertIn(log, self.profile.activities.all())
        self.assertEqual(log.activity_type, 'purchase')

class CartViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='admin',
            phone_number='09121112233',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        self.category = Category.objects.create(name='دسته تست', slug='test-category')
        self.brand = Brand.objects.create(name='برند تست', slug='test-brand')
        self.product = Product.objects.create(
            title='محصول تست',
            slug='test-product',
            sku='TEST001',
            category=self.category,
            brand=self.brand,
            price=100000,
            stock_qty=5,
        )
        self.cart = Cart.objects.create(user=self.staff_user, session_key='sess123')
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

    def test_cart_list_view_access(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:cart_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.title)

    def test_cart_bulk_sms_view(self):
        self.client.login(username='admin', password='adminpass123')
        url = reverse('dashboard:cart_bulk_sms')
        response = self.client.post(url, {
            'carts': [self.cart.id],
            'message': 'پیام تست'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:cart_list'))
