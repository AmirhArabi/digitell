from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Address, Favorite
from products.models import Product, Category, Brand
from orders.models import Order, OrderItem


class CustomerProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reza',
            phone_number='09121112233',
            first_name='رضا',
            last_name='احمدی',
            password='password123'
        )
        self.category = Category.objects.create(name='موبایل', slug='mobile')
        self.brand = Brand.objects.create(name='سامسونگ', slug='samsung')
        self.product = Product.objects.create(
            title='سامسونگ گلکسی اس ۲۴',
            slug='s24',
            sku='SAM-S24',
            category=self.category,
            brand=self.brand,
            price=50_000_000,
            stock_qty=10,
        )

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_authenticated_user_profile_loads_successfully(self):
        self.client.login(username='reza', password='password123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'رضا')
        self.assertContains(response, '09121112233')

    def test_toggle_favorite_adds_and_removes(self):
        self.client.login(username='reza', password='password123')
        toggle_url = reverse('accounts:toggle_favorite', kwargs={'product_id': self.product.id})

        # Add to favorites
        response = self.client.get(toggle_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.filter(user=self.user, product=self.product).count(), 1)

        # Remove from favorites
        response = self.client.get(toggle_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.filter(user=self.user, product=self.product).count(), 0)

    def test_profile_post_update_profile(self):
        self.client.login(username='reza', password='password123')
        response = self.client.post(reverse('accounts:profile'), {
            'action': 'update_profile',
            'first_name': 'رضا علی',
            'last_name': 'احمدی راد',
            'email': 'reza@example.com',
            'phone_number': '09129998877',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'رضا علی')
        self.assertEqual(self.user.phone_number, '09129998877')

    def test_profile_post_save_and_delete_address(self):
        self.client.login(username='reza', password='password123')
        response = self.client.post(reverse('accounts:profile'), {
            'action': 'save_address',
            'title': 'منزل',
            'recipient_name': 'رضا احمدی',
            'recipient_phone': '09121112233',
            'province': 'تهران',
            'city': 'تهران',
            'postal_address': 'میدان ونک، خیابان خدامی، پلاک ۵',
            'postal_code': '1994512345',
            'is_default': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.addresses.count(), 1)
        addr = self.user.addresses.first()
        self.assertTrue(addr.is_default)
        self.assertEqual(addr.title, 'منزل')

        # Delete address
        response = self.client.post(reverse('accounts:profile'), {
            'action': 'delete_address',
            'address_id': addr.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.addresses.count(), 0)

    def test_profile_displays_real_order_and_in_transit_stepper(self):
        self.client.login(username='reza', password='password123')
        order = Order.objects.create(
            user=self.user,
            recipient_name='رضا احمدی',
            recipient_phone='09121112233',
            province='تهران',
            city='تهران',
            shipping_address='خیابان آزادی',
            status='shipped',
            products_total=50_000_000,
            final_amount=50_049_000,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            product_sku=self.product.sku,
            unit_price=50_000_000,
            quantity=1,
            total_price=50_000_000,
        )

        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_orders_count'], 1)
        self.assertEqual(response.context['pending_delivery_count'], 1)
        self.assertEqual(response.context['in_transit_order'], order)
        self.assertEqual(response.context['stepper_step'], 3)
        self.assertContains(response, 'سامسونگ گلکسی اس ۲۴')

    def test_profile_set_default_address(self):
        self.client.login(username='reza', password='password123')
        addr1 = Address.objects.create(
            user=self.user,
            title='منزل',
            recipient_name='رضا احمدی',
            recipient_phone='09121112233',
            province='تهران',
            city='تهران',
            postal_address='ونک پلاک ۱',
            is_default=True
        )
        addr2 = Address.objects.create(
            user=self.user,
            title='محل کار',
            recipient_name='رضا احمدی',
            recipient_phone='09121112233',
            province='تهران',
            city='تهران',
            postal_address='میرداماد پلاک ۲',
            is_default=False
        )

        response = self.client.post(reverse('accounts:profile'), {
            'action': 'set_default_address',
            'address_id': addr2.id,
        })
        self.assertEqual(response.status_code, 302)
        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)

    def test_add_address_ajax_view(self):
        self.client.login(username='reza', password='password123')
        url = reverse('accounts:add_address_ajax')

        # Invalid data
        response = self.client.post(url, {'title': 'ناقص'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')

        # Valid data
        response = self.client.post(url, {
            'title': 'دفتر مرکزی',
            'recipient_name': 'رضا احمدی',
            'recipient_phone': '09121112233',
            'province': 'تهران',
            'city': 'تهران',
            'postal_address': 'بلوار کشاورز، پلاک ۱۰۰',
            'postal_code': '1415512345',
            'is_default': 'true'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['address']['title'], 'دفتر مرکزی')
        self.assertTrue(data['address']['is_default'])
        self.assertEqual(self.user.addresses.count(), 1)

