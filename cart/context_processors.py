from .models import Cart


def cart_processor(request):
    cart = None
    cart_items_count = 0
    cart_total_price = 0

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()

    if cart:
        cart_items_count = cart.total_items
        cart_total_price = cart.total_price

    return {
        'global_cart': cart,
        'global_cart_count': cart_items_count,
        'global_cart_total': cart_total_price,
    }
