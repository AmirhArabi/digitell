"""تست‌های پنل مدیریت فروشگاه زیترو (دسترسی، CRUD و فرآیندهای فروش)."""
import base64
import json
import re
import tempfile
from datetime import timedelta
from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from blog.models import BlogCategory, Post
from home.models import Banner, SiteSetting
from orders.models import Coupon, Order, OrderItem
from products.models import Brand, Category, CategoryAttribute, Product, ProductImage, ProductSpecification

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


def png_file(name="test.png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


class DashboardBaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="manager", password="pass12345", is_staff=True, is_superuser=True
        )
        self.customer = User.objects.create_user(
            username="buyer", password="pass12345", phone_number="09121112233"
        )
        self.category = Category.objects.create(name="گوشی موبایل", name_en="Smartphones",
                                                slug="smartphones", order=1)
        self.child_category = Category.objects.create(name="سامسونگ", slug="samsung-phones",
                                                     parent=self.category)
        self.brand = Brand.objects.create(name="سامسونگ", name_en="Samsung", slug="samsung")
        self.attribute = CategoryAttribute.objects.create(
            name="حافظه داخلی", category=self.category, unit="گیگابایت", type="select",
            options="۱۲۸ گیگابایت\n۲۵۶ گیگابایت",
        )
        self.product = Product.objects.create(
            title="گوشی سامسونگ A55", slug="samsung-a55", sku="SAM-A55", category=self.category,
            brand=self.brand, price=18_500_000, compare_at_price=20_000_000, stock_qty=8,
        )

    def login_staff(self):
        self.client.force_login(self.staff)


class DashboardAccessTests(DashboardBaseTestCase):
    def test_staff_can_open_every_dashboard_page(self):
        self.login_staff()
        urls = [
            reverse('dashboard:overview'),
            reverse('dashboard:reports'),
            reverse('dashboard:products'),
            reverse('dashboard:product_create'),
            reverse('dashboard:product_edit', args=[self.product.pk]),
            reverse('dashboard:inventory'),
            reverse('dashboard:categories'),
            reverse('dashboard:category_create'),
            reverse('dashboard:category_edit', args=[self.category.pk]),
            reverse('dashboard:brands'),
            reverse('dashboard:brand_create'),
            reverse('dashboard:brand_edit', args=[self.brand.pk]),
            reverse('dashboard:attributes'),
            reverse('dashboard:attribute_edit', args=[self.attribute.pk]),
            reverse('dashboard:banners'),
            reverse('dashboard:banner_create'),
            reverse('dashboard:orders'),
            reverse('dashboard:customers'),
            reverse('dashboard:customer_detail', args=[self.customer.pk]),
            reverse('dashboard:coupons'),
            reverse('dashboard:coupon_create'),
            reverse('dashboard:posts'),
            reverse('dashboard:post_create'),
            reverse('dashboard:settings'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_edit_forms_render_with_existing_records(self):
        """فرم‌های ویرایش با رکورد موجود (شاخه‌های {% if %}) درست رندر شوند."""
        self.login_staff()
        coupon = Coupon.objects.create(code='EDIT10', discount_type='amount', value=10_000,
                                      valid_from=timezone.now())
        post = Post.objects.create(title='مقاله نمونه', slug='sample-post', content='متن')
        banner = Banner.objects.create(title='بنر نمونه', image='banners/sample.png', position='hero')

        edit_urls = [
            reverse('dashboard:coupon_edit', args=[coupon.pk]),
            reverse('dashboard:post_edit', args=[post.pk]),
            reverse('dashboard:banner_edit', args=[banner.pk]),
        ]
        for url in edit_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'value=')

        # بنر باید تصویر موجود را نمایش دهد
        self.assertContains(self.client.get(reverse('dashboard:banner_edit', args=[banner.pk])), 'banners/sample.png')

    def test_anonymous_and_normal_user_are_blocked(self):
        for url in [reverse('dashboard:overview'), reverse('dashboard:products')]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('accounts:login'), response['Location'])

        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('dashboard:overview')).status_code, 302)


