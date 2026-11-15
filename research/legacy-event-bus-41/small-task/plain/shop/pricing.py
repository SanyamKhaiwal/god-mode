from .models import Cart, LineItem


def line_subtotal(line: LineItem) -> float:
    return round(line.item.unit_price * line.qty, 2)


def cart_subtotal(cart: Cart) -> float:
    return round(sum(line_subtotal(l) for l in cart.lines), 2)
