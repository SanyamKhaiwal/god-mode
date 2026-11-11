from .models import Cart
from .pricing import line_subtotal, cart_subtotal


def bulk_discount(cart: Cart) -> float:
    """5% off the whole cart when the subtotal is 5000 or more."""
    sub = cart_subtotal(cart)
    return round(sub * 0.05, 2) if sub >= 5000 else 0.0


def coupon_discount(cart: Cart) -> float:
    """Discount from cart.coupon; raises ValueError for unknown codes."""
    code = cart.coupon
    if code is None:
        return 0.0
    if code == "SAVE10":
        eligible = sum(line_subtotal(l) for l in cart.lines if l.item.category in ("food", "books"))
        return round(eligible * 0.10, 2)
    if code == "FLAT500":
        return 500.0 if cart_subtotal(cart) >= 2000 else 0.0
    raise ValueError("unknown coupon")


def total_discount(cart: Cart) -> float:
    """Bulk plus coupon discount, never more than the cart subtotal."""
    return round(min(bulk_discount(cart) + coupon_discount(cart), cart_subtotal(cart)), 2)
