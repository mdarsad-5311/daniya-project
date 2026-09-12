from decimal import Decimal
from .models import Cart, CartItem
from .utils import calculate_shipping


def cart_context(request):
    """
    Inject cart data into every template context.

    Provides:
        cart_items      — queryset of CartItem (product + category pre-fetched)
        cart_count      — total quantity of all items (sum of quantities)
        cart_subtotal   — Decimal subtotal
        cart_shipping   — Decimal shipping (calculated on server)
        cart_total      — Decimal total (subtotal + shipping)
        cart_discount   — Decimal discount
    """
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                # No session yet — return empty context without creating a session/cart
                return _empty_context()
            cart = Cart.objects.filter(
                user=None,
                session_id=session_key,
            ).first()

        if cart is None:
            return _empty_context()

        cart_items = (
            cart.items
            .select_related('product', 'product__category')
            .order_by('id')
        )

        subtotal = sum(item.total_price for item in cart_items)
        shipping = calculate_shipping(subtotal)
        total = subtotal + shipping
        count = sum(item.quantity for item in cart_items)

        return {
            'cart_items': cart_items,
            'cart_count': count,
            'cart_subtotal': subtotal,
            'cart_shipping': shipping,
            'cart_total': total,
            'cart_discount': Decimal('0.00'),
        }

    except Exception:
        # Never crash the request due to a cart error
        return _empty_context()


def _empty_context():
    return {
        'cart_items': [],
        'cart_count': 0,
        'cart_subtotal': Decimal('0.00'),
        'cart_shipping': Decimal('0.00'),
        'cart_total': Decimal('0.00'),
        'cart_discount': Decimal('0.00'),
    }

