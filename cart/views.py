from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from products.models import Product
from .models import Cart, CartItem


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
    return render(request, 'cart/cart_detail.html', context)


@require_POST
def cart_add_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _get_or_create_cart(request)

    quantity = int(request.POST.get('quantity', 1))
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    # HTMX response: return new cart badge
    if request.htmx:
        return render(request, 'cart/partials/cart_badge.html', {
            'global_cart_count': cart.total_items
        })

    return redirect('cart:cart_detail')


@require_POST
def cart_update_view(request, item_id):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    action = request.POST.get('action')
    if action == 'increase':
        item.quantity += 1
        item.save()
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
    }

    if request.htmx:
        return render(request, 'cart/partials/cart_table.html', context)

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
