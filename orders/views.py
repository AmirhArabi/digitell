import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from cart.models import Cart
from .models import Order, OrderItem


def _get_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).first()
    session_key = request.session.session_key
    if session_key:
        return Cart.objects.filter(session_key=session_key).first()
    return None


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

        if not all([recipient_name, recipient_phone, city, shipping_address]):
            messages.error(request, "لطفاً تمام اطلاعات ستاره‌دار آدرس را وارد فرمایید.")
            return render(request, 'orders/checkout.html', {'cart': cart})

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
            shipping_cost=0,  # Free shipping promo
            final_amount=cart.total_price,
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
            return redirect('orders:order_success', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
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

            # Empty Cart
            cart = _get_cart(request)
            if cart:
                cart.items.all().delete()

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
