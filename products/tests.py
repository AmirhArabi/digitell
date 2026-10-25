import base64
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from products.models import (
    Category, Brand, Product, ProductImage, ProductReview, ProductSpecification,
)
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem

User = get_user_model()

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

        # Test search query matching a category prioritizes category first
        res_cat = self.client.get(reverse('products:live_search'), {'q': 'موبایل'})
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, "دسته‌بندی")
        self.assertContains(res_cat, "گوشی موبایل")
        self.assertIn(self.category, res_cat.context['categories'])

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
        self.assertIn('id="mobile-anchor-bar"', html)
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
        self.assertIn('سود شما از این خرید: 1,301,000 <svg class="toman-icon"', html)
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

    def test_warranty_and_insurance_section_and_bottom_sheet(self):
        html = self.html()
        # بخش گارانتی و بیمه
        self.assertIn('id="product-warranty-insurance"', html)
        self.assertIn(self.product.warranty, html)
        self.assertIn('بیمه سرقت و خسارات - سامان', html)
        self.assertIn('id="open-insurance-sheet"', html)
        # محاسبه ۲.۳ درصد بیمه (1899000 * 0.023 = 43677)
        expected_fee = f"{round(self.product.price * 0.023):,}"
        self.assertIn(expected_fee, html)
        # باتم شیت دیالوگ توضیحات بیمه
        self.assertIn('id="insurance-bottom-sheet"', html)
        self.assertIn('id="close-insurance-sheet-btn"', html)
        self.assertIn('پوشش‌های بیمه تجهیزات دیجیتال سامان', html)
        # موقعیت قرارگیری قبل از خلاصه مشخصات
        self.assertLess(html.index('id="product-warranty-insurance"'), html.index('id="product-spec-summary"'))

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


