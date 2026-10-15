import base64
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from products.models import Category, Brand, Product, ProductImage, ProductSpecification
from cart.models import Cart, CartItem
from orders.models import Order

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


class ZitroShopTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            name="گوشی موبایل",
            name_en="Smartphones",
            slug="smartphones",
            order=1,
            is_active=True
        )
        self.brand = Brand.objects.create(
            name="سامسونگ",
            name_en="Samsung",
            slug="samsung",
            is_active=True
        )
        self.product = Product.objects.create(
            title="گوشی موبایل سامسونگ مدل Galaxy A55 5G",
            title_en="Samsung Galaxy A55 5G Smartphone",
            slug="samsung-galaxy-a55-5g",
            sku="SAM-A55-128",
            category=self.category,
            brand=self.brand,
            price=18500000,
            compare_at_price=20000000,
            stock_qty=15,
            is_available=True,
            is_active=True,
            is_featured=True,
            is_special_offer=True,
        )

    def test_product_model_calculations(self):
        self.assertEqual(self.product.discount_pct, 8)
        self.assertEqual(self.product.formatted_price, "18,500,000")
        self.assertTrue(self.product.is_available)
        self.assertEqual(self.product.get_absolute_url(), f"/products/{self.product.id}/samsung-galaxy-a55-5g/")

    def test_shop_and_category_endpoints(self):
        res = self.client.get(reverse('products:shop'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Galaxy A55")

        cat_url = reverse('products:category_detail', kwargs={'slug': self.category.slug})
        res_cat = self.client.get(cat_url)
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, "Galaxy A55")

    def test_live_search_endpoint(self):
        res = self.client.get(reverse('products:live_search'), {'q': 'Galaxy'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Galaxy A55")

    def test_cart_add_and_htmx_flow(self):
        # HTMX Add to cart
        add_url = reverse('cart:cart_add', kwargs={'product_id': self.product.id})
        res = self.client.post(add_url, HTTP_HX_REQUEST='true')
        self.assertEqual(res.status_code, 200)

        # Verify Cart in DB
        cart = Cart.objects.first()
        self.assertIsNotNone(cart)
        self.assertEqual(cart.total_items, 1)
        self.assertEqual(cart.total_price, 18500000)

    def test_checkout_and_payment_flow(self):
        # Add to cart first
        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}))

        # Post checkout form
        checkout_data = {
            'recipient_name': 'رضا علوی',
            'recipient_phone': '09121112233',
            'province': 'تهران',
            'city': 'تهران',
            'shipping_address': 'میدان ولیعصر، کوچه فیروزه، پلاک ۲',
            'postal_code': '1987654321',
            'payment_method': 'mock_gateway',
        }
        res = self.client.post(reverse('orders:checkout'), data=checkout_data)
        self.assertEqual(res.status_code, 302)

        order = Order.objects.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.recipient_name, 'رضا علوی')
        self.assertEqual(order.payment_status, 'pending')

        # Simulate Payment
        pay_url = reverse('orders:mock_payment', kwargs={'order_number': order.order_number})
        pay_res = self.client.post(pay_url, data={'action': 'success'})
        self.assertEqual(pay_res.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'successful')
        self.assertEqual(order.status, 'paid')
        self.assertTrue(order.transaction_id.startswith('TRX-'))


