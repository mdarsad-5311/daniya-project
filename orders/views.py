from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models import Order, OrderItem
from .forms import OrderForm
from cart.models import Cart, CartItem
from cart.utils import calculate_shipping


# ---------------------------------------------------------------------------
# Helper: get the current user's cart and items (reuses cart app's logic)
# ---------------------------------------------------------------------------

def _get_user_cart(request):
    """
    Return (cart, cart_items_qs) for the authenticated user.
    Returns (None, CartItem.objects.none()) when no cart exists.
    """
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return None, CartItem.objects.none()

    cart_items = (
        cart.items
        .select_related('product', 'product__category')
        .order_by('id')
    )
    return cart, cart_items


def _matches_pending_order(pending_order, cleaned_data, fresh_items, shipping, total):
    """
    Verify if an existing pending order matches the current checkout state.
    Returns True only if shipping details, items, quantities, and totals match exactly.
    """
    for field in ('first_name', 'last_name', 'email', 'phone', 'address', 'city', 'postal_code'):
        if getattr(pending_order, field, '') != cleaned_data.get(field, ''):
            return False

    if pending_order.shipping_cost != shipping or pending_order.total_amount != total:
        return False

    order_items = list(pending_order.items.order_by('product_id'))
    if len(order_items) != len(fresh_items):
        return False

    fresh_sorted = sorted(fresh_items, key=lambda x: x.product_id)
    for o_item, c_item in zip(order_items, fresh_sorted):
        if (
            o_item.product_id != c_item.product_id
            or o_item.quantity != c_item.quantity
            or o_item.price != c_item.product.price
        ):
            return False

    return True


# ---------------------------------------------------------------------------
# View: checkout
# ---------------------------------------------------------------------------

@login_required
def checkout_view(request):
    cart, cart_items = _get_user_cart(request)

    # ── Guard: empty cart ──────────────────────────────────────────────
    if cart is None or not cart_items.exists():
        messages.info(request, 'Your bag is empty — add something before checking out.')
        return redirect('cart')

    # Pre-compute totals server-side
    subtotal = sum(item.total_price for item in cart_items)
    shipping = calculate_shipping(subtotal)
    total = subtotal + shipping

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Re-verify cart is not empty (race-condition guard)
            fresh_items = list(
                cart.items
                .select_related('product')
                .order_by('id')
            )
            if not fresh_items:
                messages.info(request, 'Your bag is empty — add something before checking out.')
                return redirect('cart')

            # Enforce stock check
            for item in fresh_items:
                if not item.product.is_active or (item.product.stock is not None and item.product.stock < item.quantity):
                    messages.error(
                        request,
                        f'"{item.product.name}" only has {item.product.stock or 0} in stock. Please update your bag.'
                    )
                    return redirect('cart')

            # Check if pending order can be safely reused
            pending_order_id = request.session.get('pending_order_id')
            if pending_order_id:
                pending_order = Order.objects.filter(
                    id=pending_order_id,
                    user=request.user,
                    paid=False,
                    payment_status__in=('pending', 'failed'),
                ).first()

                if pending_order and _matches_pending_order(pending_order, form.cleaned_data, fresh_items, shipping, total):
                    return redirect('payment:create', order_id=pending_order.id)
                else:
                    # Invalidate stale pending order reference
                    request.session.pop('pending_order_id', None)

            # Create the order and snapshot its items.
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.shipping_cost = shipping
                order.total_amount = total
                order.paid = False
                order.payment_status = 'pending'
                order.status = 'Pending'
                order.save()

                for item in fresh_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        price=item.product.price,   # snapshot current price
                        quantity=item.quantity,
                    )

            request.session['pending_order_id'] = order.id
            return redirect('payment:create', order_id=order.id)
    else:
        # Pre-fill name/email from the authenticated user
        initial = {}
        user = request.user
        if user.first_name:
            initial['first_name'] = user.first_name
        if user.last_name:
            initial['last_name'] = user.last_name
        if user.email:
            initial['email'] = user.email
        form = OrderForm(initial=initial)

    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'orders/checkout.html', context)


# ---------------------------------------------------------------------------
# View: order confirmation
# ---------------------------------------------------------------------------

@login_required
def order_confirmation_view(request, order_id):
    # Scoped to current user — prevents IDOR
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_status != 'paid' or not order.paid:
        messages.info(request, 'Complete payment to view your order confirmation.')
        return redirect('payment:create', order_id=order.id)
    order_items = order.items.select_related('product').order_by('id')

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'orders/confirmation.html', context)


# ---------------------------------------------------------------------------
# View: my orders (list)
# ---------------------------------------------------------------------------

@login_required
def my_orders_view(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items', 'items__product')
        .order_by('-created_at')
    )
    return render(request, 'orders/my_orders.html', {'orders': orders})


# ---------------------------------------------------------------------------
# View: order detail
# ---------------------------------------------------------------------------

@login_required
def order_detail_view(request, order_id):
    # Scoped to current user — prevents IDOR
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.select_related('product').order_by('id')

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'orders/order_detail.html', context)
