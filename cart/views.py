import json

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from products.models import Product
from .models import Cart, CartItem


def _toast(response, message, tone='success'):
    """الصاق اعلان شناور به پاسخ htmx از طریق رویداد HX-Trigger."""
    if not message:
        return response
    # ensure_ascii=True تا هدر (که فقط لاتین-۱ می‌پذیرد) با متن فارسی نشکند.
    response['HX-Trigger'] = json.dumps(
        {'zitro:toast': {'message': message, 'tone': tone}},
        ensure_ascii=True,
    )
    return response


def _get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart


def cart_detail_view(request):
    cart = _get_or_create_cart(request)
    context = {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
    }
    if request.htmx and request.headers.get('HX-Target') in ('main-content-area', 'main'):
        return render(request, 'cart/partials/cart_full_partial.html', context)
    return render(request, 'cart/cart_detail.html', context)


@require_POST
def cart_add_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _get_or_create_cart(request)

    try:
        requested = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        requested = 1
    requested = max(requested, 1)

    # سقف تعداد = موجودی قابل فروش (انبار منهای رزرو سفارش‌های پرداخت‌نشده)
    available = product.available_qty
    cart_item = cart.items.filter(product=product).first()
    current = cart_item.quantity if cart_item else 0
    added = 0
    limit_message = ''

    if available <= 0:
        limit_message = f"«{product.title}» در حال حاضر موجود نیست."
    elif current + requested > available:
        added = max(available - current, 0)
        limit_message = (
            f"بیشتر از موجودی انبار نمی‌توانید سفارش دهید؛ «{product.title}» "
            f"حداکثر {available} عدد موجود است."
        )
    else:
        added = requested

    if added:
        if cart_item:
            cart_item.quantity += added
            cart_item.save()
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=added)

    context = {
        'product': product,
        'global_cart_count': cart.total_items,
        'toast_message': limit_message,
        'toast_tone': 'warning',
        'toast_default': f"«{product.title}» به سبد خرید اضافه شد." if added else '',
    }

    # HTMX response: return new cart badge and add-to-cart popup modal
    if request.htmx:
        if limit_message:
            return _toast(
                render(request, 'cart/partials/cart_badge.html', context),
                limit_message, 'warning'
            )
        return _toast(render(request, 'cart/partials/cart_add_response.html', context), context['toast_default'])

    if limit_message:
        messages.warning(request, limit_message)
    elif added:
        messages.success(request, context['toast_default'])

    return redirect('cart:cart_detail')


@require_POST
def cart_update_view(request, item_id):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    action = request.POST.get('action')
    limit_message = ''
    if action == 'increase':
        if item.quantity < item.product.available_qty:
            item.quantity += 1
            item.save()
        else:
            limit_message = f"«{item.product.title}» حداکثر {item.product.available_qty} عدد موجود است."
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()

    context = {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
        'global_cart_count': cart.total_items,
        'toast_message': limit_message,
        'toast_tone': 'warning',
    }

    if request.htmx:
        return _toast(
            render(request, 'cart/partials/cart_table.html', context),
            limit_message, 'warning'
        )

    if limit_message:
        messages.warning(request, limit_message)
    return redirect('cart:cart_detail')


@require_POST
def cart_remove_view(request, item_id):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()

    context = {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
        'global_cart_count': cart.total_items,
    }

    if request.htmx:
        return render(request, 'cart/partials/cart_table.html', context)

    return redirect('cart:cart_detail')


def cart_recover_view(request, token):
    """
    بازیابی امن سبد خرید از طریق لینک پیامک یادآوری:
    - بررسی صحت و انقضای توکن
    - اعتبارسنجی موجودی و قیمت جاری اقلام
    - هماهنگ‌سازی سشن یا هدایت برای ورود
    - اعمال خودکار کد تخفیف اختصاصی در صورت وجود
    """
    from django.utils import timezone
    cart = Cart.objects.filter(recovery_token=token).prefetch_related('items__product').first()
    if not cart:
        messages.error(request, "لینک بازیابی سبد خرید نامعتبر است.")
        return redirect('cart:cart_detail')

    if cart.recovery_token_expires_at and cart.recovery_token_expires_at < timezone.now():
        messages.warning(request, "مهلت استفاده از این لینک بازیابی به پایان رسیده است.")
        return redirect('cart:cart_detail')

    if cart.converted_order_id:
        messages.info(request, "این سبد خرید قبلاً به سفارش تبدیل شده است.")
        return redirect('cart:cart_detail')

    if not cart.user:
        if not request.session.session_key:
            request.session.create()
        if request.user.is_authenticated:
            user_cart, _ = Cart.objects.get_or_create(user=request.user)
            for item in cart.items.all():
                u_item, created = CartItem.objects.get_or_create(cart=user_cart, product=item.product)
                if not created:
                    u_item.quantity += item.quantity
                else:
                    u_item.quantity = item.quantity
                u_item.save()
            cart.recovery_status = 'recovered'
            cart.save(update_fields=['recovery_status'])
        else:
            # همگام‌سازی سشن مهمان
            if cart.session_key != request.session.session_key:
                # اگر سشن متفاوتی در همان مرورگر هست، انتقال اقلام
                curr_cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
                for item in cart.items.all():
                    c_item, created = CartItem.objects.get_or_create(cart=curr_cart, product=item.product)
                    if not created:
                        c_item.quantity = max(c_item.quantity, item.quantity)
                    else:
                        c_item.quantity = item.quantity
                    c_item.save()
    else:
        if not request.user.is_authenticated:
            messages.info(request, f"سلام {cart.customer_display_name}! لطفاً جهت مشاهده سبد خرید خود وارد شوید.")
            return redirect(f"/accounts/login/?next=/cart/recover/{token}/")
        elif request.user != cart.user:
            messages.warning(request, "شما با حساب کاربری دیگری وارد شده‌اید. لطفاً با حساب اصلی خود وارد شوید.")
            return redirect('cart:cart_detail')

    last_attempt = cart.recovery_attempts.filter(coupon__isnull=False, status='sent').order_by('-created_at').first()
    if last_attempt and last_attempt.coupon and not last_attempt.coupon.is_expired:
        request.session['coupon_code'] = last_attempt.coupon.code
        messages.success(request, f"سبد خرید شما بازیابی شد و کد تخفیف «{last_attempt.coupon.code}» برای شما فعال گردید!")
    else:
        messages.success(request, "سبد خرید شما با موفقیت بازیابی شد.")

    for item in cart.items.all():
        if item.product.available_qty < item.quantity:
            messages.warning(
                request,
                f"موجودی کالای «{item.product.title}» محدود است (موجودی فعلی: {item.product.available_qty})."
            )

    return redirect('cart:cart_detail')