class ProductManagementTests(DashboardBaseTestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_create_product_with_images_and_specifications(self):
        self.login_staff()
        response = self.client.post(reverse('dashboard:product_create'), {
            'title': 'لپ‌تاپ ایسوس ROG',
            'title_en': 'Asus ROG Laptop',
            'sku': 'ASUS-ROG-1',
            'category': self.category.pk,
            'brand': self.brand.pk,
            'price': '42,000,000',
            'compare_at_price': '45,000,000',
            'stock_qty': '۷',
            'low_stock_threshold': '3',
            'warranty': '۱۸ ماه گارانتی',
            'rating': '4.8',
            'short_description': 'لپ‌تاپ گیمینگ',
            'description': 'توضیح کامل',
            'is_active': 'on',
            'is_featured': 'on',
            'spec_name': ['حافظه داخلی', ''],
            'spec_value': ['۱ ترابایت', ''],
            'spec_unit': ['SSD', ''],
            'images': [png_file('one.png'), png_file('two.png')],
            'primary_image': '2',
        })
        self.assertEqual(response.status_code, 302)

        product = Product.objects.get(sku='ASUS-ROG-1')
        self.assertEqual(product.price, 42_000_000)
        self.assertEqual(product.stock_qty, 7)   # پشتیبانی از اعداد فارسی
        self.assertEqual(product.discount_pct, 7)
        self.assertTrue(product.is_featured)
        self.assertEqual(product.images.count(), 2)
        self.assertTrue(product.images.get(order=2).is_primary)  # تصویر اصلی انتخابی
        self.assertEqual(product.specifications.count(), 1)
        self.assertEqual(product.specifications.first().value, '۱ ترابایت SSD')
        self.assertEqual(product.slug, 'لپتاپ-ایسوس-rog')

        # اسلاگ فارسی باید در آدرس‌های فروشگاه کار کند
        detail_url = product.get_absolute_url()
        self.assertEqual(unquote(detail_url), f'/products/{product.pk}/لپتاپ-ایسوس-rog/')
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.assertEqual(self.client.get(reverse('dashboard:products')).status_code, 200)

    def test_duplicate_sku_is_rejected(self):
        self.login_staff()
        response = self.client.post(reverse('dashboard:product_create'), {
            'title': 'کالای تکراری', 'sku': 'SAM-A55', 'category': self.category.pk, 'price': '100',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.filter(sku='SAM-A55').count(), 1)

    def test_edit_and_toggle_product(self):
        self.login_staff()
        response = self.client.post(reverse('dashboard:product_edit', args=[self.product.pk]), {
            'title': 'گوشی سامسونگ A55 (ویرایش‌شده)',
            'sku': 'SAM-A55',
            'category': self.child_category.pk,
            'price': '17500000',
            'stock_qty': '4',
            'warranty': '۱۲ ماه',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.title, 'گوشی سامسونگ A55 (ویرایش‌شده)')
        self.assertEqual(self.product.category, self.child_category)
        self.assertEqual(self.product.stock_qty, 4)
        self.assertTrue(self.product.is_low_stock)

        self.client.post(reverse('dashboard:product_toggle', args=[self.product.pk, 'featured']))
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_featured)

    def test_filters_and_bulk_actions(self):
        self.login_staff()
        response = self.client.get(reverse('dashboard:products'), {'status': 'active', 'stock': 'in', 'q': 'سامسونگ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SAM-A55')

        Product.objects.create(title="کالای دوم", slug="p2", sku="P2", category=self.category,
                               price=1000, stock_qty=0, is_active=False)
        self.client.post(reverse('dashboard:product_bulk'), {
            'action': 'activate',
            'ids': [self.product.pk],
            'next': reverse('dashboard:products'),
        })
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)

        self.client.post(reverse('dashboard:product_bulk'), {
            'action': 'special',
            'ids': [self.product.pk],
        })
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_special_offer)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_image_primary_and_delete(self):
        self.login_staff()
        first = ProductImage.objects.create(product=self.product, image=png_file('a.png'), is_primary=True)
        second = ProductImage.objects.create(product=self.product, image=png_file('b.png'))

        self.client.post(reverse('dashboard:product_image_primary', args=[second.pk]))
        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(ProductImage.objects.get(pk=second.pk).is_primary)

        self.client.post(reverse('dashboard:product_image_delete', args=[second.pk]))
        self.assertEqual(self.product.images.count(), 1)
        self.assertTrue(ProductImage.objects.get(pk=first.pk).is_primary)

    def test_delete_product(self):
        self.login_staff()
        self.client.post(reverse('dashboard:product_delete', args=[self.product.pk]))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_inventory_bulk_update(self):
        self.login_staff()
        self.client.post(reverse('dashboard:inventory'), {
            f'stock_{self.product.pk}': '25',
            f'threshold_{self.product.pk}': '6',
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 25)
        self.assertEqual(self.product.low_stock_threshold, 6)
        self.assertFalse(self.product.is_low_stock)


class CatalogStructureTests(DashboardBaseTestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_category_crud_and_parent_tree(self):
        self.login_staff()
        self.client.post(reverse('dashboard:category_create'), {
            'name': 'لوازم جانبی', 'name_en': 'Accessories', 'parent': self.category.pk,
            'order': '2', 'is_active': 'on', 'image': png_file('cat.png'),
        })
        created = Category.objects.get(name_en='Accessories')
        self.assertEqual(created.parent, self.category)
        self.assertTrue(created.image)

        response = self.client.get(reverse('dashboard:categories'))
        self.assertContains(response, 'Accessories')

        # حذف دسته‌ای که کالا دارد باید مسدود شود
        self.client.post(reverse('dashboard:category_delete', args=[self.category.pk]))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

        # حذف دسته بدون کالا و بدون زیردسته
        self.client.post(reverse('dashboard:category_delete', args=[created.pk]))
        self.assertFalse(Category.objects.filter(pk=created.pk).exists())

    def test_category_cannot_be_its_own_parent(self):
        self.login_staff()
        self.client.post(reverse('dashboard:category_edit', args=[self.category.pk]), {
            'name': 'گوشی موبایل', 'parent': self.category.pk, 'is_active': 'on',
        })
        self.category.refresh_from_db()
        self.assertIsNone(self.category.parent)

    def test_brand_crud(self):
        self.login_staff()
        self.client.post(reverse('dashboard:brand_create'), {
            'name': 'اپل', 'name_en': 'Apple', 'order': '1', 'is_active': 'on',
        })
        apple = Brand.objects.get(name_en='Apple')
        self.assertEqual(apple.slug, 'apple')

        self.client.post(reverse('dashboard:brand_edit', args=[apple.pk]), {
            'name': 'اپل آمریکا', 'name_en': 'Apple', 'order': '1', 'is_active': 'on',
        })
        apple.refresh_from_db()
        self.assertEqual(apple.name, 'اپل آمریکا')

        self.client.post(reverse('dashboard:brand_delete', args=[apple.pk]))
        self.assertFalse(Brand.objects.filter(pk=apple.pk).exists())

    def test_attribute_crud_and_quick_add(self):
        self.login_staff()
        self.client.post(reverse('dashboard:attributes'), {
            'name': 'رنگ', 'category': self.category.pk, 'unit': '',
            'type': 'select', 'options': 'مشکی\nسفید', 'order': '1',
        })
        colour = CategoryAttribute.objects.get(name='رنگ')
        self.assertEqual(colour.options_list, ['مشکی', 'سفید'])

        self.client.post(reverse('dashboard:attribute_edit', args=[colour.pk]), {
            'name': 'رنگ بدنه', 'category': self.category.pk, 'type': 'select',
            'options': 'مشکی\nآبی', 'order': '1', 'is_active': 'on',
        })
        colour.refresh_from_db()
        self.assertEqual(colour.name, 'رنگ بدنه')

        self.client.post(reverse('dashboard:attribute_delete', args=[colour.pk]))
        self.assertFalse(CategoryAttribute.objects.filter(pk=colour.pk).exists())


class ContentAndOrderTests(DashboardBaseTestCase):
    def _make_order(self, **kwargs):
        order = Order.objects.create(
            user=self.customer,
            recipient_name='رضا علوی',
            recipient_phone='09121112233',
            province='تهران',
            city='تهران',
            shipping_address='میدان ولیعصر، پلاک ۱',
            postal_code='1987654321',
            products_total=self.product.price,
            final_amount=self.product.price,
            payment_status='successful',
            status='paid',
            **kwargs,
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_title=self.product.title,
            product_sku=self.product.sku, unit_price=self.product.price, quantity=1,
            total_price=self.product.price,
        )
        return order

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_banner_crud_and_ordering(self):
        self.login_staff()
        self.client.post(reverse('dashboard:banner_create'), {
            'title': 'جشنواره فروش', 'subtitle': 'تا ۴۰٪ تخفیف', 'position': 'hero',
            'link_url': '/shop/', 'order': '0', 'is_active': 'on', 'image': png_file('banner.png'),
        })
        first = Banner.objects.get(title='جشنواره فروش')
        self.assertTrue(first.image)

        self.client.post(reverse('dashboard:banner_create'), {
            'title': 'بنر دوم', 'position': 'hero', 'order': '5', 'is_active': 'on',
            'image': png_file('banner2.png'),
        })

        self.client.post(reverse('dashboard:banner_move', args=[first.pk, 'down']))
        first.refresh_from_db()
        self.assertGreater(first.order, 0)

        self.client.post(reverse('dashboard:banner_toggle', args=[first.pk]))
        first.refresh_from_db()
        self.assertFalse(first.is_active)

        self.client.post(reverse('dashboard:banner_delete', args=[first.pk]))
        self.assertFalse(Banner.objects.filter(pk=first.pk).exists())

    def test_order_detail_update_status_and_export(self):
        self.login_staff()
        order = self._make_order()

        self.assertEqual(self.client.get(reverse('dashboard:order_detail', args=[order.pk])).status_code, 200)

        self.client.post(reverse('dashboard:order_update', args=[order.pk]), {
            'status': 'shipped', 'payment_status': 'successful',
            'tracking_code': '12345678901234567890', 'shipping_method': 'post',
            'admin_note': 'با پیک ارسال شد',
        })
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertEqual(order.tracking_code, '12345678901234567890')
        self.assertEqual(order.admin_note, 'با پیک ارسال شد')

        self.client.post(reverse('dashboard:order_status', args=[order.pk]), {'status': 'cancelled'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.payment_status, 'failed')

        export = self.client.get(reverse('dashboard:orders_export'))
        self.assertEqual(export.status_code, 200)
        self.assertIn('text/csv', export['Content-Type'])
        self.assertIn(order.order_number, export.content.decode('utf-8-sig'))

        # فیلتر جستجو
        filtered = self.client.get(reverse('dashboard:orders'), {'q': '09121112233'})
        self.assertContains(filtered, order.order_number)

    def test_customer_report_and_staff_toggle(self):
        self.login_staff()
        order = self._make_order()
        self.assertEqual(order.user, self.customer)

        response = self.client.get(reverse('dashboard:customers'), {'q': '09121112233'})
        self.assertContains(response, '09121112233')

        self.client.post(reverse('dashboard:customer_toggle_staff', args=[self.customer.pk]))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_staff)

        # جلوگیری از تغییر دسترسی خود مدیر
        self.client.post(reverse('dashboard:customer_toggle_staff', args=[self.staff.pk]))
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_staff)

    def test_coupon_crud(self):
        self.login_staff()
        self.client.post(reverse('dashboard:coupon_create'), {
            'code': 'zitro10', 'title': 'کمپین تست', 'discount_type': 'percent', 'value': '10',
            'min_order_amount': '1000000', 'max_uses': '5', 'is_active': 'on',
        })
        coupon = Coupon.objects.get(code='ZITRO10')
        self.assertEqual(coupon.code, 'ZITRO10')

        valid, _, discount = coupon.validate_for(2_000_000)
        self.assertTrue(valid)
        self.assertEqual(discount, 200_000)

        invalid, message, discount = coupon.validate_for(500_000)
        self.assertFalse(invalid)
        self.assertEqual(discount, 0)
        self.assertIn('حداقل', message)

        self.client.post(reverse('dashboard:coupon_toggle', args=[coupon.pk]))
        coupon.refresh_from_db()
        self.assertFalse(coupon.is_active)

        self.client.post(reverse('dashboard:coupon_delete', args=[coupon.pk]))
        self.assertFalse(Coupon.objects.filter(pk=coupon.pk).exists())

    def test_expired_and_limited_coupons(self):
        expired = Coupon.objects.create(code='OLD', discount_type='amount', value=10_000,
                                        valid_until=timezone.now() - timedelta(days=1))
        self.assertTrue(expired.is_expired)
        self.assertFalse(expired.validate_for(1_000_000)[0])

        limited = Coupon.objects.create(code='LIMIT', discount_type='percent', value=5,
                                        max_uses=2, used_count=2)
        self.assertFalse(limited.validate_for(1_000_000)[0])
        self.assertEqual(limited.usage_left, 0)

    def test_post_crud_and_blog_categories(self):
        self.login_staff()
        self.client.post(reverse('dashboard:blog_category_create'), {'name': 'اخبار', 'order': '1'})
        blog_category = BlogCategory.objects.get(name='اخبار')

        self.client.post(reverse('dashboard:post_create'), {
            'title': 'راهنمای خرید گوشی', 'category': blog_category.pk, 'content': 'متن مقاله',
            'excerpt': 'چکیده', 'is_published': 'on',
        })
        post = Post.objects.get(title='راهنمای خرید گوشی')
        self.assertEqual(post.author, self.staff)
        self.assertTrue(post.is_published)

        self.client.post(reverse('dashboard:post_toggle', args=[post.pk]))
        post.refresh_from_db()
        self.assertFalse(post.is_published)

        self.client.post(reverse('dashboard:post_delete', args=[post.pk]))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_reports_and_settings(self):
        self.login_staff()
        self._make_order()

        report = self.client.get(reverse('dashboard:reports'), {'from': '2020-01-01', 'to': '2100-01-01'})
        self.assertEqual(report.status_code, 200)
        self.assertContains(report, self.product.title)

        export = self.client.get(reverse('dashboard:reports_export'), {'from': '2020-01-01', 'to': '2100-01-01'})
        self.assertEqual(export.status_code, 200)
        self.assertIn('شماره سفارش', export.content.decode('utf-8-sig'))

        self.client.post(reverse('dashboard:settings'), {
            'store_name': 'زیترو شاپ', 'slogan': 'شعار جدید', 'phone': '021-12345678',
            'email': 'info@zitro.ir', 'address': 'تهران', 'working_hours': '۹ تا ۱۷',
            'telegram': '@zitro', 'instagram': 'zitro', 'whatsapp': '09120000000',
            'shipping_cost': '59000', 'free_shipping_threshold': '5000000',
            'about_us': 'درباره ما', 'footer_note': 'تمام حقوق محفوظ است',
        })
        settings_obj = SiteSetting.get_settings()
        self.assertEqual(settings_obj.store_name, 'زیترو شاپ')
        self.assertEqual(settings_obj.shipping_cost, 59_000)
        self.assertEqual(settings_obj.free_shipping_threshold, 5_000_000)


class CheckoutCouponIntegrationTests(DashboardBaseTestCase):
    def test_coupon_and_shipping_applied_to_order(self):
        SiteSetting.objects.create(id=1, shipping_cost=50_000, free_shipping_threshold=0)
        coupon = Coupon.objects.create(code='SAVE10', discount_type='percent', value=10, is_active=True)

        self.client.force_login(self.customer)
        self.client.post(reverse('cart:cart_add', args=[self.product.pk]))

        self.client.post(reverse('orders:apply_coupon'), {'coupon_code': 'save10'})
        session = self.client.session
        self.assertEqual(session.get('coupon_code'), 'SAVE10')

        response = self.client.post(reverse('orders:checkout'), {
            'recipient_name': 'رضا علوی', 'recipient_phone': '09121112233', 'province': 'تهران',
            'city': 'تهران', 'shipping_address': 'تهران، خیابان ولیعصر', 'postal_code': '1234567890',
            'payment_method': 'mock_gateway', 'shipping_method': 'tipax',
        })
        self.assertEqual(response.status_code, 302)

        order = Order.objects.get()
        expected_discount = int(self.product.price * 10 / 100)
        self.assertEqual(order.coupon_code, 'SAVE10')
        self.assertEqual(order.coupon_discount, expected_discount)
        self.assertEqual(order.shipping_cost, 50_000)
        self.assertEqual(order.shipping_method, 'tipax')
        self.assertEqual(order.final_amount, self.product.price - expected_discount + 50_000)
        self.assertEqual(coupon.used_count, 0)

        self.client.post(reverse('orders:mock_payment', args=[order.order_number]), {'action': 'success'})
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'successful')

        # کد تخفیف پس از پرداخت از سشن حذف می‌شود
        self.assertNotIn('coupon_code', self.client.session)

    def test_free_shipping_threshold(self):
        SiteSetting.objects.create(id=1, shipping_cost=50_000, free_shipping_threshold=5_000_000)
        self.client.force_login(self.customer)
        self.client.post(reverse('cart:cart_add', args=[self.product.pk]))
        self.client.post(reverse('orders:checkout'), {
            'recipient_name': 'رضا علوی', 'recipient_phone': '09121112233', 'province': 'تهران',
            'city': 'تهران', 'shipping_address': 'تهران', 'postal_code': '1234567890',
            'payment_method': 'cod',
        })
        order = Order.objects.get()
        self.assertEqual(order.shipping_cost, 0)
        self.assertEqual(order.final_amount, self.product.price)

    def test_invalid_coupon_is_rejected_when_applying(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('cart:cart_add', args=[self.product.pk]))
        self.client.post(reverse('orders:apply_coupon'), {'coupon_code': 'NOPE'})
        self.assertIsNone(self.client.session.get('coupon_code'))


class HomePageIntegrationTests(DashboardBaseTestCase):
    def test_created_content_appears_on_storefront(self):
        self.login_staff()
        self.client.post(reverse('dashboard:product_toggle', args=[self.product.pk, 'featured']))
        self.client.post(reverse('dashboard:blog_category_create'), {'name': 'راهنما', 'order': '1'})
        blog_category = BlogCategory.objects.get(name='راهنما')
        self.client.post(reverse('dashboard:post_create'), {
            'title': 'بهترین گوشی‌های ۱۴۰۵', 'category': blog_category.pk,
            'content': 'متن', 'is_published': 'on',
        })

        self.client.logout()
        home = self.client.get(reverse('home:index'))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, 'بهترین گوشی‌های ۱۴۰۵')
        self.assertContains(home, self.product.title)

        shop = self.client.get(reverse('products:shop'))
        self.assertContains(shop, self.product.title)


