from .models import Wishlist, WishlistItem


def wishlist_context(request):
    """
    Context processor to inject wishlist data into all templates.

    Provides:
        wishlist_count       - integer count of items in the authenticated user's wishlist (0 for anonymous)
        wishlist_product_ids - set of product IDs currently in the authenticated user's wishlist (empty set for anonymous)
    """
    if request.user.is_authenticated:
        try:
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                items = wishlist.items.values_list('product_id', flat=True)
                product_ids = set(items)
                return {
                    'wishlist_count': len(product_ids),
                    'wishlist_product_ids': product_ids,
                }
        except Exception:
            pass

    return {
        'wishlist_count': 0,
        'wishlist_product_ids': set(),
    }
