from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Cart, CartItem
from products.models import Product


# ---------------------------------------------------------------------------
# Helper: resolve or create the current cart for this request
# ---------------------------------------------------------------------------

def _get_or_create_cart(request):
    """
    Return the Cart for the current visitor.

    Authenticated users  →  Cart.user = request.user  (OneToOne)
    Guest users          →  Cart.session_id = session key
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        # Ensure the session exists so we get a reliable key.
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(
            user=None,
            session_id=session_key,
        )
        return cart


# ---------------------------------------------------------------------------
# Helper: compute cart totals
# ---------------------------------------------------------------------------

def _cart_totals(cart):
    """
    Return (cart_items queryset, subtotal Decimal, total Decimal).

    cart_items is pre-fetched with product and category to minimise queries.
    """
    cart_items = (
        cart.items
        .select_related('product', 'product__category')
        .order_by('id')
    )
    subtotal = sum(item.total_price for item in cart_items)
    # Phase 2: total = subtotal  (no tax / shipping / discount yet)
    total = subtotal
    return cart_items, subtotal, total


# ---------------------------------------------------------------------------
# View: cart page
# ---------------------------------------------------------------------------

def cart_view(request):
    cart = _get_or_create_cart(request)
    cart_items, subtotal, total = _cart_totals(cart)

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total': total,
        # discount is 0 in Phase 2
        'discount': Decimal('0.00'),
        'cart_count': sum(item.quantity for item in cart_items),
    }
    return render(request, 'cart/cart.html', context)


# ---------------------------------------------------------------------------
# View: add to cart
# ---------------------------------------------------------------------------

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_or_create_cart(request)

    # Safely parse requested quantity (default 1)
    try:
        qty = int(request.POST.get('qty') or request.POST.get('quantity') or 1)
        if qty < 1:
            qty = 1
    except (ValueError, TypeError):
        qty = 1

    # Get or create the CartItem for this product — prevents duplicates
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': qty},
    )

    if not created:
        # Product already in cart — increment quantity
        cart_item.quantity += qty
        cart_item.save(update_fields=['quantity'])

    messages.success(request, f'"{product.name}" added to your bag.')

    # Redirect back to where the user came from, or fall back to shop
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    safe_next = next_url if next_url and next_url.startswith('/') else None
    return redirect(safe_next or 'shop')


# ---------------------------------------------------------------------------
# View: update cart item quantity
# ---------------------------------------------------------------------------

@require_POST
def update_cart(request, item_id):
    cart = _get_or_create_cart(request)

    # Scope the lookup to the current cart — prevents cross-user access
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        new_qty = int(request.POST.get('quantity', 0))
    except (ValueError, TypeError):
        messages.error(request, 'Invalid quantity. Please enter a whole number.')
        return redirect('cart')

    if new_qty <= 0:
        cart_item.delete()
        messages.success(request, f'"{cart_item.product.name}" removed from your bag.')
    else:
        cart_item.quantity = new_qty
        cart_item.save(update_fields=['quantity'])

    return redirect('cart')


# ---------------------------------------------------------------------------
# View: remove cart item
# ---------------------------------------------------------------------------

@require_POST
def remove_from_cart(request, item_id):
    cart = _get_or_create_cart(request)

    # Scope to the current cart — prevents cross-user deletion
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()

    messages.success(request, f'"{product_name}" removed from your bag.')
    return redirect('cart')