class ReportsAnalyticsTests(DashboardBaseTestCase):
    """تست‌های صفحه گزارشات: KPI، نمودارها، تفکیک محصول/انبار و خروجی‌های CSV."""

    def make_order(self, amount=None, qty=1, user=None, days_ago=0, **kwargs):
        amount = self.product.price if amount is None else amount
        order = Order.objects.create(
            user=user or self.customer,
            recipient_name='رضا علوی',
            recipient_phone='09121112233',
            province='تهران',
            city='تهران',
            shipping_address='میدان ولیعصر، پلاک ۱',
            postal_code='1987654321',
            products_total=amount,
            final_amount=amount,
            payment_status='successful',
            status='paid',
            **kwargs,
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_title=self.product.title,
            product_sku=self.product.sku, unit_price=amount // qty, quantity=qty,
            total_price=amount,
        )
        if days_ago:
            created = timezone.now() - timedelta(days=days_ago)
            Order.objects.filter(pk=order.pk).update(created_at=created)
            order.refresh_from_db()
        return order

    @staticmethod
    def chart_payload(response, element_id):
        # The template renders {{ charts|json_script:"reports-charts" }} as
        # <script id="reports-charts" type="application/json">...</script>.
        # Decode the response and extract the JSON payload from the script tag.
        self.login_staff()
        self.make_order()
        response = self.client.get(reverse('dashboard:reports'), {'from': '2020-01-01', 'to': '2100-01-01'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'گزارشات')
        for label in ['فروش موفق بازه', 'سفارش‌های پرداخت‌شده', 'میانگین ارزش سفارش',
                      'اقلام فروخته‌شده', 'خریداران یکتا', 'مشتریان جدید',
                      'تخفیف اعطاشده (کد + سود)', 'سفارش‌های بدون پرداخت']:
            self.assertContains(response, label)

        for canvas_id in ['chart-daily', 'chart-status', 'chart-top-products', 'chart-categories',
                          'chart-weekday', 'chart-stock-health', 'chart-stock-categories', 'chart-payment']:
            self.assertContains(response, 'id="%s"' % canvas_id)

        html = response.content.decode('utf-8')
        import re
        match = re.search(
            r'<script[^>]*id="%s"[^>]*>(.*?)</script>' % re.escape(element_id),
            html, re.S,
        )
        self.assertIsNotNone(match, 'Chart JSON script not found in response')
        payload = json.loads(match.group(1))

        self.assertEqual(sum(payload['daily']['revenue']), self.product.price)
        self.assertEqual(sum(payload['daily']['orders']), 1)
        self.assertEqual(payload['top_products']['labels'], [self.product.title])
        self.assertEqual(payload['top_products']['qty'], [1])
        self.assertEqual(payload['stock_health']['counts'][0], 1)  # یک کالای موجود
        self.assertEqual(sum(payload['stock_categories']['units']), self.product.stock_qty)

        inventory = response.context['inventory']
        self.assertEqual(inventory['products_count'], 1)
        self.assertEqual(inventory['units'], self.product.stock_qty)
        self.assertEqual(inventory['value'], self.product.stock_qty * self.product.price)
        self.assertEqual(inventory['out_of_stock'], 0)

    def test_reports_filters_and_previous_period_comparison(self):
        self.login_staff()
        self.make_order(amount=10_000_000)
        self.make_order(amount=4_000_000, days_ago=40)

        today = timezone.now().date()
        response = self.client.get(reverse('dashboard:reports'), {
            'from': (today - timedelta(days=29)).isoformat(),
            'to': today.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current']['revenue'], 10_000_000)
        self.assertEqual(response.context['previous']['revenue'], 4_000_000)

        revenue_kpi = response.context['kpis'][0]
        self.assertEqual(revenue_kpi['growth'], 150.0)

        # کالای ناموجود و کم‌موجود در KPI انبار شمرده شوند
        Product.objects.create(title='کالای ناموجود', slug='sold-out', sku='SO-1',
                               category=self.category, price=1_000, stock_qty=0)
        Product.objects.create(title='کالای کم‌موجود', slug='low-stock', sku='LS-1',
                               category=self.category, price=1_000, stock_qty=2, low_stock_threshold=5)
        response = self.client.get(reverse('dashboard:reports'))
        self.assertEqual(response.context['inventory']['out_of_stock'], 1)
        self.assertEqual(response.context['inventory']['low_stock'], 1)

    def test_inventory_and_product_exports(self):
        self.login_staff()
        self.make_order(amount=self.product.price, qty=2)
        Product.objects.create(title='کالای ناموجود', slug='sold-out', sku='SO-1',
                               category=self.category, price=2_000, stock_qty=0)
        Product.objects.create(title='کالای کم‌موجود', slug='low-stock', sku='LS-1',
                               category=self.category, price=3_000, stock_qty=2, low_stock_threshold=5)

        today = timezone.now().date()
        orders_csv = self.client.get(reverse('dashboard:reports_export'), {
            'from': (today - timedelta(days=7)).isoformat(), 'to': today.isoformat(),
        })
        products_csv = self.client.get(reverse('dashboard:reports_products_export'), {
            'from': (today - timedelta(days=7)).isoformat(), 'to': today.isoformat(),
        })
        inventory_csv = self.client.get(reverse('dashboard:reports_inventory_export'))

        for export in (orders_csv, products_csv, inventory_csv):
            self.assertEqual(export.status_code, 200)
            self.assertIn('text/csv', export['Content-Type'])

        product_rows = products_csv.content.decode('utf-8-sig')
        self.assertIn(self.product.title, product_rows)
        self.assertIn('تعداد فروش', product_rows)
        self.assertIn('درآمد (تومان)', product_rows)

        inventory_rows = inventory_csv.content.decode('utf-8-sig')
        self.assertIn(self.product.sku, inventory_rows)
        self.assertIn('ارزش انبار (تومان)', inventory_rows)
        self.assertIn('کم‌موجود', inventory_rows)
        self.assertIn('ناموجود', inventory_rows)
        expected_value = self.product.stock_qty * self.product.price
        self.assertIn(str(expected_value), inventory_rows.replace(',', ''))


class CustomerAnalyticsTests(DashboardBaseTestCase):
    """تست‌های سگمنت‌بندی، فیلتر و پرونده مشتریان."""

    def make_order(self, user, amount, days_ago=0):
        order = Order.objects.create(
            user=user, recipient_name='مشتری تست', recipient_phone='09120000000',
            province='تهران', city='تهران', shipping_address='تهران', postal_code='1234567890',
            products_total=amount, final_amount=amount,
            payment_status='successful', status='paid',
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_title=self.product.title,
            product_sku=self.product.sku, unit_price=amount, quantity=1, total_price=amount,
        )
        if days_ago:
            Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        return order

    def test_customer_segments_and_sorting(self):
        self.login_staff()
        vip = User.objects.create_user(username='vip', password='pass12345', phone_number='09120000001')
        loyal = User.objects.create_user(username='loyal', password='pass12345', phone_number='09120000002')
        dormant = User.objects.create_user(username='dormant', password='pass12345', phone_number='09120000003')
        User.objects.create_user(username='lead', password='pass12345', phone_number='09120000004')

        self.make_order(vip, 30_000_000)
        self.make_order(vip, 30_000_000)
        for _ in range(3):
            self.make_order(loyal, 1_000_000)
        self.make_order(dormant, 2_000_000, days_ago=120)
        self.make_order(self.customer, 3_000_000)  # کاربر تازه‌وارد با یک خرید

        response = self.client.get(reverse('dashboard:customers'))
        self.assertEqual(response.status_code, 200)
        segments = {row.username: row.segment for row in response.context['customers']}
        self.assertEqual(segments['vip'], 'vip')
        self.assertEqual(segments['loyal'], 'loyal')
        self.assertEqual(segments['dormant'], 'dormant')
        self.assertEqual(segments['lead'], 'lead')
        self.assertEqual(segments['buyer'], 'new')
        self.assertEqual(segments['manager'], 'staff')

        # ترتیب پیش‌فرض بر اساس بیشترین خرید است
        self.assertEqual(response.context['customers'][0].username, 'vip')

        filtered = self.client.get(reverse('dashboard:customers'), {'segment': 'vip'})
        self.assertEqual([row.username for row in filtered.context['customers']], ['vip'])

        by_orders = self.client.get(reverse('dashboard:customers'), {'sort': 'orders'})
        self.assertEqual(by_orders.context['customers'][0].username, 'loyal')

        stats = response.context['segment_counts']
        self.assertEqual(stats['customers'], 5)
        self.assertEqual(stats['buyers'], 4)
        self.assertEqual(stats['no_order'], 1)
        self.assertEqual(response.context['repeat_rate'], 50.0)

    def test_customer_detail_page_and_chart(self):
        self.login_staff()
        self.make_order(self.customer, 12_000_000)

        response = self.client.get(reverse('dashboard:customer_detail', args=[self.customer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'روند خرید ماهانه مشتری')
        self.assertContains(response, 'تاریخچه سفارش‌ها')
        self.assertEqual(response.context['paid_count'], 1)
        self.assertEqual(response.context['items_bought'], 1)
        self.assertEqual(response.context['days_since_last'], 0)

        # The chart is rendered via {{ chart_months|json_script:"customer-chart-data" }}
        # which produces <script id="customer-chart-data" type="application/json">...</script>
        # Find the JSON data (id may come before type)
        import re
        match = re.search(
            r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
            response.content.decode(), re.S,
        )
        self.assertIsNotNone(match, 'Chart data script not found in response')
        payload = json.loads(match.group(1))
        self.assertEqual(payload['revenue'], [12_000_000])
        self.assertEqual(len(payload['labels']), 1)
        self.assertEqual(response.context['favourite_products'][0]['qty'], 1)

    def test_non_staff_cannot_open_customer_pages(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('dashboard:customers')).status_code, 302)
        self.assertEqual(
            self.client.get(reverse('dashboard:customer_detail', args=[self.customer.pk])).status_code, 302
        )
        self.assertEqual(self.client.get(reverse('dashboard:reports')).status_code, 302)
        self.assertEqual(self.client.get(reverse('dashboard:reports_inventory_export')).status_code, 302)
