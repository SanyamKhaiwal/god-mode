from .models import Cart
from .pricing import cart_subtotal


def bulk_discount(cart: Cart) -> float:
    """5% off the whole cart when the subtotal is 5000 or more."""
    sub = cart_subtotal(cart)
    return round(sub * 0.05, 2) if sub >= 5000 else 0.0
