import uuid
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from cart.models import Cart
from home.models import SiteSetting
from accounts.models import Address, User
from accounts.services import normalize_phone, send_sms
from .models import Coupon, InsufficientStockError, Order, OrderItem


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


def _stock_error_message(error):
    """پیام فارسی خوانا از کمبود موجودی یک یا چند قلم سفارش."""
    parts = []
    for shortage in error.shortages:
        if shortage['available']:
            parts.append(
                f"«{shortage['title']}» فقط {shortage['available']} عدد موجود است "
                f"(درخواست شما: {shortage['requested']} عدد)."
            )
        else:
            parts.append(f"«{shortage['title']}» موجود نیست.")
    return "موجودی انبار کافی نیست؛ " + " ".join(parts)


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

    if request.user.is_authenticated:
        addresses = request.user.addresses.all()
        default_address = addresses.filter(is_default=True).first() or addresses.first()
    else:
        addresses = Address.objects.none()
        default_address = None

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
                'items': cart.items.select_related('product').prefetch_related('product__images').all(),
                'addresses': addresses,
                'default_address': default_address,
                'recipient_name': recipient_name,
                'recipient_phone': recipient_phone,
                'province': province,
                'city': city,
                'shipping_address': shipping_address,
                'postal_code': postal_code,
                **summary,
            })

        order_user = request.user if request.user.is_authenticated else None

        # Guest user auto-registration if not previously registered
        if not request.user.is_authenticated:
            norm_phone = normalize_phone(recipient_phone)
            existing_user = User.objects.filter(phone_number=norm_phone).first() or User.objects.filter(username=norm_phone).first()
            if existing_user:
                order_user = existing_user
            else:
                account_password = request.POST.get('account_password', '').strip()
                if account_password and len(account_password) < 4:
                    messages.error(request, "رمز عبور باید حداقل ۴ نویسه (کاراکتر) باشد.")
                    return render(request, 'orders/checkout.html', {
                        'cart': cart,
                        'items': cart.items.select_related('product').prefetch_related('product__images').all(),
                        'addresses': addresses,
                        'default_address': default_address,
                        'guest_needs_password': True,
                        'recipient_name': recipient_name,
                        'recipient_phone': recipient_phone,
                        'province': province,
                        'city': city,
                        'shipping_address': shipping_address,
                        'postal_code': postal_code,
                        **summary,
                    })

                if not account_password:
                    import random
                    account_password = f"{random.randint(100000, 999999)}"

                name_parts = recipient_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                new_user = User.objects.create_user(
                    username=norm_phone,
                    phone_number=norm_phone,
                    first_name=first_name,
                    last_name=last_name,
                    password=account_password,
                    is_verified=True,
                )

                # Save address in new user's dashboard
                Address.objects.create(
                    user=new_user,
                    title="آدرس ثبت سفارش",
                    recipient_name=recipient_name,
                    recipient_phone=norm_phone,
                    province=province or "تهران",
                    city=city or "تهران",
                    postal_address=shipping_address,
                    postal_code=postal_code,
                    is_default=True,
                )

                # Dispatch credentials SMS
                sms_message = (
                    f"سلام {recipient_name} عزیز،\n"
                    f"حساب کاربری شما در فروشگاه دیجی تل با موفقیت ایجاد شد.\n"
                    f"نام کاربری: {norm_phone}\n"
                    f"رمز عبور: {account_password}\n"
                    f"سفارش شما ثبت گردید و به درگاه پرداخت متصل می‌شوید."
                )
                send_sms(norm_phone, sms_message)

                # Log the user into the current session
                login(request, new_user)
                if not cart.user:
                    cart.user = new_user
                    cart.save(update_fields=['user'])
                order_user = new_user

        # Create Order and reserve its stock atomically: nothing is written to the
        # database unless every line can be reserved (no partial/oversold orders).
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=order_user,
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
                for item in cart.items.select_related('product'):
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_title=item.product.title,
                        product_sku=item.product.sku,
                        unit_price=item.product.price,
                        quantity=item.quantity,
                        total_price=item.line_total,
                    )

                order.reserve_stock()
        except InsufficientStockError as error:
            messages.error(request, _stock_error_message(error))
            return render(request, 'orders/checkout.html', {
                'cart': cart,
                'items': cart.items.select_related('product').prefetch_related('product__images').all(),
                'addresses': addresses,
                'default_address': default_address,
                **summary,
            })

        if payment_method == 'mock_gateway':
            return redirect('orders:mock_payment', order_number=order.order_number)
        else:
            # Cash on delivery: the goods leave the warehouse right away.
            cart.items.all().delete()
            order.status = 'paid'
            order.save()
            order.commit_stock()
            if order.coupon_id:
                Coupon.objects.filter(pk=order.coupon_id).update(used_count=order.coupon.used_count + 1)
            _clear_coupon(request)
            return redirect('orders:order_success', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'items': cart.items.select_related('product').prefetch_related('product__images').all(),
        'addresses': addresses,
        'default_address': default_address,
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

            # رزرو موجودی به خروج قطعی کالا از انبار تبدیل می‌شود.
            order.commit_stock()

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
            order.status = 'cancelled'
            order.save()
            # موجودی رزروشده آزاد می‌شود و شرط به سبد خرید بازمی‌گردد.
            order.release_stock()
            messages.error(request, "تراکنش توسط کاربر لغو شد یا با خطا مواجه شد.")
            return redirect('cart:cart_detail')

    return render(request, 'orders/mock_payment.html', {'order': order})


def order_success_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'orders/order_success.html', {'order': order})


def order_invoice_pdf_view(request, order_number):
    """دانلود فاکتور رسمی به صورت فایل PDF."""
    order = get_object_or_404(Order, order_number=order_number)

    # اگر سفارش متعلق به کاربری است و کاربر لاگین کرده باشد، دسترسی چک شود
    if order.user and request.user.is_authenticated and not request.user.is_staff and order.user != request.user:
        messages.error(request, "شما مجاز به دریافت فاکتور این سفارش نیستید.")
        return redirect('accounts:profile')

    from .invoice_pdf import generate_official_invoice_pdf
    pdf_bytes = generate_official_invoice_pdf(order)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Invoice-{order.order_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


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
