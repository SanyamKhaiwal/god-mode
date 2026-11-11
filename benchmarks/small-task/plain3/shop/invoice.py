from .models import Cart
from .pricing import line_subtotal, cart_subtotal
from .discounts import total_discount
from .tax import line_tax, split_tax


def build_invoice(cart: Cart) -> dict:
    sub = cart_subtotal(cart)
    disc = total_discount(cart)
    ratio = (sub - disc) / sub if sub else 0
    tax = round(sum(line_tax(l, line_subtotal(l) * ratio) for l in cart.lines), 2)
    return {"subtotal": sub, "discount": disc, **split_tax(tax, cart.customer_state),
            "tax": tax, "total": round(sub - disc + tax, 2)}
