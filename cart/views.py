from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .models import Cart, CartItem
from .utils import calculate_shipping
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
        request.session['guest_cart_id'] = cart.id
        request.session.modified = True
        return cart


# ---------------------------------------------------------------------------
# Helper: compute cart totals
# ---------------------------------------------------------------------------

def _cart_totals(cart):
    """
    Return (cart_items queryset, subtotal Decimal, shipping Decimal, total Decimal).

    cart_items is pre-fetched with product and category to minimise queries.
    """
    cart_items = (
        cart.items
        .select_related('product', 'product__category')
        .order_by('id')
    )
    subtotal = sum(item.total_price for item in cart_items)
    shipping = calculate_shipping(subtotal)
    total = subtotal + shipping
    return cart_items, subtotal, shipping, total


def _is_ajax(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
        or request.POST.get('ajax') == 'true'
    )


# ---------------------------------------------------------------------------
# View: cart page
# ---------------------------------------------------------------------------

def cart_view(request):
    cart = _get_or_create_cart(request)
    cart_items, subtotal, shipping, total = _cart_totals(cart)

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
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
    if not product.is_active or (product.stock is not None and product.stock <= 0):
        if _is_ajax(request):
            return JsonResponse({'error': 'Product is currently out of stock.'}, status=400)
        messages.error(request, f'Sorry, "{product.name}" is out of stock.')
        return redirect(request.META.get('HTTP_REFERER', 'shop'))

    cart = _get_or_create_cart(request)

    # Safely parse requested quantity (default 1)
    try:
        qty = int(request.POST.get('qty') or request.POST.get('quantity') or 1)
        if qty < 1:
            qty = 1
    except (ValueError, TypeError):
        qty = 1

    # Cap at available stock
    if product.stock is not None and qty > product.stock:
        qty = product.stock

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': qty},
    )

    if not created:
        new_qty = cart_item.quantity + qty
        if product.stock is not None and new_qty > product.stock:
            new_qty = product.stock
            messages.warning(request, f'Only {product.stock} items available in stock.')
        cart_item.quantity = new_qty
        cart_item.save(update_fields=['quantity'])

    messages.success(request, f'"{product.name}" added to your bag.')

    cart_items, subtotal, shipping, total = _cart_totals(cart)
    cart_count = sum(i.quantity for i in cart_items)

    if _is_ajax(request):
        return JsonResponse({
            'status': 'ok',
            'message': f'"{product.name}" added to your bag.',
            'cart_count': cart_count,
            'subtotal': f"{subtotal:.2f}",
            'shipping': f"{shipping:.2f}",
            'total': f"{total:.2f}",
        })

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    safe_next = next_url if next_url and next_url.startswith('/') else None
    return redirect(safe_next or 'shop')


# ---------------------------------------------------------------------------
# View: update cart item quantity
# ---------------------------------------------------------------------------

@require_POST
def update_cart(request, item_id):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        new_qty = int(request.POST.get('quantity', 0))
    except (ValueError, TypeError):
        if _is_ajax(request):
            return JsonResponse({'error': 'Invalid quantity.'}, status=400)
        messages.error(request, 'Invalid quantity. Please enter a whole number.')
        return redirect('cart')

    item_deleted = False
    if new_qty <= 0:
        cart_item.delete()
        item_deleted = True
        messages.success(request, f'"{cart_item.product.name}" removed from your bag.')
    else:
        # Enforce inventory limit
        if cart_item.product.stock is not None and new_qty > cart_item.product.stock:
            new_qty = cart_item.product.stock
            messages.warning(request, f'Only {cart_item.product.stock} items available in stock.')
        cart_item.quantity = new_qty
        cart_item.save(update_fields=['quantity'])

    cart_items, subtotal, shipping, total = _cart_totals(cart)
    cart_count = sum(i.quantity for i in cart_items)

    if _is_ajax(request):
        return JsonResponse({
            'status': 'ok',
            'item_id': item_id,
            'item_deleted': item_deleted,
            'item_quantity': 0 if item_deleted else cart_item.quantity,
            'item_total': '0.00' if item_deleted else f"{cart_item.total_price:.2f}",
            'cart_count': cart_count,
            'subtotal': f"{subtotal:.2f}",
            'shipping': f"{shipping:.2f}",
            'total': f"{total:.2f}",
        })

    # If referer is cart, redirect to cart; otherwise stay on referer if safe
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    safe_next = next_url if next_url and next_url.startswith('/') else None
    return redirect(safe_next or 'cart')


# ---------------------------------------------------------------------------
# View: remove cart item
# ---------------------------------------------------------------------------

@require_POST
def remove_from_cart(request, item_id):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()

    messages.success(request, f'"{product_name}" removed from your bag.')

    cart_items, subtotal, shipping, total = _cart_totals(cart)
    cart_count = sum(i.quantity for i in cart_items)

    if _is_ajax(request):
        return JsonResponse({
            'status': 'ok',
            'item_id': item_id,
            'item_deleted': True,
            'cart_count': cart_count,
            'subtotal': f"{subtotal:.2f}",
            'shipping': f"{shipping:.2f}",
            'total': f"{total:.2f}",
        })

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    safe_next = next_url if next_url and next_url.startswith('/') else None
    return redirect(safe_next or 'cart')