class ProductPageDesignTests(TestCase):
    """ساختار و چیدمان صفحه محصول (الگوی موبایل‌محور برگرفته از زیترو)."""

    def setUp(self):
        self.client = Client()
        self.media_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.category = Category.objects.create(name="هدفون و هندزفری", slug="headphones")
        self.other_category = Category.objects.create(name="شارژر و پاوربانک", slug="powerbanks")
        self.brand = Brand.objects.create(name="تی سی اچ", name_en="TCH", slug="tch")
        self.product = Product.objects.create(
            title="هندزفری بی‌سیم TCH مدل Blade L10",
            title_en="TCH WIRELESS HANDSFREE MODEL BLADE L10",
            slug="tch-blade-l10",
            sku="TCH-BLADE-L10",
            category=self.category,
            brand=self.brand,
            price=1_899_000,
            compare_at_price=3_200_000,
            stock_qty=12,
            short_description="هندزفری بلوتوثی قابل حمل برای موسیقی و مکالمه روزمره.",
            description="توضیح کامل محصول برای تست نمایش بخش توضیحات.",
            warranty="۱۸ ماه گارانتی شرکتی",
        )
        for index in range(8):
            ProductSpecification.objects.create(
                product=self.product, name=f"ویژگی {index + 1}", value=f"مقدار {index + 1}", order=index
            )
        self.sibling = Product.objects.create(
            title="هندزفری بی‌سیم TCH مدل Blade L10 ANC",
            slug="tch-blade-l10-anc",
            sku="TCH-L10-ANC",
            category=self.category,
            brand=self.brand,
            price=2_499_000,
            compare_at_price=3_300_000,
            stock_qty=5,
        )

    @property
    def url(self):
        return reverse('products:product_detail', kwargs={'pk': self.product.pk, 'slug': self.product.slug})

    def html(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    # ------------------------------------------------------------------
    # سکشن‌ها و لنگرها
    # ------------------------------------------------------------------
    def test_page_has_all_product_sections_in_zitro_order(self):
        html = self.html()
        for anchor in ('id="specs"', 'id="description"', 'id="reviews"', 'id="similar"'):
            self.assertIn(anchor, html)

        self.assertLess(html.index('id="product-gallery"'), html.index('id="product-title-block"'))
        self.assertLess(html.index('id="product-title-block"'), html.index('id="product-spec-summary"'))
        self.assertLess(html.index('id="product-spec-summary"'), html.index('id="product-price"'))
        self.assertLess(html.index('id="product-price"'), html.index('id="product-cta"'))
        self.assertLess(html.index('id="description"'), html.index('id="reviews"'))
        self.assertLess(html.index('id="reviews"'), html.index('id="similar"'))

    def test_mobile_anchor_bar_links_to_every_section(self):
        html = self.html()
        self.assertIn('sticky top-32', html)
        for target in ('#specs', '#description', '#reviews', '#similar'):
            self.assertIn(f'href="{target}"', html)

    def test_single_h1_title_and_english_title(self):
        html = self.html()
        self.assertEqual(html.count('<h1'), 1)
        self.assertIn('TCH WIRELESS HANDSFREE MODEL BLADE L10', html)
        self.assertIn('dir="ltr"', html)

    # ------------------------------------------------------------------
    # قیمت، تخفیف و خرید
    # ------------------------------------------------------------------
    def test_price_block_shows_discount_and_savings(self):
        html = self.html()
        self.assertIn('1,899,000', html)
        self.assertIn('3,200,000', html)
        self.assertIn('41%', html)
        self.assertIn('سود شما از این خرید: 1,301,000 تومان', html)
        self.assertIn('کالای اصل', html)
        self.assertIn('فروشنده: ', html)

    def test_purchase_row_has_cash_and_installment_actions(self):
        html = self.html()
        self.assertIn('bg-zitro-cash', html)
        self.assertIn('bg-zitro-dark', html)
        self.assertIn('اعتباری قسطی', html)
        self.assertIn('افزودن به سبد خرید', html)
        self.assertIn('خرید اقساطی بدون ضامن با اسنپ‌پی', html)

    def test_quantity_stepper_is_capped_by_available_stock(self):
        html = self.html()
        self.assertIn('data-max="12"', html)
        self.assertIn('max="12"', html)
        self.assertIn('data-qty-step="1"', html)
        self.assertIn('data-qty-step="-1"', html)

    def test_out_of_stock_product_hides_buy_bar_and_disables_cta(self):
        self.product.reserve_stock(12)
        html = self.html()
        self.assertIn('ناموجود', html)
        self.assertRegex(html, r'type="submit"\s+disabled')
        # نوار خرید ثابت موبایل در حالت ناموجود رندر نمی‌شود.
        self.assertNotIn('shadow-[0_-6px_20px_rgba(15,23,42,0.08)]', html)
        cta = html.split('id="product-cta"')[1].split('id="specs"')[0]
        self.assertNotIn('افزودن به سبد خرید', cta)

    # ------------------------------------------------------------------
    # بخش‌های تاشو و کاروسل
    # ------------------------------------------------------------------
    def test_spec_summary_shows_six_rows_then_collapsed_rest(self):
        html = self.html()
        summary = html.split('id="product-spec-summary"')[1].split('id="product-price"')[0]
        self.assertEqual(summary.count('font-bold text-zitro-ink'), 6)
        self.assertIn('نمایش همه', summary)

        self.assertIn('id="specs-more"', html)
        self.assertIn('data-expanded="false"', html)
        specs_section = html.split('id="specs"')[1]
        self.assertIn('نمایش بیشتر', specs_section)
        self.assertIn('نمایش کمتر', specs_section)
        self.assertIn('ویژگی 8', specs_section)

    def test_specs_section_without_extra_rows_has_no_toggle(self):
        ProductSpecification.objects.filter(product=self.product, order__gte=6).delete()
        html = self.html()
        self.assertNotIn('id="specs-more"', html)

    def test_long_description_is_collapsible(self):
        html = self.html()
        self.assertNotIn('id="description-more"', html)

        self.product.description = "توضیح بسیار طولانی. " * 30
        self.product.save()
        html = self.html()
        self.assertIn('id="description-more"', html)
        self.assertIn('collapse-panel', html)

    def test_similar_products_use_horizontal_snap_carousel(self):
        html = self.html()
        similar = html.split('id="similar"')[1]
        self.assertIn('snap-x', similar)
        self.assertIn('w-[47%]', similar)
        self.assertIn('Blade L10 ANC', similar)
        self.assertIn('مشاهده بیشتر', similar)

    def test_page_uses_own_bottom_bar_instead_of_the_mobile_nav(self):
        html = self.html()
        # نوار خرید ثابت صفحه محصول جایگزین نوار ناوبری پایین موبایل می‌شود.
        self.assertIn('fixed bottom-0 left-0 right-0 z-50', html)
        self.assertNotIn('<span class="text-[10px] font-medium">خانه</span>', html)

    # ------------------------------------------------------------------
    # گالری
    # ------------------------------------------------------------------
    def test_gallery_fallback_when_product_has_no_image(self):
        html = self.html()
        self.assertNotIn('id="main-product-img"', html)
        self.assertEqual(html.count('data-gallery-thumb="'), 0)

    def test_gallery_thumbnails_switch_the_main_image(self):
        for index in range(2):
            ProductImage.objects.create(
                product=self.product,
                image=SimpleUploadedFile(f"p{index}.png", PNG_BYTES, content_type="image/png"),
                is_primary=index == 0,
                order=index,
            )
        html = self.html()
        self.assertIn('id="main-product-img"', html)
        self.assertEqual(html.count('data-gallery-thumb="'), 2)
