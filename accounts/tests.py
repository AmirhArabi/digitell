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


class PhoneAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        from home.models import SiteSetting
        self.site_setting = SiteSetting.get_settings()
        self.existing_phone = '09121112233'
        self.user = User.objects.create_user(
            username=self.existing_phone,
            phone_number=self.existing_phone,
            first_name='علی',
            last_name='کریمی',
            password='securePassword123'
        )

    def test_check_phone_existing_user(self):
        url = reverse('accounts:check_phone')
        response = self.client.get(f"{url}?phone={self.existing_phone}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['exists'])
        self.assertEqual(data['name'], 'علی کریمی')

    def test_check_phone_new_user(self):
        url = reverse('accounts:check_phone')
        response = self.client.get(f"{url}?phone=09359876543")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['exists'])

    def test_login_otp_flow(self):
        self.site_setting.login_method = 'otp'
        self.site_setting.save()

        # Step 1: Request OTP
        new_phone = '09351234567'
        response = self.client.post(reverse('accounts:login'), {
            'phone_number': new_phone
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:verify_otp'), response.url)

        # Step 2: Verify OTP created
        from accounts.models import OTPCode
        otp = OTPCode.objects.filter(phone_number=new_phone, is_used=False).first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.code), 6)

        # Step 3: Submit invalid code
        response = self.client.post(reverse('accounts:verify_otp'), {
            'code': '000000'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نامعتبر است یا منقضی شده است')

        # Step 4: Submit valid code
        response = self.client.post(reverse('accounts:verify_otp'), {
            'code': otp.code
        })
        self.assertEqual(response.status_code, 302)

        # User is created and logged in
        new_user = User.objects.filter(phone_number=new_phone).first()
        self.assertIsNotNone(new_user)
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_login_password_existing_user(self):
        self.site_setting.login_method = 'password'
        self.site_setting.save()

        response = self.client.post(reverse('accounts:login'), {
            'phone_number': self.existing_phone,
            'password': 'securePassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_login_password_new_user_registration(self):
        self.site_setting.login_method = 'password'
        self.site_setting.save()

        new_phone = '09901112233'
        # First attempt without password prompts for password
        response = self.client.post(reverse('accounts:login'), {
            'phone_number': new_phone,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_new_user'])

        # Second attempt with password creates user and logs in
        response = self.client.post(reverse('accounts:login'), {
            'phone_number': new_phone,
            'password': 'myNewPassword123'
        })
        self.assertEqual(response.status_code, 302)
        created_user = User.objects.filter(phone_number=new_phone).first()
        self.assertIsNotNone(created_user)
        self.assertEqual(int(self.client.session['_auth_user_id']), created_user.id)

    def test_user_profile_completion_properties(self):
        user = User.objects.create_user(
            username='incomplete_user',
            phone_number='09120001122',
            first_name='علی',
            last_name='کریمی',
            password='password123'
        )
        self.assertFalse(user.is_profile_complete)
        self.assertIn("کد ملی", user.missing_fields_list)
        self.assertIn("تاریخ تولد", user.missing_fields_list)

        # Update supplementary fields
        user.national_code = '0012345678'
        import datetime
        user.birth_date = datetime.date(1996, 11, 10)
        user.save()

        self.assertTrue(user.is_profile_complete)
        self.assertEqual(user.jalali_birth_date, '1375/08/20')

    def test_profile_update_supplementary_post(self):
        user = User.objects.create_user(
            username='supp_user',
            phone_number='09123334455',
            password='password123'
        )
        self.client.login(username='supp_user', password='password123')
        response = self.client.post(reverse('accounts:profile'), {
            'action': 'update_supplementary',
            'first_name': 'سهراب',
            'last_name': 'سپهری',
            'national_code': '0011223344',
            'birth_date': '1375/08/20',
            'gender': 'male',
            'job_title': 'نویسنده',
            'sheba_number': '123456789012345678901234',
            'card_number': '6037991812345678',
            'sms_marketing': 'on',
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'سهراب')
        self.assertEqual(user.last_name, 'سپهری')
        self.assertEqual(user.national_code, '0011223344')
        self.assertEqual(user.gender, 'male')
        self.assertEqual(user.job_title, 'نویسنده')
        self.assertTrue(user.sheba_number.startswith('IR'))
        self.assertTrue(user.sms_marketing_subscribed)
        self.assertFalse(user.email_marketing_subscribed)
        self.assertEqual(user.jalali_birth_date, '1375/08/20')

