from .models import Cart
from .pricing import cart_subtotal, line_subtotal

SAVE10_CATEGORIES = {"food", "books"}


def bulk_discount(cart: Cart) -> float:
    """5% off the whole cart when the subtotal is 5000 or more."""
    sub = cart_subtotal(cart)
    return round(sub * 0.05, 2) if sub >= 5000 else 0.0


def coupon_discount(cart: Cart) -> float:
    """SAVE10: 10% off food and books lines. FLAT500: 500 off a subtotal of 2000 or more."""
    if cart.coupon is None:
        return 0.0
    if cart.coupon == "SAVE10":
        eligible = sum(line_subtotal(l) for l in cart.lines if l.item.category in SAVE10_CATEGORIES)
        return round(eligible * 0.10, 2)
    if cart.coupon == "FLAT500":
        return 500.0 if cart_subtotal(cart) >= 2000 else 0.0
    raise ValueError("unknown coupon")


def total_discount(cart: Cart) -> float:
    """Bulk plus coupon discount, never more than the subtotal."""
    return round(min(bulk_discount(cart) + coupon_discount(cart), cart_subtotal(cart)), 2)
