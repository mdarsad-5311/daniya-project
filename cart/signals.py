from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart, CartItem

@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, user, request, **kwargs):
    """
    When an anonymous user logs in or registers:
    Merge their guest session cart items into their authenticated user cart.
    """
    if not request or not hasattr(request, 'session'):
        return

    guest_cart = None
    guest_cart_id = request.session.get('guest_cart_id')
    if guest_cart_id:
        guest_cart = Cart.objects.filter(id=guest_cart_id, user=None).first()

    if not guest_cart:
        session_key = getattr(request, '_guest_session_key', None) or request.session.session_key
        if session_key:
            guest_cart = Cart.objects.filter(user=None, session_id=session_key).first()

    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for guest_item in guest_cart.items.select_related('product').all():
        product = guest_item.product
        if not product.is_active:
            continue

        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            product=product,
            defaults={'quantity': guest_item.quantity},
        )
        if not created:
            # Combine quantity, capping at product stock if available
            new_qty = user_item.quantity + guest_item.quantity
            if product.stock and new_qty > product.stock:
                new_qty = product.stock
            user_item.quantity = new_qty
            user_item.save(update_fields=['quantity'])

    # Delete the guest cart after merging
    guest_cart.delete()
    if 'guest_cart_id' in request.session:
        del request.session['guest_cart_id']
        request.session.modified = True

