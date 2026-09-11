from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import Wishlist, WishlistItem
from products.models import Product


# ---------------------------------------------------------------------------
# View: wishlist page
# ---------------------------------------------------------------------------

@login_required
def wishlist_view(request):
    """
    Display the current user's wishlist.
    Only the authenticated user's own wishlist is ever exposed.
    """
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    items = (
        wishlist.items
        .select_related('product', 'product__category')
        .order_by('-added_at')
    )
    return render(request, 'wishlist/wishlist.html', {
        'wishlist': wishlist,
        'items': items,
    })


# ---------------------------------------------------------------------------
# View: add to wishlist
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_to_wishlist(request, product_id):
    """
    Add a product to the current user's wishlist.
    Duplicate protection: get_or_create ensures 1 WishlistItem per product.
    """
    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    # unique_together on (wishlist, product) prevents duplicates at DB level;
    # get_or_create prevents it at the application level too.
    _, created = WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        product=product,
    )

    if created:
        messages.success(request, f'"{product.name}" added to your wishlist.')
    else:
        messages.info(request, f'"{product.name}" is already in your wishlist.')

    # Redirect to next (if posted), HTTP referer, or product detail
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    safe_next = next_url if next_url and next_url.startswith('/') else None
    return redirect(safe_next or 'product_detail', product.slug)


# ---------------------------------------------------------------------------
# View: remove from wishlist
# ---------------------------------------------------------------------------

@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    """
    Remove a WishlistItem that belongs to the current user.
    IDOR-safe: scopes lookup to the current user's wishlist.
    User B cannot remove User A's items by guessing an item_id.
    """
    item = get_object_or_404(
        WishlistItem,
        id=item_id,
        wishlist__user=request.user,   # strict ownership check
    )
    product_name = item.product.name
    item.delete()
    messages.success(request, f'"{product_name}" removed from your wishlist.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    safe_next = next_url if next_url and next_url.startswith('/') else None
    return redirect(safe_next or 'wishlist')
