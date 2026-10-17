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
