from django.test import TestCase, Client
from django.urls import reverse
from products.models import Category, Brand, Product
from cart.models import Cart, CartItem
from orders.models import Order


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