class ProductReviewTests(TestCase):
    """سیستم ثبت نظر و محاسبهٔ امتیاز از نظرهای تأییدشده."""

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="گوشی موبایل", slug="smartphones")
        self.brand = Brand.objects.create(name="سامسونگ", slug="samsung")
        self.product = Product.objects.create(
            title="گوشی سامسونگ Galaxy A55",
            slug="galaxy-a55",
            sku="SAM-A55",
            category=self.category,
            brand=self.brand,
            price=18_500_000,
            stock_qty=5,
        )
        self.user = User.objects.create_user(username="buyer", password="zitro12345")
        self.other_user = User.objects.create_user(username="visitor", password="zitro12345")

    @property
    def review_url(self):
        return reverse('products:product_review', kwargs={'pk': self.product.pk})

    @property
    def detail_url(self):
        return self.product.get_absolute_url()

    def _submit(self, **overrides):
        payload = {'rating': '5', 'title': 'عالی بود', 'body': 'کیفیت ساخت و کارایی این گوشی بی‌نظیر است.'}
        payload.update(overrides)
        return self.client.post(self.review_url, payload)

    def test_anonymous_user_cannot_submit_a_review(self):
        response = self._submit()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_logged_in_user_can_submit_and_see_the_review(self):
        self.client.force_login(self.user)
        response = self._submit()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('#reviews'))

        review = ProductReview.objects.get()
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.author_name, 'buyer')
        self.assertTrue(review.is_approved)

        page = self.client.get(self.detail_url)
        self.assertContains(page, 'کیفیت ساخت و کارایی این گوشی بی‌نظیر است.')
        self.assertContains(page, '1 نظر ثبت‌شده')

    def test_product_rating_is_average_of_approved_reviews(self):
        ProductReview.objects.create(product=self.product, user=self.user, author_name='الف', rating=5, body='خیلی خوب')
        ProductReview.objects.create(product=self.product, user=self.other_user, author_name='ب', rating=3, body='متوسط بود')
        self.assertEqual(self.product.review_count, 2)
        self.assertEqual(self.product.review_average, 4.0)

    def test_unapproved_reviews_are_hidden_and_excluded_from_average(self):
        ProductReview.objects.create(
            product=self.product, user=self.user, author_name='الف',
            rating=1, body='نظر تأییدنشده و پنهان', is_approved=False,
        )
        self.assertEqual(self.product.review_count, 0)
        # در نبود نظر تأییدشده، امتیاز پیش‌فرض محصول نمایش داده می‌شود.
        self.assertEqual(self.product.review_average, float(self.product.rating))

        page = self.client.get(self.detail_url)
        self.assertNotContains(page, 'نظر تأییدنشده و پنهان')
        self.assertContains(page, 'هنوز نظری ثبت نشده است')

    def test_user_review_is_updated_not_duplicated(self):
        self.client.force_login(self.user)
        self._submit(rating='4', body='نظر اولیهٔ من دربارهٔ این گوشی')
        self._submit(rating='2', body='نظر ویرایش‌شدهٔ من دربارهٔ این گوشی')
        self.assertEqual(ProductReview.objects.count(), 1)
        review = ProductReview.objects.get()
        self.assertEqual(review.rating, 2)
        self.assertIn('ویرایش‌شده', review.body)

    def test_invalid_rating_and_short_body_are_rejected(self):
        self.client.force_login(self.user)
        self._submit(rating='9', body='متن کوتاه')
        self.assertEqual(ProductReview.objects.count(), 0)

        page = self.client.get(self.detail_url)
        self.assertContains(page, 'امتیاز را بین ۱ تا ۵ ستاره انتخاب کنید.')

    def test_verified_purchase_is_detected_from_paid_order(self):
        order = Order.objects.create(
            user=self.user,
            recipient_name='خریدار',
            recipient_phone='09120000000',
            province='تهران',
            city='تهران',
            shipping_address='تهران، خیابان آزادی',
            postal_code='1234567890',
            products_total=self.product.price,
            shipping_cost=0,
            final_amount=self.product.price,
            status='paid',
            payment_status='successful',
            shipping_method='post',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            product_sku=self.product.sku,
            unit_price=self.product.price,
            quantity=1,
            total_price=self.product.price,
        )
        self.client.force_login(self.user)
        self._submit()

        review = ProductReview.objects.get()
        self.assertTrue(review.is_verified_purchase)
        page = self.client.get(self.detail_url)
        self.assertContains(page, 'خریدار این کالا')

    def test_htmx_submission_returns_only_the_reviews_partial(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.review_url,
            {'rating': '5', 'title': '', 'body': 'ارسال بدون بارگذاری مجدد صفحه'},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('<html', content)
        self.assertIn('ارسال بدون بارگذاری مجدد صفحه', content)
        self.assertIn('data-star-rating', content)

    def test_review_form_shows_login_prompt_for_anonymous_visitors(self):
        content = self.client.get(self.detail_url).content.decode()
        self.assertIn('برای ثبت امتیاز و نظر', content)
        self.assertNotIn('name="rating"', content)


class CatalogFilterTests(TestCase):
    """ساختار جدید کاتالوگ: ابتدا فیلدهای فیلتر، سپس ردیف‌های همان فیلد."""

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="گوشی موبایل", slug="smartphones", order=1)
        self.samsung = Brand.objects.create(name="سامسونگ", name_en="Samsung", slug="samsung")
        self.apple = Brand.objects.create(name="اپل", name_en="Apple", slug="apple")

        self.samsung_phone = Product.objects.create(
            title="گوشی سامسونگ مدل S24", slug="samsung-s24", sku="SAM-S24",
            category=self.category, brand=self.samsung, price=50_000_000, stock_qty=4,
        )
        self.apple_phone = Product.objects.create(
            title="گوشی اپل مدل iPhone 15", slug="apple-iphone-15", sku="APL-IP15",
            category=self.category, brand=self.apple, price=90_000_000, stock_qty=2,
        )
        ProductSpecification.objects.create(product=self.samsung_phone, name="حافظه داخلی", value="۲۵۶ گیگابایت")
        ProductSpecification.objects.create(product=self.apple_phone, name="حافظه داخلی", value="۱۲۸ گیگابایت")

    def test_categories_page_lists_categories_brands_and_counts(self):
        response = self.client.get(reverse('products:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دسته‌بندی‌های کالا')
        self.assertContains(response, self.category.name)
        self.assertContains(response, 'خرید بر اساس برند')
        self.assertContains(response, 'سامسونگ')
        # بررسی وجود لینک فیلتر برند برای آن دسته
        expected_filter = f"{self.category.get_absolute_url()}?brand={self.samsung.slug}"
        self.assertContains(response, expected_filter)

        # بررسی فیلتر شدن کاتالوگ با پارامترهای دسته و برند
        shop_resp = self.client.get(self.category.get_absolute_url(), {'brand': 'samsung'})
        self.assertEqual(shop_resp.status_code, 200)
        self.assertContains(shop_resp, 'مدل S24')
        self.assertNotContains(shop_resp, 'iPhone 15')

    def test_filter_sidebar_lists_fields_before_their_rows(self):
        content = self.client.get(reverse('products:shop')).content.decode()
        fields = ['category', 'brand', 'price', 'status']
        positions = [content.index(f'data-filter-toggle="{key}"') for key in fields]
        self.assertEqual(positions, sorted(positions))
        for key in fields:
            self.assertIn(f'data-filter-panel="{key}"', content)

    def test_specifications_become_their_own_filter_fields(self):
        content = self.client.get(reverse('products:shop')).content.decode()
        self.assertIn('حافظه داخلی', content)
        self.assertIn('data-filter-toggle="spec-0"', content)
        self.assertIn('data-filter-panel="spec-0"', content)

    def test_brand_filter_narrows_the_product_grid(self):
        response = self.client.get(reverse('products:shop'), {'brand': 'samsung'})
        self.assertContains(response, 'مدل S24')
        self.assertNotContains(response, 'iPhone 15')

    def test_spec_filter_matches_product_specifications(self):
        response = self.client.get(
            reverse('products:shop'), {'spec': 'حافظه داخلی::۲۵۶ گیگابایت'}
        )
        self.assertContains(response, 'مدل S24')
        self.assertNotContains(response, 'iPhone 15')

    def test_multiple_values_of_one_spec_are_combined_with_or(self):
        response = self.client.get(
            reverse('products:shop'),
            {'spec': ['حافظه داخلی::۲۵۶ گیگابایت', 'حافظه داخلی::۱۲۸ گیگابایت']},
        )
        self.assertContains(response, 'مدل S24')
        self.assertContains(response, 'iPhone 15')

    def test_active_filters_render_as_removable_chips(self):
        content = self.client.get(reverse('products:shop'), {'brand': 'samsung'}).content.decode()
        self.assertIn('فیلترهای فعال', content)
        self.assertIn('برند: سامسونگ', content)
        self.assertIn('حذف این فیلتر', content)

    def test_sort_links_keep_the_active_filters(self):
        content = self.client.get(
            reverse('products:shop'), {'brand': 'samsung', 'sort': 'cheapest'}
        ).content.decode()
        self.assertIn('brand=samsung', content)
        self.assertIn('sort=expensive', content)

    def test_in_stock_filter_uses_sellable_units(self):
        self.apple_phone.reserve_stock(2)
        response = self.client.get(reverse('products:shop'), {'in_stock': '1'})
        self.assertContains(response, 'مدل S24')
        self.assertNotContains(response, 'iPhone 15')

    def test_htmx_filter_request_returns_the_grid_partial_only(self):
        response = self.client.get(reverse('products:shop'), {'brand': 'apple'}, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('<html', content)
        self.assertIn('id="product-grid"', content)
        self.assertContains(response, 'iPhone 15')

    def test_category_page_reuses_the_field_first_sidebar(self):
        content = self.client.get(
            reverse('products:category_detail', kwargs={'slug': self.category.slug})
        ).content.decode()
        self.assertIn('data-filter-toggle="category"', content)
        self.assertIn('data-filter-toggle="brand"', content)
        self.assertIn('id="product-grid"', content)


class CatalogPaginationTests(TestCase):
    """صفحه‌بندی کاتالوگ با حفظ فیلترها، مرتب‌سازی و وضعیت‌های خالی/بارگذاری."""

    PAGE_SIZE = 12

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="گوشی موبایل", slug="smartphones")
        self.brand = Brand.objects.create(name="سامسونگ", slug="samsung")
        self.other_brand = Brand.objects.create(name="اپل", slug="apple")
        for index in range(15):
            Product.objects.create(
                title=f"کالای تست شماره {index + 1}",
                slug=f"test-product-{index + 1}",
                sku=f"TST-{index + 1:02d}",
                category=self.category,
                brand=self.brand,
                price=1_000_000 + index,
                stock_qty=3,
            )

    def shop(self, params=None, **extra):
        return self.client.get(reverse('products:shop'), params or {}, **extra)

    def test_first_page_shows_only_page_size_products(self):
        response = self.shop()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['products']), self.PAGE_SIZE)
        self.assertContains(response, f'نمایش 1 تا {self.PAGE_SIZE} از 15 کالا')

    def test_second_page_shows_the_remaining_products(self):
        response = self.shop({'page': 2})
        self.assertEqual(len(response.context['products']), 3)
        self.assertContains(response, 'نمایش 13 تا 15 از 15 کالا')

    def test_page_links_keep_active_filters_and_sort(self):
        response = self.shop({'brand': 'samsung', 'sort': 'cheapest'})
        content = response.content.decode()
        self.assertIn('page=2', content)
        self.assertRegex(content, r'\?[^"]*brand=samsung[^"]*page=2|\?[^"]*page=2[^"]*brand=samsung')
        self.assertIn('sort=cheapest', content)

    def test_out_of_range_page_falls_back_to_the_last_page(self):
        response = self.shop({'page': 999})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نمایش 13 تا 15 از 15 کالا')

    def test_empty_result_hides_pagination_and_shows_empty_state(self):
        response = self.shop({'brand': 'apple'})
        content = response.content.decode()
        self.assertContains(response, 'کالایی با این فیلترها یافت نشد')
        self.assertNotIn('aria-label="صفحه‌بندی کالاها"', content)
        self.assertEqual(content.count('/cart/add/'), 0)

    def test_applying_a_filter_resets_to_the_first_page(self):
        response = self.shop({'brand': 'samsung'})
        self.assertContains(response, 'نمایش 1 تا 12 از 15 کالا')

    def test_htmx_page_request_returns_the_grid_partial_only(self):
        response = self.shop({'page': 2}, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('<html', content)
        self.assertIn('id="product-grid"', content)
        self.assertIn('نمایش 13 تا 15 از 15 کالا', content)

    def test_pagination_links_target_the_grid_and_show_loading_indicator(self):
        content = self.shop().content.decode()
        self.assertIn('aria-label="صفحه‌بندی کالاها"', content)
        self.assertIn('hx-indicator="#grid-loading"', content)
        self.assertIn('id="grid-loading"', content)
        self.assertIn('در حال بارگذاری نتایج', content)


class CatalogSinglePageTests(TestCase):
    """کاتالوگی که در یک صفحه جا می‌شود نباید کنترل صفحه‌بندی نشان دهد."""

    def test_single_page_result_has_no_pagination_nav(self):
        category = Category.objects.create(name="تبلت", slug="tablets")
        Product.objects.create(
            title="تبلت تست", slug="tablet-1", sku="TAB-1",
            category=category, price=5_000_000, stock_qty=2,
        )
        content = Client().get(reverse('products:shop')).content.decode()
        self.assertNotIn('aria-label="صفحه‌بندی کالاها"', content)
        self.assertIn('1 کالا', content)
