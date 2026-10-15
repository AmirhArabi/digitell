import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from cart.models import Cart
from home.models import SiteSetting
from .models import Coupon, Order, OrderItem


def _get_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).first()
    session_key = request.session.session_key
    if session_key:
        return Cart.objects.filter(session_key=session_key).first()
    return None


def _clear_coupon(request):
    if 'coupon_code' in request.session:
        del request.session['coupon_code']


def _payment_summary(request, cart):
    """جمع‌بندی مالی سفارش: تخفیف کد، هزینه ارسال و مبلغ نهایی."""
    settings_obj = SiteSetting.get_settings()
    coupon = None
    coupon_error = None
    coupon_discount = 0

    code = (request.session.get('coupon_code') or '').strip().upper()
    if code:
        coupon = Coupon.objects.filter(code=code).first()
        if coupon:
            is_valid, message, coupon_discount = coupon.validate_for(cart.total_price)
            if not is_valid:
                coupon_error = message
                coupon_discount = 0
        else:
            coupon_error = "کد تخفیف وارد‌شده یافت نشد."

    products_total = cart.total_price
    free_threshold = settings_obj.free_shipping_threshold
    shipping_cost = 0 if (free_threshold and products_total >= free_threshold) else settings_obj.shipping_cost
    if products_total == 0:
        shipping_cost = 0
    final_amount = max(products_total - coupon_discount, 0) + shipping_cost

    return {
        'settings': settings_obj,
        'coupon': coupon,
        'coupon_code': code,
        'coupon_error': coupon_error,
        'coupon_discount': coupon_discount,
        'shipping_cost': shipping_cost,
        'shipping_methods': Order.SHIPPING_CHOICES,
        'final_amount': final_amount,
    }


def apply_coupon_view(request):
    """ثبت/حذف کد تخفیف در سشن و بازگشت به صفحه تسویه."""
    if request.method == 'POST':
        code = (request.POST.get('coupon_code') or '').strip().upper()
        cart = _get_cart(request)
        if not code:
            _clear_coupon(request)
            messages.info(request, "کد تخفیف حذف شد.")
        elif not cart or cart.items.count() == 0:
            messages.error(request, "سبد خرید شما خالی است.")
        else:
            coupon = Coupon.objects.filter(code=code).first()
            if not coupon:
                messages.error(request, "کد تخفیف وارد‌شده معتبر نیست.")
            else:
                is_valid, message, _ = coupon.validate_for(cart.total_price)
                if is_valid:
                    request.session['coupon_code'] = code
                    messages.success(request, f"کد تخفیف «{code}» اعمال شد.")
                else:
                    _clear_coupon(request)
                    messages.error(request, message)
    return redirect('orders:checkout')


def checkout_view(request):
    cart = _get_cart(request)
    if not cart or cart.items.count() == 0:
        messages.warning(request, "سبد خرید شما خالی است.")
        return redirect('products:shop')

    if request.method == 'POST':
        recipient_name = request.POST.get('recipient_name', '').strip()
        recipient_phone = request.POST.get('recipient_phone', '').strip()
        province = request.POST.get('province', '').strip()
        city = request.POST.get('city', '').strip()
        shipping_address = request.POST.get('shipping_address', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        payment_method = request.POST.get('payment_method', 'mock_gateway')
        notes = request.POST.get('notes', '').strip()
        shipping_method = request.POST.get('shipping_method', 'post')
        if shipping_method not in dict(Order.SHIPPING_CHOICES):
            shipping_method = 'post'

        summary = _payment_summary(request, cart)

        if not all([recipient_name, recipient_phone, city, shipping_address]):
            messages.error(request, "لطفاً تمام اطلاعات ستاره‌دار آدرس را وارد فرمایید.")
            return render(request, 'orders/checkout.html', {
                'cart': cart,
                'items': cart.items.select_related('product').all(),
                **summary,
            })

        # Create Order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            province=province,
            city=city,
            shipping_address=shipping_address,
            postal_code=postal_code,
            products_total=cart.total_price,
            discount_amount=cart.total_discount,
            coupon=summary['coupon'] if summary['coupon_discount'] else None,
            coupon_code=summary['coupon_code'] if summary['coupon_discount'] else '',
            coupon_discount=summary['coupon_discount'],
            shipping_cost=summary['shipping_cost'],
            shipping_method=shipping_method,
            final_amount=summary['final_amount'],
            payment_method=payment_method,
            notes=notes,
        )

        # Snapshot order items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_title=item.product.title,
                product_sku=item.product.sku,
                unit_price=item.product.price,
                quantity=item.quantity,
                total_price=item.line_total,
            )

        if payment_method == 'mock_gateway':
            return redirect('orders:mock_payment', order_number=order.order_number)
        else:
            # Cash on delivery
            cart.items.all().delete()
            order.status = 'paid'
            order.save()
            if order.coupon_id:
                Coupon.objects.filter(pk=order.coupon_id).update(used_count=order.coupon.used_count + 1)
            _clear_coupon(request)
            return redirect('orders:order_success', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
        **_payment_summary(request, cart),
    })


def mock_payment_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'success':
            order.payment_status = 'successful'
            order.status = 'paid'
            order.transaction_id = f"TRX-{uuid.uuid4().hex[:10].upper()}"
            order.save()

            # ثبت آمار استفاده از کد تخفیف
            if order.coupon_id:
                Coupon.objects.filter(pk=order.coupon_id).update(used_count=order.coupon.used_count + 1)

            # Empty Cart
            cart = _get_cart(request)
            if cart:
                cart.items.all().delete()
            _clear_coupon(request)

            messages.success(request, f"پرداخت با موفقیت انجام شد. کد پیگیری: {order.transaction_id}")
            return redirect('orders:order_success', order_number=order.order_number)
        else:
            order.payment_status = 'failed'
            order.save()
            messages.error(request, "تراکنش توسط کاربر لغو شد یا با خطا مواجه شد.")
            return redirect('cart:cart_detail')

    return render(request, 'orders/mock_payment.html', {'order': order})


def order_success_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'orders/order_success.html', {'order': order})


def order_tracking_view(request):
    order = None
    searched = False
    if request.method == 'POST' or request.GET.get('order_number'):
        order_num = request.POST.get('order_number') or request.GET.get('order_number')
        phone = request.POST.get('phone') or request.GET.get('phone')
        searched = True
        if order_num:
            query = Order.objects.filter(order_number__iexact=order_num.strip())
            if phone:
                query = query.filter(recipient_phone__icontains=phone.strip())
            order = query.first()

    return render(request, 'orders/order_tracking.html', {
        'order': order,
        'searched': searched
    })
