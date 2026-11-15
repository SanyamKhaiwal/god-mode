from .models import Cart
from .pricing import line_subtotal, cart_subtotal
from .discounts import bulk_discount
from .tax import line_tax


def build_invoice(cart: Cart) -> dict:
    sub = cart_subtotal(cart)
    disc = bulk_discount(cart)
    ratio = (sub - disc) / sub if sub else 0
    tax = round(sum(line_tax(l, line_subtotal(l) * ratio) for l in cart.lines), 2)
    return {"subtotal": sub, "discount": disc, "tax": tax, "total": round(sub - disc + tax, 2)}
