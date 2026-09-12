from decimal import Decimal

FREE_SHIPPING_THRESHOLD = Decimal('500.00')
STANDARD_SHIPPING_FEE = Decimal('50.00')

def calculate_shipping(subtotal: Decimal) -> Decimal:
    """
    Authoritative server-side shipping calculation.
    Free shipping for orders of ₹500 or more; ₹50 flat rate below ₹500.
    """
    if not subtotal or subtotal <= 0:
        return Decimal('0.00')
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return STANDARD_SHIPPING_FEE
